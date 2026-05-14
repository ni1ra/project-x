# Dev Cycle 7C - Interactive Symbolic Relation Rung

Date: 2026-05-14
Branch: `feat/organic-v0-trace-id-ablation`

## Scope

Cycle 7C promoted the interactive hidden-rule rung from typed numeric relations to non-numeric symbolic same/different relations.

Added:

- cue-bound symbolic relation feature addresses in `native/organic_v0.cpp`
- `--ablate-symbolic-relations`
- `--phase interactive-symbolic-rule`
- `--phase interactive-symbolic-probe`
- pre-implementation learnability audit
- machine-readable all-on, from-disk probe, and ablation artifacts

## Result

Primary artifact:

- `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_summary.json`

Aggregate:

- held-out pre-feedback: 16/16 (`1.000000`)
- total pre-feedback: 48/64 (`0.750000`)
- support pre-feedback: 32/48 (`0.666667`)
- post-episode probes: 16/16 (`1.000000`)
- from-disk probe summary + model hash match: true for both seeds

Final child hashes:

- seed 7101: `0bb1b59f651f32eb`
- seed 7102: `5bc8e066bf1ba522`

Ablation:

- artifact: `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_symbolic_ablation.json`
- all-on held-out: 16/16
- `--ablate-symbolic-relations` held-out: 2/16
- total exact drops from 48/64 to 4/64

## Important Failure During Development

The first symbolic attempt scored only 6/8 held-out. `different_shape` failed because generic same/different relation features allowed distractor relations to compete with the intended cue. Example: `same_color` support examples also contained shape distractors, so later `different_shape` probes inherited earlier color-family labels.

The fix was to bind symbolic relation features to matching cue tokens only. A `shape` cue can activate `shape:different`; a `color` cue can activate `color:same`. Generic tokens do not bind every relation.

This is still a sense, not an answer route. No code maps a relation to an action label.

## Regression Gates

Passed after implementation:

- `make test`
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, raw `"milaquart arch6"`
- Cycle 7B numeric interactive regression: seed 7001 7/7 held-out, seed 7002 7/7 held-out

## Honest Interpretation

This is real local substrate progress: non-numeric symbolic relation features carry learned action transfer under feedback, and the ablation makes the mechanism load-bearing.

It is not GPT/Claude-style chat. It is not poetry, philosophy, general math, general physics, ARC, or beyond-human intelligence. The manifesto target remains a fully chattable, emergent, persistent brain, not a hardcoded voice layer.

## Next

Cycle 7D should climb toward ARC-like micro-worlds. Default next step: a tiny grid transformation rung with a spatial/grid substrate and an ablation, or replay/consolidation if grid implementation exposes a blocker.
