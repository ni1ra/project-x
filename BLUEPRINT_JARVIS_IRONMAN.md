# BLUEPRINT: Make JARVIS Iron Man Would Be Proud Of

**Created:** 2026-01-21
**Status:** ACTIVE
**Author:** FULLAUTO Protocol

---

## EXECUTIVE SUMMARY

This blueprint transforms the current WIRED-BRAIN system into a JARVIS that Tony Stark would approve of:
1. **Reliable** - Consistently solves bugs (>70% on TRIVIAL, >50% on EASY)
2. **Self-improving** - Uses intrinsic motivation to adjust difficulty
3. **Autonomous** - Operates without constant supervision
4. **Efficient** - Training runs at full speed (74x speedup fix applied!)

---

## CURRENT STATE (The Starting Point)

### What's Working
- [x] RPJBrain architecture (2.7M params) - validated on wind tunnel
- [x] K_eff = 5.57 (emergent neuromodulation)
- [x] DoErr = 0.216 (causal reasoning)
- [x] BC accuracy: 72.7% TRIVIAL, 76.8% EASY
- [x] All 321 tests passing
- [x] GPU burn blocking fix (74x speedup) - JUST APPLIED

### What's Broken
- [ ] RL teacher forcing fails (Fixes 5-9 all failed)
- [ ] Train/eval h_t mismatch causes 0% eval success
- [ ] Self-paced training hasn't been validated yet

### The Critical Gap
The brain works. BC works. What's missing is **reliable transfer from training to eval**.

---

## PHASE 1: VALIDATE THE 74x SPEEDUP FIX (30 min)

### 1.1 Environment Checkpoint
```bash
# Verify CUDA available
.venv/bin/python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
# Verify GPU
nvidia-smi --query-gpu=name,memory.free --format=csv
```

### 1.2 Run Quick Training Test
```bash
PYTHONPATH=. .venv/bin/python -u scripts/train_jarvis_harness.py \
    --mode self-paced \
    --num-envs 2 \
    --timesteps 1000 \
    --rollout-steps 4 \
    --initial-difficulty 10 \
    2>&1 | head -100
```

**Expected:** First output within 30 seconds. Each iteration < 2s.

### 1.3 Gate Criteria
- [ ] Training starts within 30 seconds
- [ ] collect_rollout() < 2 seconds (was 16s before fix)
- [ ] No hangs or silent stalls

---

## PHASE 2: SELF-PACED DIFFICULTY TRAINING (2 hours)

### 2.1 Configuration
```bash
PYTHONPATH=. .venv/bin/python -u scripts/train_jarvis_harness.py \
    --mode self-paced \
    --num-envs 4 \
    --timesteps 50000 \
    --rollout-steps 8 \
    --initial-difficulty 10 \
    --k-boredom 5.0 \
    --k-stress 5.0 \
    --hysteresis 0.1 \
    --patience 1 \
    --bc-anchor-coef 0.5 \
    2>&1 | tee training_selfpaced.log
```

### 2.2 Monitoring Signals
Every 1000 steps, check:
- [ ] Entropy > 0.1 (not collapsed)
- [ ] Action distribution: RT+WF+CT each > 10%
- [ ] Boredom/Stress signals oscillating (not stuck)
- [ ] Difficulty adjusting (increases when bored, decreases when stressed)

### 2.3 Success Criteria
- [ ] Completes 50k steps without crash
- [ ] Difficulty reached d >= 20 at some point
- [ ] Final entropy > 0.2
- [ ] Action balance: max action type < 80%

---

## PHASE 3: EVALUATION ON TRIVIAL (30 min)

### 3.1 Run Eval
```bash
PYTHONPATH=. .venv/bin/python -u scripts/eval_jarvis_harness.py \
    --checkpoint [CHECKPOINT_PATH] \
    --num-tasks 50 \
    --max-steps 5 \
    --difficulty trivial \
    2>&1 | tee eval_trivial.log
```

### 3.2 Metrics to Report
| Metric | Target | Measured |
|--------|--------|----------|
| Eligible tasks | > 40/50 | TBD |
| Solved rate | > 0.50 | TBD |
| Improved rate | > 0.70 | TBD |
| Write actions | > 20% | TBD |
| Run tests | 20-60% | TBD |

### 3.3 Gate Criteria
- [ ] Solved rate > 30% (minimum viable)
- [ ] Improved rate > 50%
- [ ] Agent writes code (writes > 10 across all tasks)

---

## PHASE 4: BEHAVIORAL ANALYSIS (1 hour)

### 4.1 Action Distribution Audit
```bash
# Extract action types from eval log
grep "action_type" eval_trivial.log | sort | uniq -c
```

### 4.2 Episode Deep-Dive
For 5 random episodes:
1. What was the initial state?
2. What actions did agent take?
3. Did it run tests?
4. Did it write code?
5. Was the fix correct?

### 4.3 Failure Mode Classification
| Mode | Count | Fix Strategy |
|------|-------|--------------|
| Never writes | TBD | Increase BC anchor |
| Writes wrong thing | TBD | Improve BC demos |
| Spam RUN_TESTS | TBD | RT streak penalty |
| Wrong offset | TBD | Focus jitter training |

---

## PHASE 5: ITERATIVE IMPROVEMENT (Variable)

Based on Phase 4 findings:

### If action collapse:
```python
# Increase entropy coefficient
--entropy-coef 0.02  # was 0.01
```

### If RT spam:
```python
# Add RT streak penalty
--rt-streak-penalty -0.1
--rt-streak-threshold 2
```

### If never writes:
```python
# Stronger BC anchor
--bc-anchor-coef 1.0  # was 0.5
```

### If wrong offset:
```python
# Focus jitter training
--focus-jitter 4  # was 0
```

---

## IRON MAN CRITERIA (The Final Test)

### Level 1: Proof of Concept (Current Goal)
- [ ] 50%+ solved on TRIVIAL
- [ ] 30%+ solved on EASY
- [ ] No catastrophic failures (bricked repos)
- [ ] Self-paced training works autonomously

### Level 2: Useful Operator (Next Sprint)
- [ ] 70%+ on TRIVIAL
- [ ] 50%+ on EASY
- [ ] Handles multi-file navigation
- [ ] Persistent task queue works

### Level 3: Tony Stark Approval (Research Goal)
- [ ] Solves novel bugs not in training
- [ ] Generalizes to real repositories
- [ ] Zero LLM dependencies
- [ ] Discovers new algorithms

---

## FILES TO MODIFY

1. **scripts/train_jarvis_harness.py** - Already fixed GPU burn
2. **scripts/eval_jarvis_harness.py** - May need metric improvements
3. **src/curriculum/controller.py** - Self-paced adjustment
4. **src/curriculum/signals.py** - Boredom/Stress computation

---

## RISK REGISTER

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| h_t mismatch persists | HIGH | CRITICAL | Use pure BC, no forcing |
| Entropy collapse | MEDIUM | HIGH | Higher entropy coef |
| Self-paced oscillates | LOW | MEDIUM | Increase patience |
| GPU OOM | LOW | HIGH | Monitor with nvidia-smi |

---

## DEFINITION OF DONE

JARVIS is "Iron Man Worthy" when:
1. ✅ Training runs autonomously (no manual intervention)
2. ✅ Self-paced adjusts difficulty based on intrinsic signals
3. ⬜ Solves 50%+ of TRIVIAL bugs
4. ⬜ Solves 30%+ of EASY bugs
5. ⬜ Zero LLM dependencies (verified by architecture audit)

---

## APPENDIX: Quick Commands

```bash
# Check GPU status
nvidia-smi

# Quick training test (100 steps)
PYTHONPATH=. .venv/bin/python -u scripts/train_jarvis_harness.py --mode self-paced --timesteps 100 --num-envs 2

# Full self-paced training
PYTHONPATH=. .venv/bin/python -u scripts/train_jarvis_harness.py --mode self-paced --timesteps 50000 --num-envs 4

# Evaluation
PYTHONPATH=. .venv/bin/python -u scripts/eval_jarvis_harness.py --checkpoint [PATH] --num-tasks 50

# Run tests
python -m pytest tests/ -v

# Check action distribution in logs
grep "action_histogram" training.log
```
