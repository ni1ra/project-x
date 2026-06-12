# Cycle 2 - Subword Vocabulary And Manifest

Date opened: 2026-06-12
Phase: `docs/PHASE_5_subword-to-concept-language-bridge.md`
Branch: `codex/project-x-phase5-cycle2`
Status: active

## Objective

Create deterministic BPE/subword vocabulary and token-manifest infrastructure from the existing accepted Cycle 12/Cycle 16 corpus manifests.

This cycle does not implement the recurrent subword model. It prepares auditable token artifacts so Cycle 3 can train against stable vocabulary and manifest contracts without rewriting historical corpus evidence.

## Scope

Owned files for this cycle:

- `scripts/prepare_phase5_cycle2_bpe.sh`
- `scripts/verify_phase5_cycle2_bpe.sh`
- `experience/organic-v0/phase5_bpe_config_v0.json`
- `experience/organic-v0/phase5_bpe_vocab_v0.json`
- `experience/organic-v0/phase5_token_manifest_v0.jsonl`
- `run/artifacts/organic-v0/phase5_cycle2_bpe_prepare.json`
- `run/artifacts/organic-v0/phase5_cycle2_bpe_verification.json`
- `docs/PHASE_5_subword-to-concept-language-bridge.md`
- `docs/CYCLE_2_subword-vocabulary-and-manifest.md`
- `docs/REPO_CONTROL.md`

Out of scope:

- Changing `native/organic_v0.cpp`.
- Training or evaluating a subword recurrent model.
- Claiming language progress.
- Rewriting Cycle 12/Cycle 16 corpus manifests.
- Committing raw corpus payloads under `run/corpus/` or state snapshots under `run/state/`.

## Checklist

- [x] Tokenizer preparation rail
  - [x] Add `scripts/prepare_phase5_cycle2_bpe.sh`.
  - [x] Read accepted train shards from existing manifests without rewriting them.
  - [x] Emit deterministic config and vocab artifacts with stable hashes.
  - [x] Emit token manifest rows preserving source IDs, split buckets, shard hashes, token counts, token hashes, vocab hash, and config hash.
- [x] Tokenizer verification rail
  - [x] Add `scripts/verify_phase5_cycle2_bpe.sh`.
  - [x] Independently recompute config, vocab, token row hashes, and aggregate counts.
  - [x] Reject forbidden semantic labels, expected outputs, subjective scores, and answer fixtures.
  - [x] Emit `run/artifacts/organic-v0/phase5_cycle2_bpe_verification.json`.
- [x] Docs and control surfaces
  - [x] Record Cycle 1 archive and PR #17 merge/main CI evidence.
  - [x] Update Phase 5 Workstream 2 checkboxes only where machine evidence exists.
  - [x] Add REPO_CONTROL rows for every new tracked script, experience artifact, and run artifact.
  - [x] Confirm exactly one root phase and cycle.
- [ ] Gates
  - [x] `make clean test`
  - [x] `python3 -m py_compile scripts/run_organic_wrapper.py scripts/test_run_organic_wrapper_policy.py`
  - [x] `python3 scripts/test_run_organic_wrapper_policy.py`
  - [x] `bash scripts/verify_cycle16_recurrent_train.sh`
  - [x] `bash scripts/prepare_phase5_cycle2_bpe.sh`
  - [x] `bash scripts/verify_phase5_cycle2_bpe.sh`
  - [x] `git diff --check -- . ':(exclude)run/artifacts/**'`
  - [x] staged diff review
  - [x] high-risk secret-pattern scan
  - [ ] GitHub Actions `quick native/runtime checks` passes on PR to `main`

## Required Artifact Schemas

- `project_x.phase5_bpe_config.v0`
- `project_x.phase5_bpe_vocab.v0`
- `project_x.phase5_token_manifest_row.v0`
- `project_x.phase5_cycle2_bpe_prepare.v0`
- `project_x.phase5_cycle2_bpe_verification.v0`

## Acceptance Boundaries

Cycle 2 proves only that deterministic tokenization artifacts can be prepared and verified while preserving raw corpus identity. It does not prove language improvement, concept formation, coherent generation, better NLL, or model behavior.

Any future language claim belongs to Cycle 3 or later and must include raw generations, reproducibility, source-overlap, repetition/prompt-echo, and coherent-sample audits.

## Evidence Log

- 2026-06-12: PR #17 merged to `main` at `ee166d487e7a4f39a47f07a6885eeeaf80e643cd`; final `main` push CI run `27443470633` passed.
- 2026-06-12: Cycle 2 branch opened from updated `main`: `codex/project-x-phase5-cycle2`.
- 2026-06-12: `bash scripts/prepare_phase5_cycle2_bpe.sh` passed; emitted vocab size `512`, merge count `254`, token manifest rows `49,651`, config hash `191eed005e56e3d744852644c3824ebbebaebed7d676fed9f67a97cec8362ee2`, vocab hash `46525eaae602f30be4231d8bda207dc536551145af673727f7ecd6deca3f0ab5`.
- 2026-06-12: `bash scripts/verify_phase5_cycle2_bpe.sh` passed with `all_required_checks_passed:true` and `532,436` mechanical checks.
- 2026-06-12: `make clean test`, wrapper py_compile, wrapper policy regression, `bash scripts/verify_cycle16_recurrent_train.sh`, Cycle 2 prepare/verify, and `git diff --check -- . ':(exclude)run/artifacts/**'` all passed locally in WSL.
- 2026-06-12: Staged diff review completed; high-risk credential pattern scan over new scripts, artifacts, and docs returned no hits.

## Open Risks

- BPE may improve compression without moving language quality. This cycle must not launder tokenizer prep into a cognitive claim.
- Missing local raw corpus payloads would block deterministic tokenization; manifests alone can verify identity but cannot reconstruct token rows if shard files are absent.
- Token artifacts must avoid semantic labels and expected outputs, even when source manifests carry descriptive provenance.
