# Cycle 7D Learnability Audit

Date: 2026-05-14
Status: pre-implementation audit for the tiny grid transformation rung.

## Target

Cycle 7D should move from typed symbolic entity attributes to a small grid/state world. The organism should receive 3x3 cell observations, act before oracle feedback, learn arbitrary action labels after feedback, and transfer to held-out grid layouts.

The intended rung is still tiny:

1. observe a symbolic grid through cell observations such as `cell_0_0:red`
2. expose spatial relation addresses such as horizontal mirror, vertical mirror, diagonal mirror, and row shift
3. bind those addresses to the current cue token
4. learn arbitrary action labels only from feedback
5. verify held-out layouts and from-disk child probes

This is a micro-world on the path toward ARC-like benchmarks. It is not ARC competence.

## Missing Evidence

Cycle 7C proved non-numeric same/different transfer, but the world was still typed as direct entity attributes:

- `left_color:red`
- `right_color:red`
- `source_symbol:ion`
- `target_symbol:ion`

That does not test spatial state. A grid rung must force the organism to derive a relation from positions in a board-like observation rather than from attribute-role names alone.

Without a grid/spatial sense, held-out layouts should collapse toward old labels or surface token priors. With the sense enabled, feedback can attach arbitrary action labels to spatial relation addresses.

## Allowed Mechanism

The builder may add encoder-side grid/spatial features:

- parse cell roles shaped like `cell_<row>_<col>`
- infer fixed-size 3x3 spatial relation keys from occupied cell pairs
- expose cue-bound features such as `horizontal|horizontal_mirror:yes`
- add HDC atoms for the same cue-bound spatial relation keys
- add a CLI ablation flag that disables the grid/spatial channel

These are senses, not answers. They must not map any spatial relation to an action label.

## Forbidden Mechanism

Cycle 7D must not add:

- mirror -> action branches
- rotate -> action branches
- row-shift -> action branches
- direct solver-as-agent routes
- grid-specific answer templates
- target-action leakage before generation
- a Python answer path
- frontend fallback behavior
- pretrained or remote inference

The oracle may grade and correct only after raw action.

## Benchmark Shape

Use at least two seeds. Candidate families:

- `horizontal_mirror`: whether two matching markers are mirror-paired across the vertical axis
- `vertical_mirror`: whether two matching markers are mirror-paired across the horizontal axis
- `diagonal_mirror`: whether two matching markers mirror across the main diagonal
- `row_shift`: whether two matching markers are adjacent in a row

Each family should include both yes/no support classes before held-out probes. Held-out probes should use layouts and marker values not used in support where possible. Numeric-derived channels must not carry the task: coordinates may appear in cell role names, but the cell fillers should be non-numeric symbols.

## Required Falsification

The all-on run should produce:

- action history
- support/pre-feedback mistakes
- held-out score across at least two seeds
- post-episode probes
- fresh loaded-child probe artifacts
- state growth and hashes
- event log paths

The ablated run with `--ablate-grid-spatial` should degrade on the grid families. Cycle 7C symbolic, Cycle 7B numeric interactive, cycle-6, clean-chat, and legacy rails must remain visible and green.

## Interpretation Boundary

A passing Cycle 7D would prove only this:

> organic-v0 can use a tiny grid/spatial feature channel as a learnable substrate address during interactive action/feedback, and the learned state can transfer to held-out grid layouts.

It would not prove ARC competence, natural language, general planning, a complete neural brain, or beyond-human reasoning. Those remain manifesto targets and must be built through learned persistent machinery, not hardcoded routes.
