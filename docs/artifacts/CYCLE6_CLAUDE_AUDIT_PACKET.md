# Cycle 6 Claude Audit Packet

Date: 2026-05-14
Subject: organic-v0 cycle 6, computed numeric relation generalization
Branch: `feat/organic-v0-trace-id-ablation`

## Audit Ask

Please grade cycle 6 harshly against the Project X rubric. Do not award points for prose, confidence, or the all-on score alone. Award credit only for mechanisms that are:

- visible in source;
- exercised by held-out events;
- falsified by ablation;
- preserved across save/load;
- compatible with older snapshots;
- documented without inflated claims.

Codex provisional self-score: **418/420**.

One-line rationale: cycle 6 answers the cycle-5 uncertainty by showing parity, threshold, and modular numeric relations can share a substrate pattern while remaining independently ablatable; it is not 420 because the rung is still typed, numeric, and offline rather than interactive or non-numeric.

## Claims To Audit

### Claim 1 - Expanded-fixture headline

With all cycle-6 channels enabled, the expanded fixture reaches 30/30 held-out exact.

Evidence:

- Artifact: `run/artifacts/organic-v0/eval_cycle6_relations_all_on.json`
- Exact: `1.000000`
- Count: `30`
- State hash: `29958f0880e662dc`
- Config hash: `99032d46527a795b`
- Run id: `organic-v0-eval-a774d45d3689`

This claim is substrate + cycle-6 benchmark expansion. It is not a claim of broad language understanding.

### Claim 2 - Persistence diff-clean

The trained state can be saved, loaded in a fresh eval run, and reproduce the same metrics and state hash.

Evidence:

- From-training artifact: `run/artifacts/organic-v0/eval_cycle6_relations_all_on.json`
- From-disk artifact: `run/artifacts/organic-v0/eval_cycle6_relations_from_disk.json`
- Diff command:

```bash
diff -u \
  <(jq -S '.summary_metrics, .model_state_hash' run/artifacts/organic-v0/eval_cycle6_relations_all_on.json) \
  <(jq -S '.summary_metrics, .model_state_hash' run/artifacts/organic-v0/eval_cycle6_relations_from_disk.json)
```

Expected output: empty diff.

Fresh-process round-trip:

- Artifact: `run/artifacts/organic-v0/persist_self_test_v2c6.json`
- `load_status`: `save_and_load_verified`
- Parent hash: `29958f0880e662dc`
- Child hash: `29958f0880e662dc`
- Parent output: `"mila quartz pier6"`
- Child output: `"mila quartz pier6"`

### Claim 3 - Per-family ablation isolation

Each computed-relation channel fails only its own family when disabled:

| Artifact | Flag | Exact | Expected isolated failures |
|---|---|---:|---|
| `eval_cycle6_ablate_numeric.json` | `--ablate-numeric-derived` | 26/30 (`0.866667`) | `evt_rule_test_001`, `evt_rule_test_002`, `evt_rule_test_003`, `evt_rule_test_004` |
| `eval_cycle6_ablate_threshold.json` | `--ablate-threshold-derived` | 28/30 (`0.933333`) | `evt_rule_thresh_test_001`, `evt_rule_thresh_test_002` |
| `eval_cycle6_ablate_modular.json` | `--ablate-modular-derived` | 27/30 (`0.900000`) | `evt_rule_mod_test_001`, `evt_rule_mod_test_002`, `evt_rule_mod_test_003` |
| `eval_cycle6_ablate_relation.json` | `--ablate-relation-projection` | 28/30 (`0.933333`) | `evt_abs_test_001`, `evt_abs_test_003` |

Audit command:

```bash
for f in run/artifacts/organic-v0/eval_cycle6_ablate_{numeric,threshold,modular,relation}.json; do
  jq -r 'input_filename + " exact=" + (.summary_metrics.overall.exact_rate|tostring) + " failures=" + ([.failure_cases[].event_id] | join(","))' "$f"
done
```

Why this matters: if threshold or modular piggybacked on parity, the `--ablate-numeric-derived` run would also fail threshold/modular, or the new ablations would break parity. The artifacts show clean separation.

### Claim 4 - Legacy compatibility

The cycle-2 snapshot still loads under the cycle-6 binary with its historical behavior on the cycle-5 fixture.

Evidence:

- Artifact: `run/artifacts/organic-v0/eval_cycle6_legacy_cycle2_cycle5_fixture.json`
- Exact: 9/25 (`0.360000`)
- State hash: `3536309de837d3e2`
- `evt_mem_test_001` raw output: `"milaquart arch6"`

The expanded current fixture artifact exists separately:

- Artifact: `run/artifacts/organic-v0/eval_cycle6_legacy_cycle2_current_fixture.json`
- Exact: 9/30 (`0.300000`)
- State hash: `3536309de837d3e2`

The current-fixture drop is denominator expansion from five new cycle-6 held-out tests, not a change to the loaded legacy state.

### Claim 5 - Learnability audit before data edit

The learnability audit for threshold and modular benchmark additions was written before editing the JSONL fixture.

Evidence:

- Audit/design doc: `docs/artifacts/CYCLE6_NUMERIC_RELATION_GENERALIZATION.md`
- Benchmark: `benchmarks/v2_ladder/organic_v0.jsonl`

Training-data guard:

- threshold has two low marks and two high marks;
- modular has two distinct marks per class under `modulus:3`;
- held-out tests use unseen marks and omit `threshold:*` / `modclass:*` labels.

## Source Surfaces To Inspect

Primary implementation:

- `native/organic_v0.cpp`

Load-bearing areas:

- CONFIG fields: `derived_relation_gain`, `use_threshold_derived_features`, `use_modular_derived_features`;
- relation helpers: `threshold_relation_keys`, `modular_relation_keys`;
- trace caches: `refresh_trace_caches`;
- HDC atoms: `num-threshold:*`, `num-modular:*`;
- context features and trace activation for threshold/modular;
- CLI flags: `--ablate-threshold-derived`, `--ablate-modular-derived`;
- persistence CONFIG write/load defaults.

Benchmark:

- `benchmarks/v2_ladder/organic_v0.jsonl`

Docs:

- `docs/artifacts/CYCLE6_NUMERIC_RELATION_GENERALIZATION.md`
- `docs/artifacts/PERSISTENCE_SCHEMA.md`
- `docs/REPO_CONTROL.md`
- `docs/A_TO_Z_PLAN.md`
- `docs/DO_THIS_NEXT.md`
- `docs/past_work/cycles/phase_v2_organic_substrate/dev-cycle-6*.md`

## Verification Commands

Run from repo root:

```bash
make test
```

Expected:

- native self-test OK;
- persistence round-trip OK;
- hash `29958f0880e662dc`;
- output `"mila quartz pier6"`.

Regenerate headline:

```bash
build/organic_v0 --phase eval \
  --out /tmp/eval_cycle6_relations_all_on.audit.json
```

Regenerate ablations:

```bash
build/organic_v0 --phase eval --out /tmp/eval_cycle6_ablate_numeric.audit.json --ablate-numeric-derived
build/organic_v0 --phase eval --out /tmp/eval_cycle6_ablate_threshold.audit.json --ablate-threshold-derived
build/organic_v0 --phase eval --out /tmp/eval_cycle6_ablate_modular.audit.json --ablate-modular-derived
build/organic_v0 --phase eval --out /tmp/eval_cycle6_ablate_relation.audit.json --ablate-relation-projection
```

Compare expected failure IDs to the table above.

## Speed/Efficiency Claim

Cycle 6 includes a small structural speed cleanup:

- parsed observation slots and relation keys are cached per trace after learn/load;
- trace span-position lookup uses a transient event-id index.

Measured timing on the tiny fixture did not materially change:

- baseline before cache/index: about `elapsed=0.12 user=0.12 sys=0.00 maxrss=18688`;
- after cache/index: about `elapsed=0.12 user=0.11 sys=0.01 maxrss=18688`.

Audit interpretation: accept only the reduced repeated-work/asymptotic claim. Do not count this as a meaningful wall-clock benchmark improvement.

## Residual Risks

- The relation families are still numeric and typed. This does not prove symbolic equality, role matching, or open-ended rule induction.
- The benchmark is still offline JSONL, not an interactive hidden-rule game.
- Threshold equality-at-cutoff is supported by key construction but not exercised by held-out events.
- The current organic-v0 generator is not a natural-language chat model; do not confuse these substrate scores with ChatGPT-like conversation ability.

## Suggested Score Range

414-418 if the ablation isolation and persistence checks pass under audit.

419 only if the reviewer believes the independent three-channel isolation teaches a genuinely general substrate lesson beyond the planned ladder.

420 only if the reviewer sees something more surprising than typed numeric relation generalization. Codex does not claim that here.
