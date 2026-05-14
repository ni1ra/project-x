# Cycle 7B Interactive Hidden Rule Micro-Harness

Date: 2026-05-14
Status: closed implementation evidence for the first local interactive hidden-rule rung.

## Claim

Cycle 7B moves organic-v0 beyond offline JSONL evaluation into a small action/feedback environment.

The organism now runs a native `interactive-hidden-rule` phase where it:

1. loads a parent checkpoint
2. receives one observation at a time
3. emits a raw action before seeing the oracle answer
4. receives feedback after the action
5. learns the feedback into the same state
6. continues to later steps in the same episode
7. writes action history, scorecard, failure traces, state growth, and hashes

The claim is local and bounded: numeric hidden-rule micro-rules with online feedback. It is not ARC-grid competence, natural language fluency, or general planning.

## Harness Design

Implemented in `native/organic_v0.cpp` as phase:

```bash
build/organic_v0 --phase interactive-hidden-rule \
  --scenario-seed 7001 \
  --action-budget 64 \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
  --save-state run/state/organic-v0/snapshots/raphael-local-0001/cycle7b-ihr-seed7001.pxstate \
  --event-log run/state/organic-v0/events/raphael-local-0001-cycle7b-ihr-seed7001.jsonl \
  --out run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_seed7001.json
```

Rule families:

- parity over `mark:*`
- threshold over `mark:*` and `cutoff:*`
- modular class over `mark:*` and `modulus:3`

The input and observations expose numeric fields, not class labels. The action target is not available until after generation. The oracle grades and provides correction only after the raw action.

The environment deliberately uses new arbitrary action labels:

- parity: `dax` / `mira`
- threshold: `luma` / `keto`
- modular: `zun` / `pax` / `rilo`

This prevents the loaded v2-c6 parent from simply reusing old labels such as `stay`, `go`, `above`, `below`, `zeal`, `moon`, or `nova`. The first support steps therefore preserve real pre-feedback mistakes.

## Plasticity Correction

The first harness attempt exposed a useful failure: wrong feedback was underweighted because the feedback event reward averaged `oracle_feedback=1.0` with `pre_feedback_success=0.0`, halving correction exactly when the model was wrong.

Cycle 7B fixed this by making the feedback learning event carry only oracle feedback, then setting correction strength to `2.0`. This is reward machinery, not an answer route: the correct output is still unavailable before action, and the learned state still emits later actions.

## Evidence

Aggregate artifact:

- `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_summary.json`

Seed artifacts:

- `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_seed7001.json`
- `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_seed7002.json`

Parent:

- checkpoint: `run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate`
- parent hash: `29958f0880e662dc`

Aggregate score:

- total pre-feedback actions: 26/42 exact (`0.619048`)
- support pre-feedback actions: 12/28 exact (`0.428571`)
- held-out pre-feedback actions: 14/14 exact (`1.000000`)

Per seed:

- seed 7001: 13/21 overall, 7/7 held-out, 8 support failure traces, final hash `879b7e4f6295fc12`
- seed 7002: 13/21 overall, 7/7 held-out, 8 support failure traces, final hash `030516a10354131a`

Per family, each seed:

- parity held-out: 2/2
- threshold held-out: 2/2
- modular held-out: 3/3

Regression gates after implementation:

- `make test`: PASS, persistence hash `29958f0880e662dc`, output `"mila quartz pier6"`
- cycle-6 regression: 30/30 (`1.000000`), hash `29958f0880e662dc`
- manifesto-safe live chat: 1/5 (`0.200000`), hash `888b7664126b7f5f`
- legacy cycle-2 snapshot on cycle-5 fixture: 9/25 (`0.360000`), hash `3536309de837d3e2`, raw `"milaquart arch6"`

Feedback-strength ablation:

- Artifact: `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_feedback_ablation.json`
- Baseline `--feedback-strength 2.0`: 14/14 held-out, 26/42 total
- Ablated `--feedback-strength 1.0`: 13/14 held-out, 15/42 total
- Delta: -1 held-out exact, -11 total exact

This makes the adaptation claim more falsifiable: stronger correction pressure is load-bearing when the loaded parent initially prefers old labels.

## Negative Space

Cycle 7B does not add:

- response templates
- parser-dispatcher action routes
- target-output features before action
- hidden class labels in observations
- benchmark-specific answer branches
- frontend fallback behavior
- a natural-language chat improvement

The oracle is allowed to grade and provide correction after action. It is not in the generation path.

## Interpretation

The interesting result is not the support score. Support actions are intentionally scored before the model has feedback, so old v2-c6 priors often produce wrong labels first. The interesting result is that after support feedback mutates the same loaded parent state, held-out marks in the same rule family score 14/14 across two seeds.

This shows:

- state/action/feedback history matters
- oracle feedback is learned into the same checkpoint state
- old priors can be overridden by stronger correction pressure
- held-out transfer can happen inside an interactive episode
- failure traces preserve the cost of exploration and adaptation

## Falsification

The 7B claim would be weakened or false if:

- target actions appeared in observations before generation
- action history did not record raw pre-feedback outputs
- held-out actions were scored after feedback rather than before
- event logs lacked generate/learn ordering
- support failures were hidden
- lowering correction strength had no measurable effect
- cycle-6, chat, or legacy regression gates moved silently

## What Remains

This is still a typed numeric micro-harness. The next rung should be harder:

- non-numeric hidden rules
- randomized action vocabularies
- longer episodes with delayed reward
- explicit hypothesis/action budgets
- ARC-like grid observations where the rule is not a single numeric relation
- ablations for correction strength and loaded-parent interference
