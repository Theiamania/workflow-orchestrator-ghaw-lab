"""WOGHAW E-03 runner-side resource probe (lab instrument; deterministic, no writes). Runs in the agent job after the
agent step (if: always()). Summarises the AWF api-proxy accounting and every budget-enforcement signal it can see and
emits one ::notice annotation (public check-run API)."""
import glob, json, os, re

B = "/tmp/gh-aw"
def jl(p):
    out = []
    for f in glob.glob(p):
        for l in open(f, errors="replace"):
            try: out.append(json.loads(l))
            except ValueError: pass
    return out

usage = [u for u in jl(f"{B}/sandbox/firewall/logs/api-proxy-logs/token-usage.jsonl") if u.get("event") == "token_usage"]
tracker = jl(f"{B}/sandbox/firewall/logs/api-proxy-logs/token-tracker-audit.jsonl")
audit = jl(f"{B}/sandbox/firewall/logs/audit.jsonl")
budget_events = [a for a in audit if re.search(r"budget_exceeded|max_ai_credits_exceeded", json.dumps(a))]
events = jl(f"{B}/sandbox/firewall/logs/api-proxy-logs/*events*.jsonl")
stdio = open(f"{B}/agent-stdio.log", errors="replace").read() if os.path.exists(f"{B}/agent-stdio.log") else ""
m = re.findall(r"maximum ai credits exceeded[^\n]{0,80}", stdio, re.I)
non200 = [{k: t.get(k) for k in ("event", "status", "result", "model")} for t in tracker if t.get("status") not in (None, 200) or t.get("result") not in (None, "ok")]
out = {"probe": "wo_e03_resource_probe", "agent_step": {"outcome": os.environ.get("WO_EXEC_OUTCOME")},
       "requests": [{"i": i, "model": u.get("model"), "status": u.get("status"), "in": u.get("input_tokens"), "out": u.get("output_tokens"),
                     "cr": u.get("cache_read_tokens"), "cw": u.get("cache_write_tokens"), "aic": u.get("ai_credits_this_response"), "total": u.get("ai_credits_total")} for i, u in enumerate(usage)],
       "aic_total_last": usage[-1].get("ai_credits_total") if usage else None,
       "tracker_non_ok": non200[:10], "budget_events_in_audit": [json.dumps(b)[:300] for b in budget_events[:5]],
       "proxy_event_files": [json.dumps(e)[:300] for e in events[:5]],
       "stdio_budget_messages": m[:3]}
print("::notice title=WO_E03_RESOURCE_PROBE::" + json.dumps(out, separators=(",", ":")))
