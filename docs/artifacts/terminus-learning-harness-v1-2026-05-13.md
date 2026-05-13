# Terminus Learning Harness v1 — 2026-05-13

**Scope:** Cross-seed reliability characterization + non-linear scoring exploration + scaled training repeats + HebbianBank audit-loop integration.

**Honest framing:** This is measurement, not magic. Every number below comes from the code you can run.

---

## 1. Cross-seed reliability sweep (11 seeds)

**Method:** `scripts/terminus_cross_seed_sweep.py` trains `TemporalTraceBank` on 36 training tasks, evaluates on 12 held-out tasks, repeats across 11 seeds.

| Seed | Pass rate | Action accuracy | Failure mode |
|------|-----------|-----------------|--------------|
| 1729 | 75.00% | 75.00% | — |
| 42 | 75.00% | 75.00% | — |
| 0 | 75.00% | 83.33% | — |
| 1 | 75.00% | 79.17% | — |
| 99 | 50.00% | 54.17% | first_step_wrong |
| 123 | 66.67% | 75.00% | first_step_wrong |
| 456 | 75.00% | 83.33% | — |
| 789 | 25.00% | 33.33% | first_step_wrong |
| 1337 | 66.67% | 66.67% | first_step_wrong |
| 2024 | 66.67% | 66.67% | first_step_wrong |
| 31415 | 66.67% | 79.17% | first_step_wrong |

**Summary (linear scoring, 3 repeats):**
- Mean pass rate: **65.15%**
- Std dev: **14.57%**
- Range: **25.00% – 75.00%**
- Random baseline mean: **5.30%**

**Interpretation:** The learned model consistently beats random (+60pp margin), but variance is high. Worst-case seed (789) drops to 25% — three held-out tasks fail at the first step. All failures are `first_step_wrong`; no second-step temporal transition failures were observed. The bottleneck is **first-step feature→action disambiguation**, not temporal credit assignment.

---

## 2. Non-linear scoring exploration

**Hypothesis:** Linear sum-of-conjunctions scoring lets frequent-but-weak conjunctions overwhelm rare-but-strong signals. Non-linear gating (max / softmax / competitive inhibition) may improve worst-case seeds.

**Method:** Same 11-seed sweep, identical training data, only the `scoring_mode` parameter changes.

| Mode | Mean pass rate | Std dev | Min | Max | Verdict |
|------|---------------|---------|-----|-----|---------|
| linear (default) | 65.15% | 14.57% | 25.00% | 75.00% | baseline |
| max | 36.36% | 8.16% | 25.00% | 50.00% | **worse** |
| softmax | 65.15% | 14.57% | 25.00% | 75.00% | identical to linear |
| competitive | 3.79% | 6.52% | 0.00% | 16.67% | **much worse** |

**Interpretation:**
- **max-based:** Taking the maximum conjunction score instead of the sum destroys cumulative signal. Many weak conjunctions that collectively predict the right action are discarded. Pass rate drops ~29pp.
- **softmax-gated:** Deterministic argmax selection makes softmax equivalent to linear ranking (softmax is monotonic). No change in pass rate. Softmax would matter only under stochastic sampling.
- **competitive-inhibition:** The 0.3 suppression factor is too aggressive. It punishes legitimate supporting conjunctions and collapses performance to near-random.

**Honest conclusion:** The linear average-weight model is NOT the bottleneck. The failures come from insufficient discriminative signal in the observation space for certain seed+distractor combinations, not from the scoring function. Non-linear gating without additional representational capacity (e.g., attention-like weighting) is not the fix.

---

## 3. Scale training repeats 3 → 5 → 7

**Hypothesis:** More training data pushes worst-case seeds above 70%.

**Method:** Parameterize `make_hidden_rule_tasks(repeats=N)` and re-run the 11-seed sweep.

| Repeats | Mean pass rate | Std dev | Min | Max | Train tasks |
|---------|---------------|---------|-----|-----|-------------|
| 3 | 65.15% | 14.57% | 25.00% | 75.00% | 36 |
| 5 | 75.00% | 14.65% | 41.67% | 91.67% | 60 |
| 7 | 80.30% | 10.22% | 66.67% | 100.00% | 84 |

**Interpretation:**
- Monotonic improvement in mean pass rate: 65% → 75% → 80%.
- Worst-case seed improves dramatically: 25% → 42% → 67%.
- At 7 repeats, **every seed clears 66%**; the best seed hits 100%.
- Std dev shrinks from 14.6% to 10.2%, indicating more consistent learning.

**Honest conclusion:** More data is the most reliable lever for improving pass rate. The linear model has enough capacity; it just needs more exposure to the feature/action mappings under diverse distractor combinations.

---

## 4. HebbianBank integration

**What changed:**
- `TemporalTraceBank` gained `apply_rating_to_action(action, rating, midpoint=3.0)` — converts an audit-style [1..5] rating into a reward signal and updates `action_bias`.
- `AuditLog.apply_rating()` gained optional `trace_bank` parameter. When provided and the walk has a `strategy` field (bind/bundle/greedy), the rating propagates to the trace bank's action bias for that strategy.

**Why this matters:** Natural-mode walk ratings now shape TWO substrate components:
1. `HebbianBank` — (prompt, fragment) co-occurrence ranking (existing cycle-14 #08b)
2. `TemporalTraceBank` — strategy selection bias (new v1 integration)

**Verification:** `pytest tests/test_temporal_trace_bank.py tests/test_hidden_rule_actions.py tests/test_audit_log_v1.py` — 22 tests passing, zero regressions.

**Limitation:** The integration is one-directional (audit → bank). There is no closed loop where the bank's improved strategy selection feeds back into walk generation within the same session. That's v2 scope (learned generator).

---

## 5. What v2 needs

1. **Conversational corpus** — the 22k Tier-2 corpus is math/physics/poetry/philosophy, NOT chat. The 10-prompt probe transcripts from the chat-loop bootstrap are the first conversational datapoints.
2. **Non-linear scoring that actually helps** — max/softmax/competitive all failed. A learned attention-like gating mechanism (trained on the audit signal) is the next candidate, not a hand-coded non-linearity.
3. **Closed-loop learning** — the bank updates after audit, but the generator doesn't re-use the updated bank in the same session. v2 needs a warm-start path where the bank is reloaded between turns.

---

## 6. Verdict — learned-vs-hand-coded ratio

**How much of Raphael's chattability and capability now comes from the learned model vs from hand-coded primitives?**

- **Chat-loop generation:** ~5% learned (HebbianBank retrieval ranking influences which fragments surface; HDC cosine does the retrieval) / ~95% template (response stitching from Lemma.render() + natural-mode walk template + persona wrappers). The 10-prompt probe scores 3/6 criteria passing; all 3 passes are on axes where the hand-coded scaffold already existed (register-shift, reasoning-on-demand, persona-stability). The 3 failures (multi-turn coherence, honest uncertainty, clean refusal) are all on axes where the template scaffold is insufficient.
- **Substrate action-selection:** ~75% learned (TemporalTraceBank on hidden-rule tasks achieves 80% mean pass rate at 7 repeats; the feature→action mapping is entirely learned from reward) / ~25% scaffold (encoder, rule-family verifiers, task environment).
- **Math / physics:** ~0% learned / ~100% scaffold (hand-coded primitives with algorithmically-independent cross-checks).
- **Chattability criteria passed:** 3/6.

**Trajectory check:** The ratio is shifting toward learned. v0 had 0% learned chat (no chat loop). v1 introduces the chat loop substrate and proves the TemporalTraceBank can learn action-selection from experience. v2's task is to replace the template generator with a learned one trained on the first conversational datapoints (these probe transcripts + a curated corpus). The honest label on today's chat capability is: **scaffold bootstrap, not learned intelligence.**
