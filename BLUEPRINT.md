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

# BLUEPRINT.md — Phase 11: Tool Diversity (Git Operations)

## Overview

Expand JARVIS beyond pytest to support git workflows. The model learns to use git operations (status, diff, add, commit) as part of bug-fixing trajectories. This is the first step toward full tool diversity (npm, pip, docker).

## Reconnaissance

**Existing Infrastructure (READY):**
- Git ActionTypes 7-12 already defined in `actions.py`
- Git handlers implemented in `env.py`: `_git_status()`, `_git_diff()`, `_git_add()`, etc.
- Git repos initialized on env reset via `_init_git_repo()`
- Energy costs assigned for git operations

**Missing Components:**
- BC demos demonstrating git workflows
- Task types that require git (e.g., "fix bug AND commit")
- Git-based verification (clean working tree, proper commit)
- Training infrastructure for git action prediction

---

## Architecture

### File Structure (Changes Only)

```
src/harness/
├── expert_trajectories.py  # ADD: generate_git_trajectory()
├── verifiers.py            # ADD: verify_git_commit()
├── bug_templates.py        # ADD: GitCommitTask type
└── env.py                  # MODIFY: git state in observations

scripts/
├── train_jarvis_harness.py # ADD: --enable-git-tasks flag
└── eval_jarvis_harness.py  # ADD: git task evaluation
```

### Task Type: GitCommitTask

New task type that requires the model to:
1. Run tests (discover failing test)
2. Fix the bug (WRITE_FOCUS)
3. Run tests (verify fix)
4. Stage changes (GIT_ADD)
5. Commit changes (GIT_COMMIT - new action)
6. Complete task

```python
@dataclass
class GitCommitTask:
    """Task requiring fix + git commit."""
    bug_task: Task              # The underlying bug to fix
    commit_message_hint: str    # Hint for commit message
    require_clean_tree: bool    # Must have no uncommitted changes
```

### New Action: GIT_COMMIT (ActionType 19)

```python
class ActionType(IntEnum):
    # ... existing ...
    GIT_COMMIT = 19    # Commit staged changes with message
```

**Encoding (vocab-based, JARVIS recommended):**
- Byte 0: action_type (19)
- Byte 25: vocab_idx (into GIT_COMMIT_VOCAB)
- Byte 26: vocab_mode (0 = GIT_COMMIT_VOCAB)

**GIT_COMMIT_VOCAB (standard messages):**
```python
GIT_COMMIT_VOCAB = [
    'Fix bug',
    'Fix test',
    'Update logic',
    'Fix comparison',
    'Fix off-by-one',
    'Fix typo',
    'Refactor code',
    'Add feature',
]  # 8 items - model learns to select appropriate message
```

This avoids raw text generation which destabilized training in Phase 9.

### BC Demo Sequence (7 steps)

```
Step 0: obs (tests=0/0)           → RUN_TESTS
Step 1: obs (tests=X/Y, fail)     → WRITE_FOCUS (fix bug)
Step 2: obs (tests=X/Y, fixed)    → RUN_TESTS (verify)
Step 3: obs (tests=Y/Y, pass)     → GIT_STATUS (check state)
Step 4: obs (modified files)      → GIT_ADD (stage fix)
Step 5: obs (staged)              → GIT_COMMIT (commit)
Step 6: obs (clean tree)          → COMPLETE_TASK
```

### Observation Enhancement

**JARVIS Fix:** Reduce FOCUS_PREVIEW_BYTES from 32 to 16 (occupies 32-47), freeing 48-63 for git state.

Add git state to metadata section (bytes 448-512):

```
Meta offset + 32: focus_preview (16 bytes, reduced from 32)
Meta offset + 48: git_modified_count (uint8)
Meta offset + 49: git_staged_count (uint8)
Meta offset + 50: git_untracked_count (uint8)
Meta offset + 51: git_clean_tree (bool)
Meta offset + 52-63: reserved (12 bytes for future tools)
```

### Verifier: verify_git_commit()

```python
def verify_git_commit(repo_path: str) -> Tuple[bool, str]:
    """Verify git commit was made correctly."""
    # Check working tree is clean
    status = subprocess.run(['git', 'status', '--porcelain'], ...)
    if status.stdout.strip():
        return False, "Working tree not clean"

    # Check commit exists after initial
    log = subprocess.run(['git', 'log', '--oneline', '-2'], ...)
    commits = log.stdout.strip().split('\n')
    if len(commits) < 2:
        return False, "No new commit found"

    return True, "Git commit verified"
```

---

## Implementation Steps

### Phase 11.1: Foundation (Git Commit Action)

- [x] **Step 1: Add GIT_COMMIT action type** ✓
  - File: `src/harness/actions.py`
  - Add `GIT_COMMIT = 19` to ActionType enum
  - Add encoding/decoding for commit message
  - Verify: Unit test passes

- [x] **Step 2: Implement _git_commit() handler** ✓
  - File: `src/harness/env.py`
  - Handle GIT_COMMIT action in step()
  - Extract commit message from action bytes
  - Verify: Manual test `git log` shows commit

- [x] **Step 3: Add git verifier** ✓
  - File: `src/harness/verifiers.py`
  - Add `verify_git_commit()` function
  - Verify: Unit test with clean/dirty repos

### Phase 11.2: Observations (Git State)

- [x] **Step 4: Add git state to observations** ✓
  - File: `src/harness/observations.py`
  - Add `git_modified`, `git_staged`, `git_clean` fields
  - Update `encode_observation()` and `decode_observation()`
  - Verify: Observation roundtrip test

- [x] **Step 5: Update env to populate git state** ✓
  - File: `src/harness/env.py`
  - Call `git status --porcelain` in `_get_observation()`
  - Parse output to populate git fields
  - Verify: Observation shows correct git state

### Phase 11.3: BC Demos (Expert Trajectories)

- [x] **Step 6: Create GitCommitTask type** ✓
  - File: `src/harness/expert_trajectories.py`
  - Define `GitCommitTrajectory` dataclass
  - Verify: Task can be instantiated

- [x] **Step 7: Generate git BC trajectories** ✓
  - File: `src/harness/expert_trajectories.py`
  - Add `generate_git_commit_trajectory()` function
  - 7-step sequence: RUN_TESTS → WRITE_FOCUS → RUN_TESTS → GIT_STATUS → GIT_ADD → GIT_COMMIT → COMPLETE
  - Verify: Generated trajectory is valid

- [x] **Step 8: Update BC dataset generation** ✓
  - File: `src/harness/expert_trajectories.py`
  - Add `create_git_commit_bc_dataset()` function
  - Verify: Dataset includes git trajectories

### Phase 11.4: Training Integration

- [x] **Step 9: Add training flags** ✓
  - File: `scripts/train_jarvis_harness.py`
  - Add `--enable-git-tasks` and `--git-task-ratio` flags
  - Pass to BC demo generation
  - Verify: Training with git tasks starts

- [x] **Step 10: Add eval support** ✓
  - File: `scripts/eval_jarvis_harness.py`
  - Add git task evaluation and `--enable-git-tasks` flag
  - Report git commit success rate
  - Verify: Eval reports git metrics

### Phase 11.5: Validation

- [x] **Step 11: Train on git tasks** ✓
  - Run: `--enable-git-tasks --bc-epochs 100`
  - Result: **96.5% BC accuracy** (target >80%) ✓
  - Verify: Model predicts GIT_ADD, GIT_COMMIT correctly

- [x] **Step 12: Evaluate solve rate** ✓
  - Run eval with git tasks
  - Result: **100% solve rate** (target >50%) ✓
  - Verify: Model completes full persistent workflow

---

## Acceptance Criteria

- [x] Model can predict GIT_STATUS, GIT_ADD, GIT_COMMIT actions ✓
- [x] BC accuracy on git actions > 80% → **96.5%** ✓
- [x] Git-commit task solve rate > 50% → **100%** ✓
- [x] Observations correctly reflect git state ✓
- [x] No regression on pytest-only tasks (maintain 100% EASY) ✓

**Phase 11 COMPLETE** - 2026-01-24

---

## Test Requirements

### Unit Tests
- `test_git_commit_action_encoding()` - Action bytes roundtrip
- `test_git_state_observation()` - Git state in observations
- `test_verify_git_commit()` - Verifier with clean/dirty repos
- `test_git_commit_trajectory()` - 7-step trajectory validity

### Integration Tests
- `test_git_task_bc_training()` - BC on mixed tasks (pytest + git)
- `test_git_task_evaluation()` - Full eval loop with git tasks

### E2E Tests
- Train model with `--enable-git-tasks`
- Verify BC accuracy > 80%
- Evaluate solve rate > 50%

---

## Resource Requirements

- **GPU:** RTX A4000 (16GB) - verified available
- **Python:** 3.12.3 in venv - verified
- **Git:** Available in environment - verified

---

## JARVIS Validation

**Score:** 380/420 (PROCEED)

**Issues Identified:**
1. Observation metadata collision at offset 48 - **FIXED** (reduce FOCUS_PREVIEW_BYTES)
2. Raw text generation risk for commit messages - **FIXED** (use GIT_COMMIT_VOCAB)

**Recommendations Applied:**
- Reduced FOCUS_PREVIEW_BYTES from 32 to 16
- Added GIT_COMMIT_VOCAB for vocab-based commit messages
- Must implement mock git output generators in BC demos to match env.py

---

Generated by /blueprint
Ready for /goapeshit execution
