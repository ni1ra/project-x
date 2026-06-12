# Cycle 1 - Subword Bridge Contracts

Date opened: 2026-06-12
Phase: `docs/PHASE_5_subword-to-concept-language-bridge.md`
Branch: `codex/project-x-phase5-plan`
Status: active

## Objective

Repair the Phase 4 docs drift, birth Phase 5, and make the first material Phase 5 implementation slice ready without coding the next substrate yet.

Cycle 1 ends with a reviewable docs-only PR. The next implementation instance should be able to start Cycle 2 without rediscovering the architecture decision, artifact names, verifier commands, or evidence gates.

## Scope

Owned files for this cycle:

- `docs/PHASE_5_subword-to-concept-language-bridge.md`
- `docs/CYCLE_1_subword-bridge-contracts.md`
- `docs/REPO_CONTROL.md`
- `docs/past_work/phase_4_language-architecture-pivot/PHASE_4_language-architecture-pivot.md`
- `docs/past_work/phase_4_language-architecture-pivot/CYCLE_3_architecture-path-selection.md`
- `docs/past_work/phase_4_language-architecture-pivot/CYCLE_2_github-actions-auto-checks.md`

Archived this cycle:

- `docs/PHASE_4_language-architecture-pivot.md` -> `docs/past_work/phase_4_language-architecture-pivot/PHASE_4_language-architecture-pivot.md`
- `docs/CYCLE_3_architecture-path-selection.md` -> `docs/past_work/phase_4_language-architecture-pivot/CYCLE_3_architecture-path-selection.md`

Out of scope:

- Implementing BPE/subword tokenization.
- Changing `native/organic_v0.cpp`.
- Running new language training.
- Creating or editing generated runtime artifacts except by naming the next expected artifacts.

## Current Reality Check

- Local branch at cycle birth: `main`, clean, matching `origin/main`.
- Baseline SHA: `ab6ca30acb31b172af69400458df352c41368d09`.
- PR #16 is merged and is the current `main` head.
- GitHub Actions final main run `27434705825`, job `81093591777`, passed.
- `.github/workflows/ci.yml` exists and uses `actions/checkout@v6`.
- Phase 4 and Cycle 3 were stale because they did not record PR #16/final main CI and still described Cycle 3 as active.

## Checklist

- [x] Reality verification
  - [x] Check git status, branch, local `main`, and `origin/main`.
  - [x] Check recent PR state for PR #15 and PR #16.
  - [x] Check final `main` CI run `27434705825` / job `81093591777`.
  - [x] Confirm `.github/workflows/ci.yml` uses `actions/checkout@v6`.
- [x] Phase 4 drift repair
  - [x] Archive Phase 4 under `docs/past_work/phase_4_language-architecture-pivot/`.
  - [x] Archive Cycle 3 under `docs/past_work/phase_4_language-architecture-pivot/`.
  - [x] Record PR #16 and final `main` CI in archived Phase 4/Cycle 3.
  - [x] Leave incomplete Phase 4 work as superseded, not completed.
- [x] Phase 5 birth
  - [x] Compare Path A/B/C explicitly.
  - [x] Select Path A as the first material diagnostic.
  - [x] Keep Path C as the concept-bridge fallback if subword recurrence still fails language.
  - [x] Record the Cycle 16 baseline and hard negative-space gates.
- [x] Cycle 2 contract
  - [x] Name exact likely files for the next implementation slice.
  - [x] Name exact artifact paths and schemas to introduce.
  - [x] Name local verifier commands and GitHub Actions requirements.
  - [x] Define what must be proven before claiming language progress.
- [ ] PR and gates
  - [ ] Commit as `andreashoug <andreashoug@gmail.com>`.
  - [ ] Open PR from `codex/project-x-phase5-plan` to `main`.
  - [ ] Wait for GitHub Actions quick checks to pass.
  - [ ] Merge only if the current repo instructions authorize merge after green CI.

## Cycle 2 Implementation Contract

Cycle 2 objective: create deterministic BPE/subword vocabulary and corpus/token manifest artifacts while leaving the native recurrent implementation for Cycle 3.

Likely files to add or update:

- `scripts/prepare_phase5_cycle2_bpe.sh`
- `scripts/verify_phase5_cycle2_bpe.sh`
- `experience/organic-v0/phase5_bpe_config_v0.json` with schema `project_x.phase5_bpe_config.v0`
- `experience/organic-v0/phase5_bpe_vocab_v0.json` with schema `project_x.phase5_bpe_vocab.v0`
- `experience/organic-v0/phase5_token_manifest_v0.jsonl` with per-row schema `project_x.phase5_token_manifest_row.v0`
- `run/artifacts/organic-v0/phase5_cycle2_bpe_prepare.json` with schema `project_x.phase5_cycle2_bpe_prepare.v0`
- `run/artifacts/organic-v0/phase5_cycle2_bpe_verification.json` with schema `project_x.phase5_cycle2_bpe_verification.v0`
- `docs/PHASE_5_subword-to-concept-language-bridge.md`
- next active cycle doc, likely `docs/CYCLE_2_subword-vocabulary-and-manifest.md`
- `docs/REPO_CONTROL.md`

Likely existing files to read but not rewrite unless needed:

- `native/organic_v0.cpp`
- `scripts/prepare_cycle16_corpus.sh`
- `scripts/verify_cycle16_text_scaling.sh`
- `scripts/verify_cycle16_recurrent_train.sh`
- `experience/organic-v0/corpus_manifest_v0.jsonl`
- `experience/organic-v0/cycle16_corpus_manifest.jsonl`
- `experience/organic-v0/cycle15_generation_prompts_v0.jsonl`
- `run/artifacts/organic-v0/cycle16_recurrent_text_train.json`
- `run/artifacts/organic-v0/cycle16_best_raw_output.json`
- `run/artifacts/organic-v0/cycle16_reproducibility_audit.json`
- `run/artifacts/organic-v0/cycle16_source_overlap_audit.json`

Required Cycle 2 verifier commands:

```bash
make clean test
python3 -m py_compile scripts/run_organic_wrapper.py scripts/test_run_organic_wrapper_policy.py
python3 scripts/test_run_organic_wrapper_policy.py
bash scripts/verify_cycle16_recurrent_train.sh
bash scripts/prepare_phase5_cycle2_bpe.sh
bash scripts/verify_phase5_cycle2_bpe.sh
git diff --check -- . ':(exclude)run/artifacts/**'
```

GitHub Actions must be green:

- Workflow: `.github/workflows/ci.yml`
- Trigger: PR to `main`
- Job: `quick native/runtime checks`
- Required steps: docs control surfaces, `make clean test`, wrapper policy py_compile/regression

Local-only historical rails:

- `scripts/verify_cycle16_recurrent_train.sh` remains local/manual until ignored corpus/runtime state and long training fixtures are made runner-safe.
- `run/corpus/` and `run/state/` remain local ignored substrate. Do not commit raw corpus payloads or state snapshots.
- Cycle 2 may write tracked manifest/config/artifact summaries only when they are deterministic and bounded.

Cycle 2 acceptance gates:

- BPE vocab and merge table are deterministic from the accepted Cycle 12/Cycle 16 training shards.
- Vocab/config artifact includes seed, algorithm version, max vocab or merge count, minimum frequency rule, source manifest hashes, and sha256.
- Token manifest row includes source row ID/path, original shard sha256, split bucket, token IDs or token-count summary, token hash, vocab hash, accepted/rejected status, and reason.
- Verification independently recomputes vocab/config/token hashes.
- No generated row contains answer templates, semantic labels, expected outputs, or subjective quality scores.
- Negative-space block states the tokenizer is not a language-capability claim.

## Cycle 3 Preview Contract

Cycle 3 objective: add the native subword recurrent train/eval/generation path after Cycle 2 proves deterministic token artifacts.

Likely files to touch:

- `native/organic_v0.cpp`
- `scripts/verify_phase5_cycle3_subword_recurrent.sh`
- `docs/PHASE_5_subword-to-concept-language-bridge.md`
- next active cycle doc
- `docs/REPO_CONTROL.md`

Likely artifacts:

- `run/artifacts/organic-v0/phase5_cycle3_subword_recurrent_text_train.json` with schema `project_x.phase5_subword_recurrent_text_quality.v0`
- `run/artifacts/organic-v0/phase5_cycle3_subword_generation_batch.json` with schema `project_x.phase5_subword_generation_batch.v0`
- `run/artifacts/organic-v0/phase5_cycle3_subword_text_transcript.md`
- `run/artifacts/organic-v0/phase5_cycle3_subword_reproducibility_audit.json` with schema `project_x.phase5_subword_reproducibility_audit.v0`
- `run/artifacts/organic-v0/phase5_cycle3_subword_source_overlap_audit.json` with schema `project_x.phase5_subword_source_overlap_audit.v0`
- `run/artifacts/organic-v0/phase5_cycle3_subword_best_raw_output.json` with schema `project_x.phase5_subword_best_raw_output.v0`
- `run/artifacts/organic-v0/phase5_cycle3_subword_recurrent_train_verification.json` with schema `project_x.phase5_subword_recurrent_train_verification.v0`
- `run/state/organic-v0/snapshots/raphael-local-0001/phase5-subword-recurrent-text-head.pxnn` (ignored local state, referenced by artifacts only)

Required proof before any language-progress claim:

- Probe and holdout NLL reported against Cycle 16, with token-level and char-level comparisons kept separate.
- At least 128 raw generations preserved in a transcript and machine-readable generation batch.
- Fresh-process reproducibility audit passes.
- Source-overlap audit reports near-copy count and thresholds.
- Repetition and prompt-echo metrics are reported.
- Manual coherent-sample audit reports exact pass count and raw sample pointers.
- If coherent correct English remains 0/128, the result is not language progress, even if loss improves.
- If coherent samples improve, the claim is bounded to the audited corpus, prompts, sampler settings, seed, and config.

## Verification Gates For This Cycle

Local commands:

```bash
git status --short --branch
git diff --check -- . ':(exclude)run/artifacts/**'
```

Hosted gate:

- GitHub Actions `quick native/runtime checks` must pass on the planning PR.

No code changed in this cycle, so local native training is not required for the docs-only commit. If `make test` is run anyway, record it as extra evidence, not as a substitute for the hosted PR check.

## Evidence Log

- 2026-06-12: Verified `main` and `origin/main` at `ab6ca30acb31b172af69400458df352c41368d09`.
- 2026-06-12: Verified PR #16 merged and final `main` CI run `27434705825` / job `81093591777` passed.
- 2026-06-12: Verified `.github/workflows/ci.yml` uses `actions/checkout@v6` and runs on PR/push to `main`.
- 2026-06-12: Archived Phase 4/Cycle 3 as superseded by lain's new-phase planning instruction.
- 2026-06-12: Local docs-control count passed: exactly one root `PHASE_*.md` and one root `CYCLE_*.md`.
- 2026-06-12: `CXXFLAGS="-std=c++20 -O2 -Wall -Wextra -pedantic" make clean test` passed in WSL: native self-test OK, persistence round-trip OK, short sleep/wake smoke wrote a `/tmp` artifact.
- 2026-06-12: `python3 -m py_compile scripts/run_organic_wrapper.py scripts/test_run_organic_wrapper_policy.py` passed in WSL.
- 2026-06-12: `python3 scripts/test_run_organic_wrapper_policy.py` passed in WSL.
- 2026-06-12: `git diff --check -- . ':(exclude)run/artifacts/**'` passed.

## Open Risks

- Lower subword NLL can still be another beautiful number attached to useless text. Cycle 3 must not claim language progress without raw sample quality movement.
- BPE can smuggle surface compression while adding no concept structure. Phase 5 treats it as a diagnostic, not a brain.
- Path C is likely necessary if the subword experiment only improves statistics.
