# Phase 5 - Subword To Concept Language Bridge

Date opened: 2026-06-12
Branch: `codex/project-x-phase5-plan` for birth PR; `main` after merge
Status: active

## Goal

Make the first serious post-Cycle-16 move toward Raphael as a local, persistent, auditable organism with a language channel grounded in learned state.

Phase 5 must answer one narrow architectural question before building a larger substrate: did Cycle 16 fail coherent language mainly because the recurrent path was forced to learn at character granularity, or because the current text-head family is the wrong abstraction altogether?

The phase starts with a deterministic BPE/subword recurrent experiment because it is the cheapest high-signal diagnostic that isolates token granularity while preserving the existing native recurrent training/eval/replay discipline. It is not the manifesto end-state. If it improves text statistics but still cannot produce coherent raw language, Phase 5 moves toward an HDC/concept-to-language bridge instead of making the char/subword path wider until the lights go out.

## Inherited Reality

- `main` baseline: `ab6ca30acb31b172af69400458df352c41368d09`, merged from PR #16.
- GitHub Actions baseline: run `27434705825`, job `81093591777`, passed on `main`; workflow uses `actions/checkout@v6`.
- Cycle 16 train shards: 7,990; train chars: 552,098.
- Cycle 16 probe NLL: about 1.494; holdout NLL: about 1.476.
- Cycle 16 reproducibility: 128/128 fresh-process generations matched.
- Cycle 16 source-overlap near-copies: 0/128.
- Cycle 16 coherent correct English samples: 0/128.
- Honest diagnosis: the runtime learned measurable text statistics, but the char-level recurrent language path did not learn usable language.

## Architecture Comparison

| Path | Description | Expected signal | Cost | First decision |
|---|---|---|---|---|
| A | BPE/subword tokens plus existing recurrent head | Tests whether character granularity is the immediate bottleneck while preserving the Cycle 16 train/eval/generation rail shape | Moderate: tokenizer/vocab/corpus manifest plus recurrent vocabulary/state changes | Select first material experiment |
| B | Wider/deeper char recurrent model | Tests capacity without changing tokenization | High compute for weaker information; may only lower NLL while preserving incoherent samples | Defer unless Path A has implementation failure unrelated to language evidence |
| C | HDC/concept substrate plus neural text head | Most manifesto-aligned: concepts before language and language as actuator over internal state | Highest design risk; many variables change at once | Prepare as Phase 5 fallback/bridge if Path A proves subword helps but not enough |

Decision: Path A goes first. It is the smallest experiment that can falsify "character granularity is the immediate bottleneck." Path C remains the likely long-term route if language still fails after subword tokenization. Path B is not first because it spends compute to make the same abstraction louder.

## Non-Negotiable Gates

- No pretrained model calls.
- No RAG, vector database, retrieval-fragment answer assembly, or hosted inference.
- No answer templates, response polish layers, parser routes, hardcoded fluency tricks, or benchmark-specific branches.
- Raw generations are preserved exactly; no cleanup, truncation for scoring, or selective transcript editing.
- Lower NLL alone is not language progress.
- Every claimed improvement needs a machine-readable artifact with command, run ID, seed, config, train/probe/holdout split, state path/hash, and audit links.
- Source-overlap, reproducibility, repetition/prompt-echo, and coherent-sample audits are mandatory before any language-quality claim.
- Cycle 16 is the comparison baseline until a stronger baseline replaces it with evidence.

## Workstream 1: Phase 5 Birth And Contracts

- [x] 1.1 Repair Phase 4 drift before new work.
  - [x] Record PR #16 merge and final main CI run in archived Phase 4/Cycle 3 docs.
  - [x] Archive Phase 4 and Cycle 3 under `docs/past_work/phase_4_language-architecture-pivot/`.
  - [x] Leave Phase 4 unchecked items visible as superseded, not completed.
- [x] 1.2 Birth active Phase 5 docs.
  - [x] Create this Phase 5 doc at docs root.
  - [x] Create active Cycle 1 at docs root.
  - [x] Update `docs/REPO_CONTROL.md` active pointers and PR/CI state.
- [ ] 1.3 Make Cycle 2 implementation-ready before substrate coding.
  - [x] Name exact likely files, artifact names, verifier commands, local rails, and GitHub Actions gates.
  - [x] Define what must be proven before anyone claims language progress.
  - [ ] Land the planning PR with green GitHub Actions.

## Workstream 2: Deterministic Subword Vocabulary And Corpus Manifest

- [ ] 2.1 Build the tokenizer prep rail.
  - [ ] Add `scripts/prepare_phase5_cycle2_bpe.sh`.
  - [ ] Add `scripts/verify_phase5_cycle2_bpe.sh`.
  - [ ] Reuse accepted Cycle 12/Cycle 16 corpus manifests without rewriting them.
  - [ ] Write deterministic BPE merge/vocab artifacts with stable hashes.
- [ ] 2.2 Produce tracked token artifacts.
  - [ ] Add `experience/organic-v0/phase5_bpe_config_v0.json` (`project_x.phase5_bpe_config.v0`).
  - [ ] Add `experience/organic-v0/phase5_bpe_vocab_v0.json` (`project_x.phase5_bpe_vocab.v0`).
  - [ ] Add `experience/organic-v0/phase5_token_manifest_v0.jsonl` (`project_x.phase5_token_manifest_row.v0`).
  - [ ] Add `run/artifacts/organic-v0/phase5_cycle2_bpe_prepare.json` (`project_x.phase5_cycle2_bpe_prepare.v0`).
  - [ ] Add `run/artifacts/organic-v0/phase5_cycle2_bpe_verification.json` (`project_x.phase5_cycle2_bpe_verification.v0`).
- [ ] 2.3 Acceptance gates.
  - [ ] `scripts/verify_phase5_cycle2_bpe.sh` passes locally.
  - [ ] Token manifest rows preserve source IDs, split buckets, shard hashes, token counts, and vocab/config hashes.
  - [ ] Negative-space block confirms tokenizer prep is not a language capability claim.

## Workstream 3: Subword Recurrent Train/Eval/Generation Path

- [ ] 3.1 Extend the native runtime narrowly.
  - [ ] Update `native/organic_v0.cpp` to load the Phase 5 vocab/token manifest for a subword recurrent phase.
  - [ ] Persist a subword recurrent state with a new explicit architecture tag and vocab hash.
  - [ ] Keep raw generation and event-log behavior compatible with existing audit rails.
- [ ] 3.2 Add the training verifier.
  - [ ] Add `scripts/verify_phase5_cycle3_subword_recurrent.sh`.
  - [ ] Emit `run/artifacts/organic-v0/phase5_cycle3_subword_recurrent_text_train.json` (`project_x.phase5_subword_recurrent_text_quality.v0`).
  - [ ] Emit `run/artifacts/organic-v0/phase5_cycle3_subword_generation_batch.json` (`project_x.phase5_subword_generation_batch.v0`).
  - [ ] Emit `run/artifacts/organic-v0/phase5_cycle3_subword_text_transcript.md`.
  - [ ] Emit `run/artifacts/organic-v0/phase5_cycle3_subword_reproducibility_audit.json` (`project_x.phase5_subword_reproducibility_audit.v0`).
  - [ ] Emit `run/artifacts/organic-v0/phase5_cycle3_subword_source_overlap_audit.json` (`project_x.phase5_subword_source_overlap_audit.v0`).
  - [ ] Emit `run/artifacts/organic-v0/phase5_cycle3_subword_best_raw_output.json` (`project_x.phase5_subword_best_raw_output.v0`).
- [ ] 3.3 Acceptance gates.
  - [ ] `make clean test` passes.
  - [ ] `scripts/verify_cycle16_recurrent_train.sh` remains green as the historical rail.
  - [ ] `scripts/verify_phase5_cycle3_subword_recurrent.sh` passes locally.
  - [ ] GitHub Actions quick checks pass on the PR.

## Workstream 4: Honest Quality Audit Against Cycle 16

- [ ] 4.1 Compare machine metrics.
  - [ ] Probe NLL and holdout NLL compare against Cycle 16.
  - [ ] Token-level metrics are reported separately from char-level metrics so the comparison is not mathematically laundered.
  - [ ] Model/state size, training time, corpus coverage, and config differences are recorded.
- [ ] 4.2 Audit generated language.
  - [ ] Preserve at least 128 raw generations across the same prompt family and sampler settings.
  - [ ] Reproducibility audit proves fresh-process regeneration.
  - [ ] Source-overlap audit proves no near-copy training leakage.
  - [ ] Repetition and prompt-echo checks run.
  - [ ] Manual coherent-sample audit records exact pass/fail counts and raw sample pointers.
- [ ] 4.3 Acceptance gates.
  - [ ] Any language-progress claim names both NLL movement and coherent-sample movement.
  - [ ] If coherent correct English remains 0/128, the result is a diagnostic improvement at most.
  - [ ] If coherent samples improve, the claim is bounded to the audited prompt/sampler/corpus configuration.

## Workstream 5: HDC Concept-To-Language Bridge Trigger

- [ ] 5.1 Trigger condition.
  - [ ] If subword reduces loss but still fails language quality, begin the HDC/concept bridge instead of widening the recurrent path by default.
  - [ ] If subword fails both loss and language quality, decide whether the recurrent text family is still worth testing.
- [ ] 5.2 Bridge preparation.
  - [ ] Define concept/event state that the text head must consume.
  - [ ] Define machine-readable evidence for concept activation, source IDs, and language output linkage.
  - [ ] Preserve the rule that language reports internal state; it must not become a hand-authored composer.

## Tail: Audit, Bug Search, Fixes, Closure

- [ ] 6.1 Phase audit.
  - [ ] Audit docs, scripts, native runtime, artifacts, and REPO_CONTROL for drift.
  - [ ] Confirm exactly one active phase and cycle at docs root.
  - [ ] Confirm no generated junk, secrets, ignored corpus payloads, or local state are staged.
- [ ] 6.2 Bug search and fixes.
  - [ ] Search for tokenizer leakage, hardcoded text-quality shortcuts, stale artifact paths, and broken carry-forward rails.
  - [ ] Fix findings before any phase-close claim.
- [ ] 6.3 Next architecture decision.
  - [ ] Archive completed cycles.
  - [ ] Decide whether Phase 6 should deepen subword recurrence, start the HDC bridge, or replace the text path.

## Phase Exit Standard

Phase 5 is successful only if it materially narrows the language-substrate decision with evidence. A clean PR, a lower loss curve, or nicer-looking isolated phrase is not enough. The phase must leave Raphael closer to a native, persistent, inspectable organism whose language comes from learned state and whose failures are preserved instead of decorated.
