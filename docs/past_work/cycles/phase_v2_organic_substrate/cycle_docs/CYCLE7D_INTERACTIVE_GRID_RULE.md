# Cycle 7D Interactive Grid Rule Rung

Date: 2026-05-14
Status: closed implementation evidence for the first tiny spatial/grid interactive rung.

## Claim

Cycle 7D moves organic-v0 from typed symbolic entity attributes to a tiny 3x3 grid/state world.

The organism now has a cue-bound grid/spatial sense:

- observations can contain cells such as `cell_0_0:red` and `cell_0_2:red`
- the encoder exposes spatial relation addresses such as `horizontal_mirror:yes`, `vertical_mirror:no`, `diagonal_mirror:yes`, and `row_shift:no`
- those addresses bind only to matching cue tokens such as `horizontal`, `vertical`, `diagonal`, and `row`
- arbitrary action labels are learned from feedback after the raw action

This is a substrate claim. It is not ARC competence, natural chat, poetry, philosophy, math, physics, a complete neural organism, or beyond-human intelligence.

## Mechanism

Implemented in `native/organic_v0.cpp` as:

- `use_grid_spatial_features`
- `grid_spatial_gain`
- `--ablate-grid-spatial`
- `--phase interactive-grid-rule`
- `--phase interactive-grid-probe`

The channel parses only cell roles shaped like `cell_<row>_<col>` for a 3x3 grid. Non-empty matching marker pairs can activate:

- horizontal mirror across the vertical axis
- vertical mirror across the horizontal axis
- main-diagonal mirror
- adjacent row shift

The relation channel is a sense, not an answer route. There is no code path from `horizontal_mirror:yes` to `haxo`, or from `row_shift:no` to `bask`. Action text still comes from learned weights.

## Harness

Primary command shape:

```bash
build/organic_v0 --phase interactive-grid-rule \
  --scenario-seed 7201 \
  --action-budget 64 \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
  --save-state run/state/organic-v0/snapshots/raphael-local-0001/cycle7d-grid-seed7201.pxstate \
  --event-log run/state/organic-v0/events/raphael-local-0001-cycle7d-grid-seed7201.jsonl \
  --out run/artifacts/organic-v0/interactive_grid_rule_cycle7d_seed7201.json
```

Families:

- `horizontal_mirror`
- `vertical_mirror`
- `diagonal_mirror`
- `row_shift`

The oracle action is not included in generation input or observations. Feedback is learned only after the raw action.

## Evidence

Aggregate artifact:

- `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_summary.json`

Seed artifacts:

- `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_seed7201.json`
- `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_seed7202.json`

From-disk probe artifacts:

- `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_probe_seed7201.json`
- `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_probe_seed7202.json`

Ablation artifact:

- `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_grid_ablation.json`

Aggregate score:

- total pre-feedback actions: 48/64 exact (`0.750000`)
- support pre-feedback actions: 32/48 exact (`0.666667`)
- held-out pre-feedback actions: 16/16 exact (`1.000000`)
- post-episode probes: 16/16 exact (`1.000000`)
- from-disk probe summary + model hash match: true for both seeds

Per seed:

- seed 7201: held-out 8/8, total 24/32, support 16/24, post-episode probe 8/8, final hash `93032ff81f0bc258`
- seed 7202: held-out 8/8, total 24/32, support 16/24, post-episode probe 8/8, final hash `ba359ad133fe4d3a`

Failure traces are preserved:

- seed 7201: 8 pre-feedback failures
- seed 7202: 8 pre-feedback failures

## Ablation

Artifact:

- `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_grid_ablation.json`

Baseline all-on:

- held-out: 16/16 (`1.000000`)
- total: 48/64 (`0.750000`)

Ablated with `--ablate-grid-spatial`:

- held-out: 3/16 (`0.187500`)
- total: 6/64 (`0.093750`)

Delta:

- held-out exact: -13
- total exact: -42

This isolates the cue-bound grid/spatial channel as load-bearing.

## Regression Gates

After implementation:

- `make test`: PASS, persistence hash `29958f0880e662dc`, output `"mila quartz pier6"`
- cycle-6 regression: 30/30 (`1.000000`), hash `29958f0880e662dc`
- manifesto-safe live chat: 1/5 (`0.200000`), hash `888b7664126b7f5f`
- legacy cycle-2 snapshot on cycle-5 fixture: 9/25 (`0.360000`), hash `3536309de837d3e2`, raw `"milaquart arch6"`
- Cycle 7B numeric interactive regression: seeds 7001/7002 remain 7/7 held-out exact
- Cycle 7C symbolic interactive regression: seeds 7101/7102 remain 8/8 held-out exact

## Anti-Repetition Guard

Cycle 7D should not be used as an excuse to keep adding isolated micro-puzzle channels forever. It closes a small spatial rung because ARC-like state needs spatial substrate. The next major direction should move toward the durable experience database and organic text-learning rail:

- raw text input
- generated output
- feedback/correction
- state mutation
- replayable event records
- from-disk continuation

The goal is coherent language from learned state, not an endless ladder of small puzzle patches.

## Interpretation

The result is stronger than Cycle 7C in one narrow way: the relation is derived from positions in a grid-like observation instead of directly typed attribute pairs.

The result remains small. It shows that organic-v0 can learn arbitrary action labels through a tiny spatial relation sense and transfer to held-out grid layouts after feedback. It does not show ARC competence, human-like conversation, general reasoning, or a complete neural brain.
