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
Model: jarvis_harness_v2_0.pt
Architecture: Homogeneous RPJBrain (512 hidden, 64 blocks)
BC Training accuracy: 94.0% (sequential BC on EASY)
```

### Latest Results (2026-01-24)
| Difficulty | Solved Rate | Notes |
|------------|-------------|-------|
| EASY | **100%** | Both templates working |
| HARD | 0% | Multi-file bugs need NAVIGATE action |

### Key Metrics
- RUN_TESTS at step 0: 100%
- Action sequence: RUN_TESTS → WRITE_FOCUS → RUN_TESTS → COMPLETE
- BC accuracy: 94.0%
- Templates: 50/50 balanced (data_pipeline/rest_api)

## 3. CRITICAL FIX (2026-01-24)

### BC Training Imbalance → 100% Solve Rate

**Problem**: rest_api template had 0% solve rate while data_pipeline had 100%

**Root Cause**: BC demos were 65:35 imbalanced (data_pipeline:rest_api). Model memorized vocab_idx=10 (`>`) for data_pipeline but defaulted to vocab_idx=0 (`:\n`) for rest_api instead of vocab_idx=22 (`1`).

**Fix**: Added `balance_templates=True` to `generate_task_batch()` in `repo_generator.py`
```python
# Balance templates by cycling through them (prevents BC training imbalance)
template_name = template_names[i % len(template_names)] if balance_templates else None
```

**Result**: 63.3% → 100% EASY solve rate

### Also Fixed
- `_maybe_update_focus_from_test_details()`: Don't switch focus when only test files in traceback
- Test expectations updated for 128-byte focus window and 33-item vocab

## 4. KEY FILES

| File | Purpose |
|------|---------|
| `src/harness/repo_generator.py` | Task generation, `balance_templates` fix |
| `src/harness/actions.py` | Action encoding, COMBINED_VOCAB (33 items) |
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

### COMBINED_VOCAB (33 items)
```
Index 0-4:   [':\n', ')', ',', "'", '"']           # syntax
Index 5-10:  ['<=', '>=', '!=', '==', '<', '>']    # comparison
Index 11-14: ['+', '-', '*', '/']                   # arithmetic
Index 15-20: [' + 1', ' - 1', '+1', '-1', '+ 1', '- 1']  # off-by-one
Index 21-30: ['0'-'9']                              # digits
Index 31-32: ['upper', 'del self._users[user_id]']  # HARD tokens
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

### Phase 8: Structural Plasticity (NEXT)
- Heterogeneous brain regions (different sizes/timescales)
- Optuna search for optimal structure
- Target: HARD >75%, Energy reduction >20%

### HARD Difficulty (0%)
- Requires multi-file bugs (NAVIGATE action)
- Current BC only teaches single-file fixes
- Need multi-step demos with file navigation

## 10. LESSONS LEARNED

1. **BC Training Imbalance**: Random template selection caused 65:35 imbalance. Model memorized majority pattern. Fix: Cycle through templates evenly.

2. **Vocab Prediction**: Model must learn different vocab tokens for different bug patterns. If it defaults to vocab_idx=0, BC training failed.

3. **Test Focus Switching**: After RUN_TESTS, don't switch focus to test file if no source file in traceback.

---

**GOAL: Build Iron Man's JARVIS. Sprint 1 COMPLETE (100% EASY). Phase 8 NEXT.**
