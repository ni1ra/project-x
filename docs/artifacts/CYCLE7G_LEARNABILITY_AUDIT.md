# Cycle 7G Learnability Audit

Date: 2026-05-14
Status: pre-implementation audit for raw-text span sensing.

## Target

Cycle 7G should reduce dependence on builder-provided typed observations in the text experience rail.

The organism should receive raw input text and derive generic token-span observations such as:

- `raw_span_1_1:navi`
- `raw_span_2_3:basalt prism`

Those derived spans should be ordinary observations that the existing learned segment generator can use. They must not encode intent or answer labels.

## Missing Evidence

Cycle 7E and 7F proved durable text experience, from-disk continuation, replay, and replay self-audit. But the seed database still supplies typed fields:

- `person:navi`
- `object:basalt prism`
- `place:quiet archive`

That is useful as an audit scaffold, but it is not enough for organic language. The next small step is to derive copyable chunks from the raw utterance itself.

## Allowed Mechanism

The builder may add:

- a native raw-token span derivation helper
- a CLI flag to enable derived raw spans for text-experience phases
- a CLI ablation that disables those spans
- a raw-span-only experience DB with minimal or no typed role observations
- artifacts comparing all-on and ablated behavior
- from-disk probe verification

The raw span sense is allowed because it is a generic encoder/sense mechanism. It does not know that `carry` means `carries`, or that token 1 is a person. It only exposes contiguous token chunks from the raw input.

## Forbidden Mechanism

Cycle 7G must not add:

- a carry/wait parser
- person/object/place extraction rules
- intent labels derived from trigger words
- output templates
- benchmark-specific answer branches
- target-output leakage into probe generation
- frontend cleanup
- pretrained or remote inference

If a raw span is useful, the learned state must discover how to use it through correction.

## Benchmark Shape

Use a small raw-span-only database separate from the typed Cycle 7E seed:

- raw input includes the copyable chunks
- observations include the raw utterance/source but omit typed `person`, `object`, and `place`
- native derivation appends generic span observations
- target output is learned from correction
- held-out probes use unseen names/items/places in the same span positions

Compare:

- all-on raw spans
- raw-span ablation
- from-disk child probe

If feasible, also compare the existing typed Cycle 7E rail to keep the interpretation honest.

## Required Falsification

The all-on run should produce:

- raw-span derived observation count
- train-before/train-after metrics
- held-out probe metrics
- transcript with raw outputs
- saved child hash
- from-disk probe

The ablated run should degrade when raw spans are disabled. If it does not, the new sense is not load-bearing.

Existing rails must remain visible:

- Cycle 7F replay
- Cycle 7E text rail
- Cycle 7D grid interactive
- Cycle 7C symbolic interactive
- Cycle 7B numeric interactive
- cycle-6 regression
- clean chat regression
- legacy cycle-2 compatibility

## Interpretation Boundary

A passing Cycle 7G would prove only this:

> organic-v0 can expose generic token spans from raw input as learnable observations, use them in the text experience rail, save the resulting child, reproduce from disk, and fail when the raw-span sense is ablated.

It would not prove natural language understanding, fluent chat, opinions, poetry, math, physics, broad reasoning, a complete neural brain, or beyond-human intelligence.
