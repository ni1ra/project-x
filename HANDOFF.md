# HANDOFF — WIRED-BRAIN: The Path to JARVIS

Generated: 2026-01-16 | Branch: `feat/harness-v2-multifile` (13 commits ahead of origin)

> "Sometimes you gotta run before you can walk." — Tony Stark

## 0) THE VISION: What Is JARVIS?

**JARVIS is not an LLM wrapper.** It's a 1.5M parameter neural agent that:
- Takes bytes in, produces bytes out (content-free)
- Learns to fix code through RL with ground-truth verifiers (pytest, lint)
- Emerges tool-use behavior from the RPJ (Reward-Per-Joule) objective
- Has NO transformers, NO pretrained embeddings, NO LLM calls

**Current reality:** The agent passes emergence gates on toy causal bandits but is NOT yet a competent repo fixer. The path from here to Iron Man's JARVIS is documented below.

---

## 1) ENVIRONMENT CHECKPOINT

```
GPU: NVIDIA GeForce RTX 5070 Ti (16GB total)
Python: .venv/bin/python (Python 3.12.3) — NOT on PATH, must use full path
Tests: 312 passing (./.venv/bin/python -m pytest -q)
VRAM constraint: <10GB
GPU utilization constraint: >80%
```

---

## 2) CURRENT GIT STATE

```
Branch: feat/harness-v2-multifile (13 ahead of origin)
Uncommitted changes: YES - 13 files modified
```

### Uncommitted Files (need commit/PR)
| File | Changes |
|------|---------|
| `src/harness/env.py` | +486 lines (async tests, no-op detection, reward fixes) |
| `src/harness/verifiers.py` | +142 lines (fast/full scope distinction) |
| `scripts/eval_jarvis_harness.py` | +67 lines (step-sleep, run_tests output) |
| `scripts/train_jarvis_harness.py` | +33 lines (difficulty_span param) |
| `src/utils/gpu_guard.py` | +85 lines |
| `tests/test_harness.py` | +55 lines |

### Recent Commits (already pushed)
```
9f3aa0b feat(training): enable async tests and optimize timeouts
976f5fc feat(harness): add async test execution for training
96012a0 feat(curriculum): add true TRIVIAL syntax bug injectors
15b2606 fix(curriculum): use cumulative episode reward for success metric
47cf6d1 docs(handoff): remove fragile git counts
```

---

## 3) CURRENT REWARD STRUCTURE (Critical for Debugging)

### verifiers.py: compute_reward()
```python
# Test reward (ONLY for scope="full", not "fast")
test_reward = 2.0 * pass_rate if scope == "full" else 0.0

# Diff penalty (very small to not discourage writing)
diff_penalty = -0.0001 * diff_changed_lines

# Action penalty
action_penalty = -0.01 * actions_taken

# Success bonus (all tests pass)
success_bonus = 10.0 if all_pass and scope == "full" else 0.0
```

### env.py: _compute_reward() additions
```python
# Syntax reward (dense signal from py_compile)
+1.0 for first compiling edit
+0.2 for subsequent compiling edits
-0.5 for syntax error

# Test delta reward (improvement signal)
+2.0 * delta_tests_passing

# No-op penalty (write that doesn't change anything)
-0.05 if write action succeeded but content unchanged
```

### Why This Matters
The agent currently learns to **avoid writing** because:
1. Writing risks syntax errors (-0.5)
2. NO_OP is safe (only -0.01/action)
3. Test rewards don't flow without writes

**The fix:** Make the first successful edit highly rewarded (+1.0) to bootstrap writing behavior.

---

## 4) MILESTONE STATUS: The Path to JARVIS

### Milestone A — "Edits Exist" ⚠️ IN PROGRESS
- [x] ≥80% episodes perform WRITE actions → **FAILING (50%)**
- [ ] ≥20% episodes improve tests vs baseline → **FAILING (0%)**

### Milestone B — "Fixes Easy" ❌ NOT STARTED
- [ ] ≥60% success rate on `difficulty=easy` (held-out seeds)

### Milestone C — "Fixes Medium" ❌ NOT STARTED
- [ ] ≥30% success rate on `difficulty=medium` (multi-file bugs)

### Milestone D — "Generalizes" ❌ NOT STARTED
- [ ] Success on new templates/bug families (pre-registered holdout)

---

## 5) WHAT WAS TRIED (Learn From This)

### Training Runs Summary
| Seed | Timesteps | Writes% | Test Delta | Notes |
|------|-----------|---------|------------|-------|
| 48 | 32768 | 20% | 0% | Regex bug broke test parsing |
| 49 | 32768 | 10% | 0% | After regex fix, agent collapses |
| 50 | 32768 | 100% | 0% | Removed penalties, agent writes but no progress |
| 51 | 65536 | 100% | 0% | Same - writes random garbage |
| 52 | 65536 | 50% | 0% | Added fast test scope=0 reward |

### Key Insights
1. **Regex bug** (fixed): `r"(\\d+) passed"` was double-escaped, tests never parsed
2. **Fast test farming**: Agent learned to farm baseline pass rate without fixing
3. **No-op exploitation**: Writing the same content repeatedly got syntax rewards
4. **Async timing**: Evaluation runs too fast for tests to complete (need --step-sleep-s)

### Changes Made This Session
1. Fixed regex: `r"(\d+) passed"` now correctly parses test output
2. Scoped test rewards: Only `scope="full"` gets pass_rate reward (prevents farming)
3. No-op detection: `last_edit_changed` flag, penalty for unchanged writes
4. Run tests on reset: Async test at episode start for early failure localization
5. Added `--step-sleep-s` to eval script for async test completion

---

## 6) NEXT STEPS (Priority Order)

### Step 1: Commit & Push Current State
```bash
cd /mnt/c/Users/nira/Documents/Research/WIRED/WIRED-BRAIN
git add -A
git commit -m "feat(harness): reward shaping v2 - scope distinction, no-op detection, async reset tests"
git push origin feat/harness-v2-multifile
```

### Step 2: Train With New Reward Structure
```bash
PYTHONPATH=. ./.venv/bin/python scripts/train_jarvis_harness.py \
  --mode v2 --difficulty easy --action-bytes 64 \
  --num-envs 32 --rollout-steps 128 --timesteps 100000 \
  --ppo-epochs 32 --minibatch-size 4096 \
  --entropy-coef 0.01 --hidden-dim 512 \
  --gpu-burn-ms 400 --gpu-burn-dim 4096 \
  --seed 53
```

### Step 3: Evaluate With Step Sleep
```bash
PYTHONPATH=. ./.venv/bin/python scripts/eval_jarvis_harness.py \
  --checkpoint results/jarvis_harness_v2_100000.pt \
  --mode v2 --difficulty easy --num-tasks 20 --max-steps 100 \
  --step-sleep-s 0.05
```

### Step 4: If Writes Still <80%, Try Curriculum from TRIVIAL
```bash
PYTHONPATH=. ./.venv/bin/python scripts/train_jarvis_harness.py \
  --mode curriculum --difficulty trivial --action-bytes 64 \
  --num-envs 32 --rollout-steps 128 --timesteps 200000 \
  --ppo-epochs 32 --minibatch-size 4096 \
  --entropy-coef 0.001 --hidden-dim 512 \
  --gpu-burn-ms 400 --gpu-burn-dim 4096 \
  --seed 54
```

### Step 5: If Still Stuck, Simplify Action Space
Consider reducing to 32-byte actions or adding `WRITE_FOCUS_LINE` that overwrites current focus line (simpler than offset/length selection).

---

## 7) KEY FILES (Touch These)

### Core Loop
| File | Purpose | LOC |
|------|---------|-----|
| `src/harness/env.py` | Main RL environment | ~1600 |
| `src/harness/verifiers.py` | Ground-truth rewards | ~460 |
| `scripts/train_jarvis_harness.py` | Training script | ~900 |
| `scripts/eval_jarvis_harness.py` | Evaluation script | ~230 |

### Action/Observation
| File | Purpose |
|------|---------|
| `src/harness/actions.py` | 64-byte action encoding |
| `src/harness/observations.py` | 512-byte observation encoding |

### Task Generation
| File | Purpose |
|------|---------|
| `src/harness/repo_generator.py` | Generates buggy repos |
| `src/harness/bug_templates.py` | Bug injection patterns |

---

## 8) HARD RULES (Do Not Violate)

### Ceiling Integrity (BLUEPRINT non-negotiables)
- **NO LLMs, transformers, pretrained embeddings**
- **NO model-based judges** — rewards from verifiers only
- **NO answer leakage** — observations don't reveal solution

### GPU Constraints (user hard requirement)
- **>80% GPU utilization** (use `--gpu-burn-ms` if CPU-bound)
- **<10GB VRAM** (reduce `--num-envs` or `--minibatch-size`)
- Training auto-aborts if violated

### Git Workflow
- **NEVER commit to main** — always PR from feature branch
- **NEVER add Claude attribution** to commits

---

## 9) SUCCESS CRITERIA: When Is JARVIS "Arriving"?

### Gate 1: Edits Exist (Milestone A)
```
Eval output shows:
- writes ≥ 8/10 episodes (80%)
- delta > 0 in ≥ 2/10 episodes (20%)
```

### Gate 2: Fixes Easy (Milestone B)
```
Eval output shows:
- success=1 in ≥ 6/10 episodes (60%)
- On held-out seeds (not training seeds)
```

### Gate 3: Ultimate JARVIS (Milestone D)
```
- ≥30% on medium difficulty
- Success on NEW templates not in training
- Transfer learning ratio T ≥ 0.80
```

---

## 10) QUICK START FOR NEW INSTANCE

Copy this to start a new Claude conversation:

```
Continue working on WIRED-BRAIN (JARVIS harness). Read HANDOFF.md in project root.

Current state: Reward shaping v2 implemented but untested. Agent writes 50% of time, 0% test improvement.

Next step:
1. Commit uncommitted changes
2. Run training with seed 53 (100K steps)
3. Evaluate with --step-sleep-s 0.05
4. Target: ≥80% writes, ≥20% test improvement

Key insight: Test rewards only flow for scope="full", syntax rewards bootstrap writing behavior.
```

---

## 11) THE ULTIMATE VISION

When JARVIS is complete:
1. **Enter any Python repo** with failing tests
2. **Navigate autonomously** using READ/NAVIGATE/STACKTRACE
3. **Locate bugs** by tracing test failures
4. **Write minimal patches** that fix tests
5. **Submit when confident** (all tests pass)

This is not a coding assistant. This is an **autonomous debugging agent** that emerged from RL training on bytes — no language model, no hand-coded reasoning, just RPJ pressure and verifier feedback.

> "I am Iron Man." — But first, we need to get to 80% writes.

---

*Last updated: 2026-01-16 by /handoff protocol*
