# Cycle 7G Raw Text Span Sense

Date: 2026-05-14
Status: closed implementation evidence for generic raw-text span sensing.

## Claim

Cycle 7G reduces dependence on builder-provided typed observations in the text experience rail.

The new raw-text span sense derives generic contiguous token chunks from `input_text`, for example:

- `raw_span_1_1:navi`
- `raw_span_2_3:basalt prism`

Those spans are appended as ordinary observations when `--derive-raw-text-spans` is enabled. They are not semantic labels and they do not encode answers.

## Mechanism

Implemented in `native/organic_v0.cpp` as:

- `raw_text_span_observations`
- `--derive-raw-text-spans`
- `--ablate-raw-text-spans`

The derivation is intentionally generic:

- tokenize input text
- emit spans up to 8 input tokens
- emit contiguous spans up to length 3
- role names are positional, e.g. `raw_span_2_3`

No code maps `carry` to `carries`, no code extracts person/object/place, and no code routes a span to an answer. The existing learned segment generator decides whether a raw span matters.

## Evidence

Aggregate artifact:

- `run/artifacts/organic-v0/text_experience_raw_spans_cycle7g_summary.json`

All-on artifact:

- `run/artifacts/organic-v0/text_experience_raw_spans_cycle7g.json`

Transcript:

- `run/artifacts/organic-v0/text_experience_raw_spans_cycle7g_transcript.md`

Fresh loaded-child probe:

- `run/artifacts/organic-v0/text_experience_raw_spans_cycle7g_from_disk_probe.json`

Ablation:

- `run/artifacts/organic-v0/text_experience_raw_spans_cycle7g_ablation.json`

Raw-span experience DB:

- `experience/organic-v0/text_experience_raw_spans_v0.jsonl`

## Metrics In Plain English

All-on raw-span rail:

- train-before: 2/4 (`0.500000`)
- train-after: 4/4 (`1.000000`)
- probe: 4/4 (`1.000000`)
- child hash: `16c29f604e814f58`

Fresh loaded child:

- probe: 4/4 (`1.000000`)
- loaded hash: `16c29f604e814f58`
- same-process probe + model hash diff-clean: true

Raw-span ablation:

- probe: 0/4 (`0.000000`)
- hash: `0229fbe5c96d5c3e`

Typed-reference comparison:

- Cycle 7E typed text rail probe: 4/4 (`1.000000`)
- Cycle 7G raw-span rail probe: 4/4 (`1.000000`)

The raw-span suite omits typed `person`, `object`, and `place` fields. The copyable chunks are present only in raw input text plus derived generic spans.

## Regression Gates

After implementation:

- `make test`: PASS, persistence hash `29958f0880e662dc`, output `"mila quartz pier6"`
- cycle-6 regression: 30/30 (`1.000000`), hash `29958f0880e662dc`
- manifesto-safe live chat: 1/5 (`0.200000`), hash `888b7664126b7f5f`
- legacy cycle-2 snapshot on cycle-5 fixture: 9/25 (`0.360000`), hash `3536309de837d3e2`, raw `"milaquart arch6"`
- Cycle 7F replay: all-on post-replay 4/4, from-disk 4/4, audit-ablation 1/4
- Cycle 7E text rail: all-on 4/4, from-disk 4/4, learning-disabled ablation 0/4
- Cycle 7B numeric interactive regression: seeds 7001/7002 remain 7/7 held-out exact
- Cycle 7C symbolic interactive regression: seeds 7101/7102 remain 8/8 held-out exact and 8/8 post-episode probe exact
- Cycle 7D grid interactive regression: seeds 7201/7202 remain 8/8 held-out exact and 8/8 post-episode probe exact

## Interpretation

A passing Cycle 7G proves only this:

> organic-v0 can derive generic copyable spans from raw text input, use them as observations in the text experience rail, save a child checkpoint, reproduce held-out probes from disk, and fail when the raw-span sense is disabled.

It does not prove semantic parsing, natural conversation, real opinions, poetry, philosophy, math, physics, broad reasoning, a complete neural brain, or beyond-human intelligence.

## Next Rung

Cycle 7H should make raw-text sensing less position-bound. Candidate directions: learned chunk salience, contrastive raw-span distractors, or mixed typed/raw records where typed scaffolds are gradually removed.
