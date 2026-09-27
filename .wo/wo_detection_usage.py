"""WOGHAW D09 — publish threat-detection usage as a public annotation (instrument; never fails)."""
import json, os
out = {}
for p in ("/tmp/gh-aw/threat-detection/detection_usage.json", "/tmp/gh-aw/threat-detection/detection_usage.jsonl"):
    try:
        out[os.path.basename(p)] = open(p).read()[:1500]
    except OSError:
        out[os.path.basename(p)] = None
print("::notice title=WO_EVIDENCE_DETECTION_USAGE::" + json.dumps(out, ensure_ascii=True).replace("%", "%25").replace("\n", "%0A"))
