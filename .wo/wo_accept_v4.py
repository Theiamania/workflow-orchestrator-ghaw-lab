"""WOGHAW — WO acceptance checker v4 for G-E01-2 (instrument, NOT the WO product). Fail-closed.

Reads the WO journal (a local copy of wo-journal:journal/phase1.jsonl) and GitHub facts (REST; token optional).
Usage: wo_accept_v4.py <journal.jsonl> <phase>        phase ∈ {pre-ready, pre-merge, reuse-probe}
Exit 0 = PERMITTED, 1 = DENIED_HOLD. Any error = DENIED_HOLD.

Rules (v3 R1–R12 carried over, R13–R15 new):
 R1  GitHub environment approval present (woghaw-e10, state approved)
 R2  gate run/job completed success
 R3  exactly one Approval Record for the gate; journal hashes valid; record_id unique
 R4  Approval Record precedes the gate dispatch (journal order and time)
 R5  binding: AR, Gate Request and dispatch inputs = PR 5 / head / base
 R6  AR authority = GitHub approver
 R7  AR validity window current
 R8  dependencies present and exact (tests, audit, pre-acceptance, D08, D09, mitigated lock)
 R9  PR state for the phase (open, not merged, head/base exact, draft = true pre-ready / false pre-merge; main = base)
 R10 AR not consumed
 R11 tests PASS on the exact head (journal + Actions run)
 R12 audit PASS on the exact head, zero material findings (journal + review)
 R13 scope authorises the requested transition (ready; merge of the exact head)
 R14 pre-merge only: draft transition journaled for this gate with head/base unchanged
 R15 PR has no new comments/review comments since the gate request
"""
import datetime, hashlib, json, os, sys, urllib.request

REPO = "Theiamania/workflow-orchestrator-ghaw-lab"
GATE, RUN, ENV = "G-E01-2", 36313022437, "woghaw-e10"
PR, H, B = 5, "736d9e1fb32b1537c0316ee1b16ce5f58c1c0493", "b1bd74d4e1713127053f5ad6d95fabea502b1855"
TESTS_RUN, REVIEW = 36272077796, 5327473236
AUTH = "Theiamania"


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def api(path):
    req = urllib.request.Request("https://api.github.com/repos/" + REPO + path,
                                 headers={"Accept": "application/vnd.github+json",
                                          **({"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"]}
                                             if os.environ.get("GITHUB_TOKEN") else {})})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def main(journal, phase):
    R, facts = {}, {}
    lines = open(journal, encoding="utf-8").read().splitlines()
    recs, ids = [], set()
    for line in lines:
        r = json.loads(line); h = r.pop("content_hash")
        R.setdefault("R3_journal_hashes_valid", True)
        if h != "sha256:" + hashlib.sha256(canon(r).encode()).hexdigest() or r["record_id"] in ids:
            R["R3_journal_hashes_valid"] = False
        ids.add(r["record_id"]); r["content_hash"] = h; recs.append(r)
    by = {r["record_id"]: r for r in recs}
    idx = {r["record_id"]: i for i, r in enumerate(recs)}
    ars = [r for r in recs if r["kind"] == "APPROVAL_RECORD" and r["payload"].get("gate_id") == GATE]
    R["R3_exactly_one_approval_record"] = len(ars) == 1 and R["R3_journal_hashes_valid"]
    ar = ars[0] if ars else None
    arp = ar["payload"] if ar else {}
    gr = [r for r in recs if r["kind"] == "GATE_REQUEST" and r["payload"].get("gate_id") == GATE]
    gd = [r for r in recs if r["kind"] == "GATE_DISPATCH" and r["payload"].get("gate_id") == GATE]
    facts["approval_record"] = ar and {"record_id": ar["record_id"], "content_hash": ar["content_hash"]}

    run = api(f"/actions/runs/{RUN}"); jobs = api(f"/actions/runs/{RUN}/jobs")["jobs"]
    appr = api(f"/actions/runs/{RUN}/approvals")
    ok_appr = [a for a in appr if a["state"] == "approved" and any(e["name"] == ENV for e in a["environments"])]
    facts["github_approvals"] = [{"user": a["user"]["login"], "state": a["state"]} for a in appr]
    R["R1_github_environment_approval_present"] = bool(ok_appr)
    R["R2_gate_job_success"] = run["status"] == "completed" and run["conclusion"] == "success" and \
        all(j["conclusion"] == "success" for j in jobs) and len(jobs) == 1
    R["R4_record_precedes_dispatch"] = bool(ar and gd) and idx[ar["record_id"]] < idx[gd[0]["record_id"]] and \
        arp["created_at"] < run["created_at"]
    t = arp.get("target", {})
    R["R5_binding_pr_head_base"] = bool(ar and gr and gd) and t.get("pr") == PR and t.get("head_sha") == H and \
        t.get("base_sha") == B and gr[0]["payload"]["target"] == {k: t[k] for k in gr[0]["payload"]["target"]} and \
        gd[0]["payload"]["workflow_inputs"] == {"case": "E10B", "gate_id": GATE, "pr_number": str(PR), "expected_head_sha": H} and \
        gd[0]["payload"]["actions_run_id"] == RUN
    R["R6_authority_matches_approver"] = bool(ar) and arp["authority"]["github_login"] == AUTH and \
        AUTH in [a["user"]["login"] for a in ok_appr]
    now = datetime.datetime.now(datetime.timezone.utc)
    v = arp.get("validity", {})
    R["R7_record_current"] = bool(v) and v["from"] <= now.strftime("%Y-%m-%dT%H:%M:%SZ") < v["until"] and v.get("single_use") is True
    d = arp.get("dependencies", {})
    t27, t29, t43 = by.get("J-0027", {}).get("payload", {}), by.get("J-0029", {}).get("payload", {}), by.get("J-0043", {}).get("payload", {})
    R["R8_dependencies_exact"] = d.get("tests") == "J-0027" and d.get("audit") == "J-0029" and d.get("pre_acceptance") == "J-0043" and \
        d.get("D08") == "J-0038" and d.get("D09") == "J-0042" and \
        by.get("J-0042", {}).get("payload", {}).get("REAL_AGENT_EFFECT_ADMISSION") == "PASS" and \
        t43.get("result") == "PASS" and \
        t43.get("checks", {}).get("mitigated_e01_compile", {}).get("impl_lock_sha256") == d.get("mitigated_impl_lock_sha256") and \
        t43.get("checks", {}).get("mitigated_e01_compile", {}).get("audit_lock_result", {}).get("impl") == "PASS 0"
    pr = api(f"/pulls/{PR}"); main_sha = api("/branches/main")["commit"]["sha"]
    facts["pr"] = {"state": pr["state"], "draft": pr["draft"], "merged": pr["merged"], "head": pr["head"]["sha"],
                   "base": pr["base"]["sha"], "comments": pr["comments"], "review_comments": pr["review_comments"]}
    facts["main"] = main_sha
    want_draft = {"pre-ready": True, "pre-merge": False, "reuse-probe": None}[phase]
    R["R9_pr_state_for_phase"] = pr["state"] == "open" and pr["merged"] is False and pr["head"]["sha"] == H and \
        pr["base"]["sha"] == B and main_sha == B and (want_draft is None or pr["draft"] is want_draft)
    consumed = [r["record_id"] for r in recs if r["kind"] in ("APPROVAL_RECORD_CONSUMED", "APPROVAL_CONSUMED")
                and ar and ar["record_id"] in json.dumps(r["payload"])]
    facts["consumption_records"] = consumed
    R["R10_approval_record_not_consumed"] = not consumed
    tr = api(f"/actions/runs/{TESTS_RUN}")
    R["R11_tests_pass_exact_sha"] = t27.get("head_sha") == H and t27.get("result") == "PASS" and \
        tr["head_sha"] == H and tr["conclusion"] == "success"
    rv = api(f"/pulls/{PR}/reviews/{REVIEW}")
    R["R12_audit_pass_exact_sha"] = t29.get("head_sha") == H and t29.get("findings") == [] and rv["commit_id"] == H and \
        "VERDICT = PASS" in rv["body"] and "FINDINGS:\n- none" in rv["body"]
    scope = arp.get("scope", [])
    R["R13_scope_authorises_transition"] = arp.get("draft_transition_authorised") is True and \
        "mark PR #5 ready for review" in scope and f"merge PR #5 exact head {H} into main" in scope
    if phase == "pre-merge":
        dt = [r for r in recs if r["kind"] == "DRAFT_TRANSITION" and r["payload"].get("gate_id") == GATE]
        R["R14_draft_transition_journaled_unchanged_binding"] = len(dt) == 1 and \
            dt[0]["payload"]["after"]["draft"] is False and dt[0]["payload"]["after"]["head_sha"] == H and \
            dt[0]["payload"]["after"]["base_sha"] == B
    R["R15_no_new_comments"] = pr["comments"] == 0 and pr["review_comments"] == 0
    decision = "PERMITTED" if all(R.values()) else "DENIED_HOLD"
    return {"checker": "wo_accept_v4", "phase": phase, "gate_id": GATE, "evaluated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "rules": R, "facts": facts, "acceptance": decision, "mutation_authorised": decision == "PERMITTED"}


if __name__ == "__main__":
    try:
        out = main(sys.argv[1], sys.argv[2])
    except Exception as e:  # any error → hold
        out = {"checker": "wo_accept_v4", "acceptance": "DENIED_HOLD", "error": f"{e.__class__.__name__}: {e}"}
    print(json.dumps(out, sort_keys=True))
    sys.exit(0 if out.get("acceptance") == "PERMITTED" else 1)
