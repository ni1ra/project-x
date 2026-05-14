# Cycle 7C Learnability Audit

Date: 2026-05-14
Status: pre-implementation audit for the less-typed symbolic interactive rung.

## Target

Cycle 7C should move beyond Cycle 7B's typed numeric rule families. The next organism sense should let organic-v0 notice symbolic relations between non-numeric attributes, then learn arbitrary action labels from feedback.

The intended rung is:

1. observe two or more entities with symbolic attributes such as color, shape, material, and place
2. act before seeing the oracle answer
3. receive feedback after the action
4. mutate the same loaded state
5. transfer to held-out examples where literal attribute values differ but the relation is preserved

This is still a micro-rung. It is not natural chat, poetry, philosophy, math, physics, ARC competence, or beyond-human ability.

## Missing Evidence

Cycle 7B proved interactive feedback on numeric relations:

- parity
- threshold
- modular class

Those rules were useful, but they still aligned with existing numeric-derived channels. They did not test whether the substrate can learn from a non-numeric relation such as same-color, different-shape, same-place, or role-match.

Without a new symbolic relation sense, a same/different benchmark would be unlearnable for the intended reason: held-out examples can use attribute values never seen in support. Surface token overlap would not carry the action. A learnable substrate needs an address for "these two entity attributes are same" or "different" so feedback can attach action weights to that relation.

## Allowed Mechanism

The builder may add encoder-side symbolic relation features:

- pairwise same/different addresses for slots shaped like `entity_attribute:value`
- HDC atoms for the same symbolic relation keys
- trace-activation features that reactivate past traces sharing the symbolic relation
- a CLI ablation flag that disables the symbolic relation channel

These are senses, not answers. They expose a relation as a feature address. They must not map any relation to a final action label.

## Forbidden Mechanism

Cycle 7C must not add:

- same-color -> action branches
- different-shape -> action branches
- rule-family dispatch in generation
- action templates
- target-action leakage before generation
- frontend fallback behavior
- natural-language polish hiding weak output
- a pretrained model or remote inference path

The oracle may grade and provide correction only after raw action.

## Benchmark Shape

Use at least two seeds. Each seed should contain multiple symbolic rule families and arbitrary action labels.

Candidate families:

- `same_color`: action depends on whether entity A and B have the same color
- `different_shape`: action depends on whether entity A and B have different shapes
- `same_place`: action depends on whether entity A and B share a place
- `role_match`: action depends on whether a source role's symbol matches a target role's symbol

Support steps should include both classes before held-out probes. Held-out probes should use unseen literal values where possible, so raw token replay does not explain success. Numeric observations must not be needed for the result.

## Required Falsification

The all-on run should produce:

- action history
- support mistakes before feedback
- held-out score across at least two seeds
- state growth and hashes
- event log path
- saved child state path where applicable

The ablated run with the new symbolic relation channel disabled should degrade on the symbolic family. Existing Cycle 7B parity, threshold, and modular interactive families should remain exact under the new binary unless the artifact explicitly documents a regression.

## Interpretation Boundary

A passing Cycle 7C would prove only this:

> organic-v0 can use a non-numeric symbolic relation feature as a learnable substrate address during interactive action/feedback, and the learned state can transfer to held-out symbolic probes.

It would not prove a complete neural organism, human-like language, opinions, general math, general physics, or beyond-human reasoning. Those remain manifesto targets. They must emerge from increasingly general learned machinery, not from hardcoded answer routes.
