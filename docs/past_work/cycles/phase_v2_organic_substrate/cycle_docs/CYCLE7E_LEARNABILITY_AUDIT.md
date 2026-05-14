# Cycle 7E Learnability Audit

Date: 2026-05-14
Status: pre-implementation audit for the durable text experience rail.

## Target

Cycle 7E should stop the drift toward endless isolated micro-rungs and add a first durable text-experience database path.

The organism should be able to read an append-only record of:

- raw text input
- raw output before correction
- correction or reward feedback
- event IDs and source trails
- learned state mutation
- replayable training records
- child checkpoint save
- fresh process reload and probe

This is not a claim that Raphael can chat like GPT or Claude. It is the substrate step needed before that claim can be earned honestly: text interactions must become durable experience instead of one-off benchmark rows or a frontend mask.

## Missing Evidence

The current repo has strong small-rung evidence:

- Cycle 7B: typed numeric interactive hidden rules
- Cycle 7C: non-numeric symbolic same/different relation rules
- Cycle 7D: tiny 3x3 grid/spatial rules

Those are real mechanism tests, but they are not enough for organic language. They do not yet prove that ordinary text input can be stored as experience, corrected, replayed, saved into a child brain, and regenerated from disk without rerunning the correction stream.

The clean chat rail remains intentionally weak at 1/5. That weakness should stay visible. Cycle 7E should not hide it with templates or polish.

## Allowed Mechanism

The builder may add:

- a directly auditable text-experience JSONL store
- a native phase that ingests that stream
- raw-generation capture before learning
- correction-driven learning using existing event-learning machinery
- append-only event log emission
- child checkpoint save/load
- a probe phase that loads the child and generates without replaying the stream
- an ablation flag that disables text-experience learning
- transcript artifacts that show before/after raw outputs

The experience store may carry target corrections because it is a training record. The target must not be visible to generation before the action being scored.

## Forbidden Mechanism

Cycle 7E must not add:

- response templates
- greeting/farewell/identity trigger lists
- parser-dispatcher answer routes
- benchmark-specific chat answers
- a polished voice layer
- pretrained or remote inference
- frontend fallback behavior
- direct answer composition outside the learned state
- target-output leakage into probe generation

If fluent text and honest learned substrate conflict, the correct output is weak honest text with preserved failures.

## Database Shape

Use a small seed database because the goal is the rail, not fluency:

- `experience_id`
- `session_id`
- `split`: train or probe
- `input_text`
- `observations`: raw utterance and optional source tags
- `correction_output`
- `reward`
- `source`

The native rail should convert training records into ordinary organic-v0 events, learn them, and write an event log. Probe records should generate from state and score only after the raw output exists.

## Required Falsification

The all-on run should produce:

- per-record action history
- raw output before learning for train records
- raw output after learning for train records
- probe raw outputs
- exact score over probe records
- saved child state path and hash
- fresh loaded-child probe artifact
- transcript artifact readable without C++ knowledge
- event log path

The ablated run with text-experience learning disabled should degrade on the probe records. It is acceptable and expected for the ablated transcript to be bad.

Existing rails must remain visible:

- Cycle 7D grid interactive
- Cycle 7C symbolic interactive
- Cycle 7B numeric interactive
- cycle-6 regression
- clean chat regression
- legacy cycle-2 compatibility

## Metric Translation

For Cycle 7E, report metrics in plain English:

- `train_before_exact`: how often the uncorrected brain already said the correction before learning
- `train_after_exact`: how often the same training text is emitted after correction mutates state
- `probe_exact`: how often new held-out text records are answered from learned state
- `from_disk_probe_exact`: whether the saved child brain still answers after restart
- `ablation_probe_exact`: whether the score collapses when the learning rail is disabled

These are not intelligence scores. They are evidence about whether text experience became durable, load-bearing substrate.

## Interpretation Boundary

A passing Cycle 7E would prove only this:

> organic-v0 can ingest a small durable text-interaction experience stream, mutate learned state from corrections, preserve a transcript of before/after behavior, save a child checkpoint, and reproduce probe behavior from disk; disabling that learning path breaks the result.

It would not prove normal human conversation, opinions, poetry, philosophy, math, physics, complete neural autonomy, or beyond-human reasoning. Those remain manifesto targets and must be reached through accumulated learned state, replay, broader experience, and harder external verification.
