# Dev Cycle 7F - Text Experience Replay

Date: 2026-05-14
Branch: `feat/organic-v0-trace-id-ablation`

## Scope

Cycle 7F extended the text experience rail with self-audited replay/consolidation.

Added:

- `--phase text-experience-replay`
- `--replay-passes`
- `--replay-threshold`
- `--ablate-text-experience-replay`
- `--ablate-text-replay-audit`
- replay candidate selection from first-pass weak records
- candidate acceptance audit against local record, full training set, and held-out probes
- all-on, from-disk, replay-disabled, audit-ablation, transcript, and summary artifacts

## Result

Primary artifact:

- `run/artifacts/organic-v0/text_experience_replay_cycle7f_summary.json`

All-on self-audited replay:

- first-pass train-after: 4/6 (`0.666667`)
- pre-replay probe: 4/4 (`1.000000`)
- selected for replay: 2 records
- accepted replay candidates: 1
- post-replay train: 6/6 (`1.000000`)
- post-replay probe: 4/4 (`1.000000`)
- child hash: `89fc3a01a35451e9`

Fresh loaded child:

- post-replay probe: 4/4 (`1.000000`)
- loaded hash: `89fc3a01a35451e9`

Controls:

- replay-disabled control: replay state growth zero, hash stays `be0fc781039a2038`
- acceptance-audit ablation: blind replay drops post-replay probe to 1/4 (`0.250000`) and train to 4/6 (`0.666667`)

## Regression Gates

Passed after implementation:

- `make test`
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, raw `"milaquart arch6"`
- Cycle 7E text rail: all-on 4/4, from-disk 4/4, learning-disabled ablation 0/4
- Cycle 7B numeric interactive regression: seed 7001 7/7 held-out, seed 7002 7/7 held-out
- Cycle 7C symbolic interactive regression: seed 7101 8/8 held-out and 8/8 probe, seed 7102 8/8 held-out and 8/8 probe
- Cycle 7D grid interactive regression: seed 7201 8/8 held-out and 8/8 probe, seed 7202 8/8 held-out and 8/8 probe

## Honest Interpretation

The headline is not that replay magically improved language. The important evidence is that blind replay damaged held-out text behavior and the new acceptance audit prevented that damage while still allowing a non-degrading replay mutation.

This is a small self-critical replay substrate over a tiny text database. It is not fluent chat, broad reasoning, or beyond-human capability.

The next cycle should reduce dependence on builder-provided typed observations by adding a native raw-text sensing/chunking rail with ablations.
