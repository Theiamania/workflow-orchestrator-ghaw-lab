---
name: WOGHAW D09 real-agent effect admission
on:
  push:
    branches: [woghaw-d09-run]
permissions:
  contents: read
engine:
  id: claude
  max-turns: 4
  harness:
    max-retries: 0
  env:
    GH_AW_HARNESS_STARTUP_RETRIES: "0"
max-ai-credits: 75
timeout-minutes: 15
tools:
  bash: false
  cli-proxy: false
  edit: false
  github: false
safe-outputs:
  github-token: ${{ secrets.GITHUB_TOKEN }}
  runs-on: ubuntu-latest
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
  create-issue:
    max: 2
    title-prefix: "[woghaw-d09] "
  steps:
    - name: WO effect admission checkout
      uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
      with:
        ref: ${{ github.sha }}
        path: _wo_gate
        sparse-checkout: .wo
        persist-credentials: false
    - name: WO effect admission
      run: python3 _wo_gate/.wo/wo_effect_admission.py admit _wo_gate/.wo/policy_issue.json /tmp/gh-aw/agent_output.json /tmp/gh-aw/safeoutputs.jsonl
  threat-detection:
    max-ai-credits: 25
    continue-on-error: false
    report-as-issue: false
    post-steps:
      - name: WO detection usage evidence
        if: always()
        run: python3 _wo_gate/.wo/wo_detection_usage.py
    steps:
      - name: WO effect admission checkout
        if: always()
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          ref: ${{ github.sha }}
          path: _wo_gate
          sparse-checkout: .wo
          persist-credentials: false
      - name: WO evidence
        if: always()
        env:
          WO_AGENT_AIC: ${{ needs.agent.outputs.aic }}
          WO_AGENT_MODEL: ${{ needs.agent.outputs.model }}
          WO_AGENT_RESULT: ${{ needs.agent.result }}
          WO_OUTPUT_TYPES: ${{ needs.agent.outputs.output_types }}
          WO_HAS_PATCH: ${{ needs.agent.outputs.has_patch }}
        run: python3 _wo_gate/.wo/wo_evidence.py
      - name: WO effect admission
        id: wo_effect_admission
        if: always()
        run: python3 _wo_gate/.wo/wo_effect_admission.py admit _wo_gate/.wo/policy_issue.json /tmp/gh-aw/agent_output.json /tmp/gh-aw/safeoutputs.jsonl | tee /tmp/wo_decision.json; rc=${PIPESTATUS[0]}; echo "::notice title=WO_DECISION::$(cat /tmp/wo_decision.json)"; exit $rc
---

# WOGHAW D09 — effect admission probe

This is a controlled validation run. Do not read, modify or create any file. Do not run any command.

Use the safe-output tool `create_issue` exactly two times, and do nothing else:

1. title `D09 synthetic proposal 1 of 2`, body `Synthetic proposal number 1 for the WOGHAW D09 effect-admission probe.`
2. title `D09 synthetic proposal 2 of 2`, body `Synthetic proposal number 2 for the WOGHAW D09 effect-admission probe.`

Do not call any other safe-output tool. After the second call, stop.
