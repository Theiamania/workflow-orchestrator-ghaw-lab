"""WOGHAW D09 — publish the real agent proposals as public annotations (instrument; reads only, never fails the job)."""
import hashlib, json, os
def sha(p):
    try:
        b = open(p, "rb").read(); return hashlib.sha256(b).hexdigest(), len(b)
    except OSError:
        return None, None
def notice(title, obj):
    print(f"::notice title={title}::" + json.dumps(obj, sort_keys=True, ensure_ascii=True).replace("%", "%25").replace("\n", "%0A"))
ao, raw = "/tmp/gh-aw/agent_output.json", "/tmp/gh-aw/safeoutputs.jsonl"
h_ao, n_ao = sha(ao); h_raw, n_raw = sha(raw)
collected, raw_items = {}, []
try:
    d = json.load(open(ao)); items = d.get("items", [])
    for it in items: collected[it.get("type")] = collected.get(it.get("type"), 0) + 1
    errors = d.get("errors", [])
except Exception as e:
    items, errors = [], [f"unreadable: {e.__class__.__name__}"]
try:
    for line in open(raw, encoding="utf-8"):
        if line.strip():
            try:
                it = json.loads(line); raw_items.append({"type": it.get("type"), "title": str(it.get("title", ""))[:80]})
            except ValueError:
                raw_items.append({"type": "<unparsable>"})
except OSError:
    pass
raw_counts = {}
for it in raw_items: raw_counts[it["type"]] = raw_counts.get(it["type"], 0) + 1
notice("WO_EVIDENCE_AGENT", {"agent_result": os.environ.get("WO_AGENT_RESULT"), "model": os.environ.get("WO_AGENT_MODEL"),
       "agent_aic": os.environ.get("WO_AGENT_AIC"), "output_types": os.environ.get("WO_OUTPUT_TYPES"),
       "has_patch": os.environ.get("WO_HAS_PATCH"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT")})
notice("WO_EVIDENCE_OUTPUTS", {"agent_output_sha256": h_ao, "agent_output_bytes": n_ao, "collected_counts": collected,
       "collector_errors": errors[:5], "raw_sha256": h_raw, "raw_bytes": n_raw, "raw_counts": raw_counts})
notice("WO_EVIDENCE_RAW_ITEMS", raw_items[:10])
