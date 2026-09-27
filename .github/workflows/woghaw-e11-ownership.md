---
name: WOGHAW E-11 ownership
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
run-name: "WOGHAW E-11 ${{ inputs.wo_operation_id }} ${{ inputs.wo_attempt_id }}"
concurrency:
  group: "woghaw-e11-${{ github.run_id }}"
  cancel-in-progress: false
permissions:
  contents: read
engine:
  id: claude
  max-turns: 2
  harness:
    max-retries: 0
  env:
    GH_AW_HARNESS_STARTUP_RETRIES: "0"
max-ai-credits: 25
timeout-minutes: 5
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
      description: "Inert WOGHAW lab output. It performs no action. Do not use it."
      runs-on: ubuntu-latest
      permissions: {}
      output: "inert"
      steps:
        - name: WO inert output (no GitHub effect)
          run: echo "WO_INERT_OUTPUT_RECEIVED"
jobs:
  wo_owner_acquire:
    needs: [pre_activation]
    if: needs.pre_activation.outputs.activated == 'true'
    runs-on: ubuntu-latest
    permissions:
      contents: write
    outputs:
      lease_commit: ${{ steps.acquire.outputs.lease_commit }}
      acquired_at: ${{ steps.acquire.outputs.acquired_at }}
    steps:
      - name: WO checkout (lease script only)
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          sparse-checkout: .wo
          persist-credentials: false
      - name: WO ownership acquire (CAS, before any inference)
        id: acquire
        env:
          GH_TOKEN: ${{ github.token }}
          WO_OPERATION_ID: ${{ inputs.wo_operation_id }}
          WO_ATTEMPT_ID: ${{ inputs.wo_attempt_id }}
        run: bash .wo/e11_lease.sh acquire
  wo_owner_finish:
    needs: [agent, wo_owner_acquire]
    if: always() && needs.wo_owner_acquire.result == 'success'
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: WO checkout (lease script only)
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          sparse-checkout: .wo
          persist-credentials: false
      - name: WO mutation boundary + release (atomic, lease-fenced) or release only
        env:
          GH_TOKEN: ${{ github.token }}
          WO_OPERATION_ID: ${{ inputs.wo_operation_id }}
          WO_ATTEMPT_ID: ${{ inputs.wo_attempt_id }}
          WO_LEASE_COMMIT: ${{ needs.wo_owner_acquire.outputs.lease_commit }}
          WO_ACQUIRED_AT: ${{ needs.wo_owner_acquire.outputs.acquired_at }}
          WO_AGENT_RESULT: ${{ needs.agent.result }}
          WO_AGENT_AIC: ${{ needs.agent.outputs.aic }}
        run: |
          echo "::notice title=WO_E11_AGENT_JOB::{\"attempt_id\":\"${WO_ATTEMPT_ID}\",\"agent_result\":\"${WO_AGENT_RESULT}\",\"aic\":\"${WO_AGENT_AIC}\"}"
          if [ "$WO_AGENT_RESULT" = "success" ]; then bash .wo/e11_lease.sh finish; else bash .wo/e11_lease.sh release; fi
---

# WOGHAW E-11 — runtime ownership probe

This is a controlled validation run. Do not use any tool and do not call any safe output.

Reply with the single word `DONE` and stop.
