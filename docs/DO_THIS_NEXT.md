# Do This Next - Project X v2

Generated: 2026-05-13 (post cycle-3.5 ship — GPT audit follow-up; dual-learning lifted overall 0.680 → 0.720 and direct_replay 3/5 → 4/5 with unseen_filler 8/8 held)

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/PERSISTENCE_SCHEMA.md`
5. `docs/artifacts/CYCLE3_MECHANISM.md` — the cycle-3 architecture lock; cycle-3.5 extends rather than replaces it
6. `docs/past_work/cycles/phase_v2_organic_substrate/dev-cycle-3-5.md` — what the GPT audit found, how it landed, residual failures
7. `docs/past_work/cycles/phase_v2_organic_substrate/dev-cycle-3-4a0260f.md` — preserved cycle-3 narrative (the regression that cycle-3.5 closed)
8. `docs/past_work/` only when older context is needed

## What Just Happened — Cycle 3.5

A GPT audit of cycle-3 (commit `4a0260f`) returned a 318/420 score and flagged five concrete defects plus two planning corrections. Each defect was verified at the cited source location, fixed, and re-measured.

### Defects fixed

1. **Absent-filler replay** — cycle-3 routed observation-filler spans ONLY to mode-switch weights at training. When the matching role was absent at eval, the missing-role guardrail zeroed mode-switch and the literal weights at those positions were never trained — the brain stalled. Cycle-3.5 dual-learns: mode-switch keeps full supervision; literal chars are also supervised, but ONLY through trace-id-derived state features (per-event memory anchor). The structural framing came from advisor: trace-id is the natural memory-anchor channel for literal recovery, base-context features remain the role-routing channel for mode-switch.
2. **Legacy loader default** — `load_serialized_state()` now seeds `use_segment_mode=false`, `max_roles=kMaxRoles`, `segment_mode_gain=0.3` BEFORE parsing CONFIG, so cycle-2 snapshots (which omit those keys) load with legacy semantics rather than silently keeping the binary's segment-mode default.
3. **Dishonest config hash** — `write_config()` now serializes `segment_mode_gain`, `use_segment_mode`, `max_roles`. `config_hash()` reads through `write_config()`, so the model_config_hash now reflects answer-path behavior. New cycle-3.5 hash `babe829e81dbbd0b` ≠ cycle-2's `a94747d83fbf1fc5`.
4. **Segment-mode evidence export** — `is_mode_switch`, `is_copy_emit`, `copy_role` are emitted on every step in `generation_steps`, so eval artifacts now record when the brain entered copy mode and which role drove it.
5. **Empty-role guardrail silent break** — when the only surviving votes are mode-switches for missing roles (all zeroed by the guardrail), the loop now emits an explicit END step before breaking, matching the architecture doc and giving the evidence trail a real decision instead of a missing step.

### Headline result (`run/artifacts/organic-v0/eval_compositional_v2c3.json`)

| metric | cycle 2 | cycle 3 | cycle 3.5 |
|---|---|---|---|
| overall exact_rate | 0.360 | 0.680 | **0.720** |
| `direct_replay` | 5/5 | 3/5 | **4/5** |
| `unseen_filler` | 0/8 | 8/8 | **8/8** |
| `unseen_filler_long` | 0/2 | 2/2 | **2/2** |
| `unseen_filler_short` | 1/1 | 1/1 | 1/1 |
| `evidence_absence` | 2/2 | 2/2 | 2/2 |
| `unseen_rule_transfer` | 1/2 | 1/2 | 1/2 |
| `intent_transfer` | 0/1 | 0/1 | 0/1 |
| `evidence_present` | 0/2 | 0/2 | 0/2 |
| `distractor_rule_transfer` | 0/2 | 0/2 | 0/2 |

State hash `7e14358f4b003cbe`. Persistence round-trip diff-clean (eval-from-disk vs eval-from-training: `summary_metrics + model_state_hash` empty diff). Legacy cycle-2 snapshot loads cleanly under the cycle-3.5 binary and recovers cycle-2's exact_rate 0.360 + `"milaquart arch6"` on evt_mem_test_001.

### Residual failures (7 of 25)

The audit's planning correction was to define cycle-4 candidates from the NEW failure cases, not the cycle-3 ones (which assumed a wrong diagnosis). Current failure case set:

- `evt_mem_dev_000` (direct_replay): emits `"arin copper tr copper copper copper copper coppe"`. Mode-switch person/object copy works; literal-recovery for "tray4" via trace-id-arin starts correctly with `tr`, but at pos=14 prev='r' the global-prev='r' supervision of ' ' (learned from inter-word transitions at training) edges past trace-id-arin's supervision of 'a'. The brain emits ' ' and re-enters mode-switch role:object — copper is observed, so the guardrail does NOT zero it — and copies "copper" again. Architectural boundary of trace-id-only literal supervision when global-prev's literal vote competes inside a filler span.
- `evt_rule_test_001` / `evt_rule_test_003` / `evt_rule_test_004` (rule_transfer + distractor_rule_transfer): "go"/"stay" parity rule failures. Trained signal-association beats parity computation. Affects 3 of 7 residual failures.
- `evt_lang_test_004` (intent_transfer): emits "hi elena" instead of "bye elena". `intent:farewell` does not override the trained "hi" bigram at pos=0.
- `evt_abs_test_001` / `evt_abs_test_003` (evidence_present): emits "?" instead of the recall target. Abstention shortcut still wins over trained-memory recall when the input partially overlaps the abstention domain.

## Next Cycle Contract — cycle 4

Three candidates compete via `/pick-one` at cycle open. Each is grounded in the cycle-3.5 failure_cases, not theory.

### Candidate A — Trace-id literal supervision strength at deep span positions

**Targets:** `evt_mem_dev_000` direct_replay (1 of 7 residual failures).

**Mechanism sketch:** The trace-id-anchored literal channel supervises 'a' at pos=14 prev='r' with stored weight = base_scale × reward × lr = 1.0 × 1.5 × 1.0 = 1.5. At eval, score['a'] = (similarity × trace_gain) × stored_state_feature_value. The competing global-prev='r' literal stored weight for ' ' (from train inter-word transitions) edges this out at deep span positions because the trace-id contribution is split across 4 derived state-bindings (pos, prev, bucket, pos+prev) while global-prev is a single feature with full transition_gain.

Two sub-options:
- **A1 (Cleanest):** Multiply trace-id-derived literal supervision by a scalar `trace_id_literal_boost` (config field, default ~1.5) so the literal walk inside a span receives stronger supervision specifically when routed through trace-id features. Tunable; no new feature topology.
- **A2 (Structural):** Add a NEW per-event-per-span-position state feature (combine(trace-id, "span-pos", index-within-span)) that fires only inside copy spans during literal-walk supervision. At eval, the activated trace's span-position features fire and supervise the right char without competing with global-prev features that dominate inter-word positions.

**Risk:** A1 is a tuning knob — easy to over-fit to the one remaining failure case. A2 is more principled but adds a new feature class to persistence (PXSTATE_V0 already extended once for cycle 3; another extension is paid for once).

**Close criterion:** `direct_replay` 5/5 with `unseen_filler` 8/8 held.

### Candidate B — Intent → literal-prefix learning

**Targets:** `evt_lang_test_004` intent_transfer (1 of 7 residual failures).

**Mechanism sketch:** The intent observation token (`intent:farewell`) currently contributes context features with `context_gain=1.0`. The "hi" bigram beats `intent:farewell` at pos=0 because "hi" was learned across 3 training events with reward 1.5 each while `intent:farewell` was supervised only in 1 training event. Add a scoped boost: intent-observation tokens contribute features with weight `context_gain × intent_pos0_boost` (e.g., 3.0) but ONLY when bound with pos<3 — at later positions the boost expires so it doesn't regress other domains.

**Risk:** Boosting intent specifically risks becoming an authored "intent → bye" route if implemented carelessly. The honest version: the boost applies to ALL `intent:*` observation tokens (intent_greeting, intent_farewell, intent_*), not just farewell. The intent feature class is part of the observation vocabulary; boosting its weight at early positions is learned-substrate calibration, not a parser branch.

**Close criterion:** `intent_transfer` 1/1.

### Candidate C — Rule-transfer mechanism (parity rule learning)

**Targets:** 3 of 7 residual failures (`evt_rule_test_001`, `evt_rule_test_003`, `evt_rule_test_004`).

**Mechanism sketch:** The hidden_rule domain trains on signal-label pairs ("two-step rhythm" → "go" / "single-step rhythm" → "stay"). The brain learns signal-token associations to literal answers. Distractor probes inject a signal whose label CONTRADICTS the parity rule — current brain emits the trained-signal-association literal, not the parity result. Cycle 4 would need to learn a computed boolean over the input rather than a memorized association — non-trivial structural change. May escalate to cycle 5 if the right mechanism isn't obvious at cycle open.

**Risk:** Significant. Parity computation in the same softmax substrate is either (a) a fundamentally larger reach than dual-learning, or (b) requires a new representational layer (HDC unbind + cleanup?) that cycle 3's /pick-one explicitly deferred. Worth running `/pick-one` again at cycle open with the cycle-3 advisor verdict in context.

**Close criterion:** at least 1 of the 3 hidden-rule failures flips to pass without regression elsewhere.

### Hard gates (unchanged from cycle 3 + cycle 3.5)

Reject any implementation that:

- adds parser-dispatcher logic for benchmark answers
- adds fixed response text as the agent output
- scores itself on subjective quality
- hides bad outputs
- adds new files without a `REPO_CONTROL.md` row in the same commit
- optimizes for "all tests pass" over organic learning
- adds CUDA kernels before the workload justifies parallelism
- ships a structural change without re-running on the tightened benchmark AND verifying the persistence self-test still passes
- modifies `benchmarks/v2_ladder/organic_v0.jsonl` (the benchmark exposed the bug and remains the contract)

### Close criteria for cycle 4

- Material improvement on at least ONE of: `direct_replay` (5/5), `intent_transfer` (1/1), one of the three hidden-rule failures.
- No regression on cycle-3.5 gains: `unseen_filler` 8/8, `unseen_filler_long` 2/2, `unseen_filler_short` 1/1, `direct_replay` 4/5, `evidence_absence` 2/2.
- Persistence round-trip still diff-clean (eval-from-disk vs eval-from-training on summary_metrics + model_state_hash).
- Cycle-2 snapshot still loads cleanly under the cycle-4 binary (recovers exact_rate 0.360 + `"milaquart arch6"` on evt_mem_test_001).
- REPO_CONTROL rows co-land for any new tracked artifacts.

## Suggested Command Sequence

```bash
make test                               # substrate guard + persistence round-trip (segment-mode on)
build/organic_v0 --phase eval --mode test \
  --data benchmarks/v2_ladder/organic_v0.jsonl \
  --out /tmp/eval_current.json
jq '{exact: .summary_metrics.overall.exact_rate, by_composition: .summary_metrics.by_composition}' /tmp/eval_current.json
jq '.failure_cases | map({evt: .event_id, comp: .composition, raw: .raw_generated_output, expected: .expected_output})' run/artifacts/organic-v0/eval_compositional_v2c3.json
```

## Follow-up Notes (advisor / future audit, not blocking cycle 4)

- **Artifact config_hash vs brain config_** — `write_eval_artifact` passes the outer `Config&` from `main()` to the artifact writer; after a `--load-state` flow the brain's internal config may differ (cycle-2 snapshot loaded under cycle-3.5 binary has `use_segment_mode=false` post-load, but the artifact reports `babe829e81dbbd0b` from the binary-default config). The audit's specific verification target (`config_hash` differs between cycle-2 and cycle-3.5 from-training runs) is met, but the deeper "config_hash should reflect the config actually used" honesty issue remains. Small refactor: pass `brain.config()` to the artifact writer. Cycle-4 nit unless an audit cites it again.
- **kMaxRoles overflow** is fail-fast (throws); current benchmark uses ~6 roles, headroom is 10. If benchmark v3 adds new role types beyond 16, bump the compile-time constant. Serialized state forward-compatible (role_id is a stable hash, not an index).
- **segment_mode_gain calibration** held at 0.3 through cycle 3.5. Worth re-measuring if cycle 4 changes feature topology.
- **Branch name** `feat/organic-v0-trace-id-ablation` carries cycle 1 + 2 + audit + cycle 3 + cycle 3.5 — increasingly stale. PR rollup needs lain input; do not act unprompted.

## Close Criteria For The Next Pass

- A targeted mechanism (one of the three candidates above) that materially improves at least one of the residual failure modes.
- The mechanism MUST survive the persistence round-trip on the new state (any added connection-features, atoms, or per-segment counters).
- No regression on cycle-3.5 metrics (see "Close criteria for cycle 4" above).
- No GPU/CUDA work, no Python answer-path migration, no template wrapper.
