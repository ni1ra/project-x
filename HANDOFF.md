# HANDOFF: WIRED-BRAIN Jarvis Harness v2

Generated: 2026-01-18 (Updated v10 - **EVAL LYING - METRICS UNRELIABLE**)

## 1. PROJECT CONTEXT

### What Is This?
WIRED-BRAIN is a **transformer-free** neural network (RPJ Brain, 2.7M params) trained via BC+RL to fix Python bugs autonomously. The goal was to achieve ≥70% test improvement rate on generated bug-fixing episodes for TRIVIAL difficulty.

**STATUS: ⚠️ EVAL UNRELIABLE** (2026-01-18)
- TRIVIAL BC Accuracy: 72.7% | Pytest Success: ~25-30%
- **EASY BC Accuracy: 76.8%** | **Pytest Success: UNKNOWN** (eval counts base=total as success)
- **CRITICAL ISSUE:** Eval counts "already passing" repos as successes
- **Agent behavior:** writes=0, run_tests=0 without focus hints (statue)
- Must fix eval truthfulness before trusting any metrics

### What Problem Does It Solve?
Creating an AI bug-fixer that doesn't depend on LLMs (no API keys, no intelligence ceiling). A pure RL agent that learns to edit code through environmental feedback (pytest verifiers).

### Tech Stack
- **Neural Network:** RPJ Brain (2.7M parameters, recurrent + GRU + MLP)
- **Training:** PPO with Behavioral Cloning (BC) pre-training + **Anchored RL** (NEW)
- **Environment:** JarvisHarnessEnv (multi-file Python repos with injected bugs)
- **Verifier:** pytest (ground-truth test pass/fail)
- **GPU Guard:** Enforces >80% GPU utilization during training

## 2. CURRENT STATUS

### Git State
```
Branch: feat/harness-v2-multifile
Last commit: 4f710f8 docs: Phase 4.4 + 5 validated - self-correction and navigation ready
Uncommitted changes: NO - clean state
```

### Current Progress (Updated 2026-01-17 - **72.7% BC ACCURACY**)
- [x] Phase 0: Validate Current State ✅ COMPLETE
- [x] Deep-Debug Protocol ✅ ROOT CAUSES FOUND
  - [x] Root Cause 1: BC observations EMPTY, RL observations REAL
  - [x] Root Cause 2: v1/v2 decoder mismatch (action_bytes=32 vs 64)
  - [x] Root Cause 3: Focus window mismatch (centered vs line-start)
- [x] Phase 0.5: Sanity Gates ✅ **ALL PASSED**
  - [x] Gate A: Fixed BC observation generation ✅
  - [x] Gate B: Fixed v1/v2 decoder (action_bytes=64) ✅
  - [x] Gate C: Fixed focus window alignment ✅
- [x] **MILESTONE: 25% SUCCESS RATE ACHIEVED** ✅
  - BC-only model, 1 step, TRIVIAL difficulty
  - 5/20 tasks solved (25.0%)
  - All solved tasks: 100% tests passing (11-13 tests each)
- [x] **Phase 3: TRIVIAL++ COMPLETE** ✅
  - TRIVIAL_VOCAB expanded: 3→5 tokens (added quotes)
  - Quote injector: supports both single→double and double→single
  - Focus jitter infrastructure added (hurts BC, disabled for now)
  - Finding: RL degrades BC performance (13.3% vs 25% BC-only)
- [x] **Phase 4: EASY Infrastructure COMPLETE** ✅
  - Added `--force-write-focus-prob` for gradual curriculum (1.0=always, 0.0=never)
  - Added test running incentive (+0.3 reward, capped at 3 runs)
  - EASY training runs: 20k steps, avg reward 0.48→0.58
- [x] **Phase 4.5: EASY Expert Trajectories COMPLETE** ✅ (2026-01-18)
  - EASY_VOCAB: 16 logic tokens (`<=`, `>=`, `!=`, `==`, `<`, `>`, `+`, `-`, `*`, `/`, etc.)
  - COMBINED_VOCAB: 21 tokens (TRIVIAL + EASY)
  - Fixed expert functions to detect BOTH directions of operator swaps
  - data_pipeline template: has test-catchable `> 0 → >= 0` bugs
  - rest_api template: skipped for EASY (tests don't catch operator swaps)
  - **70/100 EASY demos generated with 100% EASY token usage** (`>`: 55, `==`: 15)

### ROOT CAUSE IDENTIFIED: BC-RL Observation Gap

**The diagnostic trap found the smoking gun:**

| Region | BC non-zero | RL non-zero | Gap |
|--------|-------------|-------------|-----|
| Terminal | 0% | 100% | **100%** |
| Focus | 0% | 99% | **99%** |
| File meta | 0% | 12.5% | 12.5% |
| Test status | 99% | 100% | ~1% |
| Goal | 98% | 100% | ~2% |

**Translation:** BC training data has EMPTY focus/terminal regions while RL has real file content.
BC learned to predict actions from zeros. It can't generalize to real observations.

### Why KL Penalty Failed
KL alone doesn't preserve **competence**, it only regularizes **distribution drift**.
When BC observations differ fundamentally from RL observations, KL is meaningless.

### What's Complete
- [x] BC pre-training infrastructure (`expert_trajectories.py`)
- [x] TRIVIAL_VOCAB action space (5 tokens: `':\n'`, `')'`, `','`, `"'"`, `'"'`)
- [x] GPU burn mechanism for >80% utilization
- [x] Curriculum closure fixed (vocab modulo, offset centering)
- [x] **BC accuracy: 22.1%** (with real observations, line-based focus)
- [x] All demos valid: 426/500 (rejected 74 unfixable with vocab)
- [x] Deep-debug diagnostic traps created and run
- [x] Root cause identified AND FIXED: BC-RL observation gap
- [x] Root cause identified AND FIXED: v1/v2 decoder mismatch
- [x] Root cause identified AND FIXED: Focus window alignment
- [x] **20% SUCCESS RATE ON TRIVIAL BUGS**
- [x] **ANCHORED RL IMPLEMENTED** (2026-01-17)
  - [x] BC imitation loss during RL (`compute_bc_anchor_loss()`)
  - [x] λ_bc decay schedule (1.0 → 0.05 linear)
  - [x] Two-timescale optimizer (backbone 0.1x LR)
  - [x] No-op penalties in reward shaping
  - [x] `--bc-checkpoint` to load pre-trained BC

### /deep-debug Results (2026-01-17)

**Session 1: Curriculum closure (FIXED)**
| Bug | Location | Problem | Fix |
|-----|----------|---------|-----|
| Vocab Modulo | `train_jarvis_harness.py:503` | Used `% 4` but TRIVIAL_VOCAB has 3 items | Changed to `% 3` |
| Offset Wrap Poison | `expert_trajectories.py` | 58.2% of demos had offset >= 32 | Center focus on bug position |

**Session 2: Policy collapse (ROOT CAUSE FOUND)**
| Trap | Verdict | Finding |
|------|---------|---------|
| KL Collapsed Actions | GUILTY | Post-RL policy assigns 74.8% prob to one action |
| Hidden State Saturation | SUSPICIOUS | States bounded, but collapse happens with fresh states too |
| Dataset-Reality Gap | **GUILTY** | BC obs 0% focus, RL obs 99% focus - totally different! |

---

## 3. IMMEDIATE MOVES (Do These In Order)

### Move 0: Fix BC Observation Generation (CRITICAL)

The BC dataset uses **empty observations** while RL uses **real file content**.
This must be fixed first - everything else is downstream.

```bash
# Verify the problem exists
PYTHONPATH=. .venv/bin/python diagnostics/_debug_trap_dataset_reality_gap.py
```

**Fix:** Edit `src/harness/expert_trajectories.py` to use actual environment observations.

### Move 1: Gate A - BC-Only Evaluation

After fixing BC observations, eval BC-only (no RL) to see if it works:
```bash
PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
  --checkpoint results/jarvis_harness_v2_0.pt \
  --mode v2 --difficulty trivial --num-tasks 50 \
  --force-write-focus --max-steps 128
```

**Expected:** Some success (even 2-5%) if BC actually learned useful behavior.
**If 0%:** BC obs still broken, or env write path broken.

### Move 2: Gate B - Verify Env Registers Edits

Instrument `src/harness/env.py` to log when WRITE_FOCUS actually changes the file:
- Log: offset, replace_len, token, global_offset, changed (bool)
- Run 50 random actions and count how often changed=True

**If changed=True sometimes:** Env works, policy is the problem.
**If changed=False always:** Env write path is broken.

### Move 3: Gate C - Add Collapse Detector

Add alarm to training that triggers when:
- Last 200 actions have >95% same (type, offset, len, token)
- Dump observations when triggered for inspection

### Move 4: Anchored RL Training

**Replace KL penalty with BC imitation loss during RL:**
```python
loss = PPO_loss + λ_bc * CE(action | demo_obs) + λ_value * V_loss
```

**Schedule:**
- 0-10k steps: λ_bc = 1.0 (strong anchor)
- 10k-50k: λ_bc linear decay to 0.2
- 50k+: λ_bc = 0.05 (still anchored)

**Plus:** Two-timescale optimizer (backbone LR = 0.1× head LR)

### Move 5: Add No-Op Penalties

```python
+r_edit = 0.1   # if changed=True
-r_noop = 0.2   # if changed=False for WRITE_FOCUS
-r_repeat = 0.5 # if same action 5+ times
+r_compile = 0.5 # if py_compile passes (once per episode)
+r_test = 2.0   # if pytest improves
```

### Move 6: Full Training + Eval

```bash
PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
  --mode v2 --timesteps 100000 --difficulty trivial \
  --bc-epochs 50 --bc-demos 500 \
  --bc-anchor-coef 1.0 --bc-anchor-decay linear
```

**Target:** ≥20% success rate on TRIVIAL.

### Move 7: Commit + PR Once Working

```bash
git add -A
git commit -m "feat(harness): anchored RL + fixed BC observations"
git push -u origin feat/harness-v2-multifile
gh pr create --title "Fix BC-RL observation gap + anchored RL" --body "..."
```

---

## 4. STAGED ROADMAP TO JARVIS

### NEW INSIGHT (2026-01-17): Heterogeneous Brain Architecture

**The Key to Unlimited Intelligence:**

Biological brains have regional heterogeneity:
- Different regions with different neuron counts
- Different synapse-to-neuron ratios
- Different timescales and connectivity patterns

**Our approach:**
- **x** = number of distinct regions (sections)
- **y** = per-region settings (width, sparsity, fan-in/out, timescale, plasticity)
- **Optuna** searches for optimal (x, y) under RPJ pressure

**Why this matters:**
Transformers are homogeneous (every layer looks the same). Brains are not.
If structure is learned under task pressure, the system can discover specialized circuits.
This is the path to intelligence that exceeds the model it was trained with.

See `PLAN_TO_JARVIS.md` Phase 8 for full implementation plan.

---

### Stage A: TRIVIAL++ (Constrained but Less Toy)

**Goal:** Make TRIVIAL robust enough that success feels boring.

**A1: Add wrong-quote back (solvable)**
- Expand `TRIVIAL_VOCAB` to include `'` and `"` (still tiny)
- Ensure experts label correctly (replace length=1)
- Re-run BC gate (must stay high)

**A2: Add focus jitter curriculum**
- Slightly randomize focus start around bug
- Prevents brittle "only works at exactly centered windows"

**Exit criteria:** >70% success on TRIVIAL++ with held-out templates.

### Stage B: EASY (Enable RUN_TESTS, Stop Forcing WRITE_FOCUS)

**Goal:** Agent learns basic developer loop:
```
run tests → read failure → edit → re-run tests → submit
```

**Enable:**
- `RUN_TESTS`
- `STACKTRACE` / failure parsing
- `SEARCH` (ripgrep-like)

**Disable:**
- `--force-write-focus` (gradually: 80% forced → 20% → 0%)

**Exit criteria:** >20-30% success on EASY with multi-step episodes; agent uses tests strategically.

### Stage C: Multi-File (NAVIGATE Becomes Real)

Repo generator already produces multi-file templates (data pipeline, REST API).

**Add:**
- `LIST_FILES`
- `NAVIGATE`
- `READ_FILE` chunking

**Training trick:** Make stacktraces reliably include file/line in observation bytes. Give small reward for navigating to correct file (once per episode, not spammable).

**Exit criteria:** Solves meaningful fraction of multi-file repos without editing tests.

### Stage D: General Edits (Drop TRIVIAL_VOCAB, Go Byte-Level)

This is where "Jarvis" starts to feel like Jarvis.

**How to avoid exploding search space:**
1. Start with byte-BPE style micro-vocab learned from repo text (no pretrained models)
2. Allow only short inserts first (1-8 bytes), then extend
3. Keep closure gate: tasks requiring longer edits don't enter curriculum yet

**Exit criteria:** Agent fixes simple typos/keywords because it can emit those bytes.

### Stage E: Persistent Jarvis (Long-Horizon Operator Mode)

Current harness is episodic (reset → solve → done). Jarvis is continuous.

**Add:**
- Persistent workspace (no reset between tasks)
- Scratchpad file (agent writes notes to itself)
- Task queue ("fix bug A, then implement feature B")
- Safety sandbox (agent cannot brick system)

**Leverage existing RPJ Brain features:**
- Energy proxy and budgets
- Sleep/consolidation
- Plasticity within episodes

**Exit criteria:** Agent completes multiple tasks back-to-back, recovers from mistakes via git checkout/diff/reset.

---

## 5. THE JARVIS REALITY CHECK

Your docs are honest about the gap. Within the constraints, "Jarvis" means:

- Extremely strong operator behavior in constrained world (repos, tools, tests)
- Learned planning via reward, not natural-language reasoning
- Minimal priors, but still some priors (action formats, focus window, verifiers)

That's still a legit Jarvis-shaped beast.

---

## 6. 48-HOUR CHECKLIST (Best Next Steps)

```
[ ] 1. pytest green
[ ] 2. BC gate ~75% still holds
[ ] 3. RL 100k steps TRIVIAL
[ ] 4. Eval 50 tasks; compute success/improvement %
[ ] 5. If ≥20%: checkpoint + commit + PR
[ ] 6. If <20%: instrument action/token distribution + effective edits, fix collapse, re-run
```

---

## 7. KEY FILES

| File | Purpose | Status |
|------|---------|--------|
| `src/harness/expert_trajectories.py` | BC demo generation | **FIXED**: Offset centering |
| `scripts/train_jarvis_harness.py:503` | BC accuracy calculation | **FIXED**: `% 4` → `% 3` |
| `src/harness/actions.py:336` | TRIVIAL_VOCAB definition | 5 items (colon, paren, comma, quotes) |
| `src/harness/env.py` | Focus initialization | Working |
| `scripts/eval_jarvis_harness.py` | Evaluation script | Working |
| `diagnostics/_debug_trap_*.py` | Diagnostic traps | Archived |

---

## 8. ENVIRONMENT

```bash
# GPU: NVIDIA GeForce RTX 5070 Ti, 16303 MiB
# Python: 3.12.3 (.venv/bin/python)
# CWD: /mnt/c/Users/nira/Documents/Research/WIRED/WIRED-BRAIN
```

---

## QUICK START FOR NEW INSTANCE

```
Continue working on WIRED-BRAIN Jarvis Harness. Read HANDOFF.md for full context.

STATUS: **EVAL LYING** (2026-01-18)
- Eval counts base=total as success (free wins pollute metrics)
- Agent has writes=0, run_tests=0 without focus hints (statue)
- Reported "90% success" is unreliable - must fix eval first

REQUIRED RUNBOOK (IN ORDER):
1. Step 0: Fix eval truthfulness
   - Add: eligible = (base < total)
   - Track: solved/eligible, improved/eligible
   - Print truthful metrics

2. Step 1 (Phase 1.8): Make EASY fixable
   - Verify EASY_VOCAB is wired through decoder + demos
   - Gate: scripted oracle can fix EASY bugs

3. Step 2: BC-only gate on EASY (with focus hints)
   - Run BC eval with truthful metrics
   - Gate: solved_rate > 0% on eligible tasks

4. Step 3: Add RUN_TESTS-first BC
   - Teach agent first move
   - Gate: with --no-auto-focus, agent calls RUN_TESTS sometimes

5. Step 4: Only THEN do Phase 6 (byte-level)

KEY COMMANDS:
  # Eval (after fixing truthfulness)
  PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_100.pt \
    --mode v2 --difficulty easy --num-tasks 50 --max-steps 64

See PLAN_TO_JARVIS.md for detailed roadmap. See MISTAKES.md for failure log.
```

---

## PHASE 4 FINDINGS: BC Accuracy vs Pytest Eval

**Critical Discovery (2026-01-17):**

The 72.7% "success rate" is actually **BC action prediction accuracy**, not pytest eval success.

| Metric | What it measures | Value |
|--------|------------------|-------|
| BC Accuracy | Predicted action == expert action | 72.7% |
| Pytest Eval | Tests pass after agent applies fix | ~5% |

**Why the gap?**
1. BC accuracy: "Did the model predict the correct action?"
2. Pytest eval: "Did pytest pass after the edit?"

**The hidden catch:**
- Syntax bugs (TRIVIAL) prevent pytest from even loading test files
- When there's a syntax error, pytest shows `tests=0/0` (collection failed)
- The model must fix the syntax error perfectly for tests to run at all
- A "close but wrong" edit still results in 0 tests passing

**For EASY difficulty (logic bugs):**
- Logic bugs don't prevent test collection
- But BC has no expert trajectories for logic bug fixes
- The model only knows TRIVIAL_VOCAB (syntax tokens), not operator replacements
- Result: 0% success on EASY (expected behavior)

**Next requirement for EASY:**
BC expert trajectories that demonstrate fixing logic bugs (wrong_operator, off_by_one).

---

## STALE INFO (DO NOT USE)

Previous documents mentioned:
- "KL penalty will fix collapse" - **WRONG**, KL alone doesn't preserve competence
- "BC works, RL destroys it" - **HALF-TRUE**, BC never worked on real observations
- "75.2% BC accuracy means transfer" - **WRONG**, BC trained on empty obs, can't transfer

The real root cause was identified via /deep-debug diagnostic traps:
- BC observations have 0% non-zero in focus region
- RL observations have 99% non-zero in focus region
- This is why no amount of KL penalty could help
