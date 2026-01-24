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

Generated: 2026-01-24

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
| EASY | **100%** | Heterogeneous brain fully working |
| HARD | 36.7% | NAVIGATE bytes (5-24) not trained |

### Key Metrics
- RUN_TESTS at step 0: 100%
- Action sequence: RUN_TESTS → WRITE_FOCUS → RUN_TESTS → COMPLETE
- BC accuracy: 94.0%
- Templates: 50/50 balanced (data_pipeline/rest_api)

## 3. CRITICAL FIXES (2026-01-24)

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
- ⚠️ Need to generate BC demos for real repo bug patterns
- ⚠️ Need to train on mixed synthetic+real data

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
| 100% synthetic | **100%** | 0% (typo support ready, needs training) |

### Next Steps for Real Repos
1. ✅ ~~Expand COMBINED_VOCAB~~ (DONE - 80 items with keywords + builtins)
2. ✅ ~~Fix typo action generation~~ (DONE - uses COMBINED_VOCAB, expanded length)
3. **Generate BC demos for real repo bug patterns** (typos like `retrun` → `return`)
4. **Train on mixed synthetic+real data** with expanded vocab

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

---

**GOAL: Build Iron Man's JARVIS. Phase 8 COMPLETE (100% EASY). Phase 9 IN PROGRESS (vocab expanded, need BC demos for real repo patterns).**
