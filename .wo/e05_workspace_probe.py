"""WOGHAW E-05 workspace probe (lab instrument, not the WO product). Deterministic, no inference, no writes.

Runs on the runner, outside the agent sandbox, in the agent job:
  pre  : before the agent step  -> proves the Attempt starts from the durable ref, with no fixture/e05 state
  post : after the agent step, if: always() -> captures the workspace while the runner still exists
Emits one ::notice annotation (readable through the public check-runs API) and writes the same JSON to /tmp.
"""
import datetime, hashlib, json, os, subprocess, sys

phase = sys.argv[1]
ws = os.environ.get("GITHUB_WORKSPACE", ".")


def sh(*a):
    r = subprocess.run(list(a), cwd=ws, capture_output=True, text=True)
    return r.stdout.strip()


files = {}
for rel in ("fixture/e05/recovery.txt", "fixture/e05/marker.txt", "fixture/e05/complete.txt"):
    p = os.path.join(ws, rel)
    if os.path.isfile(p):
        b = open(p, "rb").read()
        files[rel] = {"present": True, "sha256": hashlib.sha256(b).hexdigest(), "content": b.decode("utf-8", "replace")[:200]}
    else:
        files[rel] = {"present": False}
out = {"probe": "wo_e05_workspace_probe", "phase": phase,
       "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "operation_id": os.environ.get("WO_OPERATION_ID"), "attempt_id": os.environ.get("WO_ATTEMPT_ID"),
       "mode": os.environ.get("WO_MODE"), "run_id": os.environ.get("GITHUB_RUN_ID"),
       "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "event": os.environ.get("GITHUB_EVENT_NAME"),
       "head": sh("git", "rev-parse", "HEAD"), "git_status": sh("git", "status", "--porcelain", "--untracked-files=all"),
       "files": files}


def agent_log():
    """Tool calls as recorded by the Claude CLI stream-json log (not the model's prose)."""
    uses, results, final = [], [], None
    try:
        lines = open("/tmp/gh-aw/agent-stdio.log", encoding="utf-8", errors="replace").read().splitlines()
    except OSError as e:
        return {"available": False, "error": e.__class__.__name__}
    for line in lines:
        i = line.find("{")
        if i < 0:
            continue
        try:
            m = json.loads(line[i:])
        except ValueError:
            continue
        if not isinstance(m, dict):
            continue
        if m.get("type") == "result":
            final = {k: m.get(k) for k in ("subtype", "is_error", "num_turns", "duration_ms")}
        for c in (m.get("message") or {}).get("content") or [] if isinstance(m.get("message"), dict) else []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                inp = c.get("input") or {}
                uses.append({"id": c.get("id"), "name": c.get("name"), "command": inp.get("command"),
                             "timeout": inp.get("timeout"), "run_in_background": inp.get("run_in_background")})
            elif c.get("type") == "tool_result":
                body = c.get("content")
                if isinstance(body, list):
                    body = " ".join(x.get("text", "") for x in body if isinstance(x, dict))
                results.append({"tool_use_id": c.get("tool_use_id"), "is_error": c.get("is_error"), "content": str(body)[:240]})
    return {"available": True, "lines": len(lines), "tool_uses": uses, "tool_results": results, "result_message": final}


def small_json(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError) as e:
        return {"unavailable": e.__class__.__name__}


if phase == "post":
    out["agent_step"] = {"outcome": os.environ.get("WO_EXEC_OUTCOME"), "conclusion": os.environ.get("WO_EXEC_CONCLUSION")}
    out["agent_log"] = agent_log()
    out["agent_execution"] = small_json("/tmp/gh-aw/agent_execution.json")
    ps = subprocess.run(["ps", "-eo", "pid,etimes,args"], capture_output=True, text=True).stdout.splitlines()
    out["live_operation_processes"] = [l.strip()[:160] for l in ps if "e05_operation.sh" in l or "sleep 600" in l]
open(f"/tmp/wo_e05_probe_{phase}.json", "w").write(json.dumps(out, sort_keys=True))
print(f"::notice title=WO_E05_WORKSPACE_PROBE_{phase.upper()}::" + json.dumps(out, sort_keys=True, separators=(",", ":")))
