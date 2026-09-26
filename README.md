# workflow-orchestrator-ghaw-lab

Private, disposable laboratory for WOGHAW-V01 (WO gh-aw architecture hypothesis).

- 2026-09-26: renamed from `workflow-orchestrator-woghaw-e16-20260926`. The E-16 files
  (`e16_*`, `upstream/`, `results/`, `.github/workflows/e16.yml`) are inert leftovers;
  all E-16 evidence is preserved in the canonical repo under `docs/design/ghaw/evidence/e16/`.
- FASE 1 (D-07): `.github/workflows/woghaw-e09-guard.md` (+ compiled `.lock.yml`), gh-aw v0.89.21.

- 2026-09-26: made **PUBLIC** by explicit human authority for validation only (E-10 needs
  environment required reviewers / branch protection, unavailable for private repos on GitHub Free).
  No reversibility is assumed: at the end of WOGHAW-V01 the lab is to be deleted, not made private again.
- E-10: `.github/workflows/woghaw-e10-gate.yml` (deterministic, no AI) reaches environment `woghaw-e10`.

- FASE 1 E-04/E-01 (2026-09-26): `woghaw-e04-boundary`, `woghaw-e01-impl` (Claude), `woghaw-e01-audit` (Codex),
  `woghaw-e01-fix` (Claude, only if materially needed), `woghaw-e01-tests.yml` (deterministic, no provider secrets).
  All billable workflows are `workflow_dispatch` only; agent jobs are read-only; effects only via safe outputs.
  Fixture: `fixture/e01/` (synthetic `slugify`, stdlib only).

Repository secrets (names only): ANTHROPIC_API_KEY, OPENAI_API_KEY (lab only; to be revoked at the end of V01).
No WO product code. No consumer-project code. No private data.
