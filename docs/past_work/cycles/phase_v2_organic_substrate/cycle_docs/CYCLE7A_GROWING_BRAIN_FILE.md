# Cycle 7A Growing Brain File

Date: 2026-05-14
Status: closed design and evidence for continuation learning as a first-class organic-v0 substrate primitive.

## Claim

Cycle 7A makes the Growing Brain File Law mechanically testable for organic-v0:

1. load a parent checkpoint from disk
2. ingest new rewarded events
3. append per-event learning records to the event log
4. save a child checkpoint
5. evaluate the child before and after restart
6. prove two children from the same parent diverge when they live through different event streams

This is a substrate-continuity claim. It is not a fluency claim, not an ARC claim, and not a broad intelligence claim.

## Mechanism

The runtime already had `--load-state`, `--save-state`, `--event-log`, and PXSTATE serialization. Cycle 7A tightens the orchestration contract:

- `train --load-state <parent> --save-state <child>` loads a parent brain, learns the train split, appends learn events, saves the child, and reports `parent_model_state`, `model_state`, and `state_growth`.
- `eval --load-state <parent> --save-state <child>` now performs same-process continuation: load parent, learn train split, save child, then evaluate held-out events from the continued child. This creates the "child from-training" eval artifact.
- `eval --load-state <child>` evaluates the saved child in a fresh process path without replaying parent+train events. This creates the "child from-disk" eval artifact.
- `persistence-self-test --load-state <parent> --save-state <child>` now verifies continuation in the round-trip harness: parent process loads, learns, saves; child process loads the child checkpoint and must match hash + output.

The added state reports are structural counters, not intelligence scores:

- trace count
- connection feature count
- nonzero connection count
- slot-copy link count
- learned character count
- state hash

Growth is reported as child minus loaded parent. Raw bytes are reported in the fork-divergence artifact, but bytes alone are not scored as capability.

## Negative Space

Cycle 7A deliberately does not add:

- response templates
- semantic chat trigger labels
- parser-dispatcher answer paths
- benchmark-specific answer branches
- target-output features during eval
- a new relation channel
- a phrase/chunk dictionary
- a frontend fallback

The new fork fixtures reward different outputs, but the runtime does not inspect the target during held-out generation. The child output still comes from the saved learned state.

## Evidence

Baseline regression:

- Command: `make test`
- Result: PASS
- Persistence self-test output: hash `29958f0880e662dc`, raw output `"mila quartz pier6"`

Cycle-6 regression:

- Command: `build/organic_v0 --phase eval --out /tmp/eval_cycle6_regression.json`
- Result: 30/30 held-out exact (`1.000000`)
- State hash: `29958f0880e662dc`

Child A continuation:

- Stream: `benchmarks/v2_ladder/organic_cycle7a_fork_a.jsonl`
- From-training artifact: `run/artifacts/organic-v0/eval_cycle7a_child_a_from_training.json`
- From-disk artifact: `run/artifacts/organic-v0/eval_cycle7a_child_a_from_disk.json`
- Parent hash: `29958f0880e662dc`
- Child hash: `fab9c2c0367ed2b5`
- Held-out exact: 1/1 (`1.000000`)
- Held-out raw output: `"aurora branch"`
- Growth: +2 traces, +736 connection features, +1049 nonzero connections, +0 learned chars
- Diff gate: `summary_metrics + model_state_hash` match between from-training and from-disk

Child B continuation:

- Stream: `benchmarks/v2_ladder/organic_cycle7a_fork_b.jsonl`
- From-training artifact: `run/artifacts/organic-v0/eval_cycle7a_child_b_from_training.json`
- From-disk artifact: `run/artifacts/organic-v0/eval_cycle7a_child_b_from_disk.json`
- Parent hash: `29958f0880e662dc`
- Child hash: `c0f016285e735e14`
- Held-out exact: 1/1 (`1.000000`)
- Held-out raw output: `"ember branch"`
- Growth: +2 traces, +703 connection features, +962 nonzero connections, +0 learned chars
- Diff gate: `summary_metrics + model_state_hash` match between from-training and from-disk

Fork divergence:

- Artifact: `run/artifacts/organic-v0/fork_divergence_cycle7a.json`
- Parent bytes: 752,279
- Child A bytes: 796,722
- Child B bytes: 794,311
- `child_state_hashes_diverged`: true
- `held_out_outputs_diverged`: true
- `child_a.train_vs_disk_summary_and_hash_match`: true
- `child_b.train_vs_disk_summary_and_hash_match`: true

Fresh-process child verification:

- Artifact: `run/artifacts/organic-v0/persist_self_test_cycle7a_child.json`
- Loaded parent hash: `29958f0880e662dc`
- Saved child hash: `fab9c2c0367ed2b5`
- Child loaded hash: `fab9c2c0367ed2b5`
- `hash_match`: true
- `output_match`: true
- Parent/child raw output: `"aurora branch"`

Legacy compatibility:

- Artifact: `run/artifacts/organic-v0/eval_cycle7a_legacy_cycle2_cycle5_fixture.json`
- Snapshot path: `/tmp/cycle2.pxstate`
- Fixture path: `/tmp/organic_v0_cycle5_fixture.jsonl`
- Result: 9/25 exact (`0.360000`)
- State hash: `3536309de837d3e2`
- `evt_mem_test_001` raw output: `"milaquart arch6"`

## Interpretation

Cycle 7A proves a stricter persistence contract than earlier cycles. A child checkpoint is no longer just a file emitted after training. It is a loaded parent plus new experience, with measured state growth, reloadable behavior, and fork divergence under different histories.

The result would be falsified if:

- from-training and from-disk child evals differed on `summary_metrics` or `model_state_hash`
- child A and child B had the same state hash after different event streams
- child A and child B emitted the same raw held-out output on the fork probe
- the child persistence self-test failed hash or output match
- the cycle-6 regression stopped being 30/30 with hash `29958f0880e662dc`
- `/tmp/cycle2.pxstate` stopped reproducing the cycle-2 historical hash/output on the cycle-5 fixture

## What Did Not Improve

Natural chat did not improve in this cycle. The honest manifesto-safe chat fork remains 1/5 on `run/artifacts/organic-v0/eval_live_chat_v0_manifesto_from_v2c7_chat.json`.

Cycle 7A also does not test interactive hidden-rule exploration. That is the correct next rung after this commit: build the local ARC-style or hidden-rule micro-harness with state/action/feedback history, held-out seeds, action budgets, and failure traces.
