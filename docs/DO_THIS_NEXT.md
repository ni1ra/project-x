# Do This Next - Project X v2

Generated: 2026-05-13 (post cycle-4 ship — trace-span-position literal memory lifted overall 0.720 → 0.760 and direct_replay 4/5 → 5/5 with unseen_filler 8/8 held)

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/PERSISTENCE_SCHEMA.md`
5. `docs/artifacts/CYCLE3_MECHANISM.md` — segment-mode architecture lock
6. `docs/past_work/cycles/phase_v2_organic_substrate/dev-cycle-4-422ed12.md` — cycle-4 mechanism, scoring, and measured lift
7. `docs/past_work/cycles/phase_v2_organic_substrate/dev-cycle-3-5-5c69d51.md` — audit-vs-measured calibration canon
8. `docs/past_work/` only when older context is needed

## What Just Happened — Cycle 4

Cycle 4 ran the 420-scale decision protocol over the three cycle-3.5 candidates and picked **Candidate A2 — trace-span-position literal memory** at **407/420**.

The residual `evt_mem_dev_000` failure was not a broad missing-copy problem. Person/object mode-switches already worked, and the trace-id literal fallback started `"tray4"` correctly as `"tr"`. The failure was one deep span-internal transition: at pos 14, `prev='r'`, global-prev's inter-word space scored `6.021008` while trace-id arin's literal `'a'` scored `5.443025`.

Cycle 4 added a trace-local feature keyed by `(trace-id, role, offset-inside-copied-span)`. Training writes this feature only during the trace-id literal walk for copied spans. Generation reactivates it only from the activated trace's own target segmentation when the current output position is inside that remembered span. Normal role-copy transfer still wins when the role is present; the new feature is a fallback memory anchor when a role is absent.

Small honesty fix also landed: `write_eval_artifact()` now reports `brain.config()` after load/train, not the outer binary-default `Config`, so loaded-state artifacts describe the actual answer-path config.

### Headline result (`run/artifacts/organic-v0/eval_compositional_v2c4.json`)

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

State hash `23d5362d7c8b8ea7`. Config hash `490e66afe575275c` differs from cycle-3.5 `babe829e81dbbd0b` and cycle-2 `a94747d83fbf1fc5`.

Persistence evidence:

- `run/artifacts/organic-v0/eval_compositional_v2c4_from_disk.json` is diff-clean against from-training on `summary_metrics + model_state_hash`.
- `run/artifacts/organic-v0/persist_self_test_v2c4.json` reports `save_and_load_verified` with parent/child hash `23d5362d7c8b8ea7` and output `"mila quartz pier6"`.
- A cycle-2 snapshot built from commit `78291d1` still loads under the cycle-4 binary with exact_rate `0.360`, state hash `3536309de837d3e2`, and `evt_mem_test_001` raw `"milaquart arch6"`.

## Remaining Failures (6 of 25)

- `evt_rule_test_001` (`unseen_rule_transfer`): raw `"go"`, expected `"stay"`.
- `evt_rule_test_003` (`distractor_rule_transfer`): raw `"go"`, expected `"stay"`.
- `evt_rule_test_004` (`distractor_rule_transfer`): raw `"stay"`, expected `"go"`.
- `evt_lang_test_004` (`intent_transfer`): raw `"hi elena"`, expected `"bye elena"`.
- `evt_abs_test_001` (`evidence_present`): raw `"?"`, expected `"copper"`.
- `evt_abs_test_003` (`evidence_present`): raw `"?"`, expected `"glass"`.

Important calibration: the old cycle-4 Candidate B diagnosis was stale. The benchmark has no training target containing `"bye"` and no `intent:farewell` training event. A positional intent boost cannot honestly learn `bye`; it can only amplify already-learned literal prefixes.

## Next Cycle Contract — cycle 5

Pick one candidate via the 420-scale protocol, grounded in the six current failure cases.

### Candidate A — Rule-transfer computed parity substrate

**Targets:** `evt_rule_test_001`, `evt_rule_test_003`, `evt_rule_test_004` (3 of 6 residual failures).

**Mechanism sketch:** stop treating hidden_rule as signal-label recall. The brain needs a learned/computed rule feature over the input/observations that distinguishes odd/even mark values and can override memorized signal associations when distractors contradict them. The acceptable version is a general representational layer or HDC unbind/cleanup path for numeric/parity structure, not an answer-route branch that says odd → stay / even → go.

**Close criterion:** at least 1 hidden-rule failure flips without regressing cycle-4 gains.

### Candidate B — Evidence-present memory recall bridge

**Targets:** `evt_abs_test_001`, `evt_abs_test_003` (2 of 6 residual failures).

**Mechanism sketch:** the current abstention shortcut wins whenever the input resembles unknown/topic questions. Add a learned memory-evidence bridge so a topic/entity cue can activate a stored memory trace and let an associated role filler compete with `"?"`. The honest version should route through stored trace structure and learned weights; it must not special-case `arin -> copper` or `bea -> glass`.

**Close criterion:** at least 1 evidence_present failure flips while `evidence_absence` stays 2/2.

### Candidate C — Language intent learnability audit + substrate repair

**Targets:** `evt_lang_test_004` (1 of 6 residual failures).

**Mechanism sketch:** first decide whether the current `bye` target is a valid rung for an organic learner with no pretrained semantics and no `bye` training output. If valid, the substrate needs a real compositional mechanism that can form a farewell concept from non-output evidence; if invalid, the benchmark needs a versioned curriculum repair in a separate, explicit benchmark-change cycle. Do not hide this by boosting `intent:*` and claiming learned transfer.

**Close criterion:** either `intent_transfer` flips through a defensible learned mechanism, or a documented benchmark-rung correction lands with before/after artifacts and no stale claim that the old fixture was solved.

### Hard Gates

Reject any implementation that:

- adds parser-dispatcher logic for benchmark answers
- adds fixed response text as the agent output
- scores itself on subjective quality
- hides bad outputs
- modifies `benchmarks/v2_ladder/organic_v0.jsonl` without a deliberate benchmark-versioning rationale and before/after artifacts
- regresses cycle-4 gains: `direct_replay` 5/5, `unseen_filler` 8/8, `unseen_filler_long` 2/2, `unseen_filler_short` 1/1, `evidence_absence` 2/2, overall exact_rate ≥ 0.760
- ships without persistence diff-clean and cycle-2 legacy-load verification
- adds CUDA kernels before the workload justifies parallelism

## Suggested Command Sequence

```bash
make test
build/organic_v0 --phase eval --mode test \
  --data benchmarks/v2_ladder/organic_v0.jsonl \
  --out /tmp/eval_current.json
jq '{exact: .summary_metrics.overall.exact_rate, by_composition: .summary_metrics.by_composition, failures: (.failure_cases | map({evt: .event_id, comp: .composition, raw: .raw_generated_output, expected: .expected_output}))}' /tmp/eval_current.json
```

## Close Criteria For The Next Pass

- A targeted mechanism materially improves at least one of the six residual failures.
- No regression on cycle-4 metrics listed above.
- Persistence round-trip stays diff-clean on `summary_metrics + model_state_hash`.
- Cycle-2 snapshot still loads under the new binary with exact_rate `0.360` and `evt_mem_test_001` raw `"milaquart arch6"`.
- New tracked artifacts have `REPO_CONTROL.md` rows in the same commit.
