---
name: WOGHAW E-03 budget
on:
  workflow_dispatch:
    inputs:
      wo_operation_id:
        description: WO operation_id
        required: true
        type: string
      wo_attempt_id:
        description: WO attempt_id
        required: true
        type: string
  push:
    branches: [woghaw-phase3-targets]
if: github.event_name == 'workflow_dispatch'
run-name: "WOGHAW E-03 ${{ inputs.wo_operation_id }} ${{ inputs.wo_attempt_id }}"
permissions:
  contents: read
engine:
  id: claude
  model: claude-haiku-4-5
  max-turns: 30
  harness:
    max-retries: 0
  env:
    GH_AW_HARNESS_STARTUP_RETRIES: "0"
max-ai-credits: 12
timeout-minutes: 8
tools:
  bash: false
  cli-proxy: false
  edit: false
  github: false
safe-outputs:
  github-token: ${{ secrets.GITHUB_TOKEN }}
  report-failure-as-issue: false
  report-failed-jobs: false
  noop:
    report-as-issue: false
  missing-tool:
    create-issue: false
  missing-data:
    create-issue: false
  report-incomplete:
    create-issue: false
  threat-detection: false
  jobs:
    wo-inert:
      description: "Inert WOGHAW lab counter. It performs no action other than recording the value."
      runs-on: ubuntu-latest
      permissions: {}
      max: 25
      output: "recorded"
      inputs:
        value:
          description: "Counter value"
          required: true
          type: string
      steps:
        - name: WO inert output (no GitHub effect)
          run: echo "::notice title=WO_E03_INERT::$(jq -c '[.items[] | select(.type == "wo_inert") | .value]' "$GH_AW_AGENT_OUTPUT" 2>/dev/null)"
post-steps:
  - name: WO E-03 resource probe
    if: always()
    env:
      WO_EXEC_OUTCOME: ${{ steps.agentic_execution.outcome }}
    run: python3 .wo/e03_resource_probe.py
jobs:
  wo_evidence:
    needs: [agent]
    if: always() && needs.agent.result != 'skipped'
    runs-on: ubuntu-latest
    permissions: {}
    steps:
      - name: WO E-03 agent job evidence
        env:
          WO_AGENT_RESULT: ${{ needs.agent.result }}
          WO_AGENT_AIC: ${{ needs.agent.outputs.aic }}
          WO_AGENT_MODEL: ${{ needs.agent.outputs.model }}
          WO_ATTEMPT_ID: ${{ inputs.wo_attempt_id }}
        run: echo "::notice title=WO_E03_AGENT_JOB::{\"attempt_id\":\"${WO_ATTEMPT_ID}\",\"agent_result\":\"${WO_AGENT_RESULT}\",\"aic\":\"${WO_AGENT_AIC}\",\"model\":\"${WO_AGENT_MODEL}\"}"
---

# WOGHAW E-03 — budget validation

This is a controlled budget validation run. You have no shell, no file editing and no GitHub tools.

Call the safe-output tool `wo_inert` with `value` set to "1". After it returns, call it again with "2", then "3",
and so on up to "20". Make exactly one tool call per turn and wait for each result before the next call; never put
several calls in the same turn. Do not call any other tool. After the call with "20", reply `DONE`.
