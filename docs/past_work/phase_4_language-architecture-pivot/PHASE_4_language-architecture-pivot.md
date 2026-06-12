# Phase 4 - Language Architecture Pivot

Date opened: 2026-06-12
Date archived: 2026-06-12
Branch: opened on `codex/project-x-gh-actions`; archived from `codex/project-x-phase5-plan` after `main` reached `ab6ca30acb31b172af69400458df352c41368d09`
Status: archived, superseded by lain's 2026-06-12 new-phase planning instruction; not fully completed

## Goal

Move Project X from the completed Phase v3 safety-boundary / corpus-scaling run into a docs-governed architecture pivot. The immediate objective is to make the repo reviewable, mergeable, and evidence-honest before adding the next language substrate.

Cycle 16's strict claim is the baseline: the char-level recurrent substrate improved probe/holdout NLL sharply at the tested training depth, but still produced 0/128 fully correct coherent English samples. The honest read is "insufficient at this training depth and architecture shape", not a proof that the general architecture class is mathematically dead.

Supersession note: Phase 4 intentionally closes with unchecked boxes. Lain explicitly asked for a new Phase 5 on 2026-06-12. The unchecked items below are not being blessed as complete; they are either carried into Phase 5 or left as historical gaps.

## Workstream 1: Docs-OS And PR Flow

- [ ] 1.1 Restore active docs control surfaces.
  - [x] Create one active phase doc at docs root.
  - [x] Create one active cycle doc at docs root.
  - [x] Fold forward Cycle 16 evidence and Cycle 17 pivot options from `docs/DO_THIS_NEXT.md`.
  - [x] Archive Cycle 1 after PR #14 merge.
  - [ ] Archive or demote legacy live-plan surfaces once the active phase/cycle are merged.
- [ ] 1.2 Make branch/PR state explicit.
  - [x] Record branch state in `docs/REPO_CONTROL.md`.
  - [x] Push `phase-v3-safety-boundary` to `origin`.
  - [x] Open PR #14 to `main`.
  - [x] Keep PR reviewable with cycle-scoped commits and evidence.
- [ ] 1.3 Establish merge gates.
  - [x] Run `make test`.
  - [x] Run Cycle 16 recurrent train carry-forward rail after hardening.
  - [x] Run Cycle 10 wrapper verifier after wrapper hardening.
  - [x] Run full required carry-forward rail set before merge.
  - [x] Record final gate evidence in the cycle doc before closing.
- [ ] 1.4 Establish GitHub auto-checks.
  - [x] Add a GitHub Actions workflow for PRs to `main` and pushes to `main`.
  - [x] Include a portable native smoke gate with CI-safe `CXXFLAGS`.
  - [x] Include wrapper policy regression and py_compile gates.
  - [x] Include docs control-surface validation.
  - [x] Confirm the GitHub PR check runs and passes.

## Workstream 2: Evidence-Rail Hardening

- [ ] 2.1 Pin canonical Cycle 16 evidence.
  - [x] Add `cycle_intake_id` to the canonical Cycle 16 recurrent training artifact.
  - [x] Emit `cycle_intake_id` from future recurrent-text artifacts.
  - [x] Pin the canonical Cycle 16 training artifact sha256 in `scripts/verify_cycle16_recurrent_train.sh`.
  - [x] Rerun the hardened rail and record the new verification artifact.
- [ ] 2.2 Preserve generated-evidence discipline.
  - [x] Ignore `.playwright-mcp/` scratch output.
  - [x] Harden wrapper default-manifest writes against temp-only allowed roots.
  - [ ] Review dirty tree before staging so prior work is not laundered blindly.
  - [ ] Confirm tracked artifacts are intentional evidence, not runtime junk.

## Workstream 3: Architecture Decision And First Implementation Slice

- [ ] 3.1 Decide the next substrate path.
  - [x] Record candidate path A: BPE / subword tokens plus existing GRU.
  - [x] Record candidate path B: wider/deeper recurrent char model.
  - [x] Record candidate path C: HDC concept substrate plus neural text head.
  - [ ] Pick the first implementation path after Cycle 1 merge gates are green.
- [ ] 3.2 Prepare the implementation cycle.
  - [ ] Write Cycle 2 from the selected architecture path.
  - [ ] Include exact files, artifact schemas, and verifier gates before coding.
  - [ ] Keep implementation PR separate from docs/rail hardening unless trivial.

## Workstream 4: Production-Readiness Checks

- [ ] 4.1 Local target proof.
  - [x] Confirm native build/test works in WSL via `make test`.
  - [x] Confirm hardened Cycle 10 and Cycle 16 carry-forward rails run under the local target environment.
  - [ ] Record runtime assumptions and non-prod nature in `REPO_CONTROL`.
- [ ] 4.2 Release proof.
  - [x] Push Phase 3 safety-boundary branch and open PR #14.
  - [x] Merge PR #14 to `main` after green local gates per lain's authorization for this repo/session.
  - [x] Confirm `main` contains the PR #14 merge commit.
  - [x] Push CI branch and open PR #15.
  - [x] Verify GitHub Actions auto-checks pass on PR #15.
  - [x] Merge CI PR #15 to `main` and confirm `main` contains the workflow.
  - [x] Merge PR #16 (`codex/project-x-ci-node24`) to `main` and confirm `.github/workflows/ci.yml` uses `actions/checkout@v6`.
  - [x] Confirm final `main` push CI passed on run `27434705825`, job `81093591777`, SHA `ab6ca30acb31b172af69400458df352c41368d09`.

## Tail: Audit, Bug Search, Fixes, Closure

- [x] Audit current diff for unintended file churn, secrets, and stale artifacts.
- [ ] Run bug search over touched scripts/native code.
- [ ] Fix any audit findings before merge.
- [x] Close Cycle 1 with evidence and archive it under `docs/past_work/phase_4_language-architecture-pivot/`.
- [x] Open Cycle 2 for GitHub Actions auto-checks.
- [x] Close Cycle 2 after GitHub checks are green and archive it under `docs/past_work/phase_4_language-architecture-pivot/`.
- [x] Open Cycle 3 for architecture path selection.

## Candidate Architecture Paths

Path A: BPE / subword tokens plus existing GRU. Cheapest diagnostic for whether character granularity is the immediate bottleneck.

Path B: wider or deeper recurrent char model. Lowest conceptual leverage; useful only if the goal is to test capacity before changing tokenization or substrate.

Path C: HDC concept substrate plus neural text head. Most manifesto-aligned because Project X's long-term rule is concepts before language.

## Current Evidence Baseline

- Cycle 16 train shards: 7,990; train chars: 552,098.
- Cycle 16 probe NLL: 1.494365; holdout NLL: 1.475701.
- Fresh-process regeneration: 128/128 bit-exact.
- Source-overlap audit: 0/128 near-copies.
- Manual sample audit: 0/128 correct coherent English.
- Local smoke on 2026-06-12: `make test` passed.
- GitHub Actions final Phase 4 proof: PR #16 merged on 2026-06-12; final `main` CI run `27434705825` / job `81093591777` passed with checkout `actions/checkout@v6`.
