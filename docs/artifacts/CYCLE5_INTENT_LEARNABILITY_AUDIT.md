# Cycle 5 Intent Learnability Audit

Date: 2026-05-14
Status: benchmark repair justification before editing `benchmarks/v2_ladder/organic_v0.jsonl`.

## Claim

The pre-cycle-5 `intent_transfer` fixture is not learnable for organic-v0 without either pretrained language semantics or an authored answer route.

Held-out event:

```text
intent:farewell, name:elena -> "bye elena"
```

Training evidence before repair:

- `intent:greet, name:mira -> "hi mira"`
- `intent:greet, name:soren -> "hi soren"`
- `intent:accept -> "yes"`
- `intent:decline -> "no"`

There is no training event with `intent:farewell`, no target output containing `bye`, and no intermediate observation that binds farewell to bye. The target asks the organism to emit a new literal prefix from no internal source.

## Boundary

An organic learner can transfer the `name` copy span after learning segment mode. It cannot honestly infer the English lexical mapping `farewell -> bye` from this curriculum. A pretrained language model could know that mapping, but organic-v0 is explicitly not allowed to call pretrained language semantics or use a hardcoded lexical table.

## Repair

Add two train events:

```text
intent:farewell, name:sora -> "bye sora"
intent:farewell, name:toma -> "bye toma"
```

Then the held-out event tests actual transfer:

- literal prefix `bye` learned from training evidence
- name filler `elena` copied through the existing learned segment mechanism
- no direct replay of the exact held-out name

The two-example repair is intentional. A one-example repair teaches the missing lexical mapping but also permits a replay-shaped solution: the substrate can emit `bye sora` for the held-out event because the exact farewell trace is too strong. Two distinct farewell names make the replaceable-name structure learnable without hardcoding the answer.

## Expected Measurement

Before benchmark repair on the cycle-5 substrate:

- overall: 24/25 exact
- `intent_transfer`: 0/1
- failure: `evt_lang_test_004` emits `hi elena`

After benchmark repair:

- `intent_transfer` should become 1/1 if the substrate can combine the learned farewell prefix with a held-out name filler.
- If it remains 0/1, the bug is no longer the curriculum; it is the substrate's intent/prefix discrimination.

This is a data repair, not a substrate win by itself. The substrate win is the original-benchmark 24/25 result from numeric-derived trace activation plus relation projection.
