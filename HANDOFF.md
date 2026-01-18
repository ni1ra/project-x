# HANDOFF: WIRED-BRAIN Jarvis Harness v2

Generated: 2026-01-18 (Updated v12 - **BODY BUILT, NEEDS NERVOUS SYSTEM**)

## 1. PROJECT CONTEXT

### What Is This?
WIRED-BRAIN is a **transformer-free** neural network (RPJ Brain, 2.7M params) trained via BC+RL to fix Python bugs autonomously. The goal is to achieve persistent autonomous operation (Jarvis-Operator mode).

**STATUS: Body Built, Nervous System Needed** (2026-01-18)
- Phase 7 infrastructure: COMPLETE (actions/tools/env/reward plumbing)
- All sanity gates: PASSED
- **THE GAP:** Need to train long-horizon loops (run tests → edit → rerun → recover → finish → next task)
- TRIVIAL BC Accuracy: 72.7% | Pytest Success: ~25-30%
- EASY BC Accuracy: 76.8% | Pytest Success: 90% (**with focus hints only**)

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
| COMPLETE_TASK reward | **JUST FIXED** | Was broken: bonus went to episode_return, not step reward |
| Scratchpad (.jarvis_notes) | DONE | `env.py` - `scratchpad_enabled` |
| GIT_CHECKOUT | DONE | `actions.py:11`, `env.py` |
| GIT_RESET | DONE | `actions.py:10`, `env.py` |
| Sleep module | DONE | `src/core/sleep.py`, `--enable-sleep` flag |

### Critical Bug Fixed: COMPLETE_TASK Reward
**Problem:** `_complete_current_task()` added bonus to `episode_return`, but `_compute_reward()` didn't return it. PPO never saw the bonus → agents loiter forever after solving.

**Fix Applied:**
- Added `completion_bonus_pending` field to HarnessState
- `_complete_current_task()` sets pending bonus
- `_compute_reward()` adds it to reward and clears it

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

## 3. IMMEDIATE MOVES (Gated Plan)

### Phase 7.4a: Make Persistent Training Learnable (1-2 days)

**Step 1: COMPLETE_TASK reward** ✅ FIXED
- Bonus now returned as step reward, not hidden in episode_return

**Step 2: Add BC demos that end tasks** ✅ COMPLETE
- Added `create_persistent_bc_dataset()` with 4-step loop:
  - RUN_TESTS (discover) → WRITE_FOCUS (fix) → RUN_TESTS (verify) → COMPLETE_TASK
- Training script updated to use persistent demos with `--persistent` flag

**Gate A (must pass before RL):**
- [ ] In persistent eval with 3 queued tasks, policy emits COMPLETE_TASK within N≤10 steps after tests pass
- [ ] `tasks_completed/session > 0`

**If Gate A fails:** Do NOT touch PPO. Fix BC and reward alignment first.

### Phase 7.4b: Persistent BC-Only Baseline (2-4 days)

**Target behavior per task:**
1. RUN_TESTS early
2. WRITE_FOCUS edit(s)
3. RUN_TESTS again
4. COMPLETE_TASK when solved
5. Repeat for next task without reset

**BC dataset mix needed:**
- RUN_TESTS-first steps (already implemented)
- Fix steps (WRITE_FOCUS etc.)
- RUN_TESTS-confirm steps (new)
- COMPLETE_TASK steps (new)

**Gate B (BC-only persistence):**
- [ ] `tasks_completed/session ≥ 2` on TRIVIAL+EASY mixed queue
- [ ] `run_tests_actions per task ≥ 1`
- [ ] Catastrophic failure rate ≈ 0

### Phase 7.4c: Anchored RL in Persistent Mode (1-2 weeks)

**Non-negotiables:**
- Keep BC anchor loss active (λ_bc not tiny at start)
- Two-timescale optimizer (backbone LR smaller)
- Collapse detector stays armed

**Gate C (must beat BC baseline):**
- [ ] `solved_rate (eligible) >= BC baseline`
- [ ] `tasks_completed/session` increases
- [ ] Action diversity healthy (no 95% same action)

**If it regresses:** Stop RL immediately. Increase BC baseline first.

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

### Phase Sequencing (Correct Order)
**DO NOT chase "general byte edits" or "full navigation" yet.**

1. **Persistence + developer loop** (Phase 7.4) ← YOU ARE HERE
2. General edits via MICRO_VOCAB expansion (Phase 6)
3. Navigation without auto-focus (Phase 5.5)
4. Multi-file "real repos" as default

**Reason:** A Jarvis that can only do tiny edits but reliably loops + recovers + finishes tasks is an operator. A Jarvis that emits any bytes but doesn't know when to run tests or finish tasks is a noisy keyboard ghost.

---

## 5. "IF THINGS GO WRONG" PLAYBOOK

### Symptom: Policy does nothing (writes=0, run_tests=0)
**Causes:** BC dataset missing "first move" states; action entropy collapsed
**Fixes:** Train BC on RUN_TESTS-first; add small negative for NO_OP; verify --no-auto-focus shows meaningful terminal bytes

### Symptom: Tons of WRITE_FOCUS but no file changes
**Causes:** Offset/length out of range; focus text empty/wrong file
**Fixes:** Log focus_file, focus_offset, len(focus_text); clamp offsets; temporarily force auto_focus_target=True

### Symptom: Solves tests but never calls COMPLETE_TASK
**Cause:** No reward for COMPLETE_TASK ← **NOW FIXED**; No BC examples
**Fix:** Patch reward ✅ DONE; Add BC steps with COMPLETE_TASK

### Symptom: RL regresses (BC 30% → RL 10-15%)
**Cause:** Anchor too weak, LR too high, PPO too aggressive
**Fix:** Raise λ_bc; shorten rollouts; reduce LR (especially backbone); hard-stop on non-regression gate fail

### Symptom: Eval painfully slow / GPU bored
**Fix:** Vectorize eval; async tests; cache repo generation

### Symptom: VRAM spikes / instability
**Rule:** Never exceed 10GB total
**Fix:** Reduce num_envs; smaller batches; gradient accumulation; kill python instantly if crossed

---

## 6. KEY FILES

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
Continue WIRED-BRAIN Jarvis Harness. Read HANDOFF.md.

STATUS: Body built, nervous system needed (2026-01-18)
- Phase 7 infrastructure: COMPLETE
- COMPLETE_TASK reward: JUST FIXED (was broken)
- THE GAP: Need long-horizon loops (run tests → edit → rerun → recover → finish → next task)

NEXT 3 MOVES:
1. Add BC demos with COMPLETE_TASK (expert_trajectories.py)
2. Get BC-only persistent baseline (Gate B: tasks_completed/session ≥ 2)
3. Only then: anchored RL (Gate C: must beat BC baseline)

DO NOT: Jump to Phase 6 (byte edits) or Phase 5.5 (navigation) yet.

See PLAN_TO_JARVIS.md for roadmap. See MISTAKES.md for failure log.
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
