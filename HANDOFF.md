# HANDOFF: WIRED-BRAIN Jarvis

Generated: 2026-01-21 (v28 - **FULLAUTO GOD-MODE IN PROGRESS**)

---

## IMMEDIATE CONTEXT

**Mission:** Make Jarvis that Iron Man would be proud of
**Target:** >70% TRIVIAL, >50% EASY pytest success rates
**Current State:** FULLAUTO Layer 01 complete, proceeding to implementation

---

## ROOT CAUSE IDENTIFIED (420/420 Diagnosis)

**Problem:** BC accuracy 72.7% but Pytest success 0-25%

**Root Cause:** Train/Eval h_t trajectory mismatch

```
Training:  a_prev = FORCED (16) → h_t computed on forced action
Evaluation: a_prev = NATURAL   → h_t computed on natural action
```

The brain has NEVER seen eval's hidden state sequences during training.

**Evidence:**
- SR cascades 8.3% → 0.1% even as difficulty decreases to d=1
- 100% RUN_TESTS spam at eval (collapse to safe default)
- writes=0 in ALL episodes

---

## THE FIX (Recon Validated)

### Fix A: Remove Teacher Forcing (95% of solution)

**Location:** `scripts/train_jarvis_harness.py` lines 1187-1210

```python
# DISABLE this block:
if self.upstream_teacher_forcing and random.random() < current_force_prob:
    action_to_store[:, 0] = 16  # FORCED
```

**Why it works:**
- Removes h_t trajectory divergence completely
- BC pre-training (72.7%) still sets good initial policy
- PPO learns on natural trajectories that eval will see

### Fix B: Sequential BC (additional 10-15%)

**Location:** `scripts/train_jarvis_harness.py` line ~495

```python
# Replace:
self.pretrain_behavioral_cloning(...)
# With:
self.pretrain_behavioral_cloning_sequential(...)
```

**Why it helps:**
- Trains recurrent dynamics, not just statics
- Maintains h_t across trajectory instead of zeroing

---

## ARCHITECTURE (Working Components)

| Component | Status | Location |
|-----------|--------|----------|
| RPJBrain | EXCELLENT | `src/core/rpj_brain.py` |
| Boredom/Stress signals | EXCELLENT | `src/curriculum/signals.py` |
| Self-Paced Controller | EXCELLENT | `src/curriculum/controller.py` |
| Evaluation Pipeline | CORRECT | `scripts/eval_jarvis_harness.py` |
| Training Loop | **BROKEN** | `scripts/train_jarvis_harness.py:1187-1282` |

---

## FULLAUTO PROGRESS

- [x] Layer 00: MEMORY - MISTAKES.md reviewed
- [x] Layer 01: ACCELA - Recon complete (root cause found)
- [ ] Layer 02: SOCIETY - Linear issue
- [ ] Layer 03: PSYCHE - Blueprint
- [ ] CHECKPOINT A: JARVIS validate
- [ ] Layer 04: INFORNOGRAPHY - Implement
- [ ] Layer 05: DISTORTION - Simplify
- [ ] CHECKPOINT B: JARVIS validate
- [ ] Layer 06: KIDS - Tests
- [ ] Layer 07: RUMORS - PR
- [ ] Layer 09: BRIDGE - Review
- [ ] CHECKPOINT C: JARVIS validate
- [ ] Layer 10: LOGIN - Merge

---

## CRITICAL FILES

| File | Purpose |
|------|---------|
| `scripts/train_jarvis_harness.py` | Training loop (lines 1131-1450 are critical) |
| `scripts/eval_jarvis_harness.py` | Evaluation (clean, no forcing) |
| `src/curriculum/signals.py` | Boredom/Stress computation |
| `src/curriculum/controller.py` | Self-paced difficulty adjustment |
| `src/core/rpj_brain.py` | Brain architecture |

---

## COMMAND TO RUN (After Fix)

```bash
PYTHONPATH=. .venv/bin/python -u scripts/train_jarvis_harness.py \
    --mode self-paced \
    --num-envs 4 \
    --timesteps 100000 \
    --rollout-steps 8 \
    --initial-difficulty 5 \
    --boredom-coef 5.0 \
    --stress-coef 5.0 \
    --hysteresis-margin 0.1 \
    --min-patience-episodes 2 \
    --bc-anchor-coef 0.5 \
    --entropy-coef 0.01 \
    --bc-epochs 50 \
    --bc-sequential \
    --bc-demos 1000 \
    2>&1 | tee training_fix_ht_mismatch.log
```

---

## SUCCESS CRITERIA

| Metric | Current | Target |
|--------|---------|--------|
| TRIVIAL SR | 0% | >70% |
| EASY SR | 0% | >50% |
| Action diversity | 0% writes | Mixed RT/WF/CT |
| Curriculum progression | Stuck at d=1 | Natural d increase |

---

*Last updated: 2026-01-21 02:30 UTC*
*Status: FULLAUTO GOD-MODE executing fix*
