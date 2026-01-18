# HANDOFF: WIRED-BRAIN Jarvis Harness v2

Generated: 2026-01-18 (Updated v11 - **PHASE 7 TRAINING IN PROGRESS**)

## 1. PROJECT CONTEXT

### What Is This?
WIRED-BRAIN is a **transformer-free** neural network (RPJ Brain, 2.7M params) trained via BC+RL to fix Python bugs autonomously. The goal is to achieve persistent autonomous operation (Jarvis-Operator mode).

**STATUS: Phase 7 Training In Progress** (2026-01-18)
- Phase 7 infrastructure: COMPLETE
- All sanity gates: PASSED
- BC+RL training: 200k steps running (PID 1456800)
- TRIVIAL BC Accuracy: 72.7% | Pytest Success: ~25-30%
- EASY BC Accuracy: 76.8% | Pytest Success: 90% (with focus hints)

### What Problem Does It Solve?
Creating an AI bug-fixer that doesn't depend on LLMs (no API keys, no intelligence ceiling). A pure RL agent that learns to edit code through environmental feedback (pytest verifiers).

### Tech Stack
- **Neural Network:** RPJ Brain (2.7M parameters, recurrent + GRU + MLP)
- **Training:** PPO with Behavioral Cloning (BC) pre-training + **Anchored RL**
- **Environment:** JarvisHarnessEnv (multi-file Python repos with injected bugs)
- **Verifier:** pytest (ground-truth test pass/fail)
- **GPU Guard:** Enforces >80% GPU utilization during training

## 2. CURRENT STATUS

### Git State
```
Branch: feat/harness-v2-multifile
Last commit: c666171 docs: update PLAN_TO_JARVIS.md - mark all Gate D gates as COMPLETE
Uncommitted changes: NO - clean state
```

### Phase 7 Infrastructure (COMPLETE)
| Component | Status | Location |
|-----------|--------|----------|
| Persistent mode | DONE | `env.py` - `persistent_mode` config |
| Task queue | DONE | `env.py` - `reset(task_queue=...)` |
| COMPLETE_TASK action | DONE | `actions.py:18`, `env.py:1590` |
| Scratchpad (.jarvis_notes) | DONE | `env.py` - `scratchpad_enabled` |
| GIT_CHECKOUT | DONE | `actions.py:11`, `env.py` |
| GIT_RESET | DONE | `actions.py:10`, `env.py` |
| Sleep module | DONE | `src/core/sleep.py`, `--enable-sleep` flag |

### All Gates PASSED
| Gate | Status | Evidence |
|------|--------|----------|
| Gate D: Eval Truthfulness | PASS | commit 97667ae - free-wins filtered |
| Gate D2: RL Non-Regression | PASS | Anchored RL (30%) >= BC baseline (25%) |
| Gate 3: No bricked repos | PASS | Previous eval showed no crashes |
| All 26 harness tests | PASS | `pytest tests/` passes |

### Training In Progress
```bash
PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --timesteps 200000 --difficulty trivial \
    --persistent --tasks-per-episode 3 --scratchpad \
    --num-envs 16 --action-bytes 64 --force-write-focus \
    --bc-epochs 20 --bc-demos 500 \
    --bc-anchor-coef 0.1 --bc-anchor-decay linear --bc-anchor-decay-steps 100000
```

---

## 3. IMMEDIATE MOVES (Do These In Order)

### Move 1: Wait for Training Completion

Monitor with:
```bash
ps aux | grep train_jarvis | head -1
```

### Move 2: Evaluate Checkpoint

After training completes, run Phase 7.5 evaluation:
```bash
PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
  --checkpoint results/jarvis_harness_v2_200000.pt \
  --mode v2 --difficulty trivial --num-tasks 50 \
  --force-write-focus --max-steps 10
```

### Move 3: Check Phase 7.5 Gates

**Evaluation Gates (Phase 7.5):**
- [ ] Avg tasks completed per session >= 3
- [ ] Recovery success rate >= 80%
- [x] No catastrophic failures (bricked repos) - ALREADY PASSED

### Move 4: Commit + Tag Release

If all gates pass:
```bash
git add -A
git commit -m "feat(jarvis): Persistent autonomous operator mode"
git push
git tag -a v1.0.0-jarvis -m "First Jarvis release: autonomous code-fixing agent"
git push --tags
```

---

## 4. STAGED ROADMAP TO JARVIS

See `PLAN_TO_JARVIS.md` for detailed roadmap.

### Completed Phases
- Phase 0: Validate Current State - DONE
- Phase 0.5: Sanity Gates - DONE (all passed)
- Phase 1: Anchored RL Training - DONE
- Phase 2: Commit and Establish Baseline - DONE
- Phase 2.5: Offset Encoding Fix - DONE
- Phase 3: Stage A - TRIVIAL++ - DONE (72.7%)
- Phase 4: Stage B - EASY - DONE (90% with hints)
- Phase 5: Navigation Infrastructure - DONE

### Current Phase
- **Phase 7: Stage E - Persistent Jarvis** - IN PROGRESS
  - 7.1-7.3 Infrastructure - COMPLETE
  - 7.4 Training - IN PROGRESS
  - 7.5 Evaluation - PENDING

### Future Phases
- Phase 8: Heterogeneous Brain (Research Track)
- Phase 9-12: Desktop, UI, Personal Jarvis

---

## 5. KEY FILES

| File | Purpose | Status |
|------|---------|--------|
| `src/harness/env.py` | Core environment with persistent mode | Updated |
| `src/harness/actions.py` | Action definitions incl. COMPLETE_TASK | Updated |
| `scripts/train_jarvis_harness.py` | Training script with new flags | Updated |
| `scripts/eval_jarvis_harness.py` | Evaluation with truthful metrics | Updated |
| `PLAN_TO_JARVIS.md` | Full implementation roadmap | Current |

---

## 6. ENVIRONMENT

```bash
# GPU: NVIDIA GeForce RTX 5070 Ti, 16303 MiB
# Python: 3.12.3 (.venv/bin/python)
# CWD: /mnt/c/Users/nira/Documents/Research/WIRED/WIRED-BRAIN
```

---

## QUICK START FOR NEW INSTANCE

```
Continue working on WIRED-BRAIN Jarvis Harness. Read HANDOFF.md for full context.

STATUS: Phase 7 Training In Progress (2026-01-18)
- Phase 7 infrastructure: COMPLETE
- All sanity gates: PASSED
- BC+RL training: 200k steps (check if still running with: ps aux | grep train_jarvis)

NEXT STEPS:
1. Check if training completed: ls results/jarvis_harness_v2_200000.pt
2. If complete, run evaluation (see Move 2 in HANDOFF.md)
3. Check Phase 7.5 gates
4. If gates pass, commit and tag release

KEY COMMANDS:
  # Check training status
  ps aux | grep train_jarvis | head -1

  # Eval after training
  PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_200000.pt \
    --mode v2 --difficulty trivial --num-tasks 50 \
    --force-write-focus --max-steps 10

See PLAN_TO_JARVIS.md for detailed roadmap. See MISTAKES.md for failure log.
```

---

## EVAL TRUTHFULNESS (FIXED)

Commit 97667ae fixed eval metrics to filter "free wins" (repos where base=total):

```python
# Truthful metrics now computed:
eligible = (base_tests_passing < base_tests_total)  # Has a bug to fix
solved = success AND eligible  # Actually fixed the bug
improved = (tests_passing > base_tests_passing) AND eligible  # Made progress

# Output shows:
# SOLVED: actually fixed eligible task
# IMPROVED: made progress on eligible task
# ELIGIBLE: task had a bug to fix
# FREE_WIN: base=total (no bug, excluded from metrics)
```

---

## PHASE 7 ARCHITECTURE

### Persistent Mode Flow
1. `reset(task_queue=[t1, t2, t3])` - Initialize with multiple tasks
2. Agent works on first task
3. Agent calls `COMPLETE_TASK` when done
4. Environment validates completion, advances to next task
5. Workspace preserved between tasks
6. `.jarvis_notes` scratchpad persists across all tasks
7. `GIT_RESET`/`GIT_CHECKOUT` available for recovery

### New Flags
- `--persistent`: Enable persistent mode (no reset between tasks)
- `--tasks-per-episode N`: Number of tasks per super-episode
- `--scratchpad`: Enable .jarvis_notes file
- `--enable-sleep`: Enable sleep/consolidation module
