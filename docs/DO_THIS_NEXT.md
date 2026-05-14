# Do This Next - Project X v2

Generated: 2026-05-14 (post cycle-7D close)

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

## Cycle 7B Closed - Interactive Hidden Rule Micro-Harness

Cycle 7B shipped the first native action/feedback rung.

Final evidence:

- `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_summary.json`: aggregate held-out 14/14 (`1.000000`) across seeds 7001 and 7002; total pre-feedback actions 26/42 (`0.619048`); support pre-feedback actions 12/28 (`0.428571`).
- `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_feedback_ablation.json`: feedback strength 2.0 scores 14/14 held-out and 26/42 total; feedback strength 1.0 drops to 13/14 held-out and 15/42 total.
- `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_seed7001.json`: loaded v2-c6 parent, 7/7 held-out, 8 support failure traces, final hash `879b7e4f6295fc12`.
- `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_seed7002.json`: loaded v2-c6 parent, 7/7 held-out, 8 support failure traces, final hash `030516a10354131a`.
- The oracle is not in the generation path. It grades and supplies correction only after raw action.

This proves a small action/feedback loop with held-out transfer under state mutation. It does not prove ARC-grid competence, open-ended planning, or natural chat.

## Cycle 7C Contract

Pick one:

1. **Promote to a less typed interactive rung.** Extend the native harness to symbolic same/different, role-match, or tiny grid transformation rules where no numeric-derived relation channel can carry the task alone. Close criterion: action history, held-out seeds/rules, failure traces, and a measured ablation showing which substrate carries the win.
2. **Generalize relation projection beyond topic->object.** Add held-out questions for place/effect and different cue roles while keeping evidence_absence exact. Close criterion: projection works across at least two target roles, with `--ablate-relation-projection` isolating only those families.
3. **Add replay/consolidation after interaction.** After an interactive episode, replay support failures into a saved child and rerun held-out probes from disk. Close criterion: fresh-child held-out behavior matches same-process behavior, with a replay/correction ablation that degrades predictably.

Default recommendation: option 1. Cycle 7B is still numeric and typed; the next capability proof should make the rule less directly aligned with the existing numeric relation senses.

Hard gates:

- Keep claim splits explicit: substrate-only, repaired/expanded fixture, from-training, and from-disk are separate claims.
- Every new substrate channel ships with a CLI ablation and measured per-family failure isolation.
- Do not add benchmark train examples unless a learnability audit names the missing evidence first.
- Preserve persistence diff-clean and legacy snapshot compatibility.
- Do not claim broad language understanding from the farewell or numeric-rule items.
- Keep runtime speed claims tied to measurements or state them as structural/asymptotic only.

## Cycle 7C Closed - Symbolic Interactive Rule Rung

Cycle 7C shipped the default option: a less-typed symbolic interactive rung.

Final evidence:

- `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_summary.json`: aggregate held-out 16/16 (`1.000000`) across seeds 7101/7102; total pre-feedback 48/64 (`0.750000`); support pre-feedback 32/48 (`0.666667`); post-episode probes 16/16 (`1.000000`).
- `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_symbolic_ablation.json`: `--ablate-symbolic-relations` drops held-out to 2/16 (`0.125000`) and total to 4/64 (`0.062500`).
- `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_probe_seed7101.json` and `_seed7102.json`: fresh loaded child probes match same-process probe summaries and model hashes.
- `docs/artifacts/CYCLE7C_INTERACTIVE_SYMBOLIC_RULE.md`: closed interpretation and negative-space audit.

The mechanism is cue-bound symbolic relation features over non-numeric entity attributes:

- color same/different
- shape same/different
- place same/different
- symbol role-match

The oracle still acts only after generation. The action labels are arbitrary and learned from feedback. This is not chat, poetry, philosophy, math, physics, ARC, or beyond-human ability.

Regression gates after Cycle 7C:

- `make test`: PASS
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, raw `evt_mem_test_001` `"milaquart arch6"`
- Cycle 7B numeric interactive regression: seeds 7001/7002 remain 7/7 held-out exact

## Cycle 7D Contract

Pick one:

1. **Tiny grid transformation rung.** Add a native interactive grid micro-world where observations encode 3x3 or 4x4 symbolic cells and the hidden action depends on mirror, rotate, row/column movement, or color/marker preservation. Close criterion: action history, held-out seeds/rules, failure traces, from-disk probes, and an ablation showing a grid/spatial substrate is load-bearing.
2. **Replay/consolidation after symbolic interaction.** After an interactive episode, replay support failures into a saved child and rerun held-out probes from disk. Close criterion: replay improves or preserves held-out/probe behavior with fewer support failures or stronger post-episode transfer, while `--ablate-replay` degrades predictably.
3. **Delayed feedback symbolic interaction.** Withhold feedback for short bursts, then apply correction/reward. Close criterion: action history preserves pre-feedback mistakes, delayed reward is learned into the same state, and an ablation isolates the delay-handling mechanism.

Default recommendation: option 1. Cycle 7C still used typed attribute slots; a grid rung starts moving toward ARC-like micro-worlds without allowing a direct solver route.

Hard gates:

- Write the learnability/design audit before code or fixture edits.
- Add a new substrate mechanism in `native/organic_v0.cpp`, not a Python answer path.
- Ship a CLI ablation for the new grid/spatial or replay/delay channel.
- Use held-out seeds >= 2.
- Preserve Cycle 7C, Cycle 7B, cycle-6, clean-chat, and legacy rails.
- Keep action labels arbitrary and oracle access after action.
- Update docs and `REPO_CONTROL.md`.
- Write and sha7-rename the cycle reflection.

## Cycle 7D Closed - Tiny Grid Spatial Rule Rung

Cycle 7D shipped the default option: a tiny 3x3 grid/spatial interactive rung.

Plain-English metric definitions are now in `docs/artifacts/METRIC_GLOSSARY.md`.

Final evidence:

- `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_summary.json`: aggregate held-out 16/16 (`1.000000`) across seeds 7201/7202; total pre-feedback 48/64 (`0.750000`); support pre-feedback 32/48 (`0.666667`); post-episode probes 16/16 (`1.000000`).
- `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_grid_ablation.json`: `--ablate-grid-spatial` drops held-out to 3/16 (`0.187500`) and total to 6/64 (`0.093750`).
- `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_probe_seed7201.json` and `_seed7202.json`: fresh loaded child probes match same-process probe summaries and model hashes.
- `docs/artifacts/CYCLE7D_INTERACTIVE_GRID_RULE.md`: closed interpretation, anti-repetition guard, and negative-space audit.

The mechanism is cue-bound 3x3 cell spatial relation features:

- horizontal mirror
- vertical mirror
- diagonal mirror
- adjacent row shift

The oracle still acts only after generation. The action labels are arbitrary and learned from feedback. This is not ARC, chat, poetry, philosophy, math, physics, or beyond-human ability.

Regression gates after Cycle 7D:

- `make test`: PASS
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, raw `evt_mem_test_001` `"milaquart arch6"`
- Cycle 7B numeric interactive regression: seeds 7001/7002 remain 7/7 held-out exact
- Cycle 7C symbolic interactive regression: seeds 7101/7102 remain 8/8 held-out exact

## Cycle 7E Contract

Default direction: **experience database and organic text rail**.

This is a course correction against repetition hell. Do not keep stacking isolated micro-puzzle channels as the main work. The next major substrate should make Raphael's language path learn from durable experience:

- raw text input
- generated output
- correction/feedback
- event IDs and source trails
- learned state mutation
- replayable training records
- from-disk continuation
- failure preservation

Candidate close criteria:

- add a native or directly-auditable experience store format for text interactions, separate from benchmark fixtures but compatible with event-log/state loading
- add a phase that can ingest a small text-interaction experience stream, save a child, reload it, and generate from the child without replaying the stream
- include a plain chat transcript artifact showing raw model outputs before and after correction
- include an ablation or replay-off control showing the experience rail is load-bearing
- keep the clean chat rail visible at 1/5 unless it organically improves
- do not add response templates, intent trigger lists, answer dispatchers, or a polished voice layer
- preserve Cycle 7D, Cycle 7C, Cycle 7B, cycle-6, clean-chat, and legacy rails

The goal is not to fake fluent text in one pass. The goal is to create the database-backed learning substrate that makes coherent organic text possible later.

## Cycle 7E Closed - Text Experience Rail

Cycle 7E shipped the default direction: a durable text-experience database and native organic text rail.

Final evidence:

- `run/artifacts/organic-v0/text_experience_cycle7e_summary.json`: all-on probe 4/4 (`1.000000`), from-disk probe 4/4 (`1.000000`), learning-disabled ablation probe 0/4 (`0.000000`).
- `run/artifacts/organic-v0/text_experience_cycle7e.json`: native all-on ingest run; train-before 1/6, train-after 4/6, probe 4/4, child hash `be0fc781039a2038`.
- `run/artifacts/organic-v0/text_experience_cycle7e_from_disk_probe.json`: fresh loaded child matches same-process probe metrics and model hash `be0fc781039a2038`.
- `run/artifacts/organic-v0/text_experience_cycle7e_ablate_learning.json`: `--ablate-text-experience-learning` leaves state growth at zero and drops probe to 0/4, hash `29958f0880e662dc`.
- `run/artifacts/organic-v0/text_experience_cycle7e_transcript.md`: readable transcript preserving raw before/after outputs and failures.
- `docs/artifacts/CYCLE7E_TEXT_EXPERIENCE_RAIL.md`: closed interpretation and negative-space audit.

Plain English:

- This proves the new text experience rail is durable and load-bearing.
- It does not prove fluent chat. The clean chat rail remains 1/5, and the 7E training transcript still preserves bad outputs.
- It is a database-backed substrate step toward organic language learning, not a finished language mind.

Regression gates after Cycle 7E:

- `make test`: PASS
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, raw `evt_mem_test_001` `"milaquart arch6"`
- Cycle 7B numeric interactive regression: seeds 7001/7002 remain 7/7 held-out exact
- Cycle 7C symbolic interactive regression: seeds 7101/7102 remain 8/8 held-out exact and 8/8 post-episode probe exact
- Cycle 7D grid interactive regression: seeds 7201/7202 remain 8/8 held-out exact and 8/8 post-episode probe exact

## Cycle 7F Contract

Default direction: **text-experience replay and consolidation**.

Do not drift back into isolated puzzle patching. The next major step should make the text experience database more organism-like by letting failed or weak records replay into a child state and measuring whether replay improves or stabilizes future text probes.

Candidate close criteria:

- write the learnability/design audit before code or data edits
- add a native replay/consolidation path for text experience records
- preserve raw first-pass failures and replay decisions in the artifact
- add `--ablate-text-experience-replay` or an equivalent replay-disabled control
- include from-disk child probes before and after replay
- include a replay transcript that shows which failures were replayed and what changed
- keep clean chat visible at 1/5 unless it organically improves
- preserve Cycle 7E, Cycle 7D, Cycle 7C, Cycle 7B, cycle-6, clean-chat, and legacy rails
- do not add response templates, intent trigger lists, answer dispatchers, or a polished voice layer
- update docs and `REPO_CONTROL.md`
- write and sha7-rename the cycle reflection

The target is not to claim fluency. The target is to make durable language experience accumulate, replay, and consolidate through learned state.
