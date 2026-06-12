# Phase v2 Organic Substrate — Cycle 4 reflection

**Theme:** Trace-span-position literal memory for deep absent-role replay
**Closed:** 2026-05-13
**Cycle horizon:** cycle-4 continuation after cycle-3.5 audit ship
**Implementer:** Codex GPT-5

## Context

Cycle 3.5 left one direct_replay failure: `evt_mem_dev_000` emitted `"arin copper tr copper copper copper copper coppe"` instead of `"arin copper tray4"`. The trace-id literal fallback already started the absent `place:tray4` span correctly (`"tr"`), but at pos 14 `prev='r'`, global-prev's inter-word space scored `6.021008` while trace-id arin's literal `'a'` scored `5.443025`. The brain emitted a space, then role:object mode-switch fired again because `object:copper` was present.

## 420-scale candidate verdict

- **A — Trace-id literal supervision strength:** A2 scored **407/420** and won. A1 scored 392/420: likely effective but scalar-only. A2 adds the missing feature variable instead of broadly boosting the existing trace-derived bindings.
- **B — Intent → literal-prefix learning:** scored **342/420** after reading the benchmark. There is no trained `intent:farewell` event and no trained `"bye"` output, so a positional intent boost cannot honestly learn `"bye"`.
- **C — Rule-transfer mechanism:** scored **377/420**. It targets 3 failures, but the minimum mechanism is not obvious in the current substrate without a larger computed-rule/cleanup layer.

## What shipped

1. **Trace-span-position literal feature** — during segment-mode training, when a target span matches an observation filler, the literal fallback now writes an additional trace-local feature keyed by `(trace-id, role, offset-inside-span)`. At generation, activated traces re-enable that feature only when the trace's own target segmentation says the current output position is inside that copied span.

2. **Config + persistence plumbing** — `trace_span_position_gain` and `use_trace_span_position_features` are serialized in the PXSTATE CONFIG line, parsed on load, and included in `write_config()` so `model_config_hash` changes when the answer path changes. Older snapshots default these fields off on load.

3. **Artifact config honesty nit** — `write_eval_artifact()` now reports `brain.config()` after train/load. A cycle-2 loaded artifact now shows `use_segment_mode=false` and `use_trace_span_position_features=false` instead of binary defaults.

The feature state lives in existing `CONNS` literal weights, so no new PXSTATE section was needed. State-hash compatibility stays safe because legacy snapshots have no new weights and cycle-4 fields default off when absent.

## Measurement

`run/artifacts/organic-v0/eval_compositional_v2c4.json`:

| metric | cycle 3.5 | cycle 4 |
|---|---:|---:|
| overall exact_rate | 0.720 | **0.760** |
| `direct_replay` | 4/5 | **5/5** |
| `unseen_filler` | 8/8 | **8/8** |
| `unseen_filler_long` | 2/2 | **2/2** |
| `unseen_filler_short` | 1/1 | **1/1** |
| `evidence_absence` | 2/2 | **2/2** |
| `unseen_rule_transfer` | 1/2 | 1/2 |
| `intent_transfer` | 0/1 | 0/1 |
| `evidence_present` | 0/2 | 0/2 |
| `distractor_rule_transfer` | 0/2 | 0/2 |

State hash: `23d5362d7c8b8ea7`. Config hash: `490e66afe575275c` (differs from cycle-3.5 `babe829e81dbbd0b` and cycle-2 `a94747d83fbf1fc5`).

Target flip evidence: `evt_mem_dev_000` now emits `"arin copper tray4"`. At pos 14, `'a'` scores `6.202164` vs space `6.021008`; the new span-position feature provides just enough trace-local evidence without reintroducing base-context literal supervision.

Persistence:

- `run/artifacts/organic-v0/eval_compositional_v2c4_from_disk.json` diff-clean against from-training on `summary_metrics + model_state_hash`.
- `run/artifacts/organic-v0/persist_self_test_v2c4.json`: `save_and_load_verified`, parent/child hash `23d5362d7c8b8ea7`, parent/child output `"mila quartz pier6"`.
- Legacy cycle-2 worktree at `78291d1` produced `/tmp/cycle2.pxstate`; cycle-4 binary loaded it with exact_rate `0.360`, state hash `3536309de837d3e2`, and `evt_mem_test_001` raw `"milaquart arch6"`.

Verification commands:

```bash
make build/organic_v0
make test
build/organic_v0 --phase eval --mode test --data benchmarks/v2_ladder/organic_v0.jsonl --save-state run/state/organic-v0/snapshots/raphael-local-0001/v2c4.pxstate --event-log run/state/organic-v0/events/raphael-local-0001.jsonl --out run/artifacts/organic-v0/eval_compositional_v2c4.json
build/organic_v0 --phase eval --mode test --data benchmarks/v2_ladder/organic_v0.jsonl --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c4.pxstate --out run/artifacts/organic-v0/eval_compositional_v2c4_from_disk.json
jq '{summary_metrics, model_state_hash}' run/artifacts/organic-v0/eval_compositional_v2c4.json > /tmp/v2c4.tr.json
jq '{summary_metrics, model_state_hash}' run/artifacts/organic-v0/eval_compositional_v2c4_from_disk.json > /tmp/v2c4.dk.json
diff /tmp/v2c4.tr.json /tmp/v2c4.dk.json
build/organic_v0 --phase persistence-self-test --data benchmarks/v2_ladder/organic_v0.jsonl --save-state /tmp/persist_v2c4.pxstate --verify-event evt_mem_test_001 --out run/artifacts/organic-v0/persist_self_test_v2c4.json
git worktree add /tmp/cycle2-build 78291d1
/tmp/cycle2-build/build/organic_v0 --phase eval --mode test --data /tmp/cycle2-build/benchmarks/v2_ladder/organic_v0.jsonl --save-state /tmp/cycle2.pxstate --out /tmp/cycle2_eval.json
build/organic_v0 --phase eval --mode test --data benchmarks/v2_ladder/organic_v0.jsonl --load-state /tmp/cycle2.pxstate --out /tmp/cycle2_loaded.json
git worktree remove /tmp/cycle2-build
git diff --check
```

## Why this matters

Cycle 3 introduced role-copy transfer; cycle 3.5 added trace-id fallback literals for absent roles. Cycle 4 makes that fallback structurally sharper: a memory trace can now say not only "I remember this char after this previous char at this output position", but also "I remember this char at offset K inside this role span." That is closer to a role/filler memory substrate and less like a global bigram patch.

It also preserves the cycle-3.5 lesson. The new literal evidence is trace-local and span-local. It does not supervise literal chars across shared base-context features, which was the measured cause of the cycle-3.5 first-attempt unseen_filler collapse.

## What still fails

6 of 25 held-out events still fail:

- `evt_rule_test_001`: `"go"` vs expected `"stay"`.
- `evt_rule_test_003`: `"go"` vs expected `"stay"`.
- `evt_rule_test_004`: `"stay"` vs expected `"go"`.
- `evt_lang_test_004`: `"hi elena"` vs expected `"bye elena"`.
- `evt_abs_test_001`: `"?"` vs expected `"copper"`.
- `evt_abs_test_003`: `"?"` vs expected `"glass"`.

The language failure is not just a weak intent feature. The current benchmark contains no trained `"bye"` output and no `intent:farewell` training event. Treating it as a simple boost target would be dishonest.

## Audit-vs-measured calibration

Pre-implementation expectation: A2 should add enough trace-local evidence to flip only `evt_mem_dev_000`, with low unseen_filler risk because copy-mode skips scoring after a mode-switch fires. Measured result matched that expectation: direct_replay moved 4/5 → 5/5, overall moved 0.720 → 0.760, and all cycle-3.5 gains held.

The useful surprise was Candidate B's invalid premise. The handoff/docs claimed `intent:farewell` had a training example, but the benchmark showed otherwise. Cycle 5 should not inherit that stale diagnosis.

## Self-impression score

**402 / 420.**

The cycle shipped a minimum structural feature, closed the targeted failure, preserved all regression gates, fixed a deferred config-hash honesty issue, and documented the stale Candidate B premise. Not 420 because it closed 1 of 7 residual failures; rule transfer and evidence-present recall remain untouched, and the new span-position gain is still a calibrated feature scale even though the feature topology is principled.

## Next cycle direction

Cycle 5 should pick among:

1. **Rule-transfer computed parity substrate** — highest residual count, hardest mechanism.
2. **Evidence-present memory recall bridge** — topic/entity cue activates stored role filler instead of abstention shortcut.
3. **Language intent learnability audit + substrate repair** — handle the `bye` fixture honestly, not via a stale boost story.
