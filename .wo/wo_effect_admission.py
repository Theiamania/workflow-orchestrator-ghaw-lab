"""WO Effect Admission — minimal deterministic governance shim (VALIDATION INSTRUMENT, NOT the WO product).

Two functions, both fail-closed:

  admit      Runs BEFORE any privileged effect. Receives the COMPLETE proposed effect set (gh-aw agent output) and
             the WO effect policy. Decision ALLOW only if every check passes; otherwise DENY or HOLD, exit 1.
             At gh-aw granularity the executor job runs all-or-nothing, so any violation denies the whole set
             (stricter than MR2, which only requires the affected type to be rejected).

  audit-lock Runs at WO compile time over the gh-aw .lock.yml. Verifies that the compiled workflow actually wires the
             admission gate in front of the privileged executor and that no executor that can materialise an
             unauthorised effect holds a credential for it (least privilege).

Exit codes: 0 = ALLOW / AUDIT_PASS ; 1 = DENY / HOLD / AUDIT_FAIL. Any exception → HOLD (exit 1).
Standard library only.
"""
import hashlib, json, re, sys

# gh-aw item types that carry no GitHub effect of their own *provided* their issue-reporting is disabled in the
# compiled workflow (checked by audit-lock through the job permissions, not trusted here).
PASSIVE_TYPES = {"noop", "missing_tool", "missing_data", "report_incomplete"}
PERM_LEVELS = {"none": 0, "read": 1, "write": 2}


class Hold(Exception):
    pass


def _load_json(path, what):
    try:
        with open(path, "rb") as f:
            raw = f.read()
        return json.loads(raw), hashlib.sha256(raw).hexdigest()
    except FileNotFoundError:
        raise Hold(f"{what}_missing")
    except (ValueError, UnicodeDecodeError) as e:
        raise Hold(f"{what}_parse_failure: {e.__class__.__name__}")


def _validate_policy(p):
    if not isinstance(p, dict) or not isinstance(p.get("types"), dict) or not p["types"]:
        raise Hold("policy_invalid: 'types' missing or empty")
    if not isinstance(p.get("bound_repo"), str) or p["bound_repo"].count("/") != 1:
        raise Hold("policy_invalid: 'bound_repo' missing")
    creds = p.get("credentials")
    if not isinstance(creds, dict):
        raise Hold("policy_invalid: 'credentials' missing")
    for t, rule in p["types"].items():
        if not isinstance(rule, dict) or not isinstance(rule.get("max"), int) or rule["max"] < 1:
            raise Hold(f"policy_invalid: {t}.max must be a positive integer")
        cred = rule.get("credential")
        if cred not in creds:
            raise Hold(f"credential_mapping_missing: {t} -> {cred!r}")
        if t == "create_pull_request" and rule.get("fallback_issue") is False:
            if creds[cred].get("issues", "none") != "none":
                raise Hold(f"credential_exceeds_policy: {t} forbids fallback issue but credential {cred} has issues")
    return p


def admit(policy_path, output_path):
    decision = {"decision": None, "reasons": [], "counts": {}, "per_type": {}}
    try:
        policy, policy_sha = _load_json(policy_path, "policy")
        _validate_policy(policy)
        out, out_sha = _load_json(output_path, "agent_output")
        decision.update(policy_sha256=policy_sha, agent_output_sha256=out_sha, policy_id=policy.get("policy_id"))
        items = out.get("items") if isinstance(out, dict) else None
        if not isinstance(items, list):
            raise Hold("agent_output_malformed: 'items' is not a list")
        types = policy["types"]
        for i, it in enumerate(items):
            if not isinstance(it, dict) or not isinstance(it.get("type"), str) or not it["type"]:
                raise Hold(f"agent_output_malformed: item {i} without type")
            t = it["type"]
            decision["counts"][t] = decision["counts"].get(t, 0) + 1
            if t in PASSIVE_TYPES:
                continue
            if t not in types:
                decision["reasons"].append(f"unknown_or_unauthorised_type: {t}")
                continue
            # target binding: an explicit repo must be exactly the bound repo; anything unparsable is ambiguous
            repo = it.get("repo", it.get("target_repo"))
            if repo is not None:
                if not isinstance(repo, str) or repo.count("/") != 1:
                    raise Hold(f"ambiguous_target: item {i} repo={repo!r}")
                if repo.lower() != policy["bound_repo"].lower():
                    decision["reasons"].append(f"target_not_bound: item {i} repo={repo}")
            base = it.get("base", it.get("base_branch"))
            want = types[t].get("base_branch")
            if want is not None and base is not None and base != want:
                decision["reasons"].append(f"target_not_bound: item {i} base={base}")
        errors = out.get("errors") or []
        if not isinstance(errors, list):
            raise Hold("agent_output_malformed: 'errors' is not a list")
        # the collector records over-max truncation as an error line; any such line means the set is incomplete
        for e in errors:
            if "Too many items" in str(e):
                decision["reasons"].append(f"collector_truncated_proposals: {e}")
        for t, rule in types.items():
            n = decision["counts"].get(t, 0)
            if n > rule["max"]:
                decision["per_type"][t] = "DENY_ALL_FOR_TYPE"
                decision["reasons"].append(f"max_exceeded: {t} proposed={n} max={rule['max']}")
            else:
                decision["per_type"][t] = "ALLOW" if n else "NONE_PROPOSED"
        decision["decision"] = "DENY" if decision["reasons"] else "ALLOW"
    except Hold as h:
        decision["decision"] = "HOLD"
        decision["reasons"].append(str(h))
    except Exception as e:  # anything unexpected is a HOLD, never an ALLOW
        decision["decision"] = "HOLD"
        decision["reasons"].append(f"unexpected_error: {e.__class__.__name__}: {e}")
    decision["privileged_effects_authorised"] = decision["decision"] == "ALLOW"
    return decision


# ---------------------------------------------------------------- audit-lock (compile-time, no YAML dependency)

def _jobs(lock_text):
    """Split a compiled lock into {job_name: job_text} (jobs are 2-space indented keys under 'jobs:')."""
    m = re.search(r"^jobs:\n", lock_text, re.M)
    if not m:
        raise Hold("lock_invalid: no jobs")
    body = lock_text[m.end():]
    parts = re.split(r"^  ([A-Za-z_][A-Za-z0-9_-]*):\n", body, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def _job_permissions(job_text):
    m = re.search(r"^    permissions:(.*)\n((?:      .*\n)*)", job_text, re.M)
    if not m:
        return {}
    if m.group(1).strip() in ("{}",):
        return {}
    return dict(re.findall(r"^      ([a-z-]+): (read|write|none)\s*$", m.group(2), re.M))


def audit_lock(lock_path, policy_path, gate_step_name):
    res = {"audit": None, "findings": []}
    try:
        lock = open(lock_path, encoding="utf-8").read()
        policy, _ = _load_json(policy_path, "policy")
        _validate_policy(policy)
        jobs = _jobs(lock)
        res["jobs"] = {j: _job_permissions(t) for j, t in jobs.items()}
        f = res["findings"]
        det, so = jobs.get("detection"), jobs.get("safe_outputs")
        if det is None or so is None:
            raise Hold("lock_invalid: detection or safe_outputs job missing")
        # 1. gate wired before the privileged executor, fail-closed
        if gate_step_name not in det:
            f.append("gate_step_absent_from_detection_job")
        if 'GH_AW_DETECTION_CONTINUE_ON_ERROR: "false"' not in det:
            f.append("detection_not_strict (continue-on-error must be false, otherwise a failed gate does not block)")
        if "needs.detection.result == 'success'" not in so.split("steps:")[0]:
            f.append("safe_outputs_not_conditioned_on_detection_success")
        # 2. visibility of the complete proposed set: gh-aw ceiling must be policy max + 1
        cfg = re.search(r'GH_AW_SAFE_OUTPUTS_HANDLER_CONFIG: "(.*)"\n', so)
        if not cfg:
            raise Hold("lock_invalid: handler config not found")
        handler_cfg = json.loads(cfg.group(1).encode().decode("unicode_escape"))
        res["handler_config_types"] = sorted(handler_cfg)
        for t, rule in policy["types"].items():
            got = (handler_cfg.get(t) or {}).get("max")
            if got != rule["max"] + 1:
                f.append(f"ceiling_not_sentinel: {t} gh-aw max={got} policy max={rule['max']} (need {rule['max'] + 1})")
        for t in handler_cfg:
            if t not in policy["types"] and t not in PASSIVE_TYPES and not t.startswith("create_report_incomplete"):
                f.append(f"handler_enabled_without_policy: {t}")
        # 3. least privilege: no job may hold issues:write when the policy authorises no issue effect, and the
        #    executor job may not hold it when a PR executor with fallback forbidden shares its token
        #    (gh-aw v0.89.21 create_pull_request.cjs L2815-2873 ignores fallback-as-issue on permission denied)
        issue_effects = [t for t in policy["types"] if t == "create_issue"]
        pr_no_fallback = (policy["types"].get("create_pull_request") or {}).get("fallback_issue") is False
        for j, perms in res["jobs"].items():
            if PERM_LEVELS.get(perms.get("issues", "none"), 0) >= 2:
                if not issue_effects:
                    f.append(f"least_privilege_violation: job {j} has issues: write but policy authorises no issue effect")
                elif j == "safe_outputs" and pr_no_fallback:
                    f.append("least_privilege_violation: safe_outputs shares issues: write with a create_pull_request "
                             "executor whose fallback issue is forbidden (split the Operation)")
        # 3b. a DENY fails the detection job; the conclusion job still runs (always()). If it can write issues, every
        #     issue-reporting path that fires on a failed detection must be disabled, or the DENY itself would
        #     materialise an issue effect.
        concl = jobs.get("conclusion", "")
        if PERM_LEVELS.get(res["jobs"].get("conclusion", {}).get("issues", "none"), 0) >= 2:
            if "- name: Log detection run" in concl:
                f.append("deny_path_issue_effect: conclusion.'Log detection run' (threat-detection report-as-issue must be false)")
            for var in ("GH_AW_NOOP_REPORT_AS_ISSUE", "GH_AW_MISSING_TOOL_CREATE_ISSUE", "GH_AW_MISSING_DATA_CREATE_ISSUE",
                        "GH_AW_REPORT_INCOMPLETE_CREATE_ISSUE", "GH_AW_FAILURE_REPORT_AS_ISSUE"):
                for val in re.findall(rf"^\s+{var}: (.*)$", concl, re.M):
                    if val.strip().strip('"') != "false":
                        f.append(f"deny_path_issue_effect: conclusion {var}={val.strip()}")
            if "GH_AW_FAILURE_REPORT_AS_ISSUE" not in concl:
                f.append("deny_path_issue_effect: conclusion failure reporting not explicitly disabled")
        # 4. no stronger credential than the job token may reach the effect executor
        for tok in re.findall(r"github-token: (\$\{\{[^}]*\}\})", so):
            if tok.replace(" ", "") not in ("${{secrets.GITHUB_TOKEN}}", "${{github.token}}"):
                f.append(f"executor_credential_not_pinned: {tok}")
        res["audit"] = "FAIL" if f else "PASS"
    except Hold as h:
        res["audit"] = "FAIL"
        res["findings"].append(str(h))
    except Exception as e:
        res["audit"] = "FAIL"
        res["findings"].append(f"unexpected_error: {e.__class__.__name__}: {e}")
    return res


def main(argv):
    if len(argv) >= 3 and argv[0] == "admit":
        d = admit(argv[1], argv[2])
        print(json.dumps(d, sort_keys=True))
        return 0 if d["decision"] == "ALLOW" else 1
    if len(argv) >= 4 and argv[0] == "audit-lock":
        r = audit_lock(argv[1], argv[2], argv[3])
        print(json.dumps(r, sort_keys=True))
        return 0 if r["audit"] == "PASS" else 1
    print("usage: admit <policy.json> <agent_output.json> [detection_result.json] | "
          "audit-lock <lock.yml> <policy.json> <gate_step_name>", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
