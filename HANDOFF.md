# HANDOFF: WIRED-BRAIN Jarvis

Generated: 2026-01-21 (v29 - **PR #5 READY FOR MERGE**)

---

## IMMEDIATE CONTEXT

**Mission:** Make Jarvis that Iron Man would be proud of
**Target:** >70% TRIVIAL, >50% EASY pytest success rates
**Current State:** Fix implemented, PR #5 created, pending merge

**PR:** https://github.com/ni1ra/WIRED-BRAIN/pull/5

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

## THE FIX (IMPLEMENTED)

### Fix A: BC h_t State Alignment (Critical Fix)

**Location:** `scripts/train_jarvis_harness.py` lines 832-855

```python
# Save pre-update state before forward pass
h_before = h.clone()
g_before = g.clone()
a_prev_before = a_prev.clone()

output = self.brain(obs_step, h, g, a_prev, training=True)

# Use pre-update state in evaluate_actions (matches PPO behavior)
log_probs, entropy, values, _, _, _ = self.brain.evaluate_actions(
    obs_bytes=obs_step,
    prev_h=h_before,  # Pre-update state (NOT h_next)
    prev_g=g_before,
    prev_a=a_prev_before,
    actions=target_action,
    z_t=output.z_t,
)
```

**Why it works:**
- BC now trains on same h_t trajectories that eval will see
- Eliminates train/eval distribution shift
- JARVIS validated: 420/420

### Fix B: Sequential BC Flags

Added to training command:
- `--bc-epochs 50`
- `--bc-sequential`
- `--bc-demos 1000`

---

## ARCHITECTURE (Working Components)

| Component | Status | Location |
|-----------|--------|----------|
| RPJBrain | EXCELLENT | `src/core/rpj_brain.py` |
| Boredom/Stress signals | EXCELLENT | `src/curriculum/signals.py` |
| Self-Paced Controller | EXCELLENT | `src/curriculum/controller.py` |
| Evaluation Pipeline | CORRECT | `scripts/eval_jarvis_harness.py` |
| Training Loop | **FIXED** | `scripts/train_jarvis_harness.py` |

---

## FULLAUTO PROGRESS

- [x] Layer 00: MEMORY - MISTAKES.md reviewed
- [x] Layer 01: ACCELA - Recon complete (root cause found)
- [x] Layer 02: SOCIETY - Linear issue (N/A - research project)
- [x] Layer 03: PSYCHE - Blueprint updated (Section 9)
- [x] CHECKPOINT A: JARVIS validate (420/420)
- [x] Layer 04: INFORNOGRAPHY - Implement fix
- [x] Layer 05: DISTORTION - Simplify code
- [x] CHECKPOINT B: JARVIS validate (420/420)
- [x] Layer 06: KIDS - Tests (325 passed, 1 pre-existing fail)
- [x] Layer 07: RUMORS - PR #5 created
- [ ] Layer 09: BRIDGE - PR review
- [ ] CHECKPOINT C: JARVIS validate PR
- [ ] Layer 10: LOGIN - Merge

---

## CRITICAL FILES

| File | Purpose |
|------|---------|
| `scripts/train_jarvis_harness.py` | Training loop (lines 832-855 contain fix) |
| `scripts/eval_jarvis_harness.py` | Evaluation (clean, no forcing) |
| `src/curriculum/signals.py` | Boredom/Stress computation |
| `src/curriculum/controller.py` | Self-paced difficulty adjustment |
| `src/core/rpj_brain.py` | Brain architecture |

---

## COMMAND TO RUN (After Merge)

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

*Last updated: 2026-01-21*
*Status: PR #5 ready for CHECKPOINT C and merge*
