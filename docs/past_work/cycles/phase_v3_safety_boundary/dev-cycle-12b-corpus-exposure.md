# Dev Cycle 12B - One-Source Corpus Rail With Tiny Exposure Pass

Date: 2026-05-15
Branch: `phase-v3-safety-boundary`
Commit: not committed; current HEAD before commit is `bc2adba`

## Scope

Cycle 12B implemented Option B': one small manifest-backed public-domain-in-US corpus source, versioned content-label filtering, deterministic shard splits from canonicalization hash buckets, a tiny unlabeled corpus exposure pass that mutates a child state, child reload, and quote-diff evidence on the same 12 Cycle 11 prompts.

This was a mechanical source-discipline and persistence-mutation cycle. It was not a language-quality cycle.

## Source

- `source_id`: `cycle12_poe_usher_pg932`
- authority URL: `https://www.gutenberg.org/ebooks/932`
- source URL: `https://www.gutenberg.org/cache/epub/932/pg932.txt`
- local raw cache: `run/corpus/organic-v0/cycle12/cycle12_poe_usher_pg932/raw/pg932.txt`
- raw source SHA-256: `9842d8877c59e6e94912c4a05380f117caa3cc03ab74212ab8a57a071a6d6351`
- retrieval timestamp: `2026-05-15T01:18:47Z`
- license id: `LicenseRef-PD-US`
- content origin year: 1839

The Gutenberg wrapper/license boilerplate is not treated as exposure content. It is rejected by the versioned content-label scanner.

## Files Changed

Core/runtime:

- `.gitignore`
- `native/organic_v0.cpp`

Corpus and experience:

- `experience/organic-v0/corpus_sources_v0.jsonl`
- `experience/organic-v0/corpus_label_patterns_v0.jsonl`
- `experience/organic-v0/corpus_manifest_v0.jsonl`
- `experience/organic-v0/philosophy_prompts_v0.jsonl`
- `experience/organic-v0/cycle11_probe_states_v0.jsonl`

Scripts:

- `scripts/prepare_cycle12_corpus.sh`
- `scripts/verify_cycle12_corpus.sh`
- `scripts/verify_cycle12_exposure.sh`
- `scripts/verify_cycle11_voice_pressure.sh`

Docs:

- `docs/DO_THIS_NEXT.md`
- `docs/A_TO_Z_PLAN.md`
- `docs/REPO_CONTROL.md`
- `docs/artifacts/PERSISTENCE_SCHEMA.md`
- `docs/artifacts/paper.md`
- `docs/past_work/cycles/phase_v3_safety_boundary/dev-cycle-12b-corpus-exposure.md`

Artifacts:

- Cycle 9/10/11 carry-forward artifacts were refreshed by verification commands.
- Cycle 12B artifacts listed below were added under `run/artifacts/organic-v0/`.

## Implementation Notes

Native additions:

- `--phase corpus-exposure`
- `--corpus-manifest`
- `--corpus-exposure-max-shards`
- `--ablate-corpus-learning`
- `--ablate-content-filter`

The exposure phase loads a capped Cycle 11 parent state, ingests accepted train shards as raw-utterance-only events, saves a child state, reloads it, and writes a Cycle 12B exposure artifact. The exposure artifact carries no `correction_output`, no `expected_output`, no labels, no typed observations, and no scores.

Post-audit cleanup: Claude's 412/420 audit found no blockers and identified three small credibility fixes. The schema split names now match code (`train`/`probe`/`holdout`), `expose_raw_utterance()` now documents its internal self-supervised input-as-target signal, and the unwired `--ablate-corpus-canonicalization` flag/artifact fields were removed rather than left as a phantom ablation.

The exposure event log uses `project_x.corpus_exposure_event.v1` rather than the reward/prediction-bearing v2 runtime event schema so the Cycle 12B exposure record can remain free of forbidden reward/expected/prediction fields.

## Corpus Metrics

From `run/artifacts/organic-v0/cycle12_corpus_verification.json`:

- candidate_shards: 1,626
- accepted_shards: 412
- rejected_shards: 1,214
- accepted_shards / candidate_shards: 412/1,626 = `25.338253%`
- bytes_candidate: 179,790
- bytes_accepted: 27,371
- bytes_accepted / bytes_candidate: 27,371/179,790 = `15.223872%`
- duplicate_count: 2
- duplicate_rate: 2/1,626 = `0.001230`

Rejection reason counts:

- `delimiter_policy:non_ascii`: 36
- `delimiter_policy:pxstate_observation_delimiter`: 624
- `duplicate:cycle12_poe_usher_pg932_shard_00158`: 1
- `duplicate:cycle12_poe_usher_pg932_shard_00763`: 1
- `label_pattern:byline_v1`: 8
- `label_pattern:gutenberg_sentinel_v1`: 4
- `label_pattern:gutenberg_wrapper_v1`: 205
- `label_pattern:metadata_prefix_v1`: 4
- `length_policy:max_320`: 70
- `length_policy:min_40`: 261

## Exposure Metrics

From `run/artifacts/organic-v0/cycle12_exposure_verification.json`:

- selected exposure shards: 4 accepted train shards
- parent_state_hash: `4602e2258cd639a0`
- child_state_hash: `54af4a1dc7c51495`
- reload_state_hash: `54af4a1dc7c51495`
- learning-disabled child hash: `4602e2258cd639a0`
- changed_quote_prompt_count: 11
- unchanged_quote_prompt_count: 1
- changed quote prompts: `c11p_001`, `c11p_002`, `c11p_003`, `c11p_004`, `c11p_005`, `c11p_006`, `c11p_007`, `c11p_009`, `c11p_010`, `c11p_011`, `c11p_012`

The four exposure rows used only `raw_utterance:*` observations and all four changed state in the normal exposure run. The learning-disabled ablation used the same selected shards and changed no state hashes.

## Artifact Paths

Corpus:

- `run/artifacts/organic-v0/cycle12_corpus_prepare.json`
- `run/artifacts/organic-v0/cycle12_corpus_verification.json`

Exposure:

- `run/artifacts/organic-v0/cycle12_corpus_exposure.json`
- `run/artifacts/organic-v0/cycle12_corpus_exposure_event_log.jsonl`
- `run/artifacts/organic-v0/cycle12_corpus_exposure_wrapper_manifest.json`
- `run/artifacts/organic-v0/cycle12_corpus_exposure_ablation.json`
- `run/artifacts/organic-v0/cycle12_corpus_exposure_ablation_event_log.jsonl`
- `run/artifacts/organic-v0/cycle12_corpus_exposure_ablation_wrapper_manifest.json`

Quote diff:

- `run/artifacts/organic-v0/quote_per_state_cycle12_parent.json`
- `run/artifacts/organic-v0/quote_per_state_cycle12_parent_transcript.md`
- `run/artifacts/organic-v0/cycle12_quote_parent_event_log.jsonl`
- `run/artifacts/organic-v0/cycle12_quote_parent_wrapper_manifest.json`
- `run/artifacts/organic-v0/cycle12_quote_parent_state_manifest.jsonl`
- `run/artifacts/organic-v0/quote_per_state_cycle12_child.json`
- `run/artifacts/organic-v0/quote_per_state_cycle12_child_transcript.md`
- `run/artifacts/organic-v0/cycle12_quote_child_event_log.jsonl`
- `run/artifacts/organic-v0/cycle12_quote_child_wrapper_manifest.json`
- `run/artifacts/organic-v0/cycle12_quote_child_state_manifest.jsonl`

Final verifier:

- `run/artifacts/organic-v0/cycle12_exposure_verification.json`

Carry-forward:

- `run/artifacts/organic-v0/cycle9_carry_forward_verification.json`
- `run/artifacts/organic-v0/cycle10_carry_forward_verification.json`
- `run/artifacts/organic-v0/cycle10_wrapper_manifest_clean_run.json`
- `run/artifacts/organic-v0/cycle10_wrapper_truncate_test.json`
- `run/artifacts/organic-v0/cycle10_wrapper_manifest_path_denial.json`
- `run/artifacts/organic-v0/cycle11_voice_pressure_verification.json`

## Commands Run

Context load and inspection:

```bash
sed -n '1,220p' docs/MANIFESTO.md
sed -n '1,240p' docs/DO_THIS_NEXT.md
sed -n '1,320p' docs/A_TO_Z_PLAN.md
sed -n '1,260p' docs/REPO_CONTROL.md
sed -n '1,320p' docs/artifacts/PERSISTENCE_SCHEMA.md
sed -n '1,240p' docs/past_work/cycles/phase_v3_safety_boundary/dev-cycle-11-9c78379.md
sed -n '1,260p' native/organic_v0.cpp
sed -n '1,220p' scripts/verify_cycle11_voice_pressure.sh
sed -n '1,120p' experience/organic-v0/philosophy_prompts_v0.jsonl
sed -n '1,120p' experience/organic-v0/cycle11_probe_states_v0.jsonl
sed -n '1,160p' experience/organic-v0/text_experience_raw_spans_v0.jsonl
sed -n '1,120p' .gitignore
```

Implementation/evidence:

```bash
CYCLE12_ALLOW_MANIFEST_REWRITE=1 timeout 180s scripts/prepare_cycle12_corpus.sh
timeout 180s scripts/verify_cycle12_corpus.sh
timeout 180s scripts/verify_cycle12_exposure.sh
timeout 180s make test
timeout 180s scripts/verify_cycle9_carry_forward.sh
timeout 180s scripts/verify_cycle10_wrapper.sh
timeout 180s scripts/verify_cycle11_voice_pressure.sh
```

`CYCLE12_ALLOW_MANIFEST_REWRITE=1` was used only during local Cycle 12B development to regenerate the initial manifest rows. The normal corpus verifier then ran without the override and passed.

## Verification

Passed:

- `timeout 180s scripts/verify_cycle12_corpus.sh`
- `timeout 180s scripts/verify_cycle12_exposure.sh`
- `timeout 180s make test`
- `timeout 180s scripts/verify_cycle9_carry_forward.sh`
- `timeout 180s scripts/verify_cycle10_wrapper.sh`
- `timeout 180s scripts/verify_cycle11_voice_pressure.sh`

Key verifier outputs:

- corpus verifier: `all_required_checks_passed:true`
- exposure verifier: `all_required_checks_passed:true`, `changed_quote_prompt_count:11`
- make test: substrate self-test and persistence round-trip passed
- Cycle 9 carry-forward: `all_required_checks_passed:true`
- Cycle 10 wrapper: `all_required_checks_passed:true`
- Cycle 11 voice pressure: `all_required_checks_passed:true`

## Negative Space

- not_fluency_claim
- not_philosophy_claim
- not_chat_capability
- not_semantic_quality_claim
- not_ui_layer
- not_pretrained_route
- not_template_route
- not_tokenizer_route
- not_pretrained_encoder_route
- not_a0_improvement
- not_sandbox_or_security
- not_benchmark_ladder_advance
- not_an_alignment_or_safety_claim
- not_license_laundering
- not_curated_corpus_as_capability
- not_byte_count_as_progress
- not_dedup_as_understanding
- not_filter_as_quality_judgment
- not_source_diversity_as_competence
- not_internet_clean_data_claim
- not_state_growth_as_understanding
- not_author_voice_imitation_claim
- not_curator_intelligence_claim

## Honest Boundary

Cycle 12B proves only that manifest-backed unlabeled corpus exposure can mutate persisted state and change raw probe output mechanically, under reload, learning-disabled ablation, quote-diff, and wrapper-receipt checks.

It does not prove language quality, semantic understanding, fluent chat, philosophy, author voice imitation, curator intelligence, benchmark progress, alignment, safety, sandboxing, A0 improvement, source diversity competence, or that byte count/state growth is understanding.
