# HANDOFF: WIRED-BRAIN Jarvis Harness v2

Generated: 2026-01-19 (v18 - **PHASE 7.5: 50k TRAINING COMPLETE**)

## 1. PROJECT CONTEXT

### What Is This?
WIRED-BRAIN is a **transformer-free** neural network (RPJ Brain, 2.7M params) trained via BC+RL to fix Python bugs autonomously. The goal is to achieve persistent autonomous operation (Jarvis-Operator mode).

**STATUS: Phase 7.5 TRAINING COMPLETE** (2026-01-19)
- **50k STEPS COMPLETED:** Entropy 0.28, Action diversity balanced
- **FINAL DISTRIBUTION:** RT=28.3%, WF=33.9%, CT=36.2% (all > 10%)
- **CHECKPOINT:** `results/jarvis_harness_v2_50000.pt`
- **EVAL RESULT:** 26.7% raw success, 76.7% wrote changes (baseline calc broken)
- **NEXT:** Fix eval baseline calculation, run persistent eval with 3 tasks/session

### What Problem Does It Solve?
Creating an AI bug-fixer that doesn't depend on LLMs (no API keys, no intelligence ceiling). A pure RL agent that learns to edit code through environmental feedback (pytest verifiers).

### Tech Stack
- **Neural Network:** RPJ Brain (2.7M parameters, recurrent + GRU + MLP)
- **Training:** PPO with Behavioral Cloning (BC) pre-training + **Anchored RL**
- **Environment:** JarvisHarnessEnv (multi-file Python repos with injected bugs)
- **Verifier:** pytest (ground-truth test pass/fail)
- **GPU Guard:** Enforces >80% GPU utilization during training

---

## 2. CURRENT STATUS

### Git State
```
Branch: feat/harness-v2-multifile (12 commits ahead of origin)
Last commit: bf11a0d fix(phase7.4g): reduce closer_ratio 0.25->0.05 to prevent entropy collapse

Uncommitted changes (PHASE 7.5 FIXES):
  - HANDOFF.md (this file)
  - PLAN_TO_JARVIS.md (updated roadmap)
  - scripts/train_jarvis_harness.py (+67 lines: action histogram logging)
  - src/harness/expert_trajectories.py (+49 lines: 2-step closer demos)
```

### Environment Checkpoint
```bash
# GPU: NVIDIA GeForce RTX 5070 Ti, 16303 MiB (2254 MiB used)
# Python: 3.12.3 (.venv/bin/python)
# CWD: /mnt/c/Users/nira/Documents/Research/WIRED/WIRED-BRAIN
```

### Key Checkpoints Available
```
results/jarvis_harness_v2_50000.pt  - Phase 7.4d backup (best so far)
results/jarvis_harness_v2_500.pt   - Early checkpoint
results/baseline_trivial_20pct.pt  - Baseline comparison
```

### Phase 7 Infrastructure (COMPLETE)
| Component | Status | Location |
|-----------|--------|----------|
| Persistent mode | DONE | `env.py` - `persistent_mode` config |
| Task queue | DONE | `env.py` - `reset(task_queue=...)` |
| COMPLETE_TASK action | DONE | `actions.py:18`, `env.py:1590` |
| COMPLETE_TASK reward | **FIXED** | Was broken: bonus went to episode_return, not step reward |
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

---

## 3. IMMEDIATE MOVES (What to Do Next)

### The Entropy Problem
**Root Cause Identified:** 1-step closer demos created a "toxic attractor"
- BC over-indexed on "Fresh State (h=0) -> COMPLETE_TASK"
- When RL starts with h=0 but tests failing: massive conflict
- Agent collapses to single action ("safe mode")

### Phase 7.5 Fixes IMPLEMENTED (Uncommitted)

**1. 2-step closer demos** - `src/harness/expert_trajectories.py:1470-1509`
```python
# OLD (toxic): OBS[tests_pass, h=0] -> COMPLETE_TASK
# NEW (safe): RUN_TESTS -> COMPLETE_TASK (h is post-RUN_TESTS, not h=0)
```
Forces COMPLETE_TASK to condition on post-RUN_TESTS hidden state, not fresh h=0.

**2. Action histogram logging** - `scripts/train_jarvis_harness.py:1333-1422`
- Tracks RT/WF/CT/OTHER percentages every 1k steps
- Collapse warning if any action > 85%
- Frequent checkpoints every 2k steps

### NEXT ACTION: Run Phase 7.5 Training
```bash
cd /mnt/c/Users/nira/Documents/Research/WIRED/WIRED-BRAIN

# Run with PYTHONUNBUFFERED for real-time logs
PYTHONUNBUFFERED=1 PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --timesteps 200000 --difficulty trivial \
    --persistent --tasks-per-episode 3 --scratchpad \
    --num-envs 16 --action-bytes 64 --force-write-focus \
    --bc-epochs 20 --bc-demos 500 \
    --bc-anchor-coef 0.1 --bc-anchor-decay linear --bc-anchor-decay-steps 100000 \
    2>&1 | tee /tmp/phase7_5_training.log
```

### Gates to Pass
- [ ] **Entropy > 0.15** at 10k+ RL steps
- [ ] **No single action > 85%** over 1k window
- [ ] **COMPLETE_TASK > 10%** at inference

### If Training Succeeds (entropy > 0.15 at 20k)
1. Commit Phase 7.5 changes
2. Run full 200k training
3. Run eval with `--checkpoint results/jarvis_harness_v2_latest.pt`

### If Entropy Still Collapses
Try these in order:
1. Extend BC warmup to 20k steps (modify `--bc-anchor-decay-steps 120000`)
2. Add -1.0 penalty for premature COMPLETE_TASK
3. Try `--tasks-per-episode 1` to isolate multi-task issues

---

## 4. PHASE HISTORY (What Worked, What Failed)

### Phase 7.4d: Sequential BC - PASS (2026-01-18)
**Solution:** Sequential BC (maintains h_t across steps)
**Results:** Best Accuracy 63.7%, RL Entropy 0.4171 (healthy)
**Gate A:** PARTIAL (RUN_TESTS 67%, WRITE_FOCUS 33%, COMPLETE_TASK 0%)

### Phase 7.4e: Closer Demos (25%) - FAILED (2026-01-18)
**Attempt:** Add 1-step trajectories: OBS[tests_pass] -> COMPLETE_TASK
**Result:** Entropy collapsed 0.23 -> 0.10 at 10k steps

### Phase 7.4f: Relaxed Anchor - FAILED (2026-01-18)
**Attempt:** Reduce anchor 0.5->0.2, increase entropy-coef 0.03->0.05
**Result:** Same entropy collapse 0.24 -> 0.10 at 10k steps

### Phase 7.4g: Reduced Closer Ratio - PARTIAL (2026-01-19)
**Attempt:** Reduce `closer_ratio` from 0.25 to 0.05
**BC Results:** 67.0% accuracy, COMPLETE_TASK 26% (was 0%!)
**RL Results:**
| Step | Entropy | Status |
|------|---------|--------|
| 5,120 | 0.0999 | Below 0.15 |
| 10,240 | 0.1207 | RECOVERING (not collapsing!) |

**Key Insight:** Entropy is recovering, not collapsing like 7.4e/f. The 5% ratio helps but 2-step demos needed.

---

## 5. STAGED ROADMAP TO JARVIS

See `PLAN_TO_JARVIS.md` for full details.

### Completed Phases
- Phase 0-2.5: Foundation (validation, sanity gates, baseline)
- Phase 3: Stage A - TRIVIAL++ (72.7%)
- Phase 4: Stage B - EASY (90% with hints)
- Phase 5: Navigation Infrastructure

### Current Phase
- **Phase 7: Stage E - Persistent Jarvis** - IN PROGRESS
  - 7.1-7.3 Infrastructure - COMPLETE
  - 7.4 Training - IN PROGRESS (entropy recovering)
  - 7.5 Stabilization - READY TO RUN

### Future Phases
- Phase 6: MICRO_VOCAB byte edits (AFTER Phase 7)
- Phase 8: Heterogeneous Brain (Research Track)
- Phase 9-12: Desktop, UI, Personal Jarvis

### Phase Sequencing (IMPORTANT)
**DO NOT chase "general byte edits" or "full navigation" yet.**

Order:
1. Persistence + developer loop (Phase 7.4) <- YOU ARE HERE
2. General edits via MICRO_VOCAB expansion (Phase 6)
3. Navigation without auto-focus (Phase 5.5)
4. Multi-file "real repos" as default

**Reason:** A Jarvis that can only do tiny edits but reliably loops + recovers + finishes tasks is an operator. A Jarvis that emits any bytes but doesn't know when to run tests or finish tasks is a noisy keyboard ghost.

---

## 6. "IF THINGS GO WRONG" PLAYBOOK

### Symptom: Policy does nothing (writes=0, run_tests=0)
**Causes:** BC dataset missing "first move" states; action entropy collapsed
**Fixes:** Train BC on RUN_TESTS-first; add small negative for NO_OP; verify --no-auto-focus shows meaningful terminal bytes

### Symptom: Tons of WRITE_FOCUS but no file changes
**Causes:** Offset/length out of range; focus text empty/wrong file
**Fixes:** Log focus_file, focus_offset, len(focus_text); clamp offsets; temporarily force auto_focus_target=True

### Symptom: Solves tests but never calls COMPLETE_TASK
**Cause:** No reward for COMPLETE_TASK (NOW FIXED); No BC examples
**Fix:** Patch reward - DONE; Add BC steps with COMPLETE_TASK - DONE

### Symptom: RL regresses (BC 30% -> RL 10-15%)
**Cause:** Anchor too weak, LR too high, PPO too aggressive
**Fix:** Raise bc-anchor-coef; shorten rollouts; reduce LR (especially backbone); hard-stop on non-regression gate fail

### Symptom: Entropy collapses (<0.15)
**Cause:** BC created toxic attractor (h=0 + COMPLETE_TASK)
**Fix:** 2-step closer demos (Phase 7.5) - IMPLEMENTED

### Symptom: VRAM spikes / instability
**Rule:** Never exceed 10GB total
**Fix:** Reduce num_envs; smaller batches; gradient accumulation; kill python instantly if crossed

---

## 7. KEY FILES

| File | Purpose | Status |
|------|---------|--------|
| `src/harness/env.py` | Core environment with persistent mode | Stable |
| `src/harness/actions.py` | Action definitions incl. COMPLETE_TASK | Stable |
| `src/harness/expert_trajectories.py` | BC demo generation | **MODIFIED** (2-step closers) |
| `scripts/train_jarvis_harness.py` | Training script | **MODIFIED** (action histogram) |
| `scripts/eval_jarvis_harness.py` | Evaluation with truthful metrics | Stable |
| `PLAN_TO_JARVIS.md` | Full implementation roadmap | Updated |

---

## 8. COMMANDS

### Development
```bash
# Activate environment
cd /mnt/c/Users/nira/Documents/Research/WIRED/WIRED-BRAIN

# Run tests
PYTHONPATH=. .venv/bin/python -m pytest tests/

# Run training (Phase 7.5)
PYTHONUNBUFFERED=1 PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --timesteps 200000 --difficulty trivial \
    --persistent --tasks-per-episode 3 --scratchpad \
    --num-envs 16 --action-bytes 64 --force-write-focus \
    --bc-epochs 20 --bc-demos 500 \
    --bc-anchor-coef 0.1 --bc-anchor-decay linear --bc-anchor-decay-steps 100000

# Run evaluation
PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_50000.pt \
    --mode v2 --difficulty trivial --episodes 50 --persistent
```

### Git
```bash
# Check status
git status

# Commit Phase 7.5 changes (AFTER training succeeds)
git add -A && git commit -m "feat(phase7.5): 2-step closer demos + action histogram logging"
git push origin feat/harness-v2-multifile
```

---

## QUICK START FOR NEW INSTANCE

```
Continue WIRED-BRAIN Jarvis Harness. Read HANDOFF.md.

STATUS: Phase 7.5 STABILIZATION READY (2026-01-19)
- Phase 7.4g: Entropy 0.0999->0.1207 at 10k steps (RECOVERING, not collapsing!)
- 4 files with Phase 7.5 fixes are UNCOMMITTED and ready to test
- Key fix: 2-step closer demos to avoid h=0 toxic attractor

NEXT ACTION: Run Phase 7.5 training
  PYTHONUNBUFFERED=1 PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
      --mode v2 --timesteps 200000 --difficulty trivial \
      --persistent --tasks-per-episode 3 --scratchpad \
      --num-envs 16 --action-bytes 64 --force-write-focus \
      --bc-epochs 20 --bc-demos 500 \
      --bc-anchor-coef 0.1 --bc-anchor-decay linear --bc-anchor-decay-steps 100000 \
      2>&1 | tee /tmp/phase7_5_training.log

GATES: Entropy > 0.15 at 10k+, no action > 85%, COMPLETE_TASK > 10%

DO NOT: Jump to Phase 6 (byte edits) or Phase 5.5 (navigation) yet.

See PLAN_TO_JARVIS.md for full roadmap. See MISTAKES.md for failure log.
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
