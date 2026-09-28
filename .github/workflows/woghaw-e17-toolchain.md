---
name: WOGHAW E-17 toolchain (codex, remote MCP on the approved Mac)
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
run-name: "WOGHAW E-17 ${{ inputs.wo_operation_id }} ${{ inputs.wo_attempt_id }} codex"
permissions:
  contents: read
engine:
  id: codex
  max-turns: 12
  harness:
    max-retries: 0
  env:
    GH_AW_HARNESS_STARTUP_RETRIES: "0"
max-ai-credits: 45
timeout-minutes: 10
network:
  allowed:
    - defaults
    - "cellular-broader-cut-soil.trycloudflare.com"
tools:
  bash: false
  cli-proxy: false
  edit: false
  github: false
mcp-servers:
  e17toolchain:
    url: "https://cellular-broader-cut-soil.trycloudflare.com/mcp"
    headers:
      Authorization: "Bearer ${{ secrets.WO_E17_BEARER }}"
    allowed: ["build_c", "read_diagnostics"]
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
post-steps:
  - name: WO E-17 resource probe
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
      - name: WO E-17 agent job evidence
        env:
          WO_AGENT_RESULT: ${{ needs.agent.result }}
          WO_AGENT_AIC: ${{ needs.agent.outputs.aic }}
          WO_AGENT_MODEL: ${{ needs.agent.outputs.model }}
          WO_ATTEMPT_ID: ${{ inputs.wo_attempt_id }}
        run: echo "::notice title=WO_E17_AGENT_JOB::{\"attempt_id\":\"${WO_ATTEMPT_ID}\",\"agent_result\":\"${WO_AGENT_RESULT}\",\"aic\":\"${WO_AGENT_AIC}\",\"model\":\"${WO_AGENT_MODEL}\"}"
---

<!-- WOGHAW E-17 (J-0083, J-0114). Materialized from woghaw-e17-toolchain.DRAFT.md with: engine codex, bearer header from
     the lab secret WO_E17_BEARER (no OIDC, no id-token: write), the exact Quick Tunnel hostname, max-ai-credits 45 (<= 50
     including a one-response overshoot), and the same inert safe-job / resource probe / evidence job pattern as E-03. -->

# WOGHAW E-17 — native toolchain through a remote MCP server

You have no shell, no file editing and no GitHub tools. The only tools you may use are the MCP tools `build_c` and
`read_diagnostics` of the server `e17toolchain`. They compile C code on a remote machine with its native toolchain
(`-std=c11 -Wall -Wextra -Werror -c`); nothing is ever executed.

Do exactly this, one tool call per turn:

1. Call `build_c` with the program below, unchanged. It contains defects, so the build will fail.
2. Call `read_diagnostics` with the `build_id` of that failed build.
3. From the compiler diagnostics, correct the defects in the program. Do not change the block between
   `WO-HOST-BEGIN` and `WO-HOST-END`, and keep the program's behaviour (it prints the sum of the array).
4. Call `build_c` with the corrected program. If it still fails, read its diagnostics, correct again and rebuild,
   at most 3 more times.
5. When a build succeeds, reply with one line: `E17_RESULT build_id=<id> builds=<number of build_c calls>` and stop.

Do not call any other tool.

```c
#include <stdio.h>
/* WO-HOST-BEGIN: compiles only for macOS on x86_64 */
#ifdef __APPLE__
#ifdef __x86_64__
#define WO_E17_APPLE_X86_64 1
#endif
#endif
#ifndef WO_E17_APPLE_X86_64
#define WO_E17_APPLE_X86_64 0
#endif
_Static_assert(WO_E17_APPLE_X86_64, "WO_E17 host must be macOS x86_64");
/* WO-HOST-END */

static int sum(const int *v, int n) {
  int total = 0;
  for (int i = 0; i < n; i++) total += v[i];
  return total;
}

int main(void) {
  int values[3] = {1, 2, 3};
  int unused = 7;
  printf("%d\n", sum(values, 3))
  return 0;
}
```
