# Do This Next - Project X v2

Generated: 2026-05-14 (post cycle-5 ship candidate)

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/PERSISTENCE_SCHEMA.md`
5. `docs/artifacts/CYCLE5_RELATIONAL_BINDING.md`
6. `docs/artifacts/CYCLE5_INTENT_LEARNABILITY_AUDIT.md`
7. latest cycle-5 reflection in `docs/past_work/cycles/phase_v2_organic_substrate/`

## What Just Happened - Cycle 5

Cycle 5 added two structural channels to organic-v0:

- **Numeric-derived trace activation:** pure numeric observation fillers now emit latent facts such as role-relative parity. Generation can also activate stored traces that share the computed numeric relation, so hidden-rule events are not trapped by surface signal/color similarity.
- **Relation projection:** rewarded typed traces write role-to-role projections into ordinary `CONNS` rows. A `topic:arin` query that asks what someone holds can reactivate the learned `person:arin -> object:copper` projection, while absent topics still fall back to abstention.

It also repaired a benchmark learnability bug:

- The old `intent_transfer` held-out item expected `bye elena`, but the training set contained no `bye` output and no `intent:farewell` example.
- Cycle 5 adds two farewell train events, `bye sora` and `bye toma`, so the held-out event tests transfer to a new name rather than pretrained English knowledge or a hardcoded lexical route.

### Final Repaired-Benchmark Evidence

`run/artifacts/organic-v0/eval_compositional_v2c5.json`:

| metric | cycle 4 | cycle 5 repaired |
|---|---:|---:|
| overall exact_rate | 0.760 | **1.000** |
| exact events | 19/25 | **25/25** |
| `unseen_rule_transfer` | 1/2 | **2/2** |
| `distractor_rule_transfer` | 0/2 | **2/2** |
| `evidence_present` | 0/2 | **2/2** |
| `intent_transfer` | 0/1 | **1/1** |
| existing solved families | held | **held** |

State hash `ccd7a48ec4614703`. Config hash `de2ad1690588249d`.

Important split:

- Old pre-repair fixture with the cycle-5 substrate (final binary): `run/artifacts/organic-v0/eval_cycle5_substrate_only_old_fixture.json` = **24/25 (0.960)**; only `intent_transfer` (`evt_lang_test_004`) remained unlearnable. State hash `b968647c92f30c57`.
- Repaired fixture with two farewell train examples: `run/artifacts/organic-v0/eval_compositional_v2c5.json` = **25/25 (1.000)**.

### Falsification/Ablation Evidence

- `run/artifacts/organic-v0/eval_cycle5_ablate_numeric.json`: `--ablate-numeric-derived` -> **22/25 (0.880)**; failures = `evt_rule_test_001`, `evt_rule_test_003`, `evt_rule_test_004`. Hidden-rule family regresses cleanly. State hash `6ccada17751408d0`.
- `run/artifacts/organic-v0/eval_cycle5_ablate_relation.json`: `--ablate-relation-projection` -> **23/25 (0.920)**; failures = `evt_abs_test_001`, `evt_abs_test_003`. `evidence_present` regresses to 0/2 cleanly. State hash `75c0bb8012ffb437`.

### Persistence/Compat

- `run/artifacts/organic-v0/eval_compositional_v2c5_from_disk.json` is diff-clean against from-training on `summary_metrics + model_state_hash`.
- `run/artifacts/organic-v0/persist_self_test_v2c5.json` reports `save_and_load_verified`, hash match, output match.
- Cycle-2 snapshot `/tmp/cycle2.pxstate` still loads under the cycle-5 binary with state hash `3536309de837d3e2`, exact_rate `0.360`, and `evt_mem_test_001` raw `"milaquart arch6"`.

## Cycle 6 Contract

Do not spend cycle 6 making this benchmark prettier. The v2 ladder rung is saturated after the repaired curriculum.

Pick one:

1. **Generalize the rule substrate beyond parity.** Add a hidden-rule mini-suite with at least two different computed relations (parity, threshold, equality, or modular class). Close criterion: new relation family learned without answer routes, with ablations proving which derived relation carries which gain.
2. **Generalize relation projection beyond topic->object.** Add held-out questions that ask for place/effect, use different cue roles, and include absent evidence controls. Close criterion: projection works across at least two target roles while evidence_absence stays exact.
3. **Promote to a harder benchmark rung.** Build a local hidden-rule game or ARC-style micro-harness where the organism must explore or infer a rule from sequences, not just train/eval JSONL. Close criterion: run IDs, action history, scorecard, and failure traces.

Hard gates:

- Keep old-fixture vs repaired-fixture claims separate.
- Keep ablation flags working.
- Do not claim broad language understanding from two farewell examples.
- Do not add benchmark train examples unless a learnability audit names the missing evidence.
- Preserve persistence diff-clean and legacy snapshot compatibility.
