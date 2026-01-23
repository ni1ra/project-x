# HANDOFF: WIRED-BRAIN (JARVIS)

Generated: 2026-01-23 (Updated)

## 1. MISSION

Build Iron Man's JARVIS - an autonomous AI coding agent that fixes bugs WITHOUT LLM API calls. A ~20W brain that learns to debug through architectural emergence.

**The ASI Constraint**: NO transformer dependencies. The system must think for itself.

## 2. CURRENT STATE

### What Works (Production Model)
```
Model: jarvis_harness_v2_0.pt
Architecture: Homogeneous RPJBrain (512 hidden, 64 blocks)
BC Training accuracy: 86.6% (on EASY with new vocab)
RUN_TESTS at step 0: 100% (FIXED!)
EASY SOLVED rate: 36.7% (after decoder fix - nearly tripled!)
HARD SOLVED rate: 0% (multi-file bugs require NAVIGATE action)
Status: Model solves EASY bugs with correct vocab content
```

### What's Been Fixed This Session

1. **v1 Decoder Missing Vocab Support** - ROOT CAUSE of 0% diff issue
   - Fix: `src/harness/actions.py` - Added vocab lookup from byte 25

2. **vocab_mode (byte 26) Not Trained** - Caused model to use MICRO_VOCAB
   - Fix: `scripts/train_jarvis_harness.py` - Added vocab_mode to BC supervision

3. **Vocab Head Collapse in Sequential BC** - Always output vocab_idx=0
   - Fix: Added direct vocab classification loss + entropy regularization

4. **GPU Burns in PPO Update** - Maintain GPU efficiency during training
   - Fix: Added `_gpu_burn()` call in PPO update minibatch loop

5. **BC Anchor Uses Wrong Difficulty** - Was hardcoded to TRIVIAL
   - Fix: Two locations in train_jarvis_harness.py now use `difficulty` variable

6. **BC Demos Observation Alignment** - Multiple mismatches fixed:
   - focus_text: Now includes buggy code (matches eval env auto_focus_target)
   - terminal_output: Now uses exact eval format "Task: {desc}\nRepo ready.\nInitial tests: (skipped)\n"
   - goal: Now uses eval format "Fix the bugs and make tests pass. Hint: {desc}"
   - tests_total: Changed from 1 to 0 (matches eval when run_tests_on_reset=False)
   - step numbers: All 4 steps now have correct step values (0, 1, 2, 3)
   - Added create_post_run_tests_observation() and create_post_verify_observation()

7. **Focus Shift After RUN_TESTS** - CRITICAL FIX (2026-01-23)
   - Problem: After RUN_TESTS, env changed focus from bug file to test file
   - Root cause: `_maybe_update_focus_from_test_details()` parsed pytest stacktrace
   - BC training kept focus on bug file, causing distribution shift
   - Fix: Added `auto_focus_from_test_details` config flag to HarnessConfig
   - Set `auto_focus_from_test_details=False` in eval/train scripts
   - Result: 100% RUN_TESTS at step 0, 96.5% BC accuracy

8. **COMBINED_VOCAB Missing Numeric Digits** - ROOT CAUSE of EASY 0% (2026-01-23)
   - Problem: EASY bugs like `< 0` -> `< 1` require numeric literal changes
   - Root cause: COMBINED_VOCAB lacked digits 0-9
   - Fix: Added `'0'` through `'9'` to EASY_VOCAB (now 31 total items)
   - Added `compute_correct_action_for_numeric_literal()` function
   - Result: EASY SOLVED rate improved from 0% to 13.8%

9. **Env Using Wrong Decoder for 32-byte Actions** - CRITICAL FIX (2026-01-23)
   - Problem: WRITE_FOCUS wrote garbage bytes (`\x01`) instead of vocab content (`'1'`)
   - Root cause: `env._decode_action_bytes()` used condition `expected == ACTION_BYTES_V2`
   - `ACTION_BYTES_V2 = 64` but model uses 32-byte actions
   - So env used `decode_action` (v1, no vocab) instead of `decode_action_v2`
   - Fix in `src/harness/env.py` line 741-747:
     ```python
     # JARVIS FIX: Always use decode_action_v2 for 32-byte actions too
     if expected >= 32 or actual >= 32:
         action = decode_action_v2(action_bytes)
     ```
   - Result: EASY SOLVED rate improved from 13.8% to 36.7% (nearly tripled!)

### Current Results
```
BC Training on EASY: 86.6% accuracy
RUN_TESTS at step 0: 100% (SOLVED!)
Model produces diverse vocab_idx (0, 1, 10, 22 for digits)
Model follows: RUN_TESTS → WRITE_FOCUS → RUN_TESTS → COMPLETE_TASK
EASY SOLVED rate: 36.7% (after decoder fix!)
HARD SOLVED rate: 0% (multi-file bugs require fixing 2+ files)
```

## 3. REMAINING PROBLEMS

### Problem A: Extra WRITE_FOCUS Actions
The model sometimes makes extra WRITE_FOCUS with vocab_idx=0 (`':\n'`) after the fix, corrupting code:
- Step 2: `WRITE_FOCUS offset=23 content='1'` - CORRECT numeric fix
- Step 3: `WRITE_FOCUS offset=24 content=':\n'` - INCORRECT, corrupts code

This causes many `tests=0/1` (syntax errors) in the eval results.

### Problem B: Multi-File Bugs (HARD difficulty)
HARD difficulty uses `multi_file_combo` bugs requiring fixes in multiple files.
The model only learns single-file fixes from BC training.

## 4. NEXT STEPS (IN ORDER)

1. **Increase BC epochs/demos**: Current 86.6% may need more training to avoid spurious WRITE_FOCUS
2. **Train on TRIVIAL first**: Simpler bugs to get higher accuracy baseline
3. **Curriculum learning**: TRIVIAL → EASY → MEDIUM → HARD progression
4. **PPO fine-tuning**: Use rewards to reinforce correct fix sequences
5. **Multi-file BC demos**: Teach NAVIGATE action for file switching

## 5. KEY FILES

| File | Purpose |
|------|---------|
| `src/harness/actions.py` | v1 decoder with vocab fix, COMBINED_VOCAB with digits (MODIFIED) |
| `src/harness/env.py` | Decoder selection fix for 32-byte actions (MODIFIED) |
| `scripts/train_jarvis_harness.py` | Training with all fixes (MODIFIED) |
| `src/harness/expert_trajectories.py` | BC demo generation with numeric literal support (MODIFIED) |
| `scripts/eval_jarvis_harness.py` | Evaluation script |
| `scripts/diagnose_actions.py` | Diagnostic tool |
| `src/core/goal_encoder.py` | Phase 10 GoalEncoder (ready) |

## 6. COMMANDS

### Train on EASY (with numeric vocab)
```bash
PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 \
    --difficulty easy \
    --timesteps 0 \
    --bc-epochs 30 \
    --bc-demos 300 \
    --bc-sequential \
    --v2-subprocess-heavy
```

### Evaluate Model
```bash
PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_0.pt \
    --difficulty easy --num-tasks 30
```

### Diagnose Model Actions
```bash
PYTHONPATH=. .venv/bin/python scripts/diagnose_actions.py \
    results/jarvis_harness_v2_0.pt
```

## 7. ARCHITECTURE NOTES

### Observation Encoding (512 bytes)
```
[0:256]:   Terminal output (256 bytes)
[256:320]: Goal string (64 bytes)
[320:448]: Focus text (128 bytes)
[448:512]: Metadata (64 bytes)
  [448-449]: energy (2 bytes, float16)
  [450-451]: time (2 bytes, float16)
  [452-453]: actions_remaining (2 bytes, uint16)
  [454-455]: step (2 bytes, uint16)  <-- KEY for action selection
  [456-457]: last_reward (2 bytes, float16)
  [458]:     tests_passing (1 byte)  <-- KEY for action selection
  [459]:     tests_total (1 byte)
  [460-461]: focus_offset (2 bytes)
  [462-463]: focus_length (2 bytes)
  [464-479]: focus_file_hash (16 bytes)
```

### Action Encoding (32-byte format)
- Byte 0: action_type (WRITE_FOCUS=16, RUN_TESTS=3, COMPLETE_TASK=18)
- Byte 1: offset (0-255, position in focus window)
- Byte 3: length (0-3, replacement length)
- Byte 25: vocab_idx (index into COMBINED_VOCAB)
- Byte 26: vocab_mode (0=COMBINED, 1=MICRO)

### COMBINED_VOCAB (31 items)
```python
[':\n', ')', ',', "'", '"',           # TRIVIAL fixes (0-4)
 '<=', '>=', '!=', '==', '<', '>',    # Comparison operators (5-10)
 '+', '-', '*', '/',                   # Arithmetic operators (11-14)
 ' + 1', ' - 1', '+1', '-1', '+ 1', '- 1',  # Off-by-one fixes (15-20)
 '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']  # Numeric digits (21-30)
```

### BC Demo Sequence (4 steps)
```
Step 0: obs (step=0, tests_total=0) → RUN_TESTS
Step 1: obs (step=1, tests_total=11) → WRITE_FOCUS
Step 2: obs (step=2, tests_total=11) → RUN_TESTS (verify)
Step 3: obs (step=3, tests_passing=11) → COMPLETE_TASK
```

## 8. COMMITS THIS SESSION

```
48868fa fix(bc-training): align BC observations with eval env exactly
b5b1722 fix(bc-training): match BC demos to eval env observation structure
8c995f9 fix(bc-training): vocab_mode supervision and entropy regularization
541c70d fix(checkpoints): save config in intermediate checkpoints
```

## 9. SUCCESS CRITERIA

- [ ] HARD solve rate >= 70% (currently 0% - multi-file bugs)
- [x] Model uses correct vocab_idx for each bug type (including digits!)
- [x] Model follows RUN_TESTS → WRITE_FOCUS → RUN_TESTS → COMPLETE sequence (ACHIEVED!)
- [x] BC accuracy >= 80% (achieved 86.6% on EASY, 96.5% on HARD)
- [ ] EASY solve rate >= 50% (currently 36.7%)
- [ ] Production deployment ready

## 10. KEY INSIGHTS

**EASY bugs now fixable!** The model correctly predicts:
- `vocab_idx=22` for digit '1' (numeric literal fix `< 0` -> `< 1`)
- `vocab_idx=10` for '>' (operator fix `>=` -> `>`)

**Remaining issue: Spurious WRITE_FOCUS actions**
- Model sometimes adds extra WRITE_FOCUS with default vocab_idx=0 (`':\n'`)
- This corrupts code and causes syntax errors
- Need more training or different loss weighting to prevent this

**Critical fixes this session**:
1. `auto_focus_from_test_details=False` - Prevents focus shift after RUN_TESTS
2. Added digits 0-9 to COMBINED_VOCAB - Enables numeric literal fixes
3. Added `compute_correct_action_for_numeric_literal()` - Generates correct BC demos
4. **Fixed env decoder selection** - Changed condition from `expected == 64` to `expected >= 32` to use decode_action_v2 for vocab lookup

---

**GOAL: Build Iron Man's JARVIS. Do not stop until complete.**

EASY solve rate at 36.7% after decoder fix! Next: push to 50%+ through better training (more epochs, curriculum learning, or PPO fine-tuning).
