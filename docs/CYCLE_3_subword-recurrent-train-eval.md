# Cycle 3 - Subword Recurrent Train Eval

Date opened: 2026-06-12
Phase: `docs/PHASE_5_subword-to-concept-language-bridge.md`
Branch: `main` after PR #18 merge; next implementation branch TBD
Status: active

## Objective

Implement the native subword recurrent train/eval/generation path over the deterministic Cycle 2 token artifacts.

Cycle 3 should test whether subword granularity materially improves the recurrent language rail while preserving the Cycle 16 honesty boundaries. Lower loss alone is not language progress.

## Scope

Likely owned files:

- `native/organic_v0.cpp`
- `scripts/verify_phase5_cycle3_subword_recurrent.sh`
- `docs/PHASE_5_subword-to-concept-language-bridge.md`
- `docs/CYCLE_3_subword-recurrent-train-eval.md`
- `docs/REPO_CONTROL.md`

Required inputs:

- `experience/organic-v0/phase5_bpe_config_v0.json`
- `experience/organic-v0/phase5_bpe_vocab_v0.json`
- `experience/organic-v0/phase5_token_manifest_v0.jsonl`

Likely artifacts:

- `run/artifacts/organic-v0/phase5_cycle3_subword_recurrent_text_train.json`
- `run/artifacts/organic-v0/phase5_cycle3_subword_generation_batch.json`
- `run/artifacts/organic-v0/phase5_cycle3_subword_text_transcript.md`
- `run/artifacts/organic-v0/phase5_cycle3_subword_reproducibility_audit.json`
- `run/artifacts/organic-v0/phase5_cycle3_subword_source_overlap_audit.json`
- `run/artifacts/organic-v0/phase5_cycle3_subword_best_raw_output.json`
- `run/artifacts/organic-v0/phase5_cycle3_subword_recurrent_train_verification.json`

Out of scope:

- Rewriting Cycle 12/Cycle 16 corpus manifests.
- Rebuilding BPE artifacts unless Cycle 2 verifier proves a bug.
- Claiming language progress from token-level metrics alone.
- Adding templates, parser dispatch, pretrained calls, RAG, semantic labels, expected outputs, or subjective self-scores.

## Checklist

- [ ] Native subword recurrent path
  - [ ] Load Cycle 2 vocab/config/token manifest with explicit architecture and vocab hashes.
  - [ ] Train/eval over token IDs while preserving source IDs, splits, and artifact provenance.
  - [ ] Persist and reload a subword recurrent state with architecture tag and vocab hash.
- [ ] Generation and audits
  - [ ] Preserve at least 128 raw generations with sampler seeds and prompt IDs.
  - [ ] Run fresh-process reproducibility audit.
  - [ ] Run source-overlap, repetition, prompt-echo, and coherent-sample audits.
  - [ ] Record raw failures without cleanup or transcript selection.
- [ ] Gates
  - [ ] `make clean test`
  - [ ] `python3 -m py_compile scripts/run_organic_wrapper.py scripts/test_run_organic_wrapper_policy.py`
  - [ ] `python3 scripts/test_run_organic_wrapper_policy.py`
  - [ ] `bash scripts/verify_cycle16_recurrent_train.sh`
  - [ ] `bash scripts/verify_phase5_cycle2_bpe.sh`
  - [ ] `bash scripts/verify_phase5_cycle3_subword_recurrent.sh`
  - [ ] `git diff --check -- . ':(exclude)run/artifacts/**'`
  - [ ] high-risk secret-pattern scan
  - [ ] GitHub Actions `quick native/runtime checks` passes on PR to `main`

## Evidence Boundary

Cycle 3 may prove a subword recurrent path trains, persists, reloads, and emits auditable raw generations. A language-progress claim requires both loss movement and coherent-sample movement against Cycle 16. If coherent correct English remains `0/128`, the result is diagnostic infrastructure or statistical improvement only.

## First Command

```bash
bash scripts/verify_phase5_cycle2_bpe.sh
```
