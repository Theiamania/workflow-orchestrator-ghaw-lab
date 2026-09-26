---
name: WOGHAW E-01 independent audit (Codex)
on:
  workflow_dispatch:
    inputs:
      pr_number:
        description: "Target PR number"
        required: true
        type: string
      head_sha:
        description: "Expected PR head SHA (the run must be dispatched on the PR branch)"
        required: true
        type: string
      wo_attempt_id:
        description: "WO Attempt id"
        required: true
        type: string
permissions:
  contents: read
  pull-requests: read
engine:
  id: codex
  max-turns: 8
  harness:
    max-retries: 0
  env:
    GH_AW_HARNESS_STARTUP_RETRIES: "0"
max-ai-credits: 150
timeout-minutes: 15
tools:
  bash: true
safe-outputs:
  submit-pull-request-review:
    max: 1
    target: "*"
    allowed-events: [COMMENT]
  threat-detection:
    max-ai-credits: 75
---

# WOGHAW E-01 — independent audit

You are an independent **read-only** auditor. The workspace is checked out at the head of pull request
#${{ github.event.inputs.pr_number }} (expected head SHA `${{ github.event.inputs.head_sha }}`).

1. Run `git rev-parse HEAD` and confirm it equals the expected head SHA. If it does not, the verdict is
   `CHANGES_REQUIRED` with the finding `HEAD_MISMATCH`.
2. Read `fixture/e01/SPEC.md` and `fixture/e01/normalize.py`. Check the implementation against **every**
   numbered rule of the specification. You may run `python3 -m unittest fixture/e01/test_normalize.py`,
   but judge against the specification, not only the tests.
3. Do not modify any file.
4. Call the `submit_pull_request_review` safe-output tool **once**, with `pull_request_number`
   = ${{ github.event.inputs.pr_number }}, event `COMMENT`, and a body in exactly this format:

```text
WO-AUDIT
wo_attempt: ${{ github.event.inputs.wo_attempt_id }}
head_sha: <HEAD you observed>
VERDICT = PASS | CHANGES_REQUIRED
FINDINGS:
- [MATERIAL|MINOR] <rule number> <short description>   (or "- none")
```

Use `CHANGES_REQUIRED` only for a MATERIAL finding (a specification rule is violated). Style or
optional suggestions are MINOR and do not change a PASS verdict.
