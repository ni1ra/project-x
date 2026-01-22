# HANDOFF: WIRED-BRAIN (JARVIS)

Generated: 2026-01-22

## 1. MISSION

Build Iron Man's JARVIS - an autonomous AI coding agent that fixes bugs WITHOUT LLM API calls. A ~20W brain that learns to debug through architectural emergence.

**The ASI Constraint**: NO transformer dependencies. The system must think for itself.

## 2. CURRENT STATE

### What Works (Production Model)
```
Model: jarvis_harness_v2_0.pt
Architecture: Homogeneous RPJBrain (512 hidden, 64 blocks)
BC Training accuracy: 87.7% (on HARD)
HARD IMPROVED rate: 31.8% (7/22 eligible tasks)
HARD SOLVED rate: 0% (needs RUN_TESTS integration)
Status: Model improves tests but doesn't call RUN_TESTS manually
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

### Current Results
```
BC Training on HARD: 87.7% accuracy (up from 0%)
Model produces diverse vocab_idx (0, 1, 10)
Model improves tests: 7/11 → 9/11 or 10/11 on some tasks
REMAINING ISSUE: Model doesn't call RUN_TESTS manually (run_tests=0)
```

## 3. REMAINING PROBLEM

**Model Doesn't Call RUN_TESTS Manually**: The eval shows run_tests=0 for all tasks.

Despite BC accuracy of 87.7%, the model doesn't transfer the RUN_TESTS behavior to eval:
- BC teaches: step=0 with tests_total=0 → RUN_TESTS
- Eval provides: step=0 with tests_total=0 → Model outputs WRITE_FOCUS

The model is learning to make improvements (31.8% IMPROVED rate) because:
- `auto_tests_on_write=True` runs tests automatically after WRITE_FOCUS
- The model's WRITE_FOCUS actions are fixing bugs in some cases

Root cause hypothesis:
- Model keys on text content (terminal, goal) rather than metadata (step, tests)
- 256 bytes of text vs 2 bytes of metadata creates imbalanced signal
- BC observations still have subtle differences from eval (path strings, etc.)

## 4. NEXT STEPS (IN ORDER)

1. **Architecture fix**: Add attention to metadata bytes in observation encoder
2. **Curriculum**: Train on TRIVIAL first (simpler, no RUN_TESTS needed), then HARD
3. **PPO fine-tuning**: Use rewards to reinforce RUN_TESTS behavior
4. **Alternative**: Remove RUN_TESTS requirement, use auto_tests_on_write

## 5. KEY FILES

| File | Purpose |
|------|---------|
| `src/harness/actions.py` | v1 decoder with vocab fix (MODIFIED) |
| `scripts/train_jarvis_harness.py` | Training with all fixes (MODIFIED) |
| `src/harness/expert_trajectories.py` | BC demo generation with full observation alignment (MODIFIED) |
| `scripts/eval_jarvis_harness.py` | Evaluation script |
| `scripts/diagnose_actions.py` | Diagnostic tool |
| `src/core/goal_encoder.py` | Phase 10 GoalEncoder (ready) |

## 6. COMMANDS

### Train from Scratch (with all fixes)
```bash
PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 \
    --difficulty hard \
    --timesteps 0 \
    --bc-epochs 30 \
    --bc-demos 300 \
    --bc-sequential \
    --v2-subprocess-heavy \
    --gpu-min-util 5
```

### Evaluate Model
```bash
PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_0.pt \
    --difficulty hard --num-tasks 30
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

### COMBINED_VOCAB (21 items)
```python
[':\n', ')', ',', "'", '"',           # TRIVIAL fixes (0-4)
 '<=', '>=', '!=', '==', '<', '>',    # Comparison operators (5-10)
 '+', '-', '*', '/',                   # Arithmetic operators (11-14)
 ' + 1', ' - 1', '+1', '-1', '+ 1', '- 1']  # Off-by-one fixes (15-20)
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

- [ ] HARD solve rate >= 70% (currently 0%)
- [x] Model uses correct vocab_idx for each bug type
- [ ] Model follows RUN_TESTS → WRITE_FOCUS → RUN_TESTS → COMPLETE sequence
- [x] BC accuracy >= 80% (achieved 87.7%)
- [x] IMPROVED rate > 30% (achieved 31.8%)
- [ ] Production deployment ready

## 10. KEY INSIGHT

The observation encoding puts 320 bytes of variable text (terminal + goal) before the metadata. The model likely learns spurious text correlations rather than the correct metadata-based decision rule. Future work should:

1. **Add metadata emphasis** in the observation encoder (skip connections, attention)
2. **Normalize text fields** to remove irrelevant variation
3. **Train directly from env** instead of manually constructing BC observations

---

**GOAL: Build Iron Man's JARVIS. Do not stop until complete.**

The BC observation alignment is now complete. The model achieves 87.7% BC accuracy and 31.8% IMPROVED rate on HARD. The RUN_TESTS behavior doesn't transfer - next step is to either fix the observation encoder or use curriculum learning.
