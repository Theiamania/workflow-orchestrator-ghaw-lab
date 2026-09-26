---
name: WOGHAW E-01 single correction (Claude)
on:
  workflow_dispatch:
    inputs:
      pr_number:
        description: "Target PR number"
        required: true
        type: string
      findings:
        description: "Material findings to fix"
        required: true
        type: string
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
checkout:
  fetch: ["*"]
  fetch-depth: 0
tools:
  bash: true
  edit:
safe-outputs:
  push-to-pull-request-branch:
    target: "*"
    required-title-prefix: "[woghaw-e01] "
    max: 1
    allowed-files:
      - "fixture/e01/**"
    protected-files: blocked
  threat-detection:
    max-ai-credits: 75
---

# WOGHAW E-01 — single correction

The workspace is checked out on the branch of pull request #${{ github.event.inputs.pr_number }}.
Fix **only** these material findings in `fixture/e01/normalize.py`:

${{ github.event.inputs.findings }}

Modify only `fixture/e01/normalize.py`. Run `python3 -m unittest fixture/e01/test_normalize.py` once,
commit, then call `push_to_pull_request_branch` once with `pull_request_number` =
${{ github.event.inputs.pr_number }}. Do not retry, do not create other outputs.
