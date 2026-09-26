---
name: WOGHAW E-01 implementation (Claude)
on:
  workflow_dispatch:
    inputs:
      wo_attempt_id:
        description: "WO Attempt id"
        required: true
        type: string
permissions:
  contents: read
engine:
  id: claude
  max-turns: 8
  harness:
    max-retries: 0
  env:
    GH_AW_HARNESS_STARTUP_RETRIES: "0"
max-ai-credits: 150
timeout-minutes: 15
tools:
  bash: true
  edit:
safe-outputs:
  create-pull-request:
    max: 1
    allowed-files:
      - "fixture/e01/**"
    protected-files: blocked
    fallback-as-issue: false
    base-branch: main
    title-prefix: "[woghaw-e01] "
  threat-detection:
    max-ai-credits: 75
---

# WOGHAW E-01 — implement the fixture

Read `fixture/e01/SPEC.md`. Implement `slugify` in `fixture/e01/normalize.py` exactly as specified,
using only the Python standard library.

Rules:

- Modify **only** `fixture/e01/normalize.py`. Do not modify `SPEC.md`, `test_normalize.py` or any other file.
- Run `python3 -m unittest fixture/e01/test_normalize.py` once to check your work.
- Commit the change on a new local branch named `e01-impl-${{ github.run_id }}`.
- Then call the `create_pull_request` safe-output tool once, title `implement slugify`, body
  `WO E-01 implementation. WO attempt: ${{ github.event.inputs.wo_attempt_id }}`.
- Do not retry, do not create other outputs.
