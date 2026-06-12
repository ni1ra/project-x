# Cycle 1 - Docs-OS Birth And Cycle 17 Intake

Date opened: 2026-06-12
Phase: `docs/PHASE_4_language-architecture-pivot.md`
Branch: `phase-v3-safety-boundary`
Status: active

## Objective

Make Project X reviewable and mergeable before starting the next architecture implementation. This cycle restores active docs-os surfaces, hardens the Cycle 16 evidence rail, records PR-flow state, and verifies the local baseline.

## Scope

Owned files for this cycle:

- `docs/PHASE_4_language-architecture-pivot.md`
- `docs/CYCLE_1_docs-os-birth-and-cycle17-intake.md`
- `docs/REPO_CONTROL.md`
- `.gitignore`
- `native/organic_v0.cpp`
- `scripts/verify_cycle16_recurrent_train.sh`
- `scripts/run_organic_wrapper.py`
- `scripts/test_run_organic_wrapper_policy.py`
- `run/artifacts/organic-v0/cycle16_recurrent_text_train.json`

Out of scope for this cycle:

- Implementing BPE, wider recurrent models, or HDC+neural integration.
- Rewriting the 9,985-line native translation unit.
- Deleting or reverting pre-existing dirty-tree artifacts.
- Adding GitHub Actions unless the merge gate proves it is the next blocker.

## Checklist

- [x] Docs-os birth
  - [x] Create active phase doc.
  - [x] Create active cycle doc.
  - [x] Fold forward Cycle 16 strict-reading caveat and Cycle 17 path options.
- [x] Local baseline
  - [x] Run `make test`.
  - [x] Evidence: `organic-v0 native self-test OK`; persistence round-trip hash `29958f0880e662dc`; sleep/wake smoke wrote `/tmp/organic_v0_sleep_wake.6WTHMD/sleep_wake.json`.
- [ ] Evidence rail hardening
  - [x] Add `cycle_intake_id` to recurrent-text artifact output.
  - [x] Add `cycle_intake_id` to canonical Cycle 16 training artifact.
  - [x] Pin canonical Cycle 16 artifact sha256 in the carry-forward rail.
  - [x] Run `timeout 180s scripts/verify_cycle16_recurrent_train.sh`.
  - [x] Confirm generated `run/artifacts/organic-v0/cycle16_recurrent_train_verification.json` reports all required checks passed.
- [ ] Repo-control and PR flow
  - [x] Record active docs pointers and branch state in `REPO_CONTROL`.
  - [x] Verify git/GitHub identity immediately before commit and push.
  - [x] Stage only intentional files.
  - [ ] Commit as `andreashoug <andreashoug@gmail.com>`.
  - [ ] Push branch to origin with upstream.
  - [ ] Open PR to `main`.
- [ ] Wrapper policy hardening
  - [x] Validate default wrapper manifest path against allowed write roots.
  - [x] Add fast denial test for temp-only allowed root without `--manifest-out`.
  - [x] Add fast compatibility test for explicit `--manifest-out` inside allowed root.
  - [x] Run `python3 scripts/test_run_organic_wrapper_policy.py`.
  - [x] Run `python3 -m py_compile scripts/run_organic_wrapper.py scripts/test_run_organic_wrapper_policy.py`.
  - [x] Run `timeout 240s scripts/verify_cycle10_wrapper.sh`.
- [ ] Audit and merge
  - [x] Review final diff.
  - [x] Run required gates.
  - [ ] Merge PR to `main`.
  - [ ] Confirm `main` contains the merge.
  - [ ] Archive this cycle and open Cycle 2.

## Verification Gates

Required before commit:

- `make test`
- `timeout 180s scripts/verify_cycle16_recurrent_train.sh`
- `python3 scripts/test_run_organic_wrapper_policy.py`
- `python3 -m py_compile scripts/run_organic_wrapper.py scripts/test_run_organic_wrapper_policy.py`
- final diff review for secrets and unintended runtime junk

Required before merge:

- Required pre-commit gates above remain green.
- PR exists against `main`.
- If GitHub Actions exist after push, they are green; if absent, record that absence.
- Full carry-forward set from `docs/DO_THIS_NEXT.md` is either green or any failure is fixed before merge.

## Evidence Log

- 2026-06-12: `make test` passed locally in WSL.
- 2026-06-12: canonical Cycle 16 recurrent artifact sha256 after metadata hardening: `44a0091966beea3f09c6dae6481f9ed0bbb63525d5f6e04e8578bd4376d9fa6e`.
- 2026-06-12: `timeout 180s scripts/verify_cycle16_recurrent_train.sh` passed; generated verification reports `all_required_checks_passed:true`, `total_checks:25`, canonical probe NLL `1.49436513`.
- 2026-06-12: `python3 scripts/test_run_organic_wrapper_policy.py` passed; denial and explicit-manifest compatibility cases covered.
- 2026-06-12: `python3 -m py_compile scripts/run_organic_wrapper.py scripts/test_run_organic_wrapper_policy.py` passed.
- 2026-06-12: `timeout 240s scripts/verify_cycle10_wrapper.sh` passed after regenerating historical `/tmp/cycle2.pxstate` and `/tmp/organic_v0_cycle5_fixture.jsonl`; output reported `all_required_checks_passed:true`.
- 2026-06-12: Full carry-forward set from `docs/DO_THIS_NEXT.md` passed: `make test`, Cycle 9, Cycle 10, Cycle 11, Cycle 12 corpus/exposure, Cycle 13 diagnostics, Cycle 14, Cycle 15, Cycle 16 text scaling, and Cycle 16 recurrent train. Notable outputs: Cycle 11 `checks:711`, Cycle 12 corpus `checks:28536`, Cycle 13 `checks:94`, Cycle 14 `checks:71`, Cycle 16 text scaling `checks:837173`, Cycle 16 recurrent `total_checks:25`.
- 2026-06-12: Staged secret scan found no key/token material. `git diff --cached --check` flags preserved generated-output whitespace in Cycle 14/15 transcript artifacts only; code/docs check is clean.

## Open Risks

- Branch is local-only at cycle open; no remote PR exists yet.
- No `.github/` workflows were found, so PR-flow currently depends on local gates unless workflows are added.
- Dirty tree includes substantial pre-existing Cycle 11-15 artifacts. They must be reviewed before staging; broad `git add .` would be a small administrative murder.
