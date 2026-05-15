# Dev Cycle 16 — Manifest-Backed Multi-Source Recurrent Text Scaling

Date: 2026-05-15
Branch: `phase-v3-safety-boundary`
Commits: `01473d9`, `9554f1c`, `03285b2`, `e818915`, `1ab427f`, `b28b0ba`, `fe46d3a`, `1025e0d` (+ cycle-5 close commit to follow)

## Hypothesis

Cycle 15 produced probe NLL 2.237 / holdout 2.248 on the Cycle 12B single-source corpus (Project Gutenberg #932 Poe, ~27 KB accepted-train bytes / 319 shards) with 0/128 raw samples passing the correct-coherent-English gate. The advisor framed a falsifiable diagnostic: scale corpus to multi-source cross-genre, retrain the same recurrent substrate, and read whether probe NLL drops below 1.90 while samples remain 0/128 — that result fingerprints the substrate as the architectural ceiling rather than the data as the bottleneck.

## Goal

Build a multi-source corpus rail under Cycle 12B's existing manifest discipline (append-only deterministic shard manifests, split-from-canonicalization, whole-shard rejection, no-rewrite); train the Cycle 15 recurrent char head on the combined Cycle 12 + Cycle 16 accepted-train corpus; audit the resulting samples honestly; recommend the cycle-17 architectural pivot based on the empirical answer.

## Implementation

Six atomic commits across four godify-cycles (godify-app 4h, 6 cycles × 20m ON / 20m OFF).

### Cycle 1 commits `01473d9` and `9554f1c`

- `experience/organic-v0/cycle16_corpus_sources.jsonl` — 3 cross-genre descriptors:
  - Jane Austen, Pride and Prejudice (PG #1342, 1813, early-19c British prose), sha256 `212c4047137af6855be612024988dc8fe82d4720e7ac7e2ed4311427a57eabdb`.
  - Charles Darwin, On the Origin of Species (PG #1228, 1859, mid-19c scientific prose), sha256 `c8dea67f08d19467f28987d426f88bf5bf2acbf1e9a388cac4911f2154329550`.
  - William Shakespeare, Sonnets (PG #1041, 1609 verse), sha256 `9034dcbdb674f365d6e399b229f8389052e3894a0213d1caa4fa3537a554fb3f`.
- `scripts/prepare_cycle16_corpus.sh` — fork of `prepare_cycle12_corpus.sh` with multi-source iteration; reuses `cycle12_canonical_v1` / `cycle12_dedup_v1` / `cycle12_split_v1_sha256_bucket_80_10_10` / `cycle12_label_filter_v1` policies verbatim so identical canonical text lands in the same split bucket across cycles. Writes SEPARATE `cycle16_corpus_sources.jsonl` + `cycle16_corpus_manifest.jsonl` so the Cycle 12B verifier rail (hardcoded single-source assertion) stays bytewise green.
- `experience/organic-v0/cycle16_corpus_manifest.jsonl` — 22,034 shard rows from Austen alone (cycle-1 commit `01473d9`), grew to 48,025 rows after the cycle-1 expansion commit `9554f1c` added Darwin + Shakespeare.

### Cycle 2 commits `03285b2` and `e818915`

- `scripts/verify_cycle16_text_scaling.sh` — multi-source verifier; 837,173 mechanical checks over schema, per-row sha256/canonicalization-hash/dedup-hash recomputation, deterministic split-bucket reproducibility, label-rejection pattern membership, cross-source dedup integrity, and Cycle 12B v0 baseline sha256 isolation.
- `docs/REPO_CONTROL.md` row additions for the 6 cycle-16 files; `run/corpus/` description updated.
- Carry-forward rail set rerun (~66 seconds for 9 rails): all green, zero regression from cycle 1.

### Cycle 3 commits `1ab427f` and `b28b0ba`

- `native/organic_v0.cpp` extended with:
  - `Args.corpus_manifests_extra` (vector<string>) field; default empty.
  - `--corpus-manifest-extra` repeatable CLI flag.
  - `load_neural_text_shards_combined(primary, extras, split, max_train_shards)` helper; empty `extras` short-circuits to the existing single-manifest path bit-exact.
  - `neural_recurrent_text_phase` (Cycle 15's recurrent training) replaces three `load_neural_text_shards` calls with the combined helper.
  - Cycle-15 schema artifact emits `corpus_manifests_extra` (list) and `corpus_manifest_count` fields.
- Same translation unit co-landed prior-instance Cycle 12-15 native code that had been sitting working-tree-modified for several commits (~2200 LOC). Transparent in commit body.

### Cycle 4 commits `fe46d3a` and `1025e0d`

- Background full-shape training launched at cycle-3 ON-shift end: `build/organic_v0 --phase neural-recurrent-text --corpus-manifest experience/organic-v0/corpus_manifest_v0.jsonl --corpus-manifest-extra experience/organic-v0/cycle16_corpus_manifest.jsonl --neural-hidden 96 --neural-epochs 48 --scenario-seed 7004 --neural-context 16 --neural-max-output-chars 160 --neural-min-output-chars 32 --neural-top-k 16 --neural-learning-rate 0.025 --neural-temperature 0.85 ...`. Completed during cycle-3 OFF-shift idle.
- Canonical artifact set emitted: `cycle16_recurrent_text_train.json` + `cycle16_recurrent_text_transcript.md` + `cycle16_reproducibility_audit.json` + `cycle16_best_raw_output.json`.

## Evidence

| Metric | Cycle 15 baseline | Cycle 16 result | Relative |
|---|---:|---:|---:|
| Train shards | 319 | 7,990 | +25× |
| Train chars | ~27 KB | 552,098 | +20× |
| Train targets | n/a | 560,088 | — |
| Probe NLL | 2.237254 | **1.494365** | **–33.2%** |
| Holdout NLL | 2.247765 | **1.475701** | **–34.3%** |
| Unigram probe NLL | 2.99 | 2.95 | — |
| Unigram holdout NLL | n/a | 2.95 | — |
| Probe target met (≤ Cycle 14 × 0.95) | yes | yes | — |
| Holdout beats unigram | yes | yes | — |
| PXNN v2 reload-hash match | true | true | — |
| Same-process reload-generations match | true | true | — |
| Fresh-process regen 128/128 match | n/a | **true** | — |
| Source-overlap near-copy count | 0/128 | **0/128** | — |
| Manual 128-sample correct-English count | **0/128** | **0/128** | — |

`neural_state_hash`: `0b97b6e26331c7a4`.

Per-source corpus breakdown:

| Source | Candidate shards | Accepted shards | Accept rate | Accepted bytes | Internal dup |
|---|---:|---:|---:|---:|---:|
| Austen P&P #1342 | 22,034 | 3,815 | 17.3% | 269,086 | 46 |
| Darwin Origin #1228 | 22,219 | 5,340 | 24.0% | 383,916 | 239 |
| Shakespeare Sonnets #1041 | 3,772 | 391 | 10.4% | 17,806 | 116 |
| **Aggregate** | **48,025** | **9,546** | **19.88%** | **670,808** | **401** |

Filter validation: Darwin's higher accept rate (24%) vs Shakespeare's lower (10.4%) is expected — sonnet lines are short and frequently miss `length_policy:min_40`, while Darwin's compound scientific sentences fit the 40-320 char window comfortably. Filter is doing real work, not random rejection. Cross-source dedup spans the prep run.

## Manual Output Audit

All 128 raw samples were read without editing, truncation, or cleanup. Cycle 16 outputs are markedly more coherent than Cycle 15's:

- Cycle 15: pseudo-words ("chisitens", "ferpenco", "sopen") — phonologically plausible but not English.
- Cycle 16: real English words dominate ("the", "of", "my", "thou", "thy", "love", "species", "perfect", "character", "descent"); cross-source vocabulary visible (Austen `Mrs./darcy/lydia` + Shakespeare `thou/thy/doth` + Darwin `species/transmors/genera`); short correct fragments appear ("she has done", "i should change", "he was not", "we do not have", "would probably", "you might").

But NO full sample is a grammatically correct English sentence with a meaningful claim:

```
[5]  to the beauty speak in expressing she has now become doth them wa must nor with a to thus to deer more favoured than my.
[36] to my for my period of she well deserved not as the beauties which hardly see my look.
[66] all darcy. but through may have been railly did praise;
```

**Honest count: 0/128 correct.**

## Source-Overlap Audit

Method: char 5-gram Jaccard nearest-neighbor across all 7,990 accepted-train shards + longest-common-substring in the combined corpus + span-ratio check (≥90% of 32+ char output is contiguous train span).

Cycle 15 thresholds reused: Jaccard ≥ 0.82, contiguous ≥ 48 chars, span ratio ≥ 0.90.

Result: **0/128 near-copies.** Max Jaccard observed: 0.203 (well below threshold). Max longest-common-substring: 25 chars (well below threshold). The NLL improvement is substrate generalization, not memorization.

Artifact: `run/artifacts/organic-v0/cycle16_source_overlap_audit.json`.

## Reproducibility Audit

Fresh-process `build/organic_v0 --phase neural-recurrent-regenerate --load-state run/state/organic-v0/snapshots/raphael-local-0001/cycle16-recurrent-text-head.pxnn --scenario-seed 7004 ...` loaded the saved PXNN v2 and produced 128 outputs byte-for-byte identical (and `raw_output_fnv1a64` identical) to the in-process generation batch. **mismatch_count: 0 / 128.**

Artifact: `run/artifacts/organic-v0/cycle16_reproducibility_audit.json`.

## Carry-Forward

All 10 prior carry-forward rails preserved green throughout cycle 1-5 (rerun at cycles 1, 2, 3, 5 — total runtime per rerun ~66s to ~2 minutes). Cycle 12B v0 files (`corpus_sources_v0.jsonl`, `corpus_manifest_v0.jsonl`, `corpus_label_patterns_v0.jsonl`) bytewise unchanged from HEAD `bc2adba` across the cycle 16 work — verified by the Cycle 16 text-scaling verifier as part of its 837,173-check pass. `scripts/verify_cycle16_recurrent_train.sh` added cycle 5 as the permanent carry-forward rail for the recurrent training itself.

## Audit Questions

- Did information pass through trainable parameters? Yes — recurrent GRU char head with deterministic SGD; PXNN v2 reload bit-exact.
- Did probe AND holdout loss improve? Both improved 33%+ relative vs Cycle 15 single-source baseline.
- Did any hand-coded concept/tool route enter the answer path? No.
- Did data scale produce coherent English? **No** — 0/128 raw samples are correct. Substrate is the ceiling.
- Are failures preserved verbatim? Yes — transcript + generation_batch field + best_raw_output verdict + source-overlap audit + reproducibility audit all preserve full sample text without editing.
- Did source-overlap audit confirm generalization rather than memorization? Yes — 0/128 near-copies, max Jaccard 0.203, max LCS 25 chars.
- Did multi-source carry-forward break anything? No — Cycle 12B verifier rail bytewise green; verify_cycle15_recurrent_text.sh single-manifest path bit-exact preserved.

## Honest Boundary

Cycle 16 proves: (a) the corpus rail extends cleanly to multiple cross-genre sources under Cycle 12B's existing manifest discipline; (b) the native multi-manifest extension preserves the single-manifest path bit-exact and adds combined training without breaking carry-forward; (c) char-level recurrent GRU at hidden=96 with ~600KB combined English (Austen prose + Darwin scientific + Shakespeare verse) reduces held-out NLL by 33% over Cycle 15's single-source training; (d) the resulting generation is mechanically novel (not memorization), uses cross-source vocabulary, and contains many real English word fragments and short correct phrases.

Cycle 16 does NOT prove: language quality in the product sense, semantic understanding, fluent chat, philosophy, A0 usefulness, alignment, AGI safety, sandbox escape resistance, broader tool-use safety, supply-chain safety, resource limiting, author imitation, curated-corpus competence, meaningful answers, or that any sample passes a Hassabis-stop-and-stare bar.

**The falsifiable diagnostic fired cleanly: probe NLL 1.494 ≤ 1.90 advisor threshold AND 0/128 raw samples correct coherent English. Per advisor framing, the char-RNN substrate IS the architectural ceiling at this corpus scale. Cycle 17 pivots architecture.**

## Cycle 17 Architectural Pivot — Candidate Paths

Three candidate architectures to consider for the next cycle's manifesto-aligned ship (recorded in `docs/DO_THIS_NEXT.md`):

**A. BPE / subword tokens + same GRU**: pivot char-level → BPE (~256-2048 vocab). Reuses corpus rail and training infrastructure; only the tokenizer + vocabulary + head shape change. Cost ~200 LOC. Answers: is char-level granularity the bottleneck, or is it model capacity?

**B. Multi-layer recurrent / stacked GRU + hidden width scaling**: 2-3 GRU layers, hidden 256-512, same chars. Cost ~50-100 LOC native + proportionally more training time. Answers: is single-layer the bottleneck? (Typically the weakest move — same architectural style with more parameters usually just produces longer pseudo-text.)

**C. HDC + neural integration (manifesto §Concepts Before Language)**: use the existing HDC substrate (cycle 1-7) to encode concept atoms; train a neural head that maps HDC concept activations to text continuations rather than raw char→char. The HDC substrate already supports rule learning (cycle 7B/C/D show 14/14, 16/16 held-out transfer). Coupling concepts to language is the manifesto's actual ask. Cost ~400-800 LOC + new artifact schemas.

Preliminary recommendation (subject to advisor review at cycle 6): start with **A (BPE)** — cheapest diagnostic. If A also fires 0/N correct sample gate, escalate to **C (HDC+neural)** as the manifesto-aligned structural pivot. **B** is least promising.

## Commands

```bash
# Cycle 16 corpus prep (3 sources):
timeout 120 scripts/prepare_cycle16_corpus.sh

# Cycle 16 text-scaling verifier (multi-source manifest integrity):
timeout 180 scripts/verify_cycle16_text_scaling.sh

# Cycle 16 full recurrent training (48 epochs hidden=96):
build/organic_v0 --phase neural-recurrent-text \
  --corpus-manifest experience/organic-v0/corpus_manifest_v0.jsonl \
  --corpus-manifest-extra experience/organic-v0/cycle16_corpus_manifest.jsonl \
  --experience-db experience/organic-v0/cycle15_generation_prompts_v0.jsonl \
  --save-state run/state/organic-v0/snapshots/raphael-local-0001/cycle16-recurrent-text-head.pxnn \
  --out run/artifacts/organic-v0/cycle16_recurrent_text_train.json \
  --neural-hidden 96 --neural-epochs 48 --neural-context 16 --scenario-seed 7004

# Fresh-process regen audit:
build/organic_v0 --phase neural-recurrent-regenerate \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/cycle16-recurrent-text-head.pxnn \
  --experience-db experience/organic-v0/cycle15_generation_prompts_v0.jsonl \
  --out /tmp/cycle16_regen.json --scenario-seed 7004

# Cycle 16 permanent carry-forward rail (cycle 5):
timeout 180 scripts/verify_cycle16_recurrent_train.sh

# Full carry-forward rail set including new cycle 16 rail (11 rails):
make test && \
scripts/verify_cycle9_carry_forward.sh && \
scripts/verify_cycle10_wrapper.sh && \
scripts/verify_cycle11_voice_pressure.sh && \
scripts/verify_cycle12_corpus.sh && \
scripts/verify_cycle12_exposure.sh && \
scripts/verify_cycle13_diagnostics.sh && \
scripts/verify_cycle14_neural_text.sh && \
scripts/verify_cycle15_recurrent_text.sh && \
scripts/verify_cycle16_text_scaling.sh && \
scripts/verify_cycle16_recurrent_train.sh
```
