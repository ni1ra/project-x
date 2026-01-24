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

# BLUEPRINT.md — Phase 12: Extended Tool Diversity (npm Operations)

## Overview

Expand JARVIS beyond pytest and git to support npm workflows. The model learns to use npm operations (npm install, npm test, npm run) as part of JavaScript/TypeScript bug-fixing trajectories. This validates the architecture can generalize to any CLI tool.

## Reconnaissance

**Existing Infrastructure (READY):**
- Phase 11 established the pattern for tool expansion: vocab-based actions, tool state in observations
- ActionType enum extensible (currently 0-19, ample room for 20+)
- Expert trajectory generation supports multi-tool workflows
- BC training handles mixed datasets (pytest + git tasks)
- Observation metadata layout: git uses 48-51, bytes 52-63 reserved for future tools

**Missing Components:**
- NPM ActionTypes (npm_install, npm_test, npm_run)
- JavaScript/TypeScript repo generator (like Python repo_generator.py)
- NPM-based verification (exit codes, test results parsing)
- BC demos demonstrating npm workflows
- Observation fields for npm state (package.json present, node_modules present)

---

## Architecture

### File Structure (Changes Only)

```
src/harness/
├── actions.py           # ADD: NPM_INSTALL, NPM_TEST, NPM_RUN action types
├── env.py               # ADD: _npm_install(), _npm_test(), _npm_run() handlers
├── verifiers.py         # ADD: verify_npm_test(), get_npm_state()
├── observations.py      # ADD: npm_state fields (offset 52-55)
├── expert_trajectories.py # ADD: generate_npm_trajectory()
└── js_repo_generator.py # NEW: Generate JS repos with bugs (like repo_generator.py)

scripts/
├── train_jarvis_harness.py # ADD: --enable-npm-tasks flag
└── eval_jarvis_harness.py  # ADD: npm task evaluation
```

### New Action Types (ActionTypes 20-22)

```python
class ActionType(IntEnum):
    # ... existing 0-19 ...

    # Phase 12: NPM operations
    NPM_INSTALL = 20   # Run npm install
    NPM_TEST = 21      # Run npm test
    NPM_RUN = 22       # Run npm run <script> (vocab-based)
```

**NPM_RUN Encoding (vocab-based):**
- Byte 0: action_type (22)
- Byte 25: vocab_idx (into NPM_SCRIPT_VOCAB)
- Byte 26: vocab_mode (1 = NPM_SCRIPT_VOCAB)

**NPM_SCRIPT_VOCAB (standard npm scripts):**
```python
NPM_SCRIPT_VOCAB = [
    'build',
    'lint',
    'format',
    'check',
    'dev',
    'start',
    'compile',
    'typecheck',
]  # 8 items - model learns to select appropriate script
```

### JS Repo Generator

New file: `src/harness/js_repo_generator.py`

Generates simple JavaScript repos with injectable bugs:

```python
@dataclass
class JSRepo:
    """A generated JS/TS repository with test suite."""
    name: str
    root_path: str
    source_file: str      # e.g., "src/utils.js"
    test_file: str        # e.g., "test/utils.test.js"
    original_code: str
    buggy_code: str
    bug_location: Tuple[int, int]  # (line, col)
    bug_type: str
    package_json: str
```

**Bug Types (JS):**
- `wrong_operator`: `>` vs `>=`, `===` vs `==`
- `off_by_one`: Array indexing, loop bounds
- `wrong_literal`: `null` vs `undefined`, `true` vs `false`
- `typo`: Common JS typos like `cosnt`, `fucntion`

**Test Framework:** Jest (simple, no config needed)

### Observation Enhancement

Add npm state to metadata section (bytes 52-55, after git state):

```
Meta offset + 52: npm_package_json_present (bool)
Meta offset + 53: npm_node_modules_present (bool)
Meta offset + 54: npm_last_exit_code (uint8, 0=success)
Meta offset + 55: reserved
```

### BC Demo Sequence (npm workflow, 8 steps)

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

This is an 8-step trajectory combining npm and git workflows.

### Verifier: verify_npm_test()

```python
def verify_npm_test(repo_path: str) -> Tuple[bool, int, int]:
    """Run npm test and parse results.

    Returns: (all_passed, passing, total)
    """
    result = subprocess.run(
        ['npm', 'test', '--', '--json'],
        cwd=repo_path,
        capture_output=True,
        timeout=60,
    )
    # Parse Jest JSON output for pass/fail counts
    ...
```

---

## Implementation Steps

### Phase 12.1: Foundation (JS Repo Generator)

- [x] **Step 1: Create js_repo_generator.py** ✅
  - File: `src/harness/js_repo_generator.py`
  - Generate simple JS repos with Jest tests
  - Support bug injection (wrong_operator, off_by_one)
  - Verify: Can generate valid JS repo with passing tests

- [x] **Step 2: Add NPM action types** ✅
  - File: `src/harness/actions.py`
  - Add `NPM_INSTALL = 20`, `NPM_TEST = 21`, `NPM_RUN = 22`
  - Add `NPM_SCRIPT_VOCAB` for npm run scripts
  - Verify: Action encoding/decoding works

- [x] **Step 3: Implement npm handlers** ✅
  - File: `src/harness/env.py`
  - Add `_npm_install()`, `_npm_test()`, `_npm_run()` handlers
  - Parse npm test output for pass/fail
  - Verify: Manual test shows npm commands work

### Phase 12.2: Observations (npm State)

- [x] **Step 4: Add npm state to observations** ✅
  - File: `src/harness/observations.py`
  - Add `npm_package_json`, `npm_node_modules`, `npm_exit_code` fields
  - Update `encode_observation()` and `decode_observation()`
  - Verify: Observation roundtrip test

- [x] **Step 5: Update env to populate npm state** ✅
  - File: `src/harness/env.py`
  - Check for package.json, node_modules presence
  - Track last npm exit code
  - Verify: Observation shows correct npm state

### Phase 12.3: BC Demos (Expert Trajectories)

- [x] **Step 6: Create NpmTrajectory type** ✅
  - File: `src/harness/expert_trajectories.py`
  - Define `NpmTrajectory` dataclass
  - Verify: Trajectory can be instantiated

- [x] **Step 7: Generate npm BC trajectories** ✅
  - File: `src/harness/expert_trajectories.py`
  - Add `generate_npm_trajectory()` function
  - 8-step sequence: NPM_INSTALL → NPM_TEST → WRITE_FOCUS → NPM_TEST → GIT_STATUS → GIT_ADD → GIT_COMMIT → COMPLETE
  - Verify: Generated trajectory is valid

- [x] **Step 8: Update BC dataset generation** ✅
  - File: `src/harness/expert_trajectories.py`
  - Add `create_npm_bc_dataset()` function
  - Verify: Dataset includes npm trajectories

### Phase 12.4: Training Integration

- [x] **Step 9: Add training flags** ✅
  - File: `scripts/train_jarvis_harness.py`
  - Add `--enable-npm-tasks` and `--npm-task-ratio` flags
  - Pass to BC demo generation
  - Verify: Training with npm tasks starts

- [x] **Step 10: Add eval support** ✅
  - File: `scripts/eval_jarvis_harness.py`
  - Add npm task evaluation and `--enable-npm-tasks` flag
  - Report npm success rate
  - Verify: Eval reports npm metrics

### Phase 12.5: Validation (PENDING - requires GPU training)

- [ ] **Step 11: Train on npm tasks**
  - Run: `--enable-npm-tasks --bc-epochs 100`
  - Target: BC accuracy >80%
  - Verify: Model predicts NPM_INSTALL, NPM_TEST correctly

- [ ] **Step 12: Evaluate solve rate**
  - Run eval with npm tasks
  - Target: Solve rate >50%
  - Verify: Model completes npm workflow

**IMPLEMENTATION STATUS:** Steps 1-10 complete. Infrastructure ready for training.

---

## Acceptance Criteria

- [ ] Model can predict NPM_INSTALL, NPM_TEST, NPM_RUN actions
- [ ] BC accuracy on npm actions > 80%
- [ ] npm-workflow task solve rate > 50%
- [ ] Observations correctly reflect npm state
- [ ] No regression on pytest-only tasks (maintain 100% EASY)
- [ ] No regression on git tasks (maintain 100%)

---

## Test Requirements

### Unit Tests
- `test_npm_action_encoding()` - Action bytes roundtrip
- `test_npm_state_observation()` - npm state in observations
- `test_js_repo_generator()` - JS repo generation with bugs
- `test_npm_trajectory()` - 8-step trajectory validity

### Integration Tests
- `test_npm_task_bc_training()` - BC on mixed tasks (pytest + git + npm)
- `test_npm_task_evaluation()` - Full eval loop with npm tasks

### E2E Tests
- Train model with `--enable-npm-tasks`
- Verify BC accuracy > 80%
- Evaluate solve rate > 50%

---

## Resource Requirements

- **GPU:** RTX 5070 Ti (16GB) - verified available ✅
- **Python:** 3.12.3 in venv - verified ✅
- **Node.js:** v22.21.0 - verified ✅
- **npm:** 11.6.2 - verified ✅

---

## JARVIS Validation

**Score:** PENDING

**Pre-validation Checklist:**
1. Observation metadata collision check - git uses 48-51, npm will use 52-55 ✓
2. Raw text generation risk - using NPM_SCRIPT_VOCAB ✓
3. Node.js environment check - must verify before implementation

---

Generated by /blueprint
Ready for /goapeshit execution
