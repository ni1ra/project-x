# Cycle 7F Learnability Audit

Date: 2026-05-14
Status: pre-implementation audit for text-experience replay and consolidation.

## Target

Cycle 7F should turn the Cycle 7E text-experience rail from one-pass ingestion into a primitive consolidation loop.

The organism should:

- ingest the same durable text experience database
- preserve raw first-pass outputs
- identify failed or weak training records after first-pass correction
- replay selected records through the same learned state mutation path
- preserve replay decisions and before/after outputs
- save a consolidated child
- reload the child from disk and probe without replaying the stream
- include a replay-disabled ablation

The goal is not to make chat fluent. The goal is to make durable language experience accumulate and self-correct through state.

## Missing Evidence

Cycle 7E proved that the text rail is durable and load-bearing:

- all-on probe: 4/4
- from-disk probe: 4/4 with matching child hash
- learning-disabled ablation: 0/4

But the transcript also preserved weak rows:

- train-after: 4/6
- two immediate post-correction training records still generated bad text

That is the right next target. A serious organism cannot merely store a correction once; it needs a way to revisit weak experience and strengthen it without a scripted answer path.

## Allowed Mechanism

The builder may add:

- a native replay/consolidation phase over text experience records
- a selection policy based on already-generated failure or sequence-ratio evidence
- repeated `OrganicBrain::learn` calls for selected training records
- replay event-log rows
- transcript rows that show why each record was replayed
- a replay-disabled ablation flag
- from-disk probes before and after replay

Replay is allowed because it is state mutation from stored experience, not answer composition.

## Forbidden Mechanism

Cycle 7F must not add:

- hand-authored fixes for `arin carries copper key`
- per-record answer branches
- templates for carry/place sentences
- intent detection trigger lists
- answer dispatchers
- target-output access during probe generation
- frontend fallback or cleanup
- pretrained or remote inference

If replay worsens a record, that failure must remain visible.

## Replay Selection

The first replay selector should be simple and auditable:

- replay training records whose post-first-pass output is not exact
- optionally replay records whose sequence ratio is below a fixed threshold
- do not replay probe records
- do not read oracle target during probe generation

The selector may use the correction output for training records because those are already feedback records. It must not use target output to produce probe text directly.

## Required Falsification

The all-on replay run should produce:

- first-pass train-before and train-after metrics
- replay selection list
- replay-before and replay-after outputs for selected records
- post-replay train metrics
- pre-replay and post-replay probe metrics
- saved consolidated child hash
- fresh loaded-child post-replay probe artifact
- replay transcript

The replay-disabled ablation should log the same selected records but skip state mutation. It should fail to improve the selected training records and should preserve zero replay state growth.

Existing rails must remain visible:

- Cycle 7E text rail
- Cycle 7D grid interactive
- Cycle 7C symbolic interactive
- Cycle 7B numeric interactive
- cycle-6 regression
- clean chat regression
- legacy cycle-2 compatibility

## Metric Translation

- `first_pass_train_after`: score after the initial correction pass.
- `replay_selected`: number of failed or weak training records chosen for replay.
- `post_replay_train`: training-record score after replay.
- `pre_replay_probe`: held-out text score before replay.
- `post_replay_probe`: held-out text score after replay.
- `from_disk_post_replay_probe`: saved child score after restart.
- `replay_ablation`: same selection list, but replay mutation disabled.

These are not chat quality scores. They are evidence about whether stored text experience can be revisited and consolidated through learned state.

## Interpretation Boundary

A passing Cycle 7F would prove only this:

> organic-v0 can select weak text experience records after a first pass, replay them into learned state, preserve the replay trace, save a consolidated child, and reproduce the post-replay behavior from disk; disabling replay mutation prevents that consolidation.

It would not prove natural conversation, opinions, poetry, philosophy, math, physics, broad reasoning, a complete neural brain, or beyond-human intelligence.
