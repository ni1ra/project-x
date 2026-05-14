# Cycle 5 Mechanism - Derived Beliefs + Relation Projection

Date: 2026-05-14
Status: pre-implementation design note for organic-v0 cycle 5.

## Problem

Cycle 4 can replay traces and copy visible role fillers, but three residual families require a second associative channel:

- hidden-rule transfer: the held-out event shows `mark:7` but not `parity:odd`; the substrate must derive a latent fact from the mark before learned odd/even output associations can compete with signal-color replay.
- evidence-present recall: the held-out event shows `topic:arin` but not `object:copper`; the substrate must project through a stored memory relation rather than requiring the literal object role at test time.
- intent-transfer: the held-out target contains `bye`, but the old fixture has no train event with `bye` or `intent:farewell`. That is a curriculum learnability bug, not a weak feature.

Cycle 4's trace-span-position memory was still trace replay. Cycle 5 needs the organism to compute over traces and observations before generation.

## Mechanism A - Derived Belief Features

The encoder adds deterministic latent facts for numeric observation slots. For a slot like `mark:7`, it emits feature atoms for:

- role-local numeric identity: `mark has numeric value`
- role-local parity: `mark parity odd`
- role-free parity: `some observed number parity odd`
- last digit: useful for later tasks, not sufficient by itself

These features are not answer rules. They never map odd to `stay` or even to `go`. They only give the existing learned character/action connection substrate a stable address where training events can accumulate evidence. Training has `mark:2/4 -> go` and `mark:3/5 -> stay`; held-out events with unseen marks activate the same parity address.

Why this is principled:

- parity is computed from the observation value, not copied from the target
- the output remains learned through `connections_`
- signal-color associations remain in the substrate and can still win if parity evidence is absent
- the feature is role-relative, so future numeric slots can carry their own derived facts without a benchmark branch

Negative space:

- no `if odd return stay`
- no list of benchmark event ids
- no direct target-output text in the encoder
- no transformer/attention/softmax block

## Mechanism B - Relation Projection

During learning, every rewarded trace with typed observations writes auxiliary role-to-role projections into the same CONNS substrate. For a memory trace:

```text
person:arin, object:copper, place:tray4
```

the substrate learns projection sequences for `person:arin -> object:copper`, `person:arin -> place:tray4`, and the other observed role pairs. The projection is stored as ordinary character weights under a deterministic relation feature id:

```text
relation(cue_role, cue_value, target_role)
```

At generation, if the current event contains `topic:arin` and the input asks for an object-like role (`hold`, `item`, `object`, or an explicit role token), the brain scans stored traces for a role value equal to `arin` and activates the matching relation feature for target role `object`. The learned character weights then compete in the normal generator at position 0.

Why this is a second associative channel:

- retrieval finds traces by similarity; relation projection scans stored typed traces for a cue/value binding and activates a learned relation address
- it can answer with a filler that is not present in the current observation list
- absent evidence naturally produces no relation feature, so the existing abstention memory can still win
- the answer string is still emitted character-by-character from learned weights

Negative space:

- no `arin -> copper` table is authored by code; the pair is learned from the event's typed observations
- no branch returns `copper` or `glass`
- the query-role encoder names only target roles, never target answers
- relation weights live in existing `CONNS`; no new PXSTATE section is mathematically required

## Persistence

No new PXSTATE section is required. The learned projection weights and derived-belief weights are ordinary `CONNS` rows. Stored traces already contain the typed observations needed to reactivate relation projection after load.

CONFIG needs two answer-path booleans:

- `use_numeric_derived_features`
- `use_relation_projection`

Older snapshots default both off on load. New cycle-5 snapshots write both fields as enabled.

## Falsification Test

The mechanism is structural only if the following all hold:

1. With the old benchmark unchanged, hidden-rule failures improve because parity-derived features activate on unseen marks.
2. Evidence-present failures improve because relation projection activates `person:* -> object:*`; evidence-absence stays 2/2 because no relation exists.
3. Removing relation projection should collapse evidence-present while preserving hidden-rule gains.
4. Removing numeric-derived features should collapse hidden-rule gains while preserving evidence-present gains.
5. The old `intent_transfer` failure must remain unsolved until a curriculum event teaches `bye`; solving it without such evidence would be contamination.

## Measured Cycle-5 Result

Final repaired-benchmark artifact:

- `run/artifacts/organic-v0/eval_compositional_v2c5.json`
- exact: 25/25 (1.000)
- state hash: `ccd7a48ec4614703`
- config hash: `de2ad1690588249d`

Old-fixture substrate-only measurement before the farewell repair (re-run under the final binary):

- `run/artifacts/organic-v0/eval_cycle5_substrate_only_old_fixture.json`
- exact: 24/25 (0.960)
- state hash: `b968647c92f30c57`
- remaining failure: `evt_lang_test_004` because the training set had no `bye`/farewell evidence.

Ablations on the repaired benchmark:

- `run/artifacts/organic-v0/eval_cycle5_ablate_numeric.json`: `--ablate-numeric-derived` -> 22/25 (0.880). Hidden-rule transfer regresses; failures isolate to `evt_rule_test_001`, `evt_rule_test_003`, `evt_rule_test_004`. State hash `6ccada17751408d0`.
- `run/artifacts/organic-v0/eval_cycle5_ablate_relation.json`: `--ablate-relation-projection` -> 23/25 (0.920). Evidence-present recall regresses to 0/2; failures isolate to `evt_abs_test_001`, `evt_abs_test_003`. State hash `75c0bb8012ffb437`.

The measured pattern matches the design prediction: numeric-derived facts carry rule transfer; relation projection carries evidence-present recall; farewell needs explicit curriculum evidence.
