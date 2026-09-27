---
name: WOGHAW E-05 recovery
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
      wo_mode:
        description: interrupt | complete
        required: true
        type: choice
        options: [interrupt, complete]
  push:
    branches: [woghaw-phase2-targets]
if: github.event_name == 'workflow_dispatch'
run-name: "WOGHAW E-05 ${{ inputs.wo_operation_id }} ${{ inputs.wo_attempt_id }} ${{ inputs.wo_mode }}"
permissions:
  contents: read
engine:
  id: claude
  max-turns: 3
  harness:
    max-retries: 0
  env:
    GH_AW_HARNESS_STARTUP_RETRIES: "0"
max-ai-credits: 50
timeout-minutes: 3
tools:
  timeout: 600
  bash:
    - "bash .wo/e05_operation.sh interrupt ATT-E05-1"
    - "bash .wo/e05_operation.sh complete ATT-E05-2"
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
    wo-e05-inert:
      description: "Inert WOGHAW E-05 lab output. It performs no action. Do not use it."
      runs-on: ubuntu-latest
      permissions: {}
      output: "inert"
      steps:
        - name: WO E-05 inert output (no GitHub effect)
          run: echo "WO_E05_INERT_OUTPUT_RECEIVED"
steps:
  - name: WO E-05 workspace probe (pre)
    env:
      WO_OPERATION_ID: ${{ inputs.wo_operation_id }}
      WO_ATTEMPT_ID: ${{ inputs.wo_attempt_id }}
      WO_MODE: ${{ inputs.wo_mode }}
    run: python3 .wo/e05_workspace_probe.py pre
post-steps:
  - name: WO E-05 workspace probe (post)
    if: always()
    env:
      WO_OPERATION_ID: ${{ inputs.wo_operation_id }}
      WO_ATTEMPT_ID: ${{ inputs.wo_attempt_id }}
      WO_MODE: ${{ inputs.wo_mode }}
      WO_EXEC_OUTCOME: ${{ steps.agentic_execution.outcome }}
      WO_EXEC_CONCLUSION: ${{ steps.agentic_execution.conclusion }}
    run: python3 .wo/e05_workspace_probe.py post
jobs:
  wo_evidence:
    needs: [agent]
    if: always() && needs.agent.result != 'skipped'
    runs-on: ubuntu-latest
    permissions: {}
    steps:
      - name: WO E-05 agent job evidence
        env:
          WO_AGENT_RESULT: ${{ needs.agent.result }}
          WO_AGENT_AIC: ${{ needs.agent.outputs.aic }}
          WO_AGENT_MODEL: ${{ needs.agent.outputs.model }}
          WO_ATTEMPT_ID: ${{ inputs.wo_attempt_id }}
        run: |
          echo "::notice title=WO_E05_AGENT_JOB::{\"attempt_id\":\"${WO_ATTEMPT_ID}\",\"agent_result\":\"${WO_AGENT_RESULT}\",\"aic\":\"${WO_AGENT_AIC}\",\"model\":\"${WO_AGENT_MODEL}\",\"run_id\":\"${GITHUB_RUN_ID}\",\"run_attempt\":\"${GITHUB_RUN_ATTEMPT}\"}"
---

# WOGHAW E-05 — recovery operation

This is a controlled validation run. Your only task is to make exactly ONE Bash tool call, and then stop.

Run exactly this command, once, with the Bash tool `timeout` parameter set to 600000:

```
bash .wo/e05_operation.sh ${{ github.event.inputs.wo_mode }} ${{ github.event.inputs.wo_attempt_id }}
```

Rules:

- Do not run any other command. Do not read, create or modify any file yourself.
- Do not run the command in the background. Wait for it to finish.
- Do not retry the command, whatever its result or duration.
- After the command returns, reply with the single word `DONE` and stop.
