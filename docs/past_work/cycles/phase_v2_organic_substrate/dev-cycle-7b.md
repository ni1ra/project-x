# Phase v2 Organic Substrate - Cycle 7B reflection

**Theme:** Interactive hidden-rule micro-harness
**Closed:** 2026-05-14
**Implementer:** Codex GPT-5

## Context

Cycle 7A proved that a parent checkpoint can grow into reloadable divergent children. The next rung was interaction: the organism needed to act, receive feedback, mutate state, and use that state later in the same episode.

Cycle 7B implements the first local version of that rung inside the native runtime.

## What shipped

### Native interactive phase

`build/organic_v0 --phase interactive-hidden-rule` runs a small hidden-rule environment:

- load optional parent state
- generate one raw action from current observations
- grade only after action
- learn oracle feedback into the same state
- continue through support and held-out steps
- write action history, failure traces, scorecards, state hashes, state growth, event logs, and optional child checkpoint

No Python harness owns the loop.

### Rule families

The first environment covers three numeric rule families:

- parity over `mark:*`
- threshold over `mark:*` + `cutoff:*`
- modular class over `mark:*` + `modulus:3`

The observations do not expose the class label. New arbitrary action labels prevent the v2-c6 parent from passing by emitting old benchmark words.

### Feedback plasticity fix

The first run exposed a harness reward bug. Failed feedback had `oracle_feedback=1.0` and `pre_feedback_success=0.0`; organic-v0 averages reward keys, so the correction signal was halved exactly when the model was wrong.

The fix was to make the feedback learning event carry oracle correction strength only, set to `2.0`. This is reward machinery, not a response route.

## Measurement

Artifacts:

- `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_summary.json`
- `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_seed7001.json`
- `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_seed7002.json`

Parent:

- `run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate`
- hash `29958f0880e662dc`

Aggregate over seeds 7001 and 7002:

- total pre-feedback actions: 26/42 (`0.619048`)
- support pre-feedback actions: 12/28 (`0.428571`)
- held-out pre-feedback actions: 14/14 (`1.000000`)

Each seed:

- 13/21 overall
- 7/7 held-out
- 8 support failure traces

Each seed by family:

- parity held-out: 2/2
- threshold held-out: 2/2
- modular held-out: 3/3

Regression gates:

- `make test`: PASS, hash `29958f0880e662dc`, output `"mila quartz pier6"`
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- manifesto-safe chat regression: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 snapshot on cycle-5 fixture: 9/25, hash `3536309de837d3e2`, raw `"milaquart arch6"`

## What this proves

Organic-v0 now has a local action/feedback harness. The model acts before the oracle answer, then feedback mutates the same state and later held-out steps use that mutation. This is materially stronger than offline train/eval JSONL.

The support failures are part of the evidence. They show the loaded v2-c6 parent initially emits old labels such as `go`, `stay`, `zeal`, `moon`, and `nova`. After feedback, held-out steps switch to the new labels.

## What this does not prove

This is not ARC-grid competence. The rules are still typed numeric relations and the episodes are short.

This is not natural language fluency. The clean chat regression remains 1/5.

This is not a claim that all old priors are solved. It shows a correction strength that can override them inside this harness.

## Falsification

The claim would fail if:

- oracle targets were visible before action
- support failures were omitted
- held-out scoring happened after feedback
- event logs lacked generate-before-learn ordering
- regressions moved silently
- a benchmark-specific branch selected the answer text

## Self-impression score

**372 / 420.**

This crosses a real boundary: action under feedback with state mutation and held-out transfer. It is not 400+ because the environment is still tiny, numeric, and engineered around existing relation senses.

## Next direction

Move from numeric hidden rules to a less typed environment:

- symbolic same/different
- small grid transformations
- delayed reward
- randomized action vocabularies
- explicit ablation of correction strength and parent-prior interference
