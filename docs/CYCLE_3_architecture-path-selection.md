# Cycle 3 - Architecture Path Selection

Date opened: 2026-06-12
Phase: `docs/PHASE_4_language-architecture-pivot.md`
Branch: `main` after PR #15 merge; next implementation branch TBD
Status: active

## Objective

Choose the first post-Cycle-16 language substrate implementation path and prepare a narrow implementation slice. This cycle starts after GitHub auto-checks are on `main`, so future work has a real hosted gate instead of folklore with a YAML-shaped hole.

## Scope

Owned files for this cycle:

- `docs/PHASE_4_language-architecture-pivot.md`
- `docs/CYCLE_3_architecture-path-selection.md`
- `docs/REPO_CONTROL.md`

Expected next implementation surfaces after selection:

- `native/organic_v0.cpp`
- relevant `scripts/verify_cycle*.sh` rail(s)
- relevant `experience/organic-v0/*` prompt/corpus/config assets
- corresponding `run/artifacts/organic-v0/*` evidence artifacts

Out of scope until the path is selected:

- Implementing BPE/subword tokenization.
- Implementing a wider/deeper recurrent model.
- Implementing HDC+neural integration.

## Checklist

- [ ] Decision setup
  - [ ] Re-read Phase 4 candidate paths A/B/C.
  - [ ] Compare expected learning signal, implementation cost, and evidence quality.
  - [ ] Pick one path without blending three ideas into one heroic swamp.
- [ ] Implementation-slice plan
  - [ ] Name exact native/script/data/doc files for the selected path.
  - [ ] Define the verifier command and artifact schema before coding.
  - [ ] Keep the PR slice small enough for GitHub CI plus local carry-forward proof.
- [ ] Verification plan
  - [ ] Preserve `make test` and wrapper policy CI gates.
  - [ ] Decide which historical carry-forward rail must run locally before merge.
  - [ ] Record any local-only fixture requirements in `REPO_CONTROL`.

## Verification Gates

Required before implementation starts:

- GitHub Actions workflow from Cycle 2 exists on `main`.
- Active docs point to this Cycle 3 file.
- Phase 4 Workstream 3 has a selected implementation path.

## Evidence Log

- 2026-06-12: Cycle 2 added and proved GitHub Actions quick checks on PR #15 before this cycle opened.

## Open Risks

- Cycle 16 proved NLL improvement without coherent English samples; the next path must measure language quality honestly, not merely lower loss.
- Full historical carry-forward remains local/manual until runner-safe fixture hydration exists.
