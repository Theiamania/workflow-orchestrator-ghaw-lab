---
name: WOGHAW E-09 pre-inference guard
on:
  workflow_dispatch:
    inputs:
      synthetic_precondition:
        description: "WO synthetic precondition (true = allow, false = deny)"
        required: true
        type: choice
        options: ["false", "true"]
  steps:
    - name: WO deterministic guard
      id: wo_guard
      env:
        WO_PRECONDITION: ${{ github.event.inputs.synthetic_precondition }}
      run: |
        echo "wo_guard synthetic_precondition=${WO_PRECONDITION}"
        if [ "${WO_PRECONDITION}" = "true" ]; then
          echo "wo_guard decision=ALLOW"
        else
          echo "wo_guard decision=DENY"
          exit 1
        fi
if: needs.pre_activation.outputs.wo_guard_result == 'success'
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
safe-outputs:
  noop:
    max: 1
  threat-detection:
    max-ai-credits: 75
---

# WOGHAW E-09 guard probe

Reply with a single `noop` safe output stating "E-09 positive path reached". Do not read or modify any files.
