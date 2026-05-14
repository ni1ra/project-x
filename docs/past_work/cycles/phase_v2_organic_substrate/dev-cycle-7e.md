# Dev Cycle 7E - Text Experience Rail

Date: 2026-05-14
Branch: `feat/organic-v0-trace-id-ablation`

## Scope

Cycle 7E answered the architecture correction against repetition hell by moving from isolated puzzle rungs to a durable text-experience rail.

Added:

- `experience/organic-v0/text_experience_seed_v0.jsonl`
- `--phase text-experience`
- `--phase text-experience-probe`
- `--experience-db`
- `--transcript-out`
- `--ablate-text-experience-learning`
- pre-implementation learnability audit
- text experience schema documentation
- all-on, from-disk, ablation, transcript, and summary artifacts

## Result

Primary artifact:

- `run/artifacts/organic-v0/text_experience_cycle7e_summary.json`

All-on:

- train-before: 1/6 (`0.166667`)
- train-after: 4/6 (`0.666667`)
- probe: 4/4 (`1.000000`)
- child hash: `be0fc781039a2038`

Fresh loaded child:

- probe: 4/4 (`1.000000`)
- loaded hash: `be0fc781039a2038`
- same-process probe + model hash diff-clean: true

Ablation:

- artifact: `run/artifacts/organic-v0/text_experience_cycle7e_ablate_learning.json`
- `--ablate-text-experience-learning` probe: 0/4 (`0.000000`)
- state growth: zero
- hash remains parent `29958f0880e662dc`

## Regression Gates

Passed after implementation:

- `make test`
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, raw `"milaquart arch6"`
- Cycle 7B numeric interactive regression: seed 7001 7/7 held-out, seed 7002 7/7 held-out
- Cycle 7C symbolic interactive regression: seed 7101 8/8 held-out and 8/8 probe, seed 7102 8/8 held-out and 8/8 probe
- Cycle 7D grid interactive regression: seed 7201 8/8 held-out and 8/8 probe, seed 7202 8/8 held-out and 8/8 probe

## Honest Interpretation

This is a real substrate step: raw text interaction records can now become durable learning experience, with before/after output preserved, state mutation measured, child checkpoint saved, and fresh loaded-child generation verified.

It is not fluent chat. The clean chat rail remains 1/5. The Cycle 7E transcript itself preserves failures: two immediate train-after rows are still wrong. That is the correct honesty boundary.

The next cycle should extend this rail with replay/consolidation over failed or weak text records, not return to isolated puzzle patching.
