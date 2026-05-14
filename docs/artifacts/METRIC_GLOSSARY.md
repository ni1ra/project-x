# Metric Glossary

Date: 2026-05-14
Status: plain-English definitions for recurring Project X artifact metrics.

## Why These Metrics Exist

The early organic-v0 runs are not intelligence claims. They are mechanism tests.

The goal is to prove that a specific learned substrate change is real, persisted, and not explained by an older shortcut. A metric is useful only when it says what changed, what did not change, and what could falsify the claim.

## Interactive Metrics

`support`

Early examples inside an interactive episode. Raphael acts before feedback, then receives the oracle correction. Mistakes here are expected and should stay visible. Support score answers:

> How much did the organism already know before enough episode feedback existed?

`held-out`

Later examples in the same episode, still scored before feedback for those examples. The organism has learned from support feedback, but has not seen the answer to the held-out action yet. Held-out score answers:

> Did feedback mutate state in a way that transfers to new cases?

`total`

All pre-feedback actions in the episode: support plus held-out. Total is useful for seeing overall behavior, but held-out is the cleaner transfer signal.

`post-episode probe`

Extra test cases generated after the episode without learning from those probe cases. This checks whether the final mutated state can answer fresh examples after interaction.

`from-disk probe`

A child brain file is saved, loaded by a fresh process, and tested on the same probe shape. This answers:

> Did the learned behavior survive restart, or was it only an in-memory effect?

`failure traces`

Raw mistakes, with inputs, observations, raw output, expected output, and state hashes. These prevent clean scores from hiding exploration cost or adaptation failures.

## Ablation Metrics

`ablation`

Run the same task with one mechanism turned off. If the score barely changes, the new mechanism did not explain the result. If the score collapses in the targeted family, the mechanism is load-bearing.

Examples:

- `--ablate-symbolic-relations`: disables Cycle 7C symbolic same/different relation features
- `--ablate-grid-spatial`: disables Cycle 7D grid/spatial features
- `--ablate-text-experience-learning`: disables Cycle 7E correction-driven learning from the text experience database

The desired pattern is:

> all-on succeeds, ablation fails, unrelated regressions stay green.

## Text Experience Metrics

`train-before`

The raw output on a training text record before the correction is learned. This answers:

> What did the existing brain already say before this experience changed state?

`train-after`

The raw output on the same training text after correction mutates state. This answers:

> Did the correction actually change the learned state enough to affect generation?

`probe`

Held-out text experience records scored after training records have been learned. The probe records are not learned during scoring. This answers:

> Did the text experience stream transfer to new text records?

`from-disk probe`

The saved child checkpoint is loaded by a fresh process and scored on the same probe records without replaying training records. This answers:

> Did the text behavior survive restart?

`ablation probe`

The same text rail is run with correction learning disabled. This answers:

> Was the result carried by state mutation from experience, or by an unchanged parent/model shortcut?

`replay-before`

The selected record's raw output immediately before a replay candidate is tested. This answers:

> What would the current consolidated brain say before another pass over this stored correction?

`replay-after`

The selected record's output from the replay candidate. If the candidate is rejected, this output is preserved as the rejected candidate behavior rather than the live child behavior. This answers:

> What would replay have changed?

`post-replay probe`

Held-out text records scored after accepted replay candidates. This answers:

> Did replay preserve or damage transfer?

`acceptance-audit ablation`

Run replay while disabling the candidate-acceptance guard. This answers:

> Is the replay self-audit actually protecting generalization, or is blind replay harmless?

## Raw Text Sense Metrics

`raw-span all-on`

Text experience run with `--derive-raw-text-spans`. The raw input is tokenized and contiguous spans are appended as observations. This answers:

> Can the organism use generic chunks from raw input text as learned copyable substrate?

`raw-span ablation`

The same run with `--ablate-raw-text-spans`. This answers:

> Did the result depend on the raw-span sense, or would the remaining raw utterance field carry it alone?

`typed-reference comparison`

Compare raw-span results with the typed Cycle 7E text rail. This answers:

> How close is the raw-span scaffold to the older builder-provided typed scaffold on the same kind of text task?

## Regression Rails

`cycle-6 regression`

The older numeric relation benchmark. Expected: 30/30 and state hash `29958f0880e662dc`. This catches accidental breakage to parity/threshold/modular relation behavior.

`clean chat rail`

The manifesto-safe raw chat regression. Expected today: 1/5 and state hash `888b7664126b7f5f`. This is intentionally weak. It stays visible so no one pretends Raphael is already fluent.

`legacy cycle-2 rail`

A historical snapshot loaded by the current binary. Expected: 9/25, hash `3536309de837d3e2`, and raw output `"milaquart arch6"` on `evt_mem_test_001`. This catches snapshot compatibility breakage.

## What These Metrics Do Not Mean

They do not prove:

- GPT/Claude-style chat
- natural opinions
- poetry or philosophy
- math or physics competence
- ARC competence
- a complete neural organism
- beyond-human capability

They prove only the named mechanism under the named harness. The next architectural step is not more isolated metrics forever; it is a durable experience database and organic text-learning rail where text input, feedback, generated output, and state mutations become reusable training experience.
