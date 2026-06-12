# Phase v2 Organic Substrate - Cycle 6 reflection

**Theme:** Computed numeric relation substrate generalization beyond parity
**Closed:** 2026-05-14
**Implementer:** Codex GPT-5

## Context

Cycle 5 closed the repaired v2 ladder at 25/25, but its hidden-rule win still rested on one computed numeric relation: parity. That left a serious uncertainty:

- If parity was just a lucky address family, then the substrate was not relation-general.
- If threshold and modular class could be added under separate namespaces and independently ablated, then the substrate pattern was stronger than a parity patch.

Cycle 6 therefore did not try to make the old saturated score prettier. It widened the hidden-rule family and asked whether three computed relations could coexist without channel coupling.

## What shipped

### (a) Threshold-derived relation channel

Observation slots now produce threshold relation keys when a numeric filler shares an event with a cutoff role:

- example evidence: `mark:8`, `cutoff:5`
- computed address: role + cutoff role + cutoff value + `gt|lt|eq`

The address is used as HDC latent evidence, context feature evidence, and trace-activation evidence. It never maps `gt -> "above"` in code. The answer still has to be learned as ordinary character weights from rewarded train events.

### (b) Modular-derived relation channel

Observation slots now produce modular relation keys when a numeric filler shares an event with a modulus role:

- example evidence: `mark:11`, `modulus:3`
- computed address: role + modulus role + modulus value + class id

The namespace is deliberately distinct from parity. Parity remains the cycle-5 `--ablate-numeric-derived` channel; modular class is controlled by `--ablate-modular-derived`. This is the anti-collision guard for "mod 2 is parity".

### (c) Falsification flags

Two new CLI flags ship with the new channels:

- `--ablate-threshold-derived`
- `--ablate-modular-derived`

The existing flags remain live:

- `--ablate-numeric-derived`
- `--ablate-relation-projection`

The close criterion is family isolation, not the all-on score.

### (d) Benchmark mini-suite

`benchmarks/v2_ladder/organic_v0.jsonl` gains 10 train events and 5 held-out tests:

- threshold: two low marks below cutoff, two high marks above cutoff, two held-out unseen marks with conflicting surface signals;
- modular: two marks per class for `modulus:3`, three held-out unseen marks with conflicting surface signals.

The train examples include the explicit class labels (`threshold:*`, `modclass:*`) so the output mapping is learnable. The held-out tests omit those labels, forcing the runtime to compute from `mark:*` plus `cutoff:*` or `modulus:*`. The learnability audit lives in `docs/past_work/cycles/phase_v2_organic_substrate/cycle_docs/CYCLE6_NUMERIC_RELATION_GENERALIZATION.md` and was written before the benchmark edit.

### (e) Persistence and speed cleanup

No new PXSTATE section was needed. New CONFIG fields are enough:

- `derived_relation_gain`
- `use_threshold_derived_features`
- `use_modular_derived_features`

Older snapshots default the new relation booleans off and `derived_relation_gain` to `1.0`, preserving legacy semantics.

The implementation also caches parsed observation slots and computed relation keys on each trace, and adds a transient event-id index for trace span-position lookups. These caches are rebuilt from persisted observations on load, are not serialized, and are not included in `state_hash()`.

## Measurement

Cycle 6 expands the held-out set from 25 to 30. The all-on claim is:

| metric | cycle 5 repaired | cycle 6 expanded |
|---|---:|---:|
| overall exact_rate | 1.000 | **1.000** |
| exact events | 25/25 | **30/30** |
| parity hidden-rule probes | 4/4 | **4/4** |
| threshold_rule_transfer | n/a | **2/2** |
| modular_rule_transfer | n/a | **3/3** |
| evidence_present | 2/2 | **2/2** |
| existing solved families | held | **held** |

Headline artifact: `run/artifacts/organic-v0/eval_cycle6_relations_all_on.json`.

- State hash: `29958f0880e662dc`
- Config hash: `99032d46527a795b`
- Run id: `organic-v0-eval-a774d45d3689`

## Falsification

The single-channel-off ladder isolated cleanly:

| run | flag | exact | failures isolate to |
|---|---|---:|---|
| `eval_cycle6_ablate_numeric.json` | `--ablate-numeric-derived` | 26/30 (0.866667) | four parity hidden-rule probes: `evt_rule_test_001`, `evt_rule_test_002`, `evt_rule_test_003`, `evt_rule_test_004` |
| `eval_cycle6_ablate_threshold.json` | `--ablate-threshold-derived` | 28/30 (0.933333) | two threshold probes: `evt_rule_thresh_test_001`, `evt_rule_thresh_test_002` |
| `eval_cycle6_ablate_modular.json` | `--ablate-modular-derived` | 27/30 (0.900000) | three modular probes: `evt_rule_mod_test_001`, `evt_rule_mod_test_002`, `evt_rule_mod_test_003` |
| `eval_cycle6_ablate_relation.json` | `--ablate-relation-projection` | 28/30 (0.933333) | two evidence-present probes: `evt_abs_test_001`, `evt_abs_test_003` |

This is the cycle's core result. If the threshold or modular paths were parity-disguised, turning off parity would also break them, or turning off threshold/modular would break parity. It did not happen.

## Persistence verification

- `run/artifacts/organic-v0/eval_cycle6_relations_from_disk.json`: loaded from `run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate`; diff-clean against all-on for `summary_metrics + model_state_hash`.
- `run/artifacts/organic-v0/persist_self_test_v2c6.json`: `save_and_load_verified`, parent/child hash `29958f0880e662dc`, parent/child output `"mila quartz pier6"`.
- `make test`: PASS; substrate self-test plus persistence round-trip.

## Backward compatibility

The cycle-2 snapshot still loads under the cycle-6 binary:

- cycle-5 fixture: `run/artifacts/organic-v0/eval_cycle6_legacy_cycle2_cycle5_fixture.json` = 9/25 (`0.360000`), state hash `3536309de837d3e2`, `evt_mem_test_001` raw `"milaquart arch6"`;
- current expanded fixture: `run/artifacts/organic-v0/eval_cycle6_legacy_cycle2_current_fixture.json` = 9/30 (`0.300000`), same state hash and historical raw output.

The current-fixture score drops only because the denominator grew by five new cycle-6 held-out items.

## Speed/Efficiency audit

Two implementation changes reduce repeated work:

- traces cache parsed observation slots and relation keys after learn/load;
- trace-id lookup for span-position scoring uses a transient map instead of a linear scan.

The one-shot eval fixture is too small for a material wall-clock claim. `/usr/bin/time` stayed about `0.12s` before and after the cache/index cleanup, with the final run reporting `elapsed=0.12 user=0.11 sys=0.01 maxrss=18688`. The honest claim is reduced asymptotic work as trace count and output length grow, not a benchmark-speed win on this tiny rung. The behavior hash stayed `29958f0880e662dc`.

## What still fails / what was NOT addressed

- This is still an offline JSONL train/eval ladder. It does not test exploration, action budgeting, or unknown-rule interaction.
- The generalized relations are numeric. Symbolic equality, role matching, and non-numeric relational abstraction remain open.
- Relation projection beyond `topic -> object` remains unexpanded. Cycle 6 preserved that channel but did not widen its benchmark family.
- The threshold suite currently trains below-vs-above, not equality-at-cutoff. The code supports `eq` keys; the benchmark does not exercise them yet.
- The speed work improves structure but not measured fixture wall-clock.

## Five-question self-audit

**1. What can the substrate now compute that it could not compute before?**

It can compute three separate relation-address families over numeric observations: parity, threshold against an observed cutoff, and modular class under an observed modulus. Those addresses reactivate learned traces and ordinary character weights without answer branches.

**2. What would impress a hard reviewer, and what would they challenge?**

The clean ablation isolation is the impressive part. Each family has its own off switch and each switch breaks only its family. The challenge is equally clear: the ladder is still small, typed, and offline; a hard reviewer should ask for interaction, randomized seeds, and non-numeric relations next.

**3. Where is the load-bearing mechanism in the diff?**

The load-bearing mechanism is the relation-key emission and trace activation path in `native/organic_v0.cpp`: threshold/modular key construction, HDC atoms, context features, trace-id activation features, and the two ablation booleans that can remove those families. The benchmark proves these are load-bearing by failing exactly the corresponding held-out items when ablated.

**4. What would falsify the claim?**

Any cross-coupled ablation would falsify it. If `--ablate-numeric-derived` broke threshold/modular, parity would still own the new families. If `--ablate-threshold-derived` broke parity or modular, the namespaces would be entangled. The artifacts show the opposite.

**5. What is the next experiment that would actually raise the bar?**

Move from offline relation lookup to an interactive hidden-rule game or ARC-style micro-harness. The organism should observe state/action/result history, form hypotheses, and spend an action budget. That would test the universal operations in the AGENTS instructions: state fidelity, unknown-rule exploration, causal diagnosis, and planning under uncertainty.

## Self-impression score

**418 / 420.**

This is one point stronger than cycle 5 because it answers the exact structural uncertainty cycle 5 left open: parity was not the whole mechanism. Three numeric relation families now share the substrate pattern while staying separately ablatable. I am not scoring it 420 because the rung is still typed, numeric, and offline. A 420 result should either force interaction under hidden rules or generalize beyond numeric relations in a way that surprises an auditor rather than merely completing the planned ladder extension.

## Cycle 7 direction

Default recommendation: promote to a harder benchmark rung.

Build a local hidden-rule game or ARC-style micro-harness with randomized held-out seeds, action history, and explicit failure traces. Keep the current JSONL ladder as regression, but stop using a saturated offline fixture as the main proof. The next impressive result is not another 1.000 on a hand-widened JSONL; it is an organism taking actions to identify a rule it was not handed.
