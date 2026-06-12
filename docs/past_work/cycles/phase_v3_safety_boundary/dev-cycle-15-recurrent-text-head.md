# Dev Cycle 15 - Native Recurrent Neural Text Head v1

Date: 2026-05-15
Branch: `phase-v3-safety-boundary`

## Hypothesis

A deterministic native GRU-style recurrent character head should lower held-out NLL by carrying trainable state across full shards instead of using only a fixed local window.

## Goal

Move Cycle 14's fixed-window neural head to a recurrent PXNN v2 substrate while keeping the sample bar honest. Loss metrics are diagnostics; the raw sample remains the result gate.

## Implementation

- Added native phase `--phase neural-recurrent-text`.
- Added fresh-process regeneration phase `--phase neural-recurrent-regenerate`.
- Added `RecurrentCharNeuralHead`, a GRU-style character model:
  - printable ASCII plus END vocabulary
  - deterministic initialization
  - deterministic SGD with full-shard backpropagation through time
  - trainable update/reset/candidate recurrent weights
  - softmax output from recurrent hidden state
- Added PXNN v2 save/load:
  - `PXNN_V2`
  - `ARCH RECURRENT_GRU_CHAR_V1`
  - `HIDDEN`, `VOCAB`, `SEED`
  - `WX_Z`, `WX_R`, `WX_N`, `U_Z`, `U_R`, `U_N`, `B_Z`, `B_R`, `B_N`, `W_OUT`, `B_OUT`
  - terminal `STATE_HASH`
- Added prompt store `experience/organic-v0/cycle15_generation_prompts_v0.jsonl` with the 12 Cycle 11 prompts plus 20 broader prompts.
- Added verifier `scripts/verify_cycle15_recurrent_text.sh`.

## Evidence

Final verifier:

```text
run/artifacts/organic-v0/cycle15_recurrent_text_verification.json
```

Key metrics:

- `all_required_checks_passed:true`
- `all_acceptance_gates_passed:true`
- accepted train shards: `319`
- accepted probe shards: `39`
- accepted holdout shards: `54`
- final train NLL: `2.19043794`
- probe NLL: `2.23725425`
- Cycle 14 probe target: `2.55547228`
- required NLL for 5% relative improvement: `2.42769867`
- probe relative improvement vs Cycle 14: `12.45241552%`
- holdout NLL: `2.24776522`
- unigram holdout NLL: `2.99608265`
- generation batch: `128` raw samples
- fresh-process regeneration mismatches: `0`
- source-overlap near-copy count: `0`
- passed raw-output candidates: `0`

Artifacts:

- `run/artifacts/organic-v0/cycle15_recurrent_text_train.json`
- `run/artifacts/organic-v0/cycle15_recurrent_text_probe.json`
- `run/artifacts/organic-v0/cycle15_recurrent_text_holdout.json`
- `run/artifacts/organic-v0/cycle15_recurrent_generation_batch.json`
- `run/artifacts/organic-v0/cycle15_recurrent_text_transcript.md`
- `run/artifacts/organic-v0/cycle15_source_overlap_audit.json`
- `run/artifacts/organic-v0/cycle15_reproducibility_audit.json`
- `run/artifacts/organic-v0/cycle15_best_raw_output.json`
- `run/artifacts/organic-v0/cycle15_recurrent_text_wrapper_manifest.json`
- `run/state/organic-v0/snapshots/raphael-local-0001/cycle15-recurrent-text-head.pxnn`

## Manual Output Audit

All 128 generated samples were reviewed without editing, truncation, or cleanup. The outputs are more mechanically word-like than Cycle 14, but they remain pseudo-English. Examples include fragments like:

```text
on chisitens. wor in a ferpenco a cerestion ane the sopen as ot the sor
```

and:

```text
the sell of a pomall at of here four the wole sind the mance por hon
```

No sample is 100% correct English. No sample contains a coherent nontrivial claim, description, argument, or structure. Therefore no sample passed the Output Gate, and no sample passed both gates.

## Source-Overlap Audit

Method: normalized character 5-gram Jaccard nearest neighbor plus longest-common-substring guard.

Threshold: a sample is flagged near-copy if char-5gram Jaccard is at least `0.82`, or if it shares a contiguous span of at least `48` characters with an accepted train shard, or if at least `90%` of a 32+ character output is one contiguous train-corpus span.

Result: `0/128` samples were flagged as near-copy.

Artifact:

```text
run/artifacts/organic-v0/cycle15_source_overlap_audit.json
```

## Reproducibility Audit

The verifier saved the PXNN v2 checkpoint, launched a fresh process through `--phase neural-recurrent-regenerate`, regenerated the full 128-sample batch from the logged prompt store, sampler settings, and seeds, and compared every raw output byte-for-byte.

Result: `128/128` fresh-process generations matched.

Artifact:

```text
run/artifacts/organic-v0/cycle15_reproducibility_audit.json
```

## Audit Questions

- Did information pass through trainable parameters? Yes. Outputs come from a trained PXNN v2 recurrent GRU character head.
- Did probe AND holdout loss improve? Probe improved versus Cycle 14 by the required relative threshold; holdout beats unigram. Cycle 14 had no holdout artifact, so holdout is not compared to Cycle 14.
- Did any hand-coded concept/tool route enter the answer path? No Cycle 15 answer path uses route tables, templates, semantic parsers, RAG, hosted models, or response polish.
- Did generated text improve mechanically without polish? Mechanically yes on loss and character continuity; manually audited English coherence did not pass.
- Are reusable representations forming, or is the model memorizing? Loss generalizes to probe and holdout, and source-overlap audit found no near-copy samples. This is evidence against pure memorization but not proof of reusable semantic representation.
- Did data curation remain legal, reproducible, and manifest-backed? Yes. Cycle 15 stayed on the Cycle 12B one-source manifest rail instead of expanding corpus scope.
- Are failures preserved verbatim? Yes. The transcript and generation batch preserve all 128 raw outputs.
- Did any sample pass both Substrate and Output gates? No.

## Honest Boundary

This cycle proves that a deterministic native recurrent PXNN v2 text substrate trains on accepted train shards only, reloads bit-exactly, regenerates bit-exactly in a fresh process, and improves diagnostic probe/holdout metrics.

This cycle does not prove: language quality in the product sense, semantic understanding, fluent chat, philosophy, A0 usefulness, alignment, AGI safety, sandbox escape resistance, broader tool-use safety, supply-chain safety, resource limiting, author imitation, curated-corpus competence, meaningful answers, or that any sample passes a Hassabis-stop-and-stare bar. Loss improvement alone is not the bar. The sample is the bar; if no sample passed, the cycle ships its substrate and says so.

No raw sample passed the Hassabis bar; the best outputs are still pseudo-English.

## Commands

```bash
make -s build/organic_v0
timeout 180s scripts/verify_cycle15_recurrent_text.sh
```

Carry-forward rails are listed in `docs/DO_THIS_NEXT.md`.
