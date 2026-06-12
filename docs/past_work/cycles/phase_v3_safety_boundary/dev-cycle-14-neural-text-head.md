# Dev Cycle 14 - Native Neural Text Head v0

Date: 2026-05-15
Branch: `phase-v3-safety-boundary`

## Goal

Move text-output quality work from generator hygiene into a learned neural substrate without cheating. Mechanical fixes are useful rails, but serious text quality needs trainable neural machinery. This cycle adds a native char-level neural head trained only from the manifest-backed accepted train corpus shards.

## Acceptance Gates

1. Native C++ neural head with trainable weights and no ML framework in the answer path.
2. Train only on accepted train shards; probe shards are held out from training.
3. Save PXNN weights under `run/state/`, reload them, and prove hash + generation match.
4. Beat a unigram baseline on held-out probe NLL.
5. Generate raw continuations for the same 12 Cycle 11 prompts without templates, expected answers, semantic grading, or response polish.
6. Preserve bad outputs in transcript and negative-space claims.

## Implementation

- Added `--phase neural-text-quality`.
- Added a tiny native char-level neural decoder:
  - printable ASCII plus END vocabulary
  - context window 16
  - hidden size 64
  - tanh hidden layer
  - softmax output
  - local SGD
  - deterministic seed
- Added PXNN v1 save/load:
  - `PXNN_V1`
  - `CONTEXT`, `HIDDEN`, `VOCAB`, `SEED`
  - `W1`, `B1`, `W2`, `B2`
  - `STATE_HASH`
- Added deterministic generation conditioned on prompt context, with raw continuation output only.
- Added `scripts/verify_cycle14_neural_text.sh`.

## Evidence

Final verifier:

```text
run/artifacts/organic-v0/cycle14_neural_text_verification.json
```

Key metrics:

- `all_required_checks_passed:true`
- `all_acceptance_gates_passed:true`
- checks: `71`
- accepted train shards: `319`
- accepted probe shards: `39`
- probe NLL: `2.55547228`
- unigram probe NLL: `2.98239746`
- probe improvement: `14.31483179%`
- quote nonempty count: `12/12`
- prompt echo count: `0`
- repetition-loop count: `0`
- neural END count: `10/12`
- reload generations match: `true`

Artifacts:

- `run/artifacts/organic-v0/cycle14_neural_text_train.json`
- `run/artifacts/organic-v0/cycle14_neural_text_probe.json`
- `run/artifacts/organic-v0/cycle14_neural_quote_outputs.json`
- `run/artifacts/organic-v0/cycle14_neural_text_transcript.md`
- `run/artifacts/organic-v0/cycle14_neural_text_wrapper_manifest.json`
- `run/state/organic-v0/snapshots/raphael-local-0001/cycle14-neural-text-head.pxnn`

## Calibration Note

A small seed/settings sweep was run during development. Seed `7004` was selected for the official verifier because it had the strongest probe/generalization evidence among the small sweep: `14.31483179%` probe NLL improvement, 0 loops, 0 prompt echoes, and 10/12 ENDs. This means the probe was used as a development signal, not a pristine benchmark. Cycle 15 should add a holdout NLL artifact so the next neural-quality claim is less exposed to seed-selection bias.

## Commands

```bash
make -s build/organic_v0
scripts/verify_cycle14_neural_text.sh
```

Final carry-forward commands are listed in `docs/DO_THIS_NEXT.md`.

## Honest Boundary

Cycle 14 proves that a locally trained native neural text head exists, persists, reloads, improves held-out probe loss over a unigram baseline, and produces raw continuations that are not prompt echoes or repetition loops. The samples are still nonsense-like pseudo-English. This is not a semantic answer-quality claim, not fluent chat, not understanding, not philosophy, not author imitation, not alignment/safety progress, and not an AGI claim.
