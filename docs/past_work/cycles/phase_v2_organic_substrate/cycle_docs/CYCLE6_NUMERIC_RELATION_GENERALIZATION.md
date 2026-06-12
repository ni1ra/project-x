# Cycle 6 Numeric Relation Generalization

Date: 2026-05-14
Status: closed implementation evidence for cycle 6. The learnability audit below was written before editing `benchmarks/v2_ladder/organic_v0.jsonl`.

## Claim Being Tested

Cycle 5 proved one computed numeric relation: parity-derived trace activation.

Cycle 6 tests whether the same substrate pattern can carry multiple computed
relation families without collapsing them into one parity-shaped channel.

The close criterion is not just an all-on score. The close criterion is a
falsification ladder:

- `--ablate-numeric-derived` breaks the original parity hidden-rule items while
  threshold and modular items still pass.
- `--ablate-threshold-derived` breaks threshold items while parity and modular
  items still pass.
- `--ablate-modular-derived` breaks modular items while parity and threshold
  items still pass.

If these isolate, the relation substrate is becoming computed-relation-general.
If the ablations couple, the honest result is that cycle 5 was still
parity-specific or namespace-collided.

## Learnability Audit

Adding threshold and modular held-out events is legitimate only if train events
provide enough relation evidence for organic-v0 to learn the output mapping
without pretrained math semantics or authored answer routes.

### Threshold

Relation: `mark > cutoff`.

Train evidence must include:

- the cutoff constant as an observation, e.g. `cutoff:5`
- explicit relation labels in training, e.g. `threshold:low` and
  `threshold:high`
- at least two distinct mark values per class
- target outputs repeated by class, not by exact mark

Held-out tests omit `threshold:*` and include unseen mark values. The substrate
must compute the relation from `mark:*` and `cutoff:*`.

Two-example minimum:

- low class: two distinct marks below cutoff
- high class: two distinct marks above cutoff

This prevents a one-value replay solution where a held-out item activates a
single memorized mark trace.

### Modular Class

Relation: `mark mod K`.

Train evidence must include:

- the modulus as an observation, e.g. `modulus:3`
- explicit class labels in training, e.g. `modclass:0`, `modclass:1`,
  `modclass:2`
- at least two distinct mark values per modular class
- target outputs repeated by class, not by exact mark

Held-out tests omit `modclass:*` and use unseen mark values. The substrate must
compute the class from `mark:*` and `modulus:*`.

Two-example minimum:

- class 0: two marks where `mark mod 3 == 0`
- class 1: two marks where `mark mod 3 == 1`
- class 2: two marks where `mark mod 3 == 2`

Parity is `mod 2`, so modular feature IDs must use a distinct namespace and
include the modulus value. `modulus:3` features must not reuse parity feature
IDs.

## Benchmark Design

Threshold train events:

- two low-class marks below/equal cutoff
- two high-class marks above cutoff
- target outputs: `below`, `above`

Threshold held-out events:

- unseen high mark with a low-class surface signal distractor
- unseen low mark with a high-class surface signal distractor

Modular train events:

- two examples per class for `modulus:3`
- target outputs: `zeal`, `moon`, `nova`

Modular held-out events:

- unseen class-0 mark with class-2 surface distractor
- unseen class-1 mark with class-0 surface distractor
- unseen class-2 mark with class-1 surface distractor

The distractors are intentional. If the derived relation channel is off, surface
retrieval should prefer the wrong class and the held-out events should fail.

## Mechanism Plan

Add two new derived feature families while preserving the cycle-5 parity flag:

- `use_numeric_derived_features`: legacy parity channel, controlled by
  `--ablate-numeric-derived`
- `use_threshold_derived_features`: threshold channel, controlled by
  `--ablate-threshold-derived`
- `use_modular_derived_features`: modular channel, controlled by
  `--ablate-modular-derived`

Each family emits:

- HDC latent atoms for retrieval shape
- context feature IDs for ordinary learned `CONNS`
- trace-id activation features for stored traces that share the computed
  relation

All learned outputs remain ordinary character weights. There is no code route
from relation to answer text.

## Negative Space

Do not add:

- `if mark > cutoff return above`
- `if mark % 3 == 0 return zeal`
- event-id-specific branches
- feature IDs shared with parity
- single-example classes
- benchmark edits without the audit above

## Measured Evidence

All generated under `run/artifacts/organic-v0/`:

- `eval_cycle6_relations_all_on.json`: 30/30 held-out exact, overall exact_rate `1.000000`, state hash `29958f0880e662dc`, config hash `99032d46527a795b`.
- `eval_cycle6_relations_from_disk.json`: fresh-process loaded-state eval, diff-clean against all-on for `summary_metrics + model_state_hash`.
- `persist_self_test_v2c6.json`: `save_and_load_verified`, parent/child hash `29958f0880e662dc`, parent/child output `"mila quartz pier6"`.
- `eval_cycle6_ablate_numeric.json`: `--ablate-numeric-derived` -> 26/30, failures `evt_rule_test_001`, `evt_rule_test_002`, `evt_rule_test_003`, `evt_rule_test_004`; threshold and modular families remain exact.
- `eval_cycle6_ablate_threshold.json`: `--ablate-threshold-derived` -> 28/30, failures `evt_rule_thresh_test_001`, `evt_rule_thresh_test_002`; parity and modular families remain exact.
- `eval_cycle6_ablate_modular.json`: `--ablate-modular-derived` -> 27/30, failures `evt_rule_mod_test_001`, `evt_rule_mod_test_002`, `evt_rule_mod_test_003`; parity and threshold families remain exact.
- `eval_cycle6_ablate_relation.json`: `--ablate-relation-projection` -> 28/30, failures `evt_abs_test_001`, `evt_abs_test_003`; numeric relation families remain exact.
- `eval_cycle6_legacy_cycle2_cycle5_fixture.json`: cycle-2 snapshot loaded under the cycle-6 binary on the cycle-5 fixture remains at 9/25 (`0.360000`), state hash `3536309de837d3e2`, preserving legacy semantics.
- `eval_cycle6_legacy_cycle2_current_fixture.json`: same cycle-2 snapshot on the expanded cycle-6 fixture scores 9/30 (`0.300000`), showing only denominator expansion from new held-out tests.

Existing cycle-5 ablations and `make test` remain regression gates.

## Speed/Efficiency Note

Cycle 6 also removed repeated parsing and linear lookup work from the generated path:

- each loaded/learned trace now caches parsed observation slots plus threshold/modular relation keys;
- trace span-position scoring now uses a transient event-id index instead of scanning the whole trace vector for every activated trace.

These caches are rebuilt from persisted observations on load and are not serialized or hashed. The final all-on state hash stayed `29958f0880e662dc`, so the optimization did not change learned behavior. The current 62-event fixture is too small to show a meaningful wall-clock delta (`/usr/bin/time` stayed about `0.12s` for a single eval), so the honest claim is reduced asymptotic work, not measured benchmark speedup.
