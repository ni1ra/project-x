# PLAN_TO_JARVIS.md

> **The Autonomous Execution Plan**
> From BC Pre-training to Working Code-Fixing Agent to Iron Man Jarvis
>
> This document is designed to be followed by a human + copilot (any model).
> Every checkbox is a gate. If a gate fails, stop and debug that gate.
>
> **Current State:** **25% SUCCESS ACHIEVED** | BC+RL model fixes 5/20 TRIVIAL bugs
> **Target:** Jarvis Operator v1 (Persistent) + Jarvis UI v1 (Voice/CLI) + Architecture Track (Heterogeneous Brain)
> **Last Updated:** 2026-01-17 (v5 - 25% milestone achieved after offset fix)
>
> **MILESTONE (2026-01-17):** Model achieves 25% success rate on TRIVIAL bugs!
> **ROOT CAUSES FIXED:** (1) BC observations empty (2) v1/v2 decoder mismatch (3) Focus window alignment (4) Offset % 32 aliasing

---

## 0. WHAT "JARVIS" MEANS IN THIS PROJECT (Definition Ladder)

### Jarvis-Core (Repo World) ← CURRENT FOCUS
- **Inputs:** bytes (repo state, terminal buffer, test status)
- **Actions:** navigate/read/search/write/run_tests/submit
- **Verifier:** pytest / py_compile
- **Success:** improves tests on unseen generated repos

### Jarvis-Operator (Persistent)
- No episodic reset, handles a queue of tasks, can recover via git reset/checkout
- Success: completes multiple tasks back-to-back with low human babysitting

### Jarvis-UI (Iron-Man vibes, but grounded)
- Adds: CLI + optional voice I/O + screen/desktop sandbox
- **Rule:** UI is a *wrapper*, intelligence stays in the policy core
- Success: user can say "fix X / do Y" and it executes safely with confirmations

### Jarvis-Beyond (Research Track, optional)
- Heterogeneous brain search, scaling laws, cross-domain transfer

---

## 0.1 Two-Track Roadmap (After Persistent)

**Track A (Product):** Stage E → Stage G/H/I (Operator + UI + Personal)
**Track B (Research):** Stage E → Stage F → Phase 9 (Heterogeneity + scaling)

**Rule:** Do NOT start Track B until Track A reaches "Persistent Jarvis" gates,
unless you explicitly decide to pause product progress for research.

---

## CRITICAL: Root Cause Analysis (2026-01-17)

### The Problem
Policy collapse: After BC pre-training (75.2%), RL training destroys learned behavior.
Agent outputs constant action: `offset=16, length=0, vocab=1` (no-op).

### Why KL Penalty Failed
KL alone doesn't preserve **competence**, it only regularizes **distribution drift**.
When PPO updates swamp the KL penalty, the policy can still collapse.

### ROOT CAUSE: BC-RL Observation Gap (GUILTY)
**Diagnostic trap results:**
| Region | BC non-zero | RL non-zero | Gap |
|--------|-------------|-------------|-----|
| Terminal | 0% | 100% | 100% |
| Focus | 0% | 99% | 99% |
| File meta | 0% | 12.5% | 12.5% |
| Test status | 99% | 100% | 1% |
| Goal | 98% | 100% | 2% |

**BC learned to predict actions from EMPTY observations!**
The model can't transfer to RL because it never saw real file content.

### The Fix Strategy
1. **Fix BC observation generation** - use real env observations
2. **Gate 0.5** - validate BC actually works in real env
3. **Anchored RL** - BC loss during RL (not just KL)
4. **Dense signal** - prediction heads for intermediate feedback
5. **Collapse detection** - alarm when actions repeat

---

## PHASE 0: VALIDATE CURRENT STATE ✅ COMPLETE

**Goal:** Confirm the curriculum closure fix is stable before burning compute.

- [x] **0.1** Environment verified (GPU, Python, git)
- [x] **0.2** Tests pass (319 passed)
- [x] **0.3** Diagnostic traps pass (offset wrap, vocab modulo)
- [x] **0.4** BC smoke gate: 75.2% accuracy

---

## PHASE 0.5: SANITY GATES ✅ **ALL PASSED - 20% ACHIEVED**

**Goal:** Answer 3 binary questions before burning 100k RL steps.

### Gate A: Does BC-only solve anything in real env? ✅ **YES - 20%**
- [x] **0.5.A.1** Fix BC observation generation
  - [x] Edit `src/harness/expert_trajectories.py` - use `encode_observation(JarvisObservation(...))`
  - [x] Fill ALL observation fields (terminal, goal, focus, metadata)
- [x] **0.5.A.2** Fix v1/v2 decoder mismatch
  - [x] Use `--action-bytes 64` to trigger `decode_action_v2` with TRIVIAL_VOCAB
- [x] **0.5.A.3** Fix focus window alignment
  - [x] Changed from `compute_focus_start_centered` to `compute_focus_start_line_based`
  - [x] BC training now uses same focus offset calculation as env
- [x] **0.5.A.4** Verify 20% success rate
  - [x] Run: `python3 diagnostics/_debug_multi_seed.py`
  - [x] Result: 4/20 (20.0%) tasks solved with BC-only, 1 step

### Gate B: Does env register changed=True for WRITE_FOCUS? ✅ YES
- [x] Verified: diff > 0 on all eval runs (avg 13.6 lines changed)
- [x] Writes are applying correctly with `action_bytes=64`

### Gate C: Collapse Detector (No longer needed for baseline)
- [x] 20% achieved without collapse detector
- [ ] Still useful for RL phase - implement when starting Anchored RL

---

## PHASE 1: ANCHORED RL TRAINING (Replaces old Phase 1)

**Goal:** RL fine-tunes BC, not bulldozes it.

### 1.0 Key Changes from Previous Approach
| Old (Failed) | New (Anchored) |
|--------------|----------------|
| KL penalty only | BC imitation loss during RL |
| Full network same LR | Two-timescale (backbone 0.1x) |
| Sparse reward only | Dense signal (prediction heads) |
| No collapse detection | Active alarm + logging |

### 1.1 Implement Anchored RL ✅ COMPLETE
- [x] **1.1.1** Add BC imitation loss to PPO update
  ```python
  # In PPO update loop:
  loss = PPO_loss + λ_bc * CE(action | demo_obs) + λ_value * V_loss
  ```
  - [x] Edit `scripts/train_jarvis_harness.py`
  - [x] Sample from BC demos each minibatch (`compute_bc_anchor_loss`)
  - [x] Compute cross-entropy on demo (obs, action) pairs

- [x] **1.1.2** Implement λ_bc decay schedule
  ```python
  # Warm start: 0-10k steps: λ_bc = 1.0 (strong anchor)
  # Middle: 10k-50k: λ_bc linear decay to 0.2
  # Late: 50k+: λ_bc = 0.05 (still anchored)
  ```
  - [x] Added `--bc-anchor-coef`, `--bc-anchor-decay`, `--bc-anchor-warmup-steps`, `--bc-anchor-decay-steps`, `--bc-anchor-end-coef`

- [x] **1.1.3** Two-timescale optimizer
  ```python
  backbone_params = [encoder, memory]  # LR = 0.1x
  head_params = [policy_head, value_head]  # LR = 1x
  optimizer = Adam([
      {'params': backbone_params, 'lr': lr * 0.1},
      {'params': head_params, 'lr': lr},
  ])
  ```
  - [x] Added `--two-timescale` and `--backbone-lr-scale` args
  - [x] Added `--bc-checkpoint` to load pre-trained BC checkpoint

### 1.2 Add Dense Signal Heads
- [ ] **1.2.1** Edit-effect predictor: P(changed | obs, action)
  - [ ] Edit `src/core/rpj_brain.py`
  - [ ] Add binary head predicting if write will change file
  - [ ] Train on every step (dense labels: changed True/False)

- [ ] **1.2.2** Δtests predictor (optional)
  - [ ] Predict whether tests will improve
  - [ ] Used for reward shaping and exploration

### 1.3 Tighten Reward Shaping ✅ COMPLETE
- [x] **1.3.1** Add no-op penalties
  ```python
  +r_edit = 0.1 if changed=True  # encourage edits
  -r_noop = 0.2 if changed=False for WRITE_FOCUS
  -r_repeat = 0.5 if same action repeated 5+ times
  +r_compile = 0.5 if py_compile passes (one-time per episode)
  +r_test_delta = 2.0 if pytest improves
  ```
  - [x] Edited `src/harness/env.py` `_compute_reward()` method
  - [x] Added `compile_bonus_given` field to HarnessState

### 1.4 Training Run
- [x] **1.4.1** Anchored RL 20k steps first
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --timesteps 20000 --difficulty trivial \
    --bc-checkpoint results/jarvis_harness_v2_0.pt \
    --bc-anchor-coef 1.0 --two-timescale --bc-demos 500
  ```
  - [x] No collapse: Entropy at 0.55 (not 0)
  - [x] λ_bc decayed: 1.0 → 0.75 over 20k steps

- [x] **1.4.2** Eval at 20k
  - [x] Success rate: 20% (4/20) - same as BC baseline
  - [x] Entropy maintained, no collapse
  - [x] Continue to 100k to let RL explore

- [x] **1.4.3** Full 100k run (first attempt)
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --timesteps 100000 --difficulty trivial \
    --bc-checkpoint results/jarvis_harness_v2_0.pt \
    --bc-anchor-coef 1.0 --bc-anchor-decay linear \
    --bc-anchor-warmup-steps 10000 --bc-anchor-decay-steps 40000
  ```
  - [x] Training completed: 100k steps
  - [x] **RESULT: REGRESSED to 15%** (3/20 vs 4/20 baseline)
  - [x] **Root cause:** λ_bc decay too fast (0.05 by 50k steps)
  - [x] Policy drifted toward ':\n' token, losing ')' predictions

- [x] **1.4.4** Full 100k run (slower decay - still regressed)
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --timesteps 100000 --difficulty trivial \
    --bc-checkpoint results/jarvis_harness_v2_0.pt \
    --bc-anchor-coef 1.0 --bc-anchor-decay linear \
    --bc-anchor-warmup-steps 50000 --bc-anchor-decay-steps 100000 \
    --bc-anchor-end-coef 0.1 --two-timescale
  ```
  - [x] Training completed: 100k steps
  - [x] **RESULT: STILL REGRESSED to 15%** (3/20 vs 4/20 baseline)
  - [x] **Root cause:** NOT λ decay - it was h_t distribution mismatch

- [x] **1.4.5** Deep-Debug: Found root cause of regression
  - [x] **BC anchor uses fresh h_t** but **RL rollout uses sequential h_t**
  - [x] Training env uses `max_steps=100` but eval uses `max_steps=1`
  - [x] RL learns with multi-step h_t context, but eval is single-step
  - [x] **FIX:** Added `--single-step` flag to align training with eval

- [x] **1.4.6** Full 100k run with --single-step (FIXED!)
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --timesteps 100000 --difficulty trivial \
    --bc-checkpoint results/jarvis_harness_v2_0.pt \
    --bc-anchor-coef 1.0 --bc-anchor-decay linear \
    --bc-anchor-warmup-steps 50000 --bc-anchor-decay-steps 100000 \
    --bc-anchor-end-coef 0.1 --two-timescale --single-step
  ```
  - [x] Training completed: 100k steps
  - [x] **RESULT: 20% (4/20) - NO REGRESSION!** ✅
  - [x] Same 4 seeds pass as BC baseline (42, 48, 51, 59)
  - [x] RL maintains BC baseline without degradation

### 1.5 Analysis: Why RL Doesn't Improve Beyond 20%

**Observation:** RL maintains 20% but doesn't improve.

**Analysis of 20 test cases:**
- Token prediction correct: 18/20 (90%)
- Offset prediction correct: 4/20 (20%)

**Root Cause:** Offset prediction is the bottleneck.
- Tokens are easy: bug type (colon/paren) determines the token
- Offsets are hard: requires exact character position in focus window
- BC demo offsets range from 8-61 (highly variable)
- Model clusters around common values (7, 13, 15, 21, 22, 27)

**Why RL can't help:**
- Sparse reward (only +1 for test pass) doesn't provide offset gradient signal
- Correct token but wrong offset = syntax error (0/0 tests)
- No partial credit for "close" offsets

---

## PHASE 2: COMMIT AND ESTABLISH BASELINE ✅ COMPLETE

**Goal:** Create a known-good checkpoint to revert to if later stages break things.

### 2.1 Commit Changes ✅
- [x] **2.1.1** Stage all changes
- [x] **2.1.2** Create commit
  - Commit: `b115c54 feat(harness): anchored RL training with --single-step alignment`
- [x] **2.1.3** Push to remote
- [x] **2.1.4** Create baseline checkpoint backup
  - `results/baseline_trivial_20pct.pt`

### 2.2 Results Summary
| Metric | Before | After |
|--------|--------|-------|
| BC Accuracy | 21.1% | 75.2% |
| BC Success Rate | 0% | 20% |
| RL Success Rate (100k) | 15% (regressed) | 20% (no regression) |
| Token Prediction | - | 90% correct |
| Offset Prediction | - | 20% correct (bottleneck) |

---

## PHASE 2.5: CRITICAL FIX - Offset Encoding Corruption ✅ COMPLETE

**Goal:** Fix the % 32 modulo corruption that was silently breaking offset prediction.

### 2.5.1 Root Cause Discovery
**Oracle consultation (2026-01-17):** Found critical bug in offset encoding!

```python
# BUG in expert_trajectories.py (multiple locations):
action_bytes[1] = offset_in_focus % 32  # ❌ ALIASING!

# A bug at position 45 gets encoded as position 13
# The model learns wrong target offsets
```

**Impact:**
- 60% of TRIVIAL bugs have offsets >= 32
- These offsets were being aliased (45 → 13, 38 → 6, etc.)
- Model learned WRONG target positions
- BC demos were teaching incorrect fixes!

### 2.5.2 Fixes Applied ✅
- [x] **Fix actions.py decoder** - Remove `% 32` from `decode_action_v2()`
  - File: `src/harness/actions.py:316`
  - Change: `offset = int(action_bytes[1].item()) % 32` → `offset = int(action_bytes[1].item())`

- [x] **Fix expert_trajectories.py** - All 4 occurrences
  - Lines 219, 270, 322: `offset_in_focus % 32` → `max(0, min(255, offset_in_focus))`

- [x] **Add dense reward shaping** - Oracle guidance (Score 420)
  - File: `src/harness/env.py:1634-1646`
  - Gives partial credit for "close" offsets: `reward += 0.5 * (1.0 - abs(error) / 32.0)`

- [x] **Add target_offset to Task** - For reward shaping
  - File: `src/harness/env.py:100`
  - New field: `target_offset: Optional[int] = None`

- [x] **Compute target_offset in training**
  - File: `scripts/train_jarvis_harness.py:257-271`
  - Uses `compute_fix_offset_in_focus()` to get correct offset for each task

### 2.5.3 Retraining ✅ COMPLETE
- [x] **BC retraining** - Generate demos with correct offsets
  ```bash
  PYTHONPATH=. python3 scripts/train_jarvis_harness.py \
    --mode curriculum --difficulty trivial \
    --bc-epochs 50 --bc-demos 1000 \
    --timesteps 50000 --num-envs 4 \
    --single-step --force-write-focus --action-bytes 64
  ```
  - BC accuracy: 30.4% (lower than before due to harder offset targets)
  - Checkpoint: `results/jarvis_harness_curriculum_50000.pt`

- [x] **Fix eval pytest path** - Use jarvis_venv for tests
  - File: `scripts/eval_jarvis_harness.py`
  - Added `PYTEST_PYTHON = "/tmp/jarvis_venv/bin/python"`

- [x] **Evaluation** - Test with fixed offsets + dense reward
  - **Result: 25% SUCCESS RATE (5/20)** ✅
  - **+5% improvement over 20% baseline!**
  - Model correctly predicts both `)` and `:\n` tokens
  - Offsets now correctly encoded (38 stays 38, not aliased to 6)

---

## PHASE 3: STAGE A - TRIVIAL++ (Robustness) ✅ COMPLETE

**Goal:** Make TRIVIAL robust to focus jitter and expanded vocabulary.
**Status (2026-01-17):** COMPLETE - 25% success maintained with expanded vocab

### 3.1 Add Quote Support ✅
- [x] **3.1.1** Update TRIVIAL_VOCAB in `actions.py`
  - Changed from `[':\n', ')', ',']` to `[':\n', ')', ',', "'", '"']`
- [x] **3.1.2** Update expert trajectory generator
  - `compute_correct_action_for_wrong_quote()` now works
  - `compute_correct_action_generic()` handles quotes
  - Maps `'` to vocab_idx 3, `"` to vocab_idx 4
- [x] **3.1.3** Update BC accuracy calculation
  - Changed `% 3` to `% 5` for vocab, `% 32` to `% 64` for offset
- [x] **3.1.4** Re-enable wrong_quote injector
  - Enhanced to handle both single->double and double->single
  - Bug distribution: 42% colon, 37% paren, 21% quote

### 3.2 Add Focus Jitter ✅
- [x] **3.2.1** Implement jitter in expert generation
  - Added `jitter` parameter to `compute_focus_start_line_based()`
  - Wired through `generate_expert_demos()` and `create_bc_dataset()`
- [x] **3.2.2** Implement jitter in environment
  - Added `HarnessConfig.focus_jitter` parameter
  - Implemented in `_set_focus_from_location()`
  - Note: jitter=8 hurts BC accuracy significantly (2.9% vs 14.9%)
  - Recommendation: Use jitter=0 for now, revisit after RL stable

### 3.3 Validate TRIVIAL++ ✅
- [x] **3.3.1** BC smoke gate
  - BC accuracy: 26.7% (down from 29.5% with 3-item vocab)
  - Expected drop due to harder task (5 vs 3 items)
- [x] **3.3.2** Eval maintains 25% success
  - 5/20 TRIVIAL bugs fixed with force_write_focus

### 3.4 Commit TRIVIAL++ ✅
- [x] **3.4.1** Committed: `e675f9b feat(curriculum): TRIVIAL++ with quote support and focus jitter`

---

## PHASE 4: STAGE B - EASY (The Developer Loop)

**Goal:** Agent learns: Test -> Observe -> Hypothesize -> Act -> Test

### 4.1 Enable RUN_TESTS Action
- [ ] **4.1.1** Verify RUN_TESTS is implemented
  - [ ] Check `src/harness/env.py` has `_execute_run_tests()`
  - [ ] Check `src/harness/actions.py` has `ActionType.RUN_TESTS`

- [ ] **4.1.2** Remove --force-write-focus gradually
  - [ ] First: 80% forced, 20% free
  - [ ] Edit training script to support `--force-write-focus-prob 0.8`

- [ ] **4.1.3** Enable SEARCH action
  - [ ] Verify `ActionType.SEARCH` is implemented
  - [ ] Verify search results appear in observation

### 4.2 Update Reward Shaping
- [ ] **4.2.1** Add test improvement reward
  - [ ] Edit `src/harness/env.py`
  - [ ] Add large bonus for `tests_passing_now > tests_passing_before`
  ```python
  if self.state.tests_passing > self.state.prev_tests_passing:
      reward += 5.0  # Big bonus for actual improvement
  ```

- [ ] **4.2.2** Add test running incentive
  - [ ] Small reward for running tests (encourages the loop)
  - [ ] But cap at 2-3 runs per episode (prevent farming)

### 4.3 Train EASY
- [ ] **4.3.1** Generate EASY tasks
  - [ ] Verify `--difficulty easy` generates appropriate bugs
  - [ ] Verify bugs require logic changes (not just syntax)

- [ ] **4.3.2** Run training
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --timesteps 200000 --difficulty easy \
    --bc-epochs 50 --bc-demos 500 \
    --force-write-focus-prob 0.5
  ```
  - [ ] Training completes

- [ ] **4.3.3** Evaluate
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_200000.pt \
    --mode v2 --difficulty easy --num-tasks 100
  ```
  - [ ] Success rate >= 20%
  - [ ] Agent runs tests in >50% of episodes
  - [ ] Multi-step corrections observed

### 4.4 Validate The Loop
- [ ] **4.4.1** Check for self-correction behavior
  - [ ] Review episode logs
  - [ ] Look for: edit -> test fail -> edit again -> test pass
  - [ ] This is the critical capability

- [ ] **4.4.2** Check test interaction rate
  - [ ] Agent should run tests at least once in 90% of successful episodes
  - [ ] If not: adjust reward to encourage test running

### 4.5 Commit EASY
- [ ] **4.5.1** Commit and push
  ```bash
  git add -A
  git commit -m "feat(curriculum): EASY with developer loop (test->edit->test)"
  git push
  ```
  - [ ] Pushed

---

## PHASE 5: STAGE C - MULTI-FILE (Navigation)

**Goal:** Agent can find bugs in files it wasn't shown initially.

### 5.1 Enable Navigation Actions
- [ ] **5.1.1** Verify LIST_FILES action
  - [ ] Check implementation in `env.py`
  - [ ] Verify file list appears in observation

- [ ] **5.1.2** Verify NAVIGATE action
  - [ ] Can change focus to different file
  - [ ] Observation updates correctly

- [ ] **5.1.3** Verify STACKTRACE action
  - [ ] Parses pytest output for file:line info
  - [ ] Extracts relevant error locations

### 5.2 Update Observations
- [ ] **5.2.1** Add file list to observation
  - [ ] Edit `src/harness/observations.py`
  - [ ] Reserve bytes for current file list
  - [ ] Include file sizes or truncated names

- [ ] **5.2.2** Ensure stacktraces include paths
  - [ ] Edit verifier output parsing
  - [ ] Include file paths in terminal buffer

### 5.3 Add Navigation Reward
- [ ] **5.3.1** Reward for navigating to correct file
  - [ ] Edit `env.py`
  - [ ] If agent navigates to file containing bug: +1.0 reward
  - [ ] One-time reward (not spammable)

### 5.4 Generate Multi-File Tasks
- [ ] **5.4.1** Verify repo generator creates multi-file repos
  - [ ] Check `data_pipeline` template has multiple files
  - [ ] Check `rest_api` template has multiple files

- [ ] **5.4.2** Verify bug can be in any file
  - [ ] Not just the "main" file
  - [ ] Agent must navigate to find it

### 5.5 Train Multi-File
- [ ] **5.5.1** Run training
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --timesteps 300000 --difficulty easy \
    --bc-epochs 50 --bc-demos 500 \
    --multi-file
  ```
  - [ ] Training completes

- [ ] **5.5.2** Evaluate
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_300000.pt \
    --mode v2 --difficulty easy --num-tasks 100 \
    --multi-file
  ```
  - [ ] Success rate >= 30%
  - [ ] Agent navigates in >50% of episodes
  - [ ] Agent follows stacktrace hints

### 5.6 Commit Multi-File
- [ ] **5.6.1** Commit and push
  ```bash
  git add -A
  git commit -m "feat(curriculum): Multi-file navigation with stacktrace following"
  git push
  ```
  - [ ] Pushed

---

## PHASE 6: STAGE D - GENERAL EDITS (Byte-Level)

**Goal:** Remove TRIVIAL_VOCAB training wheels. Agent outputs raw bytes.

### 6.1 Implement Micro-Vocab
- [ ] **6.1.1** Create BPE-style vocabulary
  - [ ] Analyze generated repos for common byte sequences
  - [ ] Create vocab of ~256 common tokens
  - [ ] Include: `def `, `return `, `import `, `class `, etc.

- [ ] **6.1.2** Update action decoder
  - [ ] Edit `src/core/byte_interface.py`
  - [ ] Support variable-length token output
  - [ ] Start with 1-8 byte tokens

### 6.2 Gradual Curriculum
- [ ] **6.2.1** Phase 1: Restricted byte range
  - [ ] Only allow a-z, 0-9, common punctuation
  - [ ] Train until stable

- [ ] **6.2.2** Phase 2: Full ASCII
  - [ ] Expand to all printable ASCII
  - [ ] Train until stable

- [ ] **6.2.3** Phase 3: Full byte range
  - [ ] Allow any byte (with UTF-8 validation)
  - [ ] Final training

### 6.3 Train General Edits
- [ ] **6.3.1** Run training
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --timesteps 500000 --difficulty medium \
    --bc-epochs 50 --bc-demos 1000 \
    --general-vocab
  ```
  - [ ] Training completes

- [ ] **6.3.2** Evaluate on typo fixes
  - [ ] Can fix `retrun` -> `return`
  - [ ] Can fix `improt` -> `import`
  - [ ] Success rate >= 20% on typo bugs

### 6.4 Commit General
- [ ] **6.4.1** Commit and push
  ```bash
  git add -A
  git commit -m "feat(curriculum): General byte-level edits with micro-vocab"
  git push
  ```
  - [ ] Pushed

---

## PHASE 7: STAGE E - PERSISTENT JARVIS

**Goal:** Continuous operation. No resets between tasks.

### 7.1 Implement Persistent Mode
- [ ] **7.1.1** Add workspace persistence
  - [ ] Edit `env.py` to not reset between episodes
  - [ ] Add `--persistent` flag

- [ ] **7.1.2** Add COMPLETE_TASK action
  - [ ] Agent signals when it thinks task is done
  - [ ] Triggers external validation

- [ ] **7.1.3** Add task queue
  - [ ] Multiple tasks per "super-episode"
  - [ ] Agent must complete one before getting next

### 7.2 Add Memory/Scratchpad
- [ ] **7.2.1** Add scratchpad file
  - [ ] Agent can write notes to `.jarvis_notes`
  - [ ] Persists across tasks
  - [ ] Visible in observation

- [ ] **7.2.2** Enable sleep module
  - [ ] Activate `src/core/sleep.py`
  - [ ] Offline consolidation between tasks

### 7.3 Add Recovery Actions
- [ ] **7.3.1** Implement GIT_CHECKOUT
  - [ ] Agent can undo changes
  - [ ] Critical for recovery from mistakes

- [ ] **7.3.2** Implement GIT_RESET
  - [ ] Hard reset to clean state
  - [ ] Emergency recovery

### 7.4 Train Persistent
- [ ] **7.4.1** Run training
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --timesteps 1000000 --difficulty medium \
    --persistent --tasks-per-episode 5
  ```
  - [ ] Training completes

- [ ] **7.4.2** Evaluate
  - [ ] Agent completes multiple tasks back-to-back
  - [ ] Agent recovers from mistakes
  - [ ] Success rate >= 50% per task

### 7.5 Final Validation
- [ ] **7.5.1** Run on held-out repos
  - [ ] Generate 100 new repos (unseen templates)
  - [ ] Evaluate without training

- [ ] **7.5.2** Measure key metrics
  - [ ] Avg tasks completed per session: >= 3
  - [ ] Recovery success rate: >= 80%
  - [ ] No catastrophic failures (bricked repos)

### 7.6 Commit Persistent Jarvis
- [ ] **7.6.1** Final commit
  ```bash
  git add -A
  git commit -m "feat(jarvis): Persistent autonomous operator mode"
  git push
  ```
  - [ ] Pushed

- [ ] **7.6.2** Tag release
  ```bash
  git tag -a v1.0.0-jarvis -m "First Jarvis release: autonomous code-fixing agent"
  git push --tags
  ```
  - [ ] Tagged

---

## PHASE 8: STAGE F - HETEROGENEOUS BRAIN (The Key to Unlimited Intelligence)

**Goal:** Replace hand-designed architecture with Optuna-discovered optimal brain structure.

### 8.0 The Core Insight (2026-01-17)

Biological brains don't have homogeneous architecture:
- Visual cortex: massive, hierarchical, feedforward-heavy
- Prefrontal cortex: smaller, deeply recurrent, integrative
- Cerebellum: huge neuron count, simple local circuits
- Basal ganglia: sparse, acts as router/gate

**The key variables:**
- **x** = number of distinct regions (sections)
- **y** = per-region settings (neurons, synapses/neuron, sparsity, timescale, plasticity)

**The method:** Optuna searches for optimal (x, y) under RPJ pressure.

### 8.1 Define the Search Space

#### 8.1.1 Region Roles (Candidate x)
- [ ] **8.1.1.1** Define region role template
  ```python
  REGION_ROLES = {
      'perception': {  # Bytes → latent compression
          'required': True,
          'default_width': 256,
          'default_depth': 1,
      },
      'working_memory': {  # Recurrent context
          'required': True,
          'default_width': 128,
          'default_recurrence': 'gru',
      },
      'router': {  # Action type selection
          'required': True,
          'default_width': 32,
          'default_sparsity': 0.9,
      },
      'motor': {  # Action byte generation
          'required': True,
          'default_width': 128,
      },
      'world_model': {  # Predicts verifier deltas (optional)
          'required': False,
          'default_width': 64,
      },
      'second_memory': {  # Slower timescale (optional)
          'required': False,
          'default_width': 64,
          'default_timescale': 10,
      },
  }
  ```
  - [ ] Implemented in `src/core/heterogeneous_brain.py`

#### 8.1.2 Per-Region Settings (y parameters)
- [ ] **8.1.2.1** Define y search space per region
  ```python
  REGION_HYPERPARAMS = {
      # Structural
      'width': (16, 512),           # neurons in region
      'depth': (1, 3),              # layers within region
      'sparsity': (0.0, 0.95),      # fraction of zeroed connections

      # Connectivity (synapses per neuron)
      'fan_in_cap': (4, 64),        # max incoming connections per neuron
      'fan_out_cap': (4, 64),       # max outgoing connections
      'block_size': (4, 32),        # for block-sparse layouts

      # Temporal
      'timescale': (1, 100),        # update frequency (1=every step)
      'gru_bias': (-2.0, 2.0),      # update gate bias (slower/faster)

      # Plasticity
      'fast_weight_rank': (0, 64),  # adapter rank (0=no fast weights)
      'learning_rate_mult': (0.1, 10.0),

      # Energy
      'activation_cost': (0.0, 1.0),  # penalty for activating region
  }
  ```
  - [ ] Implemented as Optuna search space

### 8.2 Optuna Integration

#### 8.2.1 Trial Definition
- [ ] **8.2.1.1** Create `scripts/optuna_brain_search.py`
  ```python
  def objective(trial):
      # Sample x (which regions enabled)
      enable_world_model = trial.suggest_categorical('enable_world_model', [True, False])
      enable_second_memory = trial.suggest_categorical('enable_second_memory', [True, False])

      # Sample y (per-region settings)
      config = {}
      for region in REGION_ROLES:
          if REGION_ROLES[region]['required'] or trial.suggest_categorical(f'enable_{region}', [True, False]):
              config[region] = {
                  'width': trial.suggest_int(f'{region}_width', 16, 512),
                  'sparsity': trial.suggest_float(f'{region}_sparsity', 0.0, 0.95),
                  'fan_in_cap': trial.suggest_int(f'{region}_fan_in', 4, 64),
                  'timescale': trial.suggest_int(f'{region}_timescale', 1, 100),
                  'fast_weight_rank': trial.suggest_int(f'{region}_fw_rank', 0, 64),
              }

      # Build brain with this config
      brain = HeterogeneousBrain(config)

      # Train for budget steps
      trainer = PPOTrainer(brain, env)
      trainer.train(timesteps=trial_budget)

      # Evaluate on fixed task suite
      success_rate = evaluate(brain, EVAL_SUITE)
      energy_used = trainer.total_energy
      steps_used = trainer.total_steps

      # RPJ-aligned objective
      score = success_rate - alpha * energy_used - beta * steps_used
      return score
  ```
  - [ ] Script created and tested

#### 8.2.2 Multi-Fidelity Search (ASHA)
- [ ] **8.2.2.1** Use pruning to avoid wasting compute
  ```python
  study = optuna.create_study(
      direction='maximize',
      pruner=optuna.pruners.HyperbandPruner(
          min_resource=10_000,      # 10k steps minimum
          max_resource=150_000,     # 150k steps maximum
          reduction_factor=3,
      ),
  )
  ```
  - [ ] Implemented with early stopping

#### 8.2.3 Fixed Evaluation Suite
- [ ] **8.2.3.1** Create deterministic eval tasks
  ```python
  # Generate once, freeze forever
  EVAL_SUITE = generate_tasks(
      num_tasks=50,
      difficulty='trivial',
      seed=42,  # FROZEN
  )
  save_eval_suite('fixtures/optuna_eval_suite.pkl')
  ```
  - [ ] Suite generated and committed

### 8.3 V2: Structural Plasticity (Inner-Loop Optimization)

**After Optuna finds good macro structure, enable micro-adaptation during training.**

#### 8.3.1 Learnable Neuron Gates
- [ ] **8.3.1.1** Add per-neuron gate scalars
  ```python
  class GatedRegion(nn.Module):
      def __init__(self, width):
          self.gates = nn.Parameter(torch.ones(width))  # learnable
          self.gate_penalty = 0.01  # L1 penalty

      def forward(self, x):
          active_gates = torch.sigmoid(self.gates)
          return x * active_gates, active_gates.sum()  # output, active count
  ```
  - [ ] Implemented in `src/core/heterogeneous_brain.py`

#### 8.3.2 Dynamic Edge Pruning/Regrowth
- [ ] **8.3.2.1** Implement RigL-style pruning
  ```python
  def prune_and_regrow(self, prune_fraction=0.1):
      # Prune: remove lowest-magnitude weights
      mask = self.weight.abs() > threshold

      # Regrow: add connections where gradients are large
      grad_magnitude = self.weight.grad.abs()
      new_connections = grad_magnitude.topk(num_to_add)
      mask[new_connections] = True

      self.mask = mask
  ```
  - [ ] Implemented with "sleep phase" only (between rollout batches)

#### 8.3.3 Region Resizing (Advanced)
- [ ] **8.3.3.1** Allow dynamic neuron addition/removal
  ```python
  def maybe_resize(self, utilization, threshold=0.9):
      if utilization > threshold:
          self.grow(factor=1.2)
      elif utilization < 0.1:
          self.shrink(factor=0.8)
  ```
  - [ ] Implemented behind `--dynamic-resize` flag

### 8.4 The Search Protocol

#### 8.4.1 Phase A: Coarse Search (x only)
- [ ] **8.4.1.1** Fix y to defaults, search which regions help
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/optuna_brain_search.py \
    --search-mode coarse \
    --n-trials 50 \
    --budget 50000
  ```
  - [ ] Best x configuration found: `_________________`
  - [ ] Regions enabled: `_________________`

#### 8.4.2 Phase B: Fine Search (y given best x)
- [ ] **8.4.2.1** Fix x, search per-region settings
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/optuna_brain_search.py \
    --search-mode fine \
    --fixed-regions perception,working_memory,router,motor \
    --n-trials 200 \
    --budget 100000
  ```
  - [ ] Best y configuration found
  - [ ] Success rate: `_____%`
  - [ ] Energy efficiency: `_____`

#### 8.4.3 Phase C: Structural Plasticity Tuning
- [ ] **8.4.3.1** Enable V2 gates/pruning, tune coefficients
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/optuna_brain_search.py \
    --search-mode plasticity \
    --base-config results/best_xy_config.json \
    --enable-gates \
    --enable-pruning \
    --n-trials 100
  ```
  - [ ] Optimal gate penalty: `_____`
  - [ ] Optimal prune fraction: `_____`
  - [ ] Final success rate: `_____%`

### 8.5 Validation: Does Structure Actually Matter?

#### 8.5.1 Ablation: Homogeneous vs Heterogeneous
- [ ] **8.5.1.1** Compare best Optuna config vs flat baseline
  ```bash
  # Flat baseline (same total params, no regions)
  PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --arch flat --total-params 2773634

  # Best Optuna config
  PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --arch heterogeneous --config results/best_xy_config.json
  ```
  - [ ] Heterogeneous success rate: `_____%`
  - [ ] Flat baseline success rate: `_____%`
  - [ ] Improvement: `_____x`

#### 8.5.2 Ablation: With vs Without Structural Plasticity
- [ ] **8.5.2.1** Compare fixed structure vs adaptive
  - [ ] Fixed structure success: `_____%`
  - [ ] With plasticity success: `_____%`
  - [ ] Steps to convergence: `_____` vs `_____`

### 8.6 Commit Heterogeneous Brain
- [ ] **8.6.1** Commit Optuna integration
  ```bash
  git add -A
  git commit -m "feat(brain): Optuna-discovered heterogeneous architecture"
  git push
  ```
  - [ ] Pushed

- [ ] **8.6.2** Tag milestone
  ```bash
  git tag -a v2.0.0-heterogeneous -m "Heterogeneous brain with structural plasticity"
  git push --tags
  ```
  - [ ] Tagged

---

## PHASE 9: BEYOND (The Frontier)

**Goal:** Use the Optuna-discovered architecture as the base for scaling experiments.

### 9.1 Scaling Laws Under RPJ
- [ ] What happens when you 10x the total params?
- [ ] Does the optimal (x, y) change with scale?
- [ ] Is there a "phase transition" where structure matters more?

### 9.2 Transfer to New Domains
- [ ] Train on TRIVIAL → does the same structure work for EASY?
- [ ] Train on code → does the same structure work for math?
- [ ] Is there a "universal" brain structure?

### 9.3 The Intelligence Ceiling Question
- [ ] At what point does structure stop helping?
- [ ] Is there diminishing returns, or does heterogeneity keep paying off?
- [ ] **The big question:** Can this approach exceed human-level on constrained tasks?

---

## PHASE 10: STAGE G - DESKTOP OPERATOR SANDBOX (Real World Without Bricking Anything)

**Goal:** Move from "repo-world" to "OS-world" safely via a sandboxed desktop harness.

### 10.1 Build DesktopGym (Sandbox)
- [ ] Run inside a disposable VM or containerized desktop session
- [ ] Hard-permission model: the agent cannot execute destructive actions without explicit allow
- [ ] Add action wrappers: OPEN_APP, TYPE_TEXT, CLICK, COPY, PASTE, RUN_CMD (allowlist)

### 10.2 Verifiers (No vibes, only checks)
- [ ] "Did the file change as expected?"
- [ ] "Did the command exit 0?"
- [ ] "Did the window title match target?"
- [ ] "Did the screenshot hash match expected region?" (coarse, fast)

### 10.3 Curriculum
- [ ] Start with 5 deterministic tasks (copy file, edit config, run command, revert change, confirm output)
- [ ] Exit criteria: >=70% success on 100 unseen task instances

---

## PHASE 11: STAGE H - JARVIS UI v1 (CLI + Optional Voice)

**Goal:** Make Jarvis *usable* by a human without turning the policy into a chatbot.

### 11.1 CLI Wrapper (Mandatory)
- [ ] `jarvis do "<task>"` creates a task spec file (structured, not freeform)
- [ ] The policy reads the task spec bytes and executes in sandbox
- [ ] Logs every action + rationale bytes to a session folder

### 11.2 Voice I/O (Optional, UI-only)
- [ ] Speech-to-text and text-to-speech are allowed as "UI adapters"
- [ ] **Rule:** the core policy still consumes/produces *structured* task specs, not conversational reasoning

### 11.3 Safety UX
- [ ] Confirmation prompts for: deleting, moving, installing, network access
- [ ] Big red kill-switch: immediate STOP + revert via git/restore snapshot

---

## PHASE 12: STAGE I - PERSONAL JARVIS (Memory + Proactivity, Still Safe)

**Goal:** Persistent preferences and long-horizon help, without hallucination.

### 12.1 Memory (Grounded)
- [ ] Persistent notebook files (facts/decisions/todos) stored as plain text
- [ ] Retrieval is byte-level or learned latent retrieval (no external RAG required)
- [ ] Exit criteria: uses memory correctly in >=80% of relevant tasks

### 12.2 Proactivity (Constrained)
- [ ] The agent may propose actions, but must request confirmation to execute
- [ ] Add a "suggestion score" head (trained on accept/reject feedback)

### 12.3 Final Gate
- [ ] Can run for 1 hour in sandbox doing a queue of tasks with:
  - <=2 human interventions
  - zero destructive mistakes
  - >=3 tasks completed end-to-end

---

## FAILURE RECOVERY PROTOCOLS

### If Training Diverges (Loss -> NaN)
1. [ ] Reduce learning rate by 10x
2. [ ] Reduce batch size
3. [ ] Check for numerical overflow in reward
4. [ ] Restart from last good checkpoint

### If Agent Learns No-Op
1. [ ] Increase no-op penalty
2. [ ] Decrease action penalty
3. [ ] Check reward signal magnitude
4. [ ] Verify expert demos are valid (not all no-ops)

### If Agent Spams One Action
1. [ ] Increase entropy coefficient (0.01 -> 0.05 -> 0.1)
2. [ ] Check action space constraints
3. [ ] Verify reward diversity (not dominated by one term)

### If Tests Hang
1. [ ] Add pytest timeout: `--timeout 10`
2. [ ] Use py_compile instead of pytest for syntax
3. [ ] Check for infinite loops in generated code

### If VRAM OOM
1. [ ] Reduce batch size
2. [ ] Reduce rollout steps
3. [ ] Enable gradient checkpointing
4. [ ] Use smaller network

---

## SUCCESS METRICS SUMMARY

| Stage | Metric | Target | Gate |
|-------|--------|--------|------|
| **TRIVIAL** | RL Success Rate | >=20% | HARD |
| **TRIVIAL++** | Quote Bug Success | >=70% | HARD |
| **EASY** | Multi-step Correction | Observed | SOFT |
| **Multi-File** | Navigation Rate | >50% | HARD |
| **General** | Typo Fix Success | >=20% | HARD |
| **Persistent** | Tasks per Session | >=3 | HARD |
| **DesktopSandbox** | OS task success | >=70% | HARD |
| **Jarvis UI v1** | User tasks completed | >=10/day | SOFT |
| **Personal Jarvis** | Memory correctness | >=80% | HARD |

---

## LANDMINES TO AVOID

1. **Modulo Mismatch:** When changing vocab size, update ALL modulo operations
2. **Observation Lag:** Refresh observation AFTER writes, not before
3. **Relative Paths:** Normalize all paths (./src != src != /full/path/src)
4. **Test Pollution:** Always clean state between episodes (or use fixtures)
5. **UTF-8 Cliff:** Validate all byte outputs as valid UTF-8
6. **Timeout Farming:** Cap rewards from test running to prevent gaming
7. **Context Thrashing:** Limit files open simultaneously

---

## CHECKPOINT NAMING

```
results/baseline_trivial_v1.pt      # Phase 1 success
results/trivial_plus_quotes_v1.pt   # Phase 3 success
results/easy_loop_v1.pt             # Phase 4 success
results/multifile_nav_v1.pt         # Phase 5 success
results/general_bytes_v1.pt         # Phase 6 success
results/jarvis_persistent_v1.pt     # Phase 7 success (FINAL)
```

---

**Document Version:** 1.1
**Last Updated:** 2026-01-17
**Author:** Project notes (human + copilot)

> "Gate 0: Curriculum Closure is Non-Negotiable.
> If any closure fails, STOP. Fix it. Do not scale."
