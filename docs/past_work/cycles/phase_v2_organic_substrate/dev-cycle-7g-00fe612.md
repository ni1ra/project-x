# Dev Cycle 7G - Raw Text Span Sense

Date: 2026-05-14
Branch: `feat/organic-v0-trace-id-ablation`

## Scope

Cycle 7G reduced dependence on builder-provided typed observations by adding a generic raw-text span sense.

Added:

- `raw_text_span_observations`
- `--derive-raw-text-spans`
- `--ablate-raw-text-spans`
- `experience/organic-v0/text_experience_raw_spans_v0.jsonl`
- all-on, from-disk, ablation, transcript, and summary artifacts

## Result

Primary artifact:

- `run/artifacts/organic-v0/text_experience_raw_spans_cycle7g_summary.json`

All-on raw-span rail:

- train-before: 2/4 (`0.500000`)
- train-after: 4/4 (`1.000000`)
- probe: 4/4 (`1.000000`)
- child hash: `16c29f604e814f58`

Fresh loaded child:

- probe: 4/4 (`1.000000`)
- loaded hash: `16c29f604e814f58`

Ablation:

- `--ablate-raw-text-spans` probe: 0/4 (`0.000000`)
- hash: `0229fbe5c96d5c3e`

## Regression Gates

Passed after implementation:

- `make test`
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, raw `"milaquart arch6"`
- Cycle 7F replay: all-on post-replay 4/4, from-disk 4/4, audit-ablation 1/4
- Cycle 7E text rail: all-on 4/4, from-disk 4/4, learning-disabled ablation 0/4
- Cycle 7B numeric interactive regression: seed 7001 7/7 held-out, seed 7002 7/7 held-out
- Cycle 7C symbolic interactive regression: seed 7101 8/8 held-out and 8/8 probe, seed 7102 8/8 held-out and 8/8 probe
- Cycle 7D grid interactive regression: seed 7201 8/8 held-out and 8/8 probe, seed 7202 8/8 held-out and 8/8 probe

## Honest Interpretation

This is a real but narrow language-substrate step. The raw-span suite omits typed person/object/place observations, and the new generic spans carry the copyable chunks from raw input.

It is still not semantic parsing. The suite is position-pattern-bound, uses a tiny carry-only grammar, and does not prove fluent chat or broad reasoning.

The next cycle should make raw sensing less position-bound with contrastive distractors or learned chunk salience.
