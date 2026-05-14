# Cycle 7C Interactive Symbolic Rule Rung

Date: 2026-05-14
Status: closed implementation evidence for the first non-numeric interactive relation rung.

## Claim

Cycle 7C moves organic-v0 from typed numeric interactive rules to non-numeric symbolic same/different relations.

The organism now has a cue-bound symbolic relation sense:

- observations can contain entity attributes such as `left_color:red`, `right_color:red`, `source_symbol:ion`, and `target_symbol:ion`
- the encoder exposes relation addresses such as `color:same`, `shape:different`, `place:same`, and `symbol:same`
- those addresses are bound to the current cue token, for example `shape|shape:different`
- arbitrary action labels are learned from feedback after the raw action

This is a substrate claim. It is not natural chat, poetry, philosophy, math, physics, ARC competence, a complete neural organism, or beyond-human intelligence.

## Mechanism

Implemented in `native/organic_v0.cpp` as:

- `use_symbolic_relation_features`
- `symbolic_relation_gain`
- `--ablate-symbolic-relations`
- `--phase interactive-symbolic-rule`
- `--phase interactive-symbolic-probe`

The relation channel is intentionally cue-bound. The first implementation attempt exposed a real interference failure: a generic same/different feature let distractor relations compete across families. For example, `same_color` support examples also contained a shape distractor, and those distractor features pushed `different_shape` actions toward the earlier color labels.

The fix was not an answer route. The fix was a more precise sense:

> relation keys only bind to matching cue tokens. A `shape` cue can activate `shape:different`; a `color` cue can activate `color:same`; generic words such as `symbolic`, `rule`, and `pair` do not bind every relation.

This leaves action choice in learned weights. There is still no code path from `shape:different` to `talu`, or from `color:same` to `vire`.

## Harness

Primary command shape:

```bash
build/organic_v0 --phase interactive-symbolic-rule \
  --scenario-seed 7101 \
  --action-budget 64 \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
  --save-state run/state/organic-v0/snapshots/raphael-local-0001/cycle7c-symbolic-seed7101.pxstate \
  --event-log run/state/organic-v0/events/raphael-local-0001-cycle7c-symbolic-seed7101.jsonl \
  --out run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_seed7101.json
```

Families:

- `same_color`
- `different_shape`
- `same_place`
- `role_match`

Each family uses arbitrary action labels. The oracle action is not included in generation input or observations. Feedback is learned only after the raw action.

## Evidence

Aggregate artifact:

- `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_summary.json`

Seed artifacts:

- `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_seed7101.json`
- `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_seed7102.json`

From-disk probe artifacts:

- `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_probe_seed7101.json`
- `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_probe_seed7102.json`

Ablation artifact:

- `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_symbolic_ablation.json`

Aggregate score:

- total pre-feedback actions: 48/64 exact (`0.750000`)
- support pre-feedback actions: 32/48 exact (`0.666667`)
- held-out pre-feedback actions: 16/16 exact (`1.000000`)
- post-episode probes: 16/16 exact (`1.000000`)
- from-disk probe summary + model hash match: true for both seeds

Per seed:

- seed 7101: held-out 8/8, total 24/32, support 16/24, post-episode probe 8/8, final hash `0bb1b59f651f32eb`
- seed 7102: held-out 8/8, total 24/32, support 16/24, post-episode probe 8/8, final hash `5bc8e066bf1ba522`

Per family, each seed:

- same_color held-out: 2/2
- different_shape held-out: 2/2
- same_place held-out: 2/2
- role_match held-out: 2/2

Failure traces are preserved:

- seed 7101: 8 pre-feedback failures
- seed 7102: 8 pre-feedback failures

These failures are expected exploration/adaptation cost, not hidden errors.

## Ablation

Artifact:

- `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_symbolic_ablation.json`

Baseline all-on:

- held-out: 16/16 (`1.000000`)
- total: 48/64 (`0.750000`)

Ablated with `--ablate-symbolic-relations`:

- held-out: 2/16 (`0.125000`)
- total: 4/64 (`0.062500`)

Delta:

- held-out exact: -14
- total exact: -44

This isolates the cue-bound symbolic relation channel as load-bearing.

## Regression Gates

After implementation:

- `make test`: PASS, persistence hash `29958f0880e662dc`, output `"mila quartz pier6"`
- cycle-6 regression: 30/30 (`1.000000`), hash `29958f0880e662dc`
- manifesto-safe live chat: 1/5 (`0.200000`), hash `888b7664126b7f5f`
- legacy cycle-2 snapshot on cycle-5 fixture: 9/25 (`0.360000`), hash `3536309de837d3e2`, raw `"milaquart arch6"`
- Cycle 7B numeric interactive regression: seed 7001 7/7 held-out, seed 7002 7/7 held-out, hashes `879b7e4f6295fc12` and `030516a10354131a`

## Negative Space

Cycle 7C does not add:

- response templates
- semantic chat trigger labels
- parser-dispatcher action routes
- same/different-to-action branches
- target-output features before action
- hidden rule truth in observations
- frontend fallback behavior
- pretrained or remote inference
- a natural-language fluency improvement

The oracle grades and corrects after action. It does not answer in the generation path.

## Interpretation

The result is stronger than Cycle 7B in one narrow way: the hidden relation is non-numeric, symbolic, and less aligned with earlier parity/threshold/modular channels.

The result remains small. It shows that organic-v0 can learn arbitrary action labels through a symbolic relation sense and transfer to held-out symbolic probes after feedback. It does not show human-like conversation, general reasoning, open-ended planning, or a complete neural brain.

The manifesto direction remains: keep replacing authored answer behavior with learned, persistent, auditable substrate mechanisms until language and action emerge from internal state rather than from builder-written output.
