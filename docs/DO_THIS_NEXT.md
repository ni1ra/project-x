# Do This Next - Project X v2

Generated: 2026-05-14 (post cycle-6 close)

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/PERSISTENCE_SCHEMA.md`
5. `docs/artifacts/CYCLE6_NUMERIC_RELATION_GENERALIZATION.md`
6. `docs/artifacts/CYCLE6_CLAUDE_AUDIT_PACKET.md`
7. latest cycle-6 reflection in `docs/past_work/cycles/phase_v2_organic_substrate/`

## What Just Happened - Cycle 6

Cycle 6 generalized the hidden-rule substrate beyond parity.

The benchmark now contains 62 events: 32 train and 30 held-out. Hidden-rule coverage now includes three computed numeric relation families:

- parity: `mark` odd/even, carried by the existing `--ablate-numeric-derived` channel;
- threshold: `mark > cutoff`, carried by the new `--ablate-threshold-derived` channel;
- modular class: `mark mod 3`, carried by the new `--ablate-modular-derived` channel.

The train suite uses at least two distinct mark values per threshold/modular class. The held-out tests use unseen marks and conflicting surface signals, so a replay-shaped or surface-color solution fails.

The runtime also received a small efficiency pass: loaded/learned traces cache parsed observation slots plus threshold/modular keys, and trace span-position lookup now uses a transient event-id index. The tiny fixture still runs at roughly 0.12s, so this is an asymptotic cleanup, not a claimed wall-clock win.

### Final Cycle-6 Evidence

`run/artifacts/organic-v0/eval_cycle6_relations_all_on.json`:

| metric | cycle 5 repaired | cycle 6 expanded |
|---|---:|---:|
| held-out count | 25 | 30 |
| overall exact_rate | 1.000 | **1.000** |
| exact events | 25/25 | **30/30** |
| parity rule transfer | 4/4 | **4/4** |
| threshold_rule_transfer | n/a | **2/2** |
| modular_rule_transfer | n/a | **3/3** |
| evidence_present | 2/2 | **2/2** |
| existing solved families | held | **held** |

State hash `29958f0880e662dc`. Config hash `99032d46527a795b`.

Persistence:

- `run/artifacts/organic-v0/eval_cycle6_relations_from_disk.json` is diff-clean against all-on on `summary_metrics + model_state_hash`.
- `run/artifacts/organic-v0/persist_self_test_v2c6.json` reports `save_and_load_verified`, hash match, output match.

Legacy compatibility:

- `run/artifacts/organic-v0/eval_cycle6_legacy_cycle2_cycle5_fixture.json`: cycle-2 snapshot loaded under the cycle-6 binary on the cycle-5 fixture remains 9/25 (`0.360000`), state hash `3536309de837d3e2`, raw `evt_mem_test_001` output `"milaquart arch6"`.
- `run/artifacts/organic-v0/eval_cycle6_legacy_cycle2_current_fixture.json`: same snapshot on the expanded fixture is 9/30 (`0.300000`), expected denominator expansion only.

### Falsification/Ablation Evidence

- `run/artifacts/organic-v0/eval_cycle6_ablate_numeric.json`: `--ablate-numeric-derived` -> **26/30 (0.866667)**; failures = `evt_rule_test_001`, `evt_rule_test_002`, `evt_rule_test_003`, `evt_rule_test_004`. Threshold and modular remain exact.
- `run/artifacts/organic-v0/eval_cycle6_ablate_threshold.json`: `--ablate-threshold-derived` -> **28/30 (0.933333)**; failures = `evt_rule_thresh_test_001`, `evt_rule_thresh_test_002`. Parity and modular remain exact.
- `run/artifacts/organic-v0/eval_cycle6_ablate_modular.json`: `--ablate-modular-derived` -> **27/30 (0.900000)**; failures = `evt_rule_mod_test_001`, `evt_rule_mod_test_002`, `evt_rule_mod_test_003`. Parity and threshold remain exact.
- `run/artifacts/organic-v0/eval_cycle6_ablate_relation.json`: `--ablate-relation-projection` -> **28/30 (0.933333)**; failures remain isolated to evidence-present (`evt_abs_test_001`, `evt_abs_test_003`). Numeric relation families remain exact.

The key claim is isolation, not the all-on 1.000. Threshold and modular are not piggybacking on parity; turning off one relation channel breaks only that family.

## Cycle 7A Closed - Growing Brain File Contract

Cycle 7A made continuation learning first-class before starting the harder interactive rung.

Final evidence:

- `run/artifacts/organic-v0/fork_divergence_cycle7a.json`: two children load the same v2-c6 parent, learn different streams, reload cleanly, diverge in state hash, and emit different held-out raw outputs.
- child A: `fab9c2c0367ed2b5`, 1/1 from-training and 1/1 from-disk, raw `"aurora branch"`.
- child B: `c0f016285e735e14`, 1/1 from-training and 1/1 from-disk, raw `"ember branch"`.
- `run/artifacts/organic-v0/persist_self_test_cycle7a_child.json`: loaded parent hash `29958f0880e662dc`, child hash `fab9c2c0367ed2b5`, `hash_match=true`, `output_match=true`.
- `run/artifacts/organic-v0/eval_cycle7a_legacy_cycle2_cycle5_fixture.json`: legacy cycle-2 snapshot remains 9/25 (`0.360000`), state hash `3536309de837d3e2`, raw `"milaquart arch6"`.

This proves restart-surviving fork divergence under different experience. It does not prove fluent chat or interactive rule induction.

## Cycle 7B Contract

Pick one:

1. **Promote to a harder benchmark rung.** Build a local hidden-rule game or ARC-style micro-harness where the organism must infer a rule from interaction/state history, not just train/eval JSONL. Close criterion: run IDs, action history, scorecard, held-out seeds, and failure traces.
2. **Generalize relation projection beyond topic->object.** Add held-out questions for place/effect and different cue roles while keeping evidence_absence exact. Close criterion: projection works across at least two target roles, with `--ablate-relation-projection` isolating only those families.
3. **Generalize computed relations beyond numeric values.** Add symbolic equality or role-match relations, e.g. two observed fillers being the same/different, without numeric parsing. Close criterion: new non-numeric relation family learned without answer routes and ablated cleanly.

Default recommendation: option 1. The current JSONL ladder is saturated again; the next capability proof should force exploration, state fidelity, and rule induction under a budget.

Hard gates:

- Keep claim splits explicit: substrate-only, repaired/expanded fixture, from-training, and from-disk are separate claims.
- Every new substrate channel ships with a CLI ablation and measured per-family failure isolation.
- Do not add benchmark train examples unless a learnability audit names the missing evidence first.
- Preserve persistence diff-clean and legacy snapshot compatibility.
- Do not claim broad language understanding from the farewell or numeric-rule items.
- Keep runtime speed claims tied to measurements or state them as structural/asymptotic only.
