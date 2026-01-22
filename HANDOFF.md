# HANDOFF: WIRED-BRAIN (JARVIS)

Generated: 2026-01-22

## 1. MISSION

Build Iron Man's JARVIS - an autonomous AI coding agent that fixes bugs WITHOUT LLM API calls. A ~20W brain that learns to debug through architectural emergence.

**The ASI Constraint**: NO transformer dependencies. The system must think for itself.

## 2. CURRENT STATE

### What Works (Production Model)
```
Model: jarvis_harness_v2_100000.pt
Architecture: Homogeneous RPJBrain (512 hidden, 64 blocks)
HARD IMPROVED rate: 32% (8/25 eligible tasks)
HARD SOLVED rate: 0% (needs RUN_TESTS integration)
Status: Best available - makes fixes but doesn't verify
```

### What's Been Fixed This Session

1. **v1 Decoder Missing Vocab Support** - ROOT CAUSE of 0% diff issue
   - Fix: `src/harness/actions.py` - Added vocab lookup from byte 25

2. **vocab_mode (byte 26) Not Trained** - Caused model to use MICRO_VOCAB
   - Fix: `scripts/train_jarvis_harness.py` - Added vocab_mode to BC supervision

3. **Vocab Head Collapse in Sequential BC** - Always output vocab_idx=0
   - Fix: Added direct vocab classification loss + entropy regularization

### Current Results
```
BC Training on HARD: 71.7% accuracy (up from 0%)
Model produces diverse vocab_idx (0, 1, 10)
Model no longer spams colons everywhere
REMAINING ISSUE: Model doesn't call RUN_TESTS first
```

## 3. REMAINING PROBLEM

**Missing RUN_TESTS First Step**: The model goes straight to WRITE_FOCUS instead of:
1. RUN_TESTS (to get stacktrace and focus)
2. WRITE_FOCUS (apply fix)
3. RUN_TESTS (verify)
4. COMPLETE_TASK

The BC demos have the correct 4-step sequence, but the model isn't learning to start with RUN_TESTS. This may be due to observation differences between BC demos and evaluation.

## 4. NEXT STEPS (IN ORDER)

1. **Debug RUN_TESTS issue** - Why doesn't model start with RUN_TESTS?
2. **Try PPO fine-tuning** - BC alone may not be enough
3. **Evaluate** on HARD difficulty - target >70% solve rate
4. **Continue to Phase 10** - natural language goals with GoalEncoder

## 5. KEY FILES

| File | Purpose |
|------|---------|
| `src/harness/actions.py` | v1 decoder with vocab fix (MODIFIED) |
| `scripts/train_jarvis_harness.py` | Training with vocab_mode and entropy (MODIFIED) |
| `src/harness/expert_trajectories.py` | BC demo generation |
| `scripts/eval_jarvis_harness.py` | Evaluation script |
| `scripts/diagnose_actions.py` | Diagnostic tool |
| `src/core/goal_encoder.py` | Phase 10 GoalEncoder (ready) |

## 6. COMMANDS

### Evaluate Production Model
```bash
PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_100000.pt \
    --difficulty hard --num-tasks 30
```

### Diagnose Model Actions
```bash
PYTHONPATH=. .venv/bin/python scripts/diagnose_actions.py \
    results/jarvis_harness_v2_0.pt
```

### Training (with fixes)
```bash
PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 \
    --difficulty hard \
    --timesteps 0 \
    --bc-epochs 30 \
    --bc-demos 300 \
    --bc-sequential \
    --v2-subprocess-heavy
```

## 7. ARCHITECTURE NOTES

### Action Encoding (32-byte format)
- Byte 0: action_type (WRITE_FOCUS=16, RUN_TESTS=3, COMPLETE_TASK=18)
- Byte 1: offset (0-255, position in focus window)
- Byte 3: length (0-3, replacement length)
- Byte 25: vocab_idx (index into COMBINED_VOCAB)
- Byte 26: vocab_mode (0=COMBINED, 1=MICRO)

### COMBINED_VOCAB (21 items)
```python
[':\n', ')', ',', "'", '"',           # TRIVIAL fixes (0-4)
 '<=', '>=', '!=', '==', '<', '>',    # Comparison operators (5-10)
 '+', '-', '*', '/',                   # Arithmetic operators (11-14)
 ' + 1', ' - 1', '+1', '-1', '+ 1', '- 1']  # Off-by-one fixes (15-20)
```

### BC Demo Sequence (4 steps)
```
Step 0: obs (no focus) → RUN_TESTS (get stacktrace)
Step 1: obs (focused)  → WRITE_FOCUS (apply fix)
Step 2: obs (fixed)    → RUN_TESTS (verify)
Step 3: obs (passing)  → COMPLETE_TASK (done)
```

## 8. FIXES APPLIED THIS SESSION

### scripts/train_jarvis_harness.py
- Added `vocab_mode_log_prob = log_probs[:, 26]` to both sequential and non-sequential BC
- Added direct vocab classification loss with entropy regularization to sequential BC
- Fixed vocab_size clamp from hardcoded 4 to `vocab_size - 1`

### src/harness/actions.py
- Added vocab-based content decoding to v1 decoder (`decode_action()`)
- If bytes 5-24 are zeros and byte 25 has vocab_idx, lookup from COMBINED_VOCAB

## 9. SUCCESS CRITERIA

- [ ] HARD solve rate >= 70% (currently 0%)
- [ ] Model uses correct vocab_idx for each bug type ✓
- [ ] Model follows RUN_TESTS → WRITE_FOCUS → RUN_TESTS → COMPLETE sequence
- [ ] Production deployment ready

## 10. GIT STATE

```
Branch: main
Uncommitted:
  M HANDOFF.md
  M src/harness/actions.py (vocab fix applied)
  M scripts/train_jarvis_harness.py (vocab_mode + entropy fixes)
  ?? scripts/diagnose_actions.py (new diagnostic)
```

---

**GOAL: Build Iron Man's JARVIS. Do not stop until complete.**

The vocab_mode and entropy fixes are done. Now debug why the model doesn't start with RUN_TESTS.
