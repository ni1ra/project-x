# Phase v2 Organic Substrate - Cycle 7A reflection

**Theme:** Continuation learning as first-class substrate primitive
**Closed:** 2026-05-14
**Implementer:** Codex GPT-5

## Context

Cycle 6 closed the offline numeric-relation rung at 30/30 with clean ablation isolation, but the organism claim still needed a stricter persistence proof. A saved checkpoint was loadable, but continuation learning was not yet a fully documented contract:

- load parent checkpoint
- learn new events
- write an event log
- save child checkpoint
- evaluate child before and after restart
- show two children diverging from different experience

Cycle 7A stayed on that substrate problem and did not start the interactive hidden-rule rung.

## What shipped

### Continuation eval path

`eval --load-state <parent> --save-state <child>` now loads the parent, learns the train split, saves the child, and evaluates held-out events from the in-memory child. The artifact records:

- `parent_model_state_hash`
- `parent_model_state`
- `model_state`
- `state_growth`
- persistence status `loaded_then_learned_and_saved`

This provides the same-process "child from-training" artifact needed to compare against a fresh loaded-child eval.

### Continuation persistence self-test

`persistence-self-test --load-state <parent> --save-state <child>` now supports the same continuation path. The parent process loads the parent, learns the train split, saves the child, and spawns a child process that loads the child checkpoint and verifies hash + output.

The artifact now includes the loaded parent state, saved child state, growth deltas, and the fresh child verdict.

### Fork-divergence fixtures

Two tiny fork streams were added:

- `benchmarks/v2_ladder/organic_cycle7a_fork_a.jsonl`
- `benchmarks/v2_ladder/organic_cycle7a_fork_b.jsonl`

They use the same parent, same probe shape, and same explicit observation, but reward different outputs. This is intentionally not a broad cognition benchmark. It is a controlled persistence test: different lives should produce different files and different behavior.

## Measurement

Regression gates:

- `make test`: PASS, persistence hash `29958f0880e662dc`, output `"mila quartz pier6"`
- cycle-6 eval: 30/30 (`1.000000`), hash `29958f0880e662dc`

Child A:

- from-training artifact: `run/artifacts/organic-v0/eval_cycle7a_child_a_from_training.json`
- from-disk artifact: `run/artifacts/organic-v0/eval_cycle7a_child_a_from_disk.json`
- exact: 1/1 both ways
- state hash: `fab9c2c0367ed2b5`
- raw held-out output: `"aurora branch"`
- growth: +2 traces, +736 connection features, +1049 nonzero connections

Child B:

- from-training artifact: `run/artifacts/organic-v0/eval_cycle7a_child_b_from_training.json`
- from-disk artifact: `run/artifacts/organic-v0/eval_cycle7a_child_b_from_disk.json`
- exact: 1/1 both ways
- state hash: `c0f016285e735e14`
- raw held-out output: `"ember branch"`
- growth: +2 traces, +703 connection features, +962 nonzero connections

Fork verdict:

- artifact: `run/artifacts/organic-v0/fork_divergence_cycle7a.json`
- parent hash: `29958f0880e662dc`
- child A hash != child B hash
- child A raw output != child B raw output
- both children reload from disk with matching `summary_metrics + model_state_hash`

Fresh-process child persistence:

- artifact: `run/artifacts/organic-v0/persist_self_test_cycle7a_child.json`
- loaded parent hash: `29958f0880e662dc`
- saved child hash: `fab9c2c0367ed2b5`
- child loaded hash: `fab9c2c0367ed2b5`
- `hash_match`: true
- `output_match`: true

Legacy compatibility:

- artifact: `run/artifacts/organic-v0/eval_cycle7a_legacy_cycle2_cycle5_fixture.json`
- `/tmp/cycle2.pxstate` on `/tmp/organic_v0_cycle5_fixture.jsonl`
- 9/25 (`0.360000`)
- state hash `3536309de837d3e2`
- `evt_mem_test_001` raw output `"milaquart arch6"`

## What this proves

The brain file can now be treated as a durable body, not just an export artifact. A parent checkpoint can be loaded, changed by new experience, saved as a child, reloaded in a separate process, and compared against another child that lived through a different stream.

The strongest claim is fork divergence under shared parent:

- same parent
- different rewarded streams
- different child hashes
- different held-out outputs
- reload parity for each child

## What this does not prove

This does not prove natural language fluency. The manifesto-safe live-chat fork remains 1/5.

This does not prove hidden-rule interaction, exploration, or action-under-feedback. Cycle 7B should still move to the local ARC-style or hidden-rule micro-harness.

This does not prove that bigger files are smarter. The child files grew because they gained traces and connections, but future cycles must tie growth to behavior, compression/parsimony, and harder held-out tasks.

## Falsification

Cycle 7A would be false or weakened if:

- child from-training and child from-disk evals differed on `summary_metrics + model_state_hash`
- the child persistence self-test failed hash or output match
- child A and child B produced the same state hash
- child A and child B produced the same held-out raw output
- cycle-6 regression no longer reached 30/30 with hash `29958f0880e662dc`
- cycle-2 legacy snapshot behavior changed

## Self-impression score

**344 / 420.**

This is a real organism-continuity primitive: the checkpoint grows, survives restart, and forks into different descendants under different experience. It is not 400+ because the fork task is tiny and non-interactive. The next 420-class attempt must force unknown-rule exploration with action history and feedback.

## Next direction

Commit 7A, then start cycle 7B: a local interactive hidden-rule micro-harness with hidden rules, observations, actions, feedback after each step, action budget, held-out seeds/rules, scorecards, and failure traces.
