# Cycle 2 - GitHub Actions Auto-Checks

Date opened: 2026-06-12
Phase: `docs/PHASE_4_language-architecture-pivot.md`
Branch: `codex/project-x-gh-actions`
Status: active

## Objective

Make Project X's PR flow self-verifying on GitHub. Local gates remain useful, but every PR to `main` must get real GitHub auto-checks instead of depending on whoever remembered to run a shell command before lunch. Civilization, barely.

## Scope

Owned files for this cycle:

- `.github/workflows/ci.yml`
- `docs/PHASE_4_language-architecture-pivot.md`
- `docs/CYCLE_2_github-actions-auto-checks.md`
- `docs/REPO_CONTROL.md`
- `docs/past_work/phase_4_language-architecture-pivot/CYCLE_1_docs-os-birth-and-cycle17-intake.md`

Out of scope for this cycle:

- Making the full Cycle 9-16 historical carry-forward chain mandatory in CI.
- Fetching or hydrating ignored corpus/runtime caches on GitHub-hosted runners.
- Changing native model behavior or adding the next language substrate.

## Checklist

- [ ] Docs-os rollover
  - [x] Archive Cycle 1 under `docs/past_work/phase_4_language-architecture-pivot/`.
  - [x] Open this active Cycle 2 for GitHub auto-checks.
  - [ ] Update phase and repo-control state after the PR/checks are proven.
- [ ] GitHub Actions workflow
  - [x] Add `.github/workflows/ci.yml`.
  - [x] Run on `pull_request` to `main`.
  - [x] Run on `push` to `main`.
  - [x] Use portable CI `CXXFLAGS` without `-march=native`.
  - [x] Use shell/Python commands that do not depend on script executable bits.
- [ ] Required CI gates
  - [x] Validate docs control surfaces: manifesto, repo control, exactly one active phase, exactly one active cycle.
  - [x] Build and run `make clean test`.
  - [x] Run wrapper policy py_compile and regression tests.
  - [ ] Confirm the GitHub PR check appears and passes.
- [ ] Local verification
  - [x] Run `make clean test` with CI `CXXFLAGS`.
  - [x] Run wrapper policy py_compile and regression tests.
  - [x] Run the docs control-surface check locally.
  - [x] Run diff whitespace check excluding generated run artifacts.
  - [ ] Review diff for secrets and unintended runtime artifacts.
- [ ] PR and merge
  - [ ] Commit as `andreashoug <andreashoug@gmail.com>`.
  - [ ] Push `codex/project-x-gh-actions`.
  - [ ] Open PR to `main`.
  - [ ] Wait for GitHub auto-checks to pass.
  - [ ] Merge PR to `main` per lain's session authorization.
  - [ ] Delete/close the feature branch and confirm `main` contains the workflow.

## Verification Gates

Required before push:

- `CXXFLAGS="-std=c++20 -O2 -Wall -Wextra -pedantic" make clean test`
- `python3 -m py_compile scripts/run_organic_wrapper.py scripts/test_run_organic_wrapper_policy.py`
- `python3 scripts/test_run_organic_wrapper_policy.py`
- docs control-surface shell check from `.github/workflows/ci.yml`

Required before merge:

- GitHub PR check `quick native/runtime checks` is green.
- Final docs update records check evidence and closes this cycle.
- Staged diff has no secrets, `.env` files, or runtime cache junk.

## Evidence Log

- 2026-06-12: Read current docs state; Cycle 1 remained active after PR #14 merge and recorded GitHub Actions absence.
- 2026-06-12: Yang CI feasibility audit recommended a small Ubuntu workflow and warned against making the full historical carry-forward chain required CI until local-only fixtures are rewritten or hydrated.
- 2026-06-12: `CXXFLAGS="-std=c++20 -O2 -Wall -Wextra -pedantic" make clean test` passed locally; output included native self-test OK, persistence hash `29958f0880e662dc`, and a sleep/wake smoke artifact under `/tmp/organic_v0_sleep_wake.*`.
- 2026-06-12: `python3 -m py_compile scripts/run_organic_wrapper.py scripts/test_run_organic_wrapper_policy.py` and `python3 scripts/test_run_organic_wrapper_policy.py` passed locally.
- 2026-06-12: Local docs control-surface check passed: `docs/MANIFESTO.md`, `docs/REPO_CONTROL.md`, exactly one active `PHASE_*.md`, and exactly one active `CYCLE_*.md`.
- 2026-06-12: `git diff --check -- . ':(exclude)run/artifacts/**'` passed.

## Open Risks

- Full historical carry-forward rails remain local/manual because they rely on ignored corpus/runtime state and old `/tmp` fixtures.
- First PR check run proves the workflow registration path; until that run is green, local evidence is necessary but not sufficient.
