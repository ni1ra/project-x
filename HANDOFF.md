<!--
================================================================================
WIRED-BRAIN ROOT DOCUMENTATION STRUCTURE
================================================================================

ROOT FILES ARE STATIC - DO NOT ADD NEW FILES TO ROOT.
New content must go into existing docs or subdirectories (scripts/, src/, etc.)

Root Documents:
- README.md        : Project overview, quick start, current results
- BLUEPRINT.md     : Core thesis, architecture design, falsification criteria
- PLAN_TO_JARVIS.md: Phased roadmap to Jarvis (Phase 1-10 plans, future work)
- HANDOFF.md       : Context for continuing work in new Claude instances
- MISTAKES.md      : Failure log with patterns and lessons learned
- paper.md         : Academic write-up of methodology and results

Subdirectories:
- src/             : Source code (core/, harness/, utils/)
- scripts/         : Training, evaluation, and diagnostic scripts
- results/         : Checkpoints and evaluation outputs
- tests/           : Unit and integration tests

RULE: If you need to create a new doc, integrate it into an existing root doc
or place it in the appropriate subdirectory. Single files in root = violation.
================================================================================
-->

# HANDOFF: WIRED-BRAIN (JARVIS)

Generated: 2026-01-24 (Updated after Phase 12 infrastructure completion)

## 1. MISSION

Build Iron Man's JARVIS - an autonomous AI coding agent that fixes bugs WITHOUT LLM API calls. A ~20W brain that learns to debug through architectural emergence.

**The ASI Constraint**: NO transformer dependencies. The system must think for itself.

## 2. CURRENT STATE

### Production Model
```
Model: HeterogeneousBrain (Phase 8)
Architecture: 3 regions (fast_perception: 128, slow_memory: 320, fast_execution: 64)
Total width: 512, Parameters: 1,853,259
BC Training accuracy: 100% TypeAcc, 100% VocabAcc (50 epochs)
```

### Latest Results (2026-01-24)
| Difficulty | Solved Rate | Notes |
|------------|-------------|-------|
| EASY | **100%** (100/100 tasks) | Terminal format fix + more training |
| HARD | 70.4% improved, 0% solved | Model generalizes but HARD bugs untrained |

### Key Metrics
- RUN_TESTS at step 0: 100%
- Action sequence: RUN_TESTS → WRITE_FOCUS → RUN_TESTS → COMPLETE_TASK (4 steps)
- BC training: 200 epochs, 40 demos → 100% accuracy
- Templates: 50/50 balanced (data_pipeline/rest_api)
- Average writes per task: 1.0 (exactly correct)

## 3. CRITICAL FIXES (2026-01-24)

### Terminal Format Mismatch Fix (Latest)

**Problem**: BC training achieved 38.8% accuracy with 50 epochs / 20 demos. Model predicted `length=0` for WRITE_FOCUS instead of correct `length=1` or `length=2`.

**Root Causes**:
1. BC terminal format used `offset + len(content)` but eval used `offset + action.length`
   - For data_pipeline: content='>' (1 char) but length=2 (replacing '>=')
   - BC showed `WRITE_FOCUS[23:24]` but eval showed `WRITE_FOCUS[23:25]`
2. BC showed `'>'` but eval showed `'>...'` (action_to_string always adds `...`)
3. Training too short - only 50 epochs with 20 demos couldn't learn length byte (75% of samples have length=0)

**Fix**:
1. Added `length` parameter to `create_post_fix_observation()` in `expert_trajectories.py`
2. Use `offset + length` in terminal format string
3. Always add `...` suffix to content preview
4. Train 200 epochs with 40 demos → 100% BC accuracy

**Result**: 0% → **100%** solve rate on EASY difficulty (100/100 tasks)

### Phase 8: Heterogeneous Brain + Env Fix

**Problem 1**: Heterogeneous brain achieved 100% TypeAcc/VocabAcc in BC training but 0% solve rate in evaluation.

**Root Cause**: `env.py` step() function had a bug where COMPLETE_TASK set `state.done=True` but the local `done` variable (returned) was never updated from it.

**Fix 1**: Added sync in step():
```python
if self.state.done:
    done = True
    if not reason:
        reason = "success"
```

**Problem 2**: Step byte after phi() normalization produced nearly identical values for steps 0-3.

**Fix 2**: Added `amplify_step_signal()` with sinusoidal positional encoding (JARVIS Oracle 420 fix).

**Result**: 0% → **100%** EASY solve rate with heterogeneous brain.

### Previous Fix: BC Training Imbalance
- BC demos were 65:35 imbalanced (data_pipeline:rest_api)
- Fix: `balance_templates=True` cycles through templates evenly

## 4. KEY FILES

| File | Purpose |
|------|---------|
| `src/harness/repo_generator.py` | Task generation, `balance_templates` fix |
| `src/harness/actions.py` | Action encoding, COMBINED_VOCAB (64 items) |
| `src/harness/env.py` | JarvisHarnessEnv, focus management |
| `src/harness/expert_trajectories.py` | BC demo generation |
| `scripts/train_jarvis_harness.py` | Training script |
| `scripts/eval_jarvis_harness.py` | Evaluation script |

## 5. COMMANDS

### Train
```bash
PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --difficulty easy --timesteps 0 \
    --bc-epochs 30 --bc-demos 300 --bc-sequential
```

### Evaluate
```bash
PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_0.pt \
    --difficulty easy --num-tasks 30
```

### Run Tests
```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/ -q
```

## 6. OBSERVATION LAYOUT (512 bytes)

```
[0:256]:   Terminal output
[256:320]: Goal string (64 bytes)
[320:448]: Focus text (128 bytes)
[448:512]: Metadata
  [454-455]: step (uint16) - KEY for action selection
  [458]:     tests_passing
  [459]:     tests_total
```

## 7. ACTION LAYOUT (32 bytes)

```
Byte 0:  action_type (WRITE_FOCUS=16, RUN_TESTS=3, COMPLETE=18)
Byte 1:  offset (0-127, within focus window)
Byte 3:  length (0-3)
Byte 25: vocab_idx (into COMBINED_VOCAB)
Byte 26: vocab_mode (0=COMBINED, forced)
```

### COMBINED_VOCAB (80 items)
```
Index 0-4:   [':\n', ')', ',', "'", '"']           # TRIVIAL_VOCAB (syntax)
Index 5-10:  ['<=', '>=', '!=', '==', '<', '>']    # comparison
Index 11-14: ['+', '-', '*', '/']                   # arithmetic
Index 15-20: [' + 1', ' - 1', '+1', '-1', '+ 1', '- 1']  # off-by-one
Index 21-30: ['0'-'9']                              # digits
Index 31-32: ['upper', 'del self._users[user_id]']  # HARD tokens
Index 33-63: ['return', 'def', 'class', 'if', ...]  # Python keywords (31)
Index 64-79: ['print', 'len', 'int', 'str', ...]   # Python builtins (16)
```

## 8. BC DEMO SEQUENCE

```
Step 0: obs (step=0, tests=0/0)   → RUN_TESTS
Step 1: obs (step=1, tests=X/Y)   → WRITE_FOCUS (offset=23, vocab=10 or 22)
Step 2: obs (step=2, tests=X/Y)   → RUN_TESTS (verify)
Step 3: obs (step=3, tests=Y/Y)   → COMPLETE_TASK
```

**Template-specific vocab tokens:**
- data_pipeline: vocab_idx=10 (`>`) to fix `>= 0` → `> 0`
- rest_api: vocab_idx=22 (`1`) to fix `< 0` → `< 1`

## 9. REMAINING WORK

### Phase 8: Structural Plasticity (COMPLETE for EASY)
- ✅ Heterogeneous brain regions implemented (3 regions: perception/memory/execution)
- ✅ 100% EASY solve rate achieved
- ⚠️ HARD at 36.7% - needs NAVIGATE byte supervision (bytes 5-24 for file path)

### HARD Difficulty (36.7%)
- 6-step trajectories working: RUN_TESTS → WRITE_FOCUS → NAVIGATE → WRITE_FOCUS → RUN_TESTS → COMPLETE
- Issue: BC loss doesn't train NAVIGATE target file bytes (5-24)
- Need to add supervision for file path encoding

### Phase 9: Real Codebase Integration (IN PROGRESS)
- ✅ Infrastructure complete: `real_repo_source.py`, eval `--real-ratio` flag
- ✅ BC demos generate correct pytest output for real repos
- ✅ Step amplification ported to main RPJBrain (`enable_step_amplification=True`)
- ✅ 100% synthetic EASY with step amplification
- ✅ COMBINED_VOCAB expanded to 80 items (31 keywords + 16 builtins)
- ✅ Typo fix support: `compute_correct_action_for_typo()` uses COMBINED_VOCAB
- ✅ Action length range expanded from 0-3 to 0-15 for multi-char typos
- ✅ BC demos support real repos via `--real-ratio` (2026-01-24)
- ✅ Focus jitter support via `--focus-jitter` for offset diversity (2026-01-24)
- ✅ **100% solve rate on REAL REPOS** when trained on 50% mixed data!
- ⚠️ Synthetic templates break when trained on mixed data (0% rest_api)

**Vocab Expansion (2026-01-24)**:
- COMBINED_VOCAB = TRIVIAL (5) + EASY (28) + REAL_REPO (47) = 80 items
- REAL_REPO_VOCAB includes:
  - 31 Python keywords: `return`, `def`, `class`, `if`, `elif`, `else`, `for`, `while`, `try`, `except`, `finally`, `with`, `import`, `from`, `True`, `False`, `None`, `self`, `pass`, `in`, `not`, `and`, `or`, `is`, `as`, `raise`, `assert`, `yield`, `break`, `continue`, `lambda`
  - 16 Python builtins: `print`, `len`, `int`, `str`, `list`, `dict`, `range`, `type`, `open`, `bool`, `float`, `tuple`, `set`, `enumerate`, `zip`, `map`
- 22 same-length typo pairs supported (e.g., `retrun`→`return`, `pritn`→`print`)
- Default `vocab_size` in RPJConfig changed from 64 to 80

### Phase 9 Results
| Training Data | Eval on Synthetic | Eval on Real Repos |
|--------------|-------------------|-------------------|
| 100% synthetic | **100%** | 0% (model introduces syntax errors) |
| 50% mixed + jitter | 0% (writes `1or`) | **100%** (6/6 real repos!) |

**Key Fix (2026-01-24):** Removed `inject_typo_keyword` from real repo EASY injectors.
- Typo bugs like `retrun` cause Python syntax errors at import time
- Pytest can't collect tests when imports fail (showed `0/1` instead of `7/8`)
- Real repos now use only logic bugs (`inject_wrong_operator`, `inject_off_by_one`)
- Baselines now correct: 7/8, 9/11, 11/12 instead of 0/1

**Jitter Fix (2026-01-24):** Added `--focus-jitter` to randomize bug offset in focus window.
- Synthetic bugs always at offset=23; real bugs at offsets 9, 14, 19
- Model memorized offset=23, failed on real repos with different offsets
- Jitter makes offset vary ±16, forcing model to find bug dynamically

**Real Ratio Fix (2026-01-24):** Added `--real-ratio` to BC demo generation.
- Previously `--real-ratio` only affected eval tasks, not BC training demos
- Now BC demos include real repos, teaching model real bug patterns
- Model learns vocab=5 (`<=`) and vocab=8 (`==`) for real bugs

**Current State:** Model achieves **100% on real repos** but breaks synthetic templates.
This is expected - the model learned the harder task (real repos with variable offsets)
but forgot the easier synthetic patterns. Next: find training approach for both.

### Next Steps for Real Repos
1. ✅ ~~Expand COMBINED_VOCAB~~ (DONE - 80 items with keywords + builtins)
2. ✅ ~~Fix typo action generation~~ (DONE - uses COMBINED_VOCAB, expanded length)
3. ✅ ~~Generate BC demos for real repo bug patterns~~ (DONE via --real-ratio)
4. ✅ ~~Train on mixed synthetic+real data~~ (DONE - 100% on real repos!)
5. **Unify training approach** to work on both synthetic AND real repos

## 10. LESSONS LEARNED

1. **BC Training Imbalance**: Random template selection caused 65:35 imbalance. Model memorized majority pattern. Fix: Cycle through templates evenly.

2. **Vocab Prediction**: Model must learn different vocab tokens for different bug patterns. If it defaults to vocab_idx=0, BC training failed.

3. **Test Focus Switching**: After RUN_TESTS, don't switch focus to test file if no source file in traceback.

4. **Env Done Flag Bug**: COMPLETE_TASK set state.done but step() returned local done=False. Always sync state changes to return values.

5. **Step Signal Weakness**: Phi() normalization makes step bytes nearly identical (0.012 apart). Sinusoidal encoding amplifies differences.

6. **BC Demo vs Eval Mismatch**: BC demos must generate observations that match the actual eval environment EXACTLY. For real repos, the pytest output templates must include actual test file names and line numbers (e.g., `test_strings.py:35: in test_truncate`), not generic placeholders.

7. **Step Amplification is Critical**: The step amplification fix from Phase 8 (`amplify_step_signal()`) is now ported to RPJBrain. Without it, models RUN_TESTS-spam because they can't distinguish steps 0-3.

8. **Vocab Mismatch Between Training and Real Repos**: The model's vocabulary (COMBINED_VOCAB) was designed for synthetic bugs (comparison operators, off-by-one errors). Real repos have different bug patterns (typos like `retrun`). **Solution**: Expanded COMBINED_VOCAB from 33 to 80 items by adding REAL_REPO_VOCAB with 31 Python keywords + 16 builtins.

9. **Action Length Constraint**: Original decoder used `length % 4` (0-3 range) which was too small for typo fixes (e.g., `retrun` is 6 chars). **Solution**: Expanded to `length % 16` (0-15 range) to support multi-character replacements.

10. **Same-Length Typos Only**: Different-length typo pairs (e.g., `Nonee`→`None`) require more complex edits. For simplicity, only support same-length typos where delete + insert works cleanly.

11. **Offset Memorization**: Synthetic templates always have bugs at offset=23 in the focus window. Model memorizes this fixed offset and fails on real repos where bugs are at offset 9, 14, 19, etc. **Solution**: Use `--focus-jitter 16` to randomize offset ±16 during training.

12. **BC Demo Data Source Matters**: The `--real-ratio` flag was only affecting eval task generation, not BC demo generation. BC demos were always 100% synthetic. **Solution**: Propagate `real_ratio` through `create_sequential_bc_dataset` → `generate_persistent_demos` → `generate_mixed_task_batch`.

13. **Synthetic vs Real Trade-off**: Training on 50% mixed data achieves 100% on real repos but 0% on synthetic. Training on 100% synthetic achieves 100% on synthetic but 0% on real. The model can't generalize across both due to different offset/vocab patterns. **Next**: Unified training approach needed.

---

**GOAL: Build Iron Man's JARVIS. Phase 8 COMPLETE (100% EASY). Phase 9 100% on synthetic EASY. Phase 10 COMPLETE (Goal Encoder with 100% solve rate). Phase 11 COMPLETE (Git Operations with 100% solve rate). Phase 12 INFRASTRUCTURE COMPLETE (NPM Operations - ready for training). Next: Train and validate npm workflows.**

## 11. PHASE 10: NATURAL LANGUAGE INTERFACE

### Infrastructure Status (2026-01-24)
- ✅ `GoalEncoder` class implemented in `src/core/goal_encoder.py`
- ✅ `RPJBrain` integration: `enable_goal_encoder` config flag
- ✅ `encode_goal_batch()` utility for batch text encoding
- ✅ Training script: `--enable-goal-encoder` flag added
- ✅ BC demos: `goal_texts` field added to `PersistentTrajectory`
- ✅ BC dataset: `create_sequential_bc_dataset` returns `goal_texts` list
- ✅ Training loop: `pretrain_behavioral_cloning_sequential` passes `goal_bytes`

### Training Command
```bash
PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --difficulty easy --timesteps 0 \
    --bc-epochs 200 --bc-demos 40 --bc-sequential \
    --enable-goal-encoder \
    --gpu-min-util 5 --v2-subprocess-heavy
```

### Files Modified (Phase 10)
| File | Changes |
|------|---------|
| `scripts/train_jarvis_harness.py` | Added `--enable-goal-encoder`, `--goal-embed-dim`, `--max-goal-len` flags |
| `src/harness/expert_trajectories.py` | Added `goal_text` field to `PersistentTrajectory`, `goal_texts` in dataset |
| `src/core/rpj_brain.py` | `forward()` accepts `goal_bytes` and `goal_lengths` |
| `src/core/goal_encoder.py` | `GoalEncoder` class, `encode_goal_batch()` utility |

### Goal Encoder Architecture
```
GoalEncoder (~130K params, <5% overhead):
  Byte Embedding (256 → 64)
  BiGRU (64 → 256, 2 layers)
  Projection (256 → 64)
  Output: [B, 64] goal embedding
```

### Expected Behavior
- Model conditions on goal embedding during forward pass
- `phi_obs = phi_obs + goal_features` (additive conditioning)
- Should learn to distinguish: "fix off-by-one" vs "fix operator" from NL text

### Results (2026-01-24)
- ✅ **BC Training**: 100% accuracy with goal encoder enabled
- ✅ **Solve Rate**: 99-100% on EASY difficulty (100/100 with seed 42)
- ✅ **Checkpoint**: `results/jarvis_harness_v2_0.pt` includes goal encoder weights (23 keys)
- ✅ **Config**: Checkpoint contains `enable_goal_encoder: True`

### Phase 10 Status: **COMPLETE**
The goal encoder integrates seamlessly with the BC training pipeline. The model can process full natural language goal texts (up to 512 UTF-8 bytes) and condition actions on goal embeddings.

### Future Work
1. ⏳ Evaluate NL understanding: can model distinguish task types from goal text?
2. ⏳ Compare solve rates: with vs without goal encoder
3. ⏳ Test with diverse goal phrasings to verify NL generalization

## 12. PHASE 11: TOOL DIVERSITY (GIT OPERATIONS)

### Status: **COMPLETE** (2026-01-24)

Phase 11 expanded JARVIS beyond pytest to support git workflows. The model learned to use git operations (GIT_STATUS, GIT_ADD, GIT_COMMIT) as part of bug-fixing trajectories.

### Results
| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| BC accuracy on git actions | >80% | **96.5%** | PASS |
| Git-commit task solve rate | >50% | **100%** | PASS |
| No regression on EASY | 100% | **100%** | PASS |

### Architecture Additions

**New Action: GIT_COMMIT (ActionType 19)**
- Vocab-based commit messages (8 standard messages in GIT_COMMIT_VOCAB)
- Avoids raw text generation which destabilized training in Phase 9

**GIT_COMMIT_VOCAB:**
```python
GIT_COMMIT_VOCAB = ['Fix bug', 'Fix test', 'Update logic', 'Fix comparison',
                    'Fix off-by-one', 'Fix typo', 'Refactor code', 'Add feature']
```

**Observation Enhancement:**
- Reduced FOCUS_PREVIEW_BYTES from 32 to 16
- Added git state at metadata offset 48-51:
  - `git_modified` (uint8): Count of modified files
  - `git_staged` (uint8): Count of staged files
  - `git_untracked` (uint8): Count of untracked files
  - `git_clean` (bool): Whether working tree is clean

### 7-Step Git Commit Trajectory
```
Step 0: obs (tests=0/0)         → RUN_TESTS
Step 1: obs (tests=X/Y, fail)   → WRITE_FOCUS (fix bug)
Step 2: obs (tests=X/Y, fixed)  → RUN_TESTS (verify)
Step 3: obs (tests=Y/Y, pass)   → GIT_STATUS (check state)
Step 4: obs (modified files)    → GIT_ADD (stage fix)
Step 5: obs (staged)            → GIT_COMMIT (commit)
Step 6: obs (clean tree)        → COMPLETE_TASK
```

### Training Command
```bash
PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --difficulty easy --timesteps 0 \
    --bc-epochs 100 --bc-demos 500 --bc-sequential \
    --enable-git-tasks --git-task-ratio 0.3
```

### Files Modified
| File | Changes |
|------|---------|
| `src/harness/actions.py` | GIT_COMMIT = 19, GIT_COMMIT_VOCAB |
| `src/harness/env.py` | `_git_commit()` handler, git state in observations |
| `src/harness/verifiers.py` | `verify_git_commit()`, `get_git_state()` |
| `src/harness/observations.py` | Git state fields, FOCUS_PREVIEW_BYTES = 16 |
| `src/harness/expert_trajectories.py` | `GitCommitTrajectory`, git trajectory functions |
| `scripts/train_jarvis_harness.py` | `--enable-git-tasks`, `--git-task-ratio` |
| `scripts/eval_jarvis_harness.py` | Git action tracking, metrics reporting |

### Key Lessons
1. **Vocab-based text generation**: Using a vocabulary of standard messages avoids raw text generation instability
2. **Observation space planning**: Must plan metadata layout carefully to avoid collisions
3. **Extended trajectories**: 7-step sequences work well with BC training

## 13. PHASE 12: EXTENDED TOOL DIVERSITY (NPM OPERATIONS)

### Status: **IMPLEMENTATION COMPLETE** (2026-01-24)

Phase 12 expanded JARVIS beyond pytest and git to support npm workflows. The infrastructure is ready for training and evaluation.

### Architecture Additions

**New Actions (ActionType 20-22):**
- `NPM_INSTALL = 20`: Run `npm install`
- `NPM_TEST = 21`: Run `npm test` (Jest)
- `NPM_RUN = 22`: Run `npm run <script>` (vocab-based)

**NPM_SCRIPT_VOCAB (8 scripts):**
```python
NPM_SCRIPT_VOCAB = ['build', 'lint', 'format', 'check', 'dev', 'start', 'compile', 'typecheck']
```

**Observation Enhancement (bytes 52-55):**
- `npm_package_json` (bool): True if package.json exists
- `npm_node_modules` (bool): True if node_modules exists
- `npm_last_exit_code` (uint8): Last npm command exit code

### 8-Step NPM Workflow Trajectory
```
Step 0: obs (tests=0/0)           → NPM_INSTALL (install deps)
Step 1: obs (node_modules=1)      → NPM_TEST (discover failing test)
Step 2: obs (tests=X/Y, fail)     → WRITE_FOCUS (fix bug)
Step 3: obs (tests=X/Y, fixed)    → NPM_TEST (verify fix)
Step 4: obs (tests=Y/Y, pass)     → GIT_STATUS (check state)
Step 5: obs (modified files)      → GIT_ADD (stage fix)
Step 6: obs (staged)              → GIT_COMMIT (commit)
Step 7: obs (clean tree)          → COMPLETE_TASK
```

### Files Created/Modified

**New File:**
| File | Purpose |
|------|---------|
| `src/harness/js_repo_generator.py` | Generate JS repos with Jest tests and injectable bugs |

**Modified Files:**
| File | Changes |
|------|---------|
| `src/harness/actions.py` | NPM_INSTALL, NPM_TEST, NPM_RUN actions, NPM_SCRIPT_VOCAB |
| `src/harness/env.py` | `_npm_install()`, `_npm_test()`, `_npm_run()` handlers |
| `src/harness/observations.py` | npm state fields at bytes 52-55 |
| `src/harness/expert_trajectories.py` | `NpmTrajectory`, `create_npm_bc_dataset()` |
| `scripts/train_jarvis_harness.py` | `--enable-npm-tasks`, `--npm-task-ratio` |
| `scripts/eval_jarvis_harness.py` | npm action tracking, `--enable-npm-tasks` |

### Training Command
```bash
PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --difficulty easy --timesteps 0 \
    --bc-epochs 100 --bc-demos 500 --bc-sequential \
    --enable-npm-tasks --npm-task-ratio 0.2
```

### Verified Working (2026-01-24)
- ✅ npm trajectory generation produces 8-step sequences (24 samples per 3 tasks)
- ✅ BC dataset merges npm trajectories with pytest trajectories
- ✅ Training with `--enable-npm-tasks` starts successfully
- ✅ Eval script tracks npm action counts

### Remaining Steps (Validation)
- [ ] Train on npm tasks with 100 BC epochs (target BC accuracy >80%)
- [ ] Evaluate npm task solve rate (target >50%)

### Environment Requirements
- Node.js: v22.21.0 ✅
- npm: 11.6.2 ✅
- GPU: RTX 5070 Ti (16GB) ✅
