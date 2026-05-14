# REPO_CONTROL - Project X v2

Date: 2026-05-14
Status: every tracked source/test/script/non-docs artifact owns a row here, one-line justification per entry. `docs/` is exempt — the live-docs system is self-justifying. `run/state/` is gitignored — local-runtime substrate that regenerates per run.

## Rule

Every commit owns its delta. File added → row added in the same commit. File deleted → row removed in the same commit. Auto-generated noise (`build/`, `__pycache__/`, runtime state under `run/state/`) is `.gitignore`'d, not listed. Empty placeholder directories are NOT tracked.

## Tracked tree

### root

| Path | Justification |
|---|---|
| `.gitignore` | excludes `build/`, `__pycache__/`, `*.pyc`, and runtime persistence substrate under `run/state/` from version control |
| `Makefile` | minimal native build: `g++ -std=c++20 -O3 -march=native` → `build/organic_v0`; `make test` runs the combined self-test (substrate guard + persistence round-trip) |

### native/ — brain core (C++20)

| Path | Justification |
|---|---|
| `native/organic_v0.cpp` | organic-v0 runtime: HDC encoder, context-feature learner, slot-typed observation pass-through, computed numeric relation channels (parity/threshold/modular), cue-bound symbolic same/different relation channel, cue-bound grid/spatial relation channel, relation projection, autoregressive char generator, train/eval/self-test phases, line-oriented state save/load, append-only event log, fresh-process persistence-round-trip orchestration, native interactive hidden-rule/symbolic-rule/grid-rule action-feedback harnesses, artifact writer. Single translation unit by design — the first code has nowhere to hide |

### scripts/ — thin harness over the native binary

| Path | Justification |
|---|---|
| `scripts/train_organic_v0.sh` | `make -s build/organic_v0 && exec build/organic_v0 --phase train "$@"` — forwards all flags to the native binary |
| `scripts/eval_organic_v0.sh` | same pattern for `--phase eval`; supports `--load-state` / `--save-state` / `--event-log` / `--ablate-trace-id` / `--ablate-numeric-derived` / `--ablate-threshold-derived` / `--ablate-modular-derived` / `--ablate-relation-projection` / `--ablate-symbolic-relations` / `--ablate-grid-spatial` |
| `scripts/test_organic_v0.sh` | runs both phases: `--phase self-test` (substrate guard — cold brain emits nothing, learns one event, emits "zx") then `--phase persistence-self-test` (full round-trip — train → save → fresh child process load → generate → hash + output match). Either failure is `set -e` fatal |

### benchmarks/ — measurement substrate

| Path | Justification |
|---|---|
| `benchmarks/v2_ladder/organic_v0.jsonl` | honest compositional baseline for organic-v0. 62 events: 32 train + 30 held-out across 5 domains. Cycle 6 adds threshold and modular hidden-rule mini-suites with at least two train marks per class and held-out unseen marks; hidden_rule keeps parity distractors, threshold distractors, and modular distractors where surface signal conflicts with the computed relation; abstention keeps 2 evidence-present + 2 evidence-absence items with identical wording; memory/causal/language carry filler-length variance |
| `benchmarks/v2_ladder/organic_live_chat_v0.jsonl` | manifesto-safe live-chat regression rail. Raw utterance observations only; no frontend-inferred greeting/farewell/identity labels. Preserves the honest 1/5 chat baseline without making chat the cycle headline |
| `benchmarks/v2_ladder/organic_cycle7a_fork_a.jsonl` | cycle-7A continuation-learning fork stream A. Same parent and probe shape as fork B, but rewarded with a different output so checkpoint hash and held-out behavior must diverge from experience alone |
| `benchmarks/v2_ladder/organic_cycle7a_fork_b.jsonl` | cycle-7A continuation-learning fork stream B. Same parent and probe shape as fork A, but rewarded with a different output so checkpoint hash and held-out behavior must diverge from experience alone |

### run/ — artifact output (machine-readable claims, tracked) — `run/state/` is gitignored (runtime substrate)

| Path | Justification |
|---|---|
| `run/artifacts/organic-v0/train.json` | per-train-run artifact: run_id, command, seed, config, state hash, split audit, per-event raw outputs with generation evidence |
| `run/artifacts/organic-v0/eval.json` | legacy aggregate eval artifact from the bootstrap pass; preserved as historical evidence of the 95.6% score that motivated the trace-id ablation |
| `run/artifacts/organic-v0/eval_with_trace.json` | ablation control: eval with `use_trace_id_feature=true` (default). Establishes baseline 95.6% exact rate. State hash `5a870dad7f70de83` |
| `run/artifacts/organic-v0/eval_no_trace.json` | ablation experimental: eval with `use_trace_id_feature=false`. Same exact rate (95.6%); state hash `35b32e4c2790826a`; proves trace-id is redundant, not load-bearing |
| `run/artifacts/organic-v0/eval_compositional_unchanged.json` | redesigned-benchmark baseline produced before the structural runtime change. Exact rate `0.520000`; memory/causal/language unseen-filler probes expose replay collapse |
| `run/artifacts/organic-v0/eval_compositional_slot_pass.json` | redesigned-benchmark eval after learned slot-typed observation pass-through. Exact rate remains `0.520000`; partial filler copying improves sequence ratio but does not solve composition |
| `run/artifacts/organic-v0/eval_compositional_tightened_persisted.json` | this cycle's headline: tightened-benchmark eval running from `loaded_from_disk` state (no JSONL training this run). Overall `0.360000`; hidden_rule drops 100%→40% (parity-cheat exposure), abstention 100%→60% (contrastive items expose domain-shortcut). Emits real `loaded_state_path` and `appended_event_log_path` |
| `run/artifacts/organic-v0/persist_self_test.json` | cycle-2 persistence-round-trip verdict: hash + output bit-exact across save→load. Preserved as historical evidence of the manifesto §"Persistence Is Pass-0" first ship |
| `run/artifacts/organic-v0/eval_compositional_v2c3.json` | cycle-3.5 headline (overwrites the cycle-3 ship after GPT audit follow-up): overall exact_rate `0.720` (+0.04 over cycle-3 0.680). unseen_filler 8/8 held, unseen_filler_long 2/2 held, direct_replay 4/5 (recovers cycle-3's regression from 3/5 toward cycle-2's 5/5). State hash `7e14358f4b003cbe`, model_config_hash `babe829e81dbbd0b` (differs from cycle-2's `a94747d83fbf1fc5` per audit finding 3) |
| `run/artifacts/organic-v0/eval_compositional_v2c3_from_disk.json` | cycle-3.5 verification: fresh-process eval loaded from disk (no JSONL training), summary_metrics + model_state_hash diff-clean against the from-JSONL eval. Proves the cycle-3.5 dual-learning state (mode-switch + trace-id-anchored literal channel) survives the persistence round-trip |
| `run/artifacts/organic-v0/persist_self_test_v2c3.json` | cycle-3.5 persistence-round-trip verdict: parent state_hash + raw_output `"mila quartz pier6"` matches child bit-exactly under hash `7e14358f4b003cbe`; `load_status: save_and_load_verified`. Confirms ROLES + SEGMENT_CONNS sections serialize and load cleanly under the cycle-3.5 dual-learning topology |
| `run/artifacts/organic-v0/eval_compositional_v2c4.json` | cycle-4 headline: trace-span-position literal memory lifts overall exact_rate to `0.760` and direct_replay to 5/5 while holding unseen_filler 8/8, unseen_filler_long 2/2, unseen_filler_short 1/1, and evidence_absence 2/2. State hash `23d5362d7c8b8ea7`, model_config_hash `490e66afe575275c` |
| `run/artifacts/organic-v0/eval_compositional_v2c4_from_disk.json` | cycle-4 verification: fresh-process eval loaded from `run/state/organic-v0/snapshots/raphael-local-0001/v2c4.pxstate`; summary_metrics + model_state_hash diff-clean against the from-training eval, proving trace-span-position CONNS and CONFIG fields persist cleanly |
| `run/artifacts/organic-v0/persist_self_test_v2c4.json` | cycle-4 persistence-round-trip verdict: parent state_hash + raw_output `"mila quartz pier6"` matches child bit-exactly under hash `23d5362d7c8b8ea7`; `load_status: save_and_load_verified` |
| `run/artifacts/organic-v0/eval_compositional_v2c5.json` | cycle-5 headline on the repaired benchmark: numeric-derived trace activation + relation projection + two-example farewell curriculum repair reach overall exact_rate `1.000` (25/25), hidden_rule 5/5, evidence_present 2/2, intent_transfer 1/1. State hash `ccd7a48ec4614703`, model_config_hash `de2ad1690588249d` |
| `run/artifacts/organic-v0/eval_compositional_v2c5_from_disk.json` | cycle-5 verification: fresh-process eval loaded from `run/state/organic-v0/snapshots/raphael-local-0001/v2c5.pxstate`; summary_metrics + model_state_hash diff-clean against the from-training eval |
| `run/artifacts/organic-v0/persist_self_test_v2c5.json` | cycle-5 persistence-round-trip verdict: parent_state_hash + child_state_hash `ccd7a48ec4614703`, parent_raw_output + child_raw_output `"mila quartz pier6"`, `hash_match: true`, `output_match: true`, `load_status: save_and_load_verified` |
| `run/artifacts/organic-v0/eval_cycle5_substrate_only_old_fixture.json` | cycle-5 falsification baseline: final binary on the un-repaired benchmark (no `bye sora`/`bye toma` train events). Substrate channels alone reach exact_rate `0.960` (24/25); only `evt_lang_test_004` (`bye elena`) fails — the by-design unlearnable farewell. State hash `b968647c92f30c57`. Splits the substrate claim from the curriculum-repair claim |
| `run/artifacts/organic-v0/eval_cycle5_ablate_numeric.json` | cycle-5 falsification: `--ablate-numeric-derived` on the repaired benchmark drops exact_rate to `0.880` (22/25); failures isolate to the hidden-rule family (`evt_rule_test_001`, `evt_rule_test_003`, `evt_rule_test_004`). State hash `6ccada17751408d0`. Proves the numeric-derived trace activation channel is what carries hidden-rule transfer |
| `run/artifacts/organic-v0/eval_cycle5_ablate_relation.json` | cycle-5 falsification: `--ablate-relation-projection` on the repaired benchmark drops exact_rate to `0.920` (23/25); failures isolate to evidence-present (`evt_abs_test_001`, `evt_abs_test_003`). State hash `75c0bb8012ffb437`. Proves the relation projection channel is what carries topic→object recall |
| `run/artifacts/organic-v0/eval_cycle6_relations_all_on.json` | cycle-6 headline on the expanded benchmark: parity + threshold + modular computed-relation channels reach overall exact_rate `1.000` (30/30), with threshold_rule_transfer 2/2 and modular_rule_transfer 3/3. State hash `29958f0880e662dc`, model_config_hash `99032d46527a795b` |
| `run/artifacts/organic-v0/eval_cycle6_relations_from_disk.json` | cycle-6 verification: fresh-process eval loaded from `run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate`; summary_metrics + model_state_hash diff-clean against the all-on from-training eval |
| `run/artifacts/organic-v0/persist_self_test_v2c6.json` | cycle-6 persistence-round-trip verdict: parent_state_hash + child_state_hash `29958f0880e662dc`, parent_raw_output + child_raw_output `"mila quartz pier6"`, `hash_match: true`, `output_match: true`, `load_status: save_and_load_verified` |
| `run/artifacts/organic-v0/eval_cycle6_ablate_numeric.json` | cycle-6 falsification: `--ablate-numeric-derived` drops exact_rate to `0.866667` (26/30); failures isolate to the four parity hidden-rule probes while threshold and modular families remain exact |
| `run/artifacts/organic-v0/eval_cycle6_ablate_threshold.json` | cycle-6 falsification: `--ablate-threshold-derived` drops exact_rate to `0.933333` (28/30); failures isolate to the two threshold probes while parity and modular families remain exact |
| `run/artifacts/organic-v0/eval_cycle6_ablate_modular.json` | cycle-6 falsification: `--ablate-modular-derived` drops exact_rate to `0.900000` (27/30); failures isolate to the three modular probes while parity and threshold families remain exact |
| `run/artifacts/organic-v0/eval_cycle6_ablate_relation.json` | cycle-6 regression gate: `--ablate-relation-projection` drops exact_rate to `0.933333` (28/30); failures remain isolated to evidence-present (`evt_abs_test_001`, `evt_abs_test_003`), while all numeric-relation families remain exact |
| `run/artifacts/organic-v0/eval_cycle6_legacy_cycle2_cycle5_fixture.json` | cycle-6 legacy compatibility: cycle-2 snapshot loaded under the cycle-6 binary on the cycle-5 fixture remains at exact_rate `0.360000` (9/25), state hash `3536309de837d3e2`, and `evt_mem_test_001` raw `"milaquart arch6"` |
| `run/artifacts/organic-v0/eval_cycle6_legacy_cycle2_current_fixture.json` | cycle-6 legacy compatibility on the expanded fixture: same cycle-2 snapshot scores exact_rate `0.300000` (9/30) because the denominator adds five new cycle-6 tests; state hash and historical raw output remain unchanged |
| `run/artifacts/organic-v0/train_live_chat_v0_manifesto_from_v2c6.json` | manifesto-safe chat continuation artifact: v2-c6 parent learns six raw-utterance chat seed events without semantic intent labels; child hash `888b7664126b7f5f` |
| `run/artifacts/organic-v0/eval_live_chat_v0_manifesto_from_v2c7_chat.json` | manifesto-safe chat regression artifact: child hash `888b7664126b7f5f` scores 1/5 (`0.200000`) on held-out raw chat, preserving honest failure instead of counting the contaminated 3/5 fork |
| `run/artifacts/organic-v0/train_cycle7a_child_a.json` | cycle-7A continuation train artifact: v2-c6 parent loaded, fork stream A learned, child checkpoint saved, and state growth reported under hash `fab9c2c0367ed2b5` |
| `run/artifacts/organic-v0/train_cycle7a_child_b.json` | cycle-7A continuation train artifact: v2-c6 parent loaded, fork stream B learned, child checkpoint saved, and state growth reported under hash `c0f016285e735e14` |
| `run/artifacts/organic-v0/eval_cycle7a_child_a_from_training.json` | cycle-7A same-process continued-child eval for fork A; learns from parent then evaluates held-out probe at 1/1 with raw output `"aurora branch"` |
| `run/artifacts/organic-v0/eval_cycle7a_child_a_from_disk.json` | cycle-7A fresh loaded-child eval for fork A; summary_metrics + model_state_hash match the from-training child eval |
| `run/artifacts/organic-v0/eval_cycle7a_child_b_from_training.json` | cycle-7A same-process continued-child eval for fork B; learns from parent then evaluates held-out probe at 1/1 with raw output `"ember branch"` |
| `run/artifacts/organic-v0/eval_cycle7a_child_b_from_disk.json` | cycle-7A fresh loaded-child eval for fork B; summary_metrics + model_state_hash match the from-training child eval |
| `run/artifacts/organic-v0/persist_self_test_cycle7a_child.json` | cycle-7A continuation persistence self-test: v2-c6 parent loads, stream A is learned, child checkpoint reloads in a child process with hash and output match |
| `run/artifacts/organic-v0/eval_cycle7a_legacy_cycle2_cycle5_fixture.json` | cycle-7A legacy compatibility gate: `/tmp/cycle2.pxstate` still scores 9/25 (`0.360000`) on the historical cycle-5 fixture with state hash `3536309de837d3e2` |
| `run/artifacts/organic-v0/fork_divergence_cycle7a.json` | cycle-7A machine-readable fork-divergence verdict: children A/B load the same parent, grow by different connection deltas, reload cleanly, diverge in state hash, and emit different held-out raw outputs |
| `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_seed7001.json` | cycle-7B native interactive hidden-rule artifact for seed 7001: loaded v2-c6 parent, action-before-feedback history, 7/7 held-out exact, and support failure traces preserved |
| `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_seed7002.json` | cycle-7B native interactive hidden-rule artifact for seed 7002: loaded v2-c6 parent, action-before-feedback history, 7/7 held-out exact, and support failure traces preserved |
| `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_summary.json` | cycle-7B aggregate scorecard over seeds 7001/7002: 14/14 held-out exact and 26/42 total pre-feedback exact, with oracle access limited to after-action feedback |
| `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_feedback1_seed7001.json` | cycle-7B feedback-strength ablation member: seed 7001 rerun with correction strength 1.0 instead of 2.0; preserves the weaker adaptation trace |
| `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_feedback1_seed7002.json` | cycle-7B feedback-strength ablation member: seed 7002 rerun with correction strength 1.0 instead of 2.0; exposes the held-out modular miss under weaker correction |
| `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_feedback_ablation.json` | cycle-7B feedback-strength ablation summary: strength 2.0 reaches 14/14 held-out and 26/42 total; strength 1.0 drops to 13/14 held-out and 15/42 total |
| `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_seed7101.json` | cycle-7C native interactive symbolic-rule artifact for seed 7101: loaded v2-c6 parent, action-before-feedback history over same_color/different_shape/same_place/role_match, 8/8 held-out exact, post-episode probe 8/8, support failure traces preserved |
| `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_seed7102.json` | cycle-7C native interactive symbolic-rule artifact for seed 7102: second held-out seed for the same non-numeric symbolic relation rung, 8/8 held-out exact, post-episode probe 8/8, distinct final state hash |
| `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_probe_seed7101.json` | cycle-7C fresh loaded-child probe artifact for seed 7101: loaded `cycle7c-symbolic-seed7101.pxstate` and reproduced the same 8/8 post-episode probe score with matching model hash |
| `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_probe_seed7102.json` | cycle-7C fresh loaded-child probe artifact for seed 7102: loaded `cycle7c-symbolic-seed7102.pxstate` and reproduced the same 8/8 post-episode probe score with matching model hash |
| `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_summary.json` | cycle-7C aggregate scorecard over seeds 7101/7102: 16/16 held-out exact, 48/64 total pre-feedback exact, 16/16 post-episode probes, and from-disk probe hash/summary matches |
| `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_ablate_seed7101.json` | cycle-7C symbolic-channel ablation member for seed 7101: `--ablate-symbolic-relations` drops held-out transfer from 8/8 to 1/8 and preserves the failure traces |
| `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_ablate_seed7102.json` | cycle-7C symbolic-channel ablation member for seed 7102: `--ablate-symbolic-relations` drops held-out transfer from 8/8 to 1/8 and preserves the failure traces |
| `run/artifacts/organic-v0/interactive_symbolic_rule_cycle7c_symbolic_ablation.json` | cycle-7C ablation summary: all-on reaches 16/16 held-out and 48/64 total; disabling cue-bound symbolic relation features drops to 2/16 held-out and 4/64 total |
| `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_seed7201.json` | cycle-7D native interactive grid-rule artifact for seed 7201: loaded v2-c6 parent, action-before-feedback history over horizontal/vertical/diagonal/row spatial families, 8/8 held-out exact, post-episode probe 8/8, support failure traces preserved |
| `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_seed7202.json` | cycle-7D native interactive grid-rule artifact for seed 7202: second held-out seed for the tiny 3x3 spatial relation rung, 8/8 held-out exact, post-episode probe 8/8, distinct final state hash |
| `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_probe_seed7201.json` | cycle-7D fresh loaded-child probe artifact for seed 7201: loaded `cycle7d-grid-seed7201.pxstate` and reproduced the same 8/8 post-episode probe score with matching model hash |
| `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_probe_seed7202.json` | cycle-7D fresh loaded-child probe artifact for seed 7202: loaded `cycle7d-grid-seed7202.pxstate` and reproduced the same 8/8 post-episode probe score with matching model hash |
| `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_summary.json` | cycle-7D aggregate scorecard over seeds 7201/7202: 16/16 held-out exact, 48/64 total pre-feedback exact, 16/16 post-episode probes, and from-disk probe hash/summary matches |
| `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_ablate_seed7201.json` | cycle-7D grid-spatial ablation member for seed 7201: `--ablate-grid-spatial` drops held-out transfer from 8/8 to 2/8 and preserves the failure traces |
| `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_ablate_seed7202.json` | cycle-7D grid-spatial ablation member for seed 7202: `--ablate-grid-spatial` drops held-out transfer from 8/8 to 1/8 and preserves the failure traces |
| `run/artifacts/organic-v0/interactive_grid_rule_cycle7d_grid_ablation.json` | cycle-7D ablation summary: all-on reaches 16/16 held-out and 48/64 total; disabling cue-bound grid/spatial features drops to 3/16 held-out and 6/64 total |

## Not tracked, on disk

- `.agents/`, `.codex/` — environment-owned scratch dirs from the agent harness; not project content
- `build/` — gitignored; produced by `make`
- `run/state/` — gitignored; persistence runtime substrate (state snapshots under `snapshots/<organism_id>/`, append-only event logs under `events/`). These ARE the organism's memory but regenerate per run; tracked artifacts above point to these paths
- `src/project_x_v2/`, `tests/` — empty directories left over from the v1 reset. Untracked, candidates for removal next cycle
