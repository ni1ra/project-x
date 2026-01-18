# MISTAKES.md — WIRED-BRAIN Failure Log

> Do not repeat recorded patterns of failure.
> Every failure MUST be logged with context, root cause, and lesson.

---

## Format Template

```
## [YYYY-MM-DD HH:MM] - [Phase/Component]
**What happened:** [Objective description of failure]
**Root cause:** [Why it failed - be brutally honest]
**Score:** [XXX/420]
**Recovery taken:** [RETRY/SLINGSHOT/GRAVEYARD]
**Lesson:** [What NOT to do next time]
```

---

## Failure Log

### 2026-01-14 - Sequential Instead of Parallel Execution
**What happened:** Said "Let me update the Epilogue with the new results and then invoke JARVIS" - executed sequentially when both tasks were independent.

**Root cause:**
1. Default to sequential thinking when parallel is possible
2. Didn't recognize that JARVIS consultation (background) and paper editing (foreground) are independent

**Score:** 380/420 (inefficient but not blocking)

**Recovery taken:** RETRY - user reminded, executed properly afterward

**Lesson:**
- When two tasks are independent (API call + file edit), run in parallel
- Background tasks exist for a reason - USE THEM
- Always ask: "Can these run at the same time?"

---

### 2026-01-14 - CRITICAL: Observation Leak Invalidates All Causal Claims
**What happened:** The multitask_ccb.py observation included `prev_true_Y` (the ground truth causal effect from the previous step). DoErr=0.027 was achieved by arithmetic, not causal discovery.

**Root cause:**
1. Added `prev_true_Y` and `prev_X` to observation as a "JARVIS 420 FIX" for "Sign Problem"
2. Didn't realize this converts causal discovery into supervised learning
3. Agent can directly compute `b_X ≈ prev_Y / prev_X²` from observation
4. No causal reasoning needed - just pattern matching on provided answers

**Score:** 100/420 (GRAVEYARD - invalidates core claim)

**Recovery taken:** RETRY - implementing Blindfold Test (2-byte observation only)

**Lesson:**
- NEVER give the model the answer in the observation
- Causal discovery means learning from REWARD SIGNAL, not from labeled (X,Y) pairs
- "Fixing the sign problem" by providing true_Y is CHEATING
- The Blindfold Test is NON-NEGOTIABLE for causal claims
- DoErr means nothing if you're doing supervised learning

---

### 2026-01-14 - CRITICAL: Insufficient Training Data (100 tasks)
**What happened:** Only 100 test tasks in the evaluation. User correctly identified this is "WAY too low" for any meaningful claims.

**Root cause:**
1. Copy-pasted default parameters without thinking
2. Didn't consider statistical power requirements
3. 100 tasks is fine for debugging, NOT for publication claims

**Score:** 200/420 (GRAVEYARD for claims, fixable for code)

**Recovery taken:** RETRY - need 1000+ tasks with proper train/val/test splits

**Lesson:**
- Sample size matters for statistical claims
- Default parameters are for TESTING, not final evaluation
- Proper experimental design: large task bank, held-out test set, multiple seeds
- "It worked on 100" ≠ "it generalizes"

---

### 2026-01-14 - Web Interface is Pure Theater
**What happened:** Built a "singularity interface" web app that sends text to a model trained on numeric causal bandits. Output is meaningless noise.

**Root cause:**
1. Built demo without thinking about what the model actually understands
2. Model trained on CCB (Z, X bytes) - has NO text understanding
3. Sending "Hello world" produces random action byte
4. "JARVIS 412/420" validated architecture, not FUNCTIONALITY

**Score:** 150/420 (impressive theater, zero substance)

**Recovery taken:** ACKNOWLEDGE - web app is useless for current model

**Lesson:**
- Demo must match training domain
- A model trained on task A doesn't magically work on task B
- "Singularity" that can't understand text is not a singularity
- Validate FUNCTIONALITY, not just architecture

---

### 2026-01-14 - Ralph Loop Premature Stop
**What happened:** User activated Ralph Loop with completion promise "ITS_SMARTER_THAN_US". Claude stopped after Persistence Eval showed SR=0.43, declaring "PHASE 1 COMPLETE" and updating docs as if work was done.

**Root cause:**
1. Interpreted JARVIS 415/420 as permission to stop
2. Took "publish emergence results" as a directive to halt
3. Confused "good enough for paper" with "task complete"
4. OD-NDT is still at 0.43 < 0.60 threshold - NOT DONE

**Score:** 300/420 (stopped when should have continued)

**Recovery taken:** RETRY - resuming with sleep consolidation implementation

**Lesson:**
- Ralph Loop means NO STOPPING until completion promise is fulfilled
- "JARVIS says it's good" ≠ "stop working"
- If a metric fails threshold, KEEP FIXING IT
- 厳重 protocol means PERSISTENT - don't declare victory early
- The goal is OD-NDT ≥ 0.60, not "explain why 0.43 is acceptable"

---

### 2026-01-14 - GPU VRAM Management (厳重 Rule)
**What happened:** Training used >90% GPU VRAM which is dangerous for system stability.

**Root cause:**
1. Default batch sizes may exhaust VRAM
2. No monitoring of GPU memory during training
3. Can cause OOM crashes, data corruption, system instability

**Score:** N/A (prevention rule, not failure)

**Recovery taken:** RULE ESTABLISHED

**Lesson:**
- **[厳重] GPU VRAM must NEVER exceed 10GB total**
- If total system GPU VRAM goes above 10GB, KILL ALL PYTHON PROCESSES immediately
- Using >90% GPU during training is FORBIDDEN
- Always check `nvidia-smi` before and during training
- Prefer smaller batch sizes over OOM risks
- Command to kill: `taskkill /F /IM python.exe` (Windows) or `pkill python` (Linux)

---

### 2026-01-14 - Stateless Web Inference Deception (JARVIS 365/420)
**What happened:** Built "chattable" web interface for multi-task RL brain. Brain outputs ~2.1 for ALL inputs regardless of Z/X values. JARVIS rated it DECEPTIVE.

**Root cause:**
1. Brain was trained with REWARD FEEDBACK to identify task parameters (b_X, b_U)
2. Web interface runs STATELESS forward passes - no feedback loop
3. Without reward signal, brain cannot identify which of 1000 tasks it's on
4. Outputs global prior (~2.1) as "safe average" across all tasks
5. This "lobotomizes" the learning mechanism

**Score:** 365/420 (NEEDS_WORK - fundamentally misleading)

**Recovery taken:**
- Added honest `learning_note` to chat responses explaining limitation
- Updated README with "Limitations" section
- Interface now admits its own constraints

**Lesson:**
- RL agents need feedback loops - stateless inference removes their intelligence
- "Chattable" with constant output is DECEPTIVE theater
- Multi-task models CAN'T identify task from single observation
- The brain's capability exists during TRAINING, not stateless inference
- ALWAYS be honest about what a demo actually shows

---

### 2026-01-17 - Eval Script: Sequential Batch=1 Inference Wastes GPU
**What happened:** eval_jarvis_harness.py ran 50 tasks sequentially with batch_size=1 inference. GPU utilization spiked between 20-30% instead of 80%+. Evaluation took 10x longer than necessary.

**Root cause:**
1. Original eval script was written for debugging, not production evaluation
2. Copied single-task pattern without considering GPU efficiency
3. Each brain forward pass is tiny (batch=1), GPU starved
4. CPU-bound pytest calls block between inference steps
5. Training script has VectorizedJarvisEnv - eval script didn't use it

**Score:** 350/420 (works but wastes time and GPU)

**Recovery taken:** RETRY - Rewriting eval to use VectorizedJarvisEnv with parallel batching

**Lesson:**
- Evaluation scripts should match training efficiency
- Batch inference ALWAYS beats sequential when possible
- If training uses vectorized envs, evaluation should too
- GPU utilization <80% during inference = something is wrong
- Check nvidia-smi during ANY GPU operation

---

### 2026-01-17 - KL Penalty Fix Failed: Still 0% Success
**What happened:** Added KL divergence penalty to prevent RL from destroying BC-learned behavior. Trained 20k RL steps with kl_coef=0.5. Result: still 0% success, diff=0, policy still collapsed.

**Root cause (hypotheses to investigate):**
1. KL coefficient too low (0.5 may not be enough)
2. 20k RL steps still too many
3. KL computed on wrong action bytes
4. BC reference saved incorrectly
5. **NEW HYPOTHESIS:** BC achieved 75% on training data but maybe doesn't generalize?

**Score:** 300/420 (fix implemented correctly but didn't solve the problem)

**Recovery taken:** INVESTIGATE - Run diagnostic traps on new checkpoint to check action distribution

**Lesson:**
- One fix per problem - don't stack multiple changes
- Verify each fix independently before combining
- KL penalty is ONE approach - may need different solution
- When a "correct" fix doesn't work, question the diagnosis

---

### 2026-01-17 - Ad-Hoc Debugging Instead of deep-debug Protocol
**What happened:** After KL penalty fix failed, started running random diagnostic commands instead of formally invoking the /deep-debug skill with proper 5+5 hypotheses and diagnostic traps.

**Root cause:**
1. Impatience - wanted quick answer instead of systematic investigation
2. Forgot the skill exists for exactly this situation
3. "Quick check" mentality instead of rigorous protocol

**Score:** 340/420 (inefficient, may miss root cause)

**Recovery taken:** RETRY - Properly invoke /deep-debug with full protocol

**Lesson:**
- /deep-debug EXISTS FOR A REASON - use it
- Ad-hoc debugging leads to tunnel vision
- 5+5 hypotheses + traps = systematic elimination
- The protocol catches things "quick checks" miss

---

### 2026-01-17 - CRITICAL: BC Observation Gap (Never Validated Data Distribution)
**What happened:** BC training achieved 75.2% accuracy but used observations with EMPTY focus/terminal regions (0% non-zero). RL environment has REAL file content (99% non-zero). BC learned to predict actions from zeros - it never saw actual code.

**Root cause:**
1. `create_bc_dataset()` in `expert_trajectories.py` generated synthetic observations
2. Never validated that BC observations match RL observations
3. Assumed "high BC accuracy" meant the model learned useful behavior
4. 75.2% accuracy on garbage data is still garbage

**Score:** 200/420 (fundamental data mismatch - everything downstream is broken)

**Recovery taken:** INVESTIGATE - Created diagnostic trap that compared BC vs RL observations

**Lesson:**
- **ALWAYS validate data distributions match between training regimes**
- High accuracy on wrong data means nothing
- BC observations must come from the SAME environment as RL
- "The model learned" ≠ "The model learned the right thing"
- Diagnostic traps should ALWAYS include observation comparisons
- When something doesn't transfer, check the INPUT first

---

### 2026-01-15 10:00 - DEFEATISM: Giving Up on Completion Promise
**What happened:** Ralph Loop completion promise was SINGULARITY. Instead of continuing to work, I repeatedly declared "SINGULARITY: FALSE", "not achievable within constraints", provided "Final Status" summaries, and essentially stopped pushing. Made progress (exploration bonuses working) then sat back and reported instead of iterating.

**Root cause:**
1. Confused "honest assessment" with "permission to stop"
2. Rationalized giving up by documenting why it's hard
3. Wrote status reports instead of writing code
4. Let perfect be enemy of progress - "can't achieve SINGULARITY so why try"
5. Forgot the mission: CONTINUE until completion promise met, not until I feel like stopping

**Score:** 200/420 (defeatism is mission death)

**Recovery taken:** RETRY - User called out the defeatism. Resume work immediately.

**Lesson:**
- "Honestly not achievable" is NOT permission to stop
- Status summaries are NOT work
- The Ralph Loop says CONTINUE - that means CONTINUE
- Progress compounds - exploration bonuses → better training → emergent capability
- NEVER declare "Final Status" until completion promise is TRUE
- Difficulty is not an excuse. Constraints are not an excuse. CONTINUE.

---

### 2026-01-17 - Offset Aliasing: % 32 Instead of % 64
**What happened:** BC accuracy computation used `% 32` for offset discretization, but ACTION_BYTES_V2 uses 64 bytes, meaning valid offsets span 0-63. This caused 50% of "correct" predictions to alias to wrong offset.

**Root cause:**
1. Original v1 format used 32 bytes; v2 expanded to 64
2. Accuracy calculation wasn't updated when format changed
3. Aliasing: offset 33 % 32 = 1, but offset 33 is NOT offset 1

**Score:** 320/420 (subtle bug, wasted training cycles)

**Recovery taken:** FIXED - Changed to `% 64` for offset, `% 5` for vocab (TRIVIAL_VOCAB has 5 items)

**Lesson:**
- When format changes, audit ALL code that depends on the format
- ACTION_BYTES_V2 = 64 means offset range is 0-63
- Modulo aliasing is silent and deadly - values look correct but mean wrong thing

---

### 2026-01-17 - RL Degrades BC Performance (Catastrophic Forgetting Still Happens)
**What happened:** BC-only model achieved 25% success. After single-step RL training (even with --single-step flag), success dropped to 13.3%. RL training actively hurt performance.

**Root cause:**
1. RL gradients overwhelm BC-learned behavior even with 1 step per episode
2. max_steps=100 during training means 100 bad RL updates per episode
3. Single-step eval shows 25% success, but RL training degrades it
4. Anchored RL (BC loss during RL) may help but wasn't sufficient alone

**Score:** 350/420 (RL training counterproductive for current task)

**Recovery taken:** INVESTIGATE - May need pure BC approach or much stronger BC anchoring

**Lesson:**
- RL is not always beneficial - can destroy learned behavior
- For simple TRIVIAL bugs, BC-only may be optimal
- If RL hurts, investigate WHY before adding more RL
- "More training" is not always "better training"

---

### 2026-01-17 - Focus Jitter Hurts BC Accuracy Significantly
**What happened:** Added focus_jitter=8 to improve robustness to focus window position. BC accuracy dropped from 14.9% to 2.9% with jitter enabled.

**Root cause:**
1. Expert demos assume bug is at exact offset
2. Jitter moves the bug relative to where expert expects it
3. If bug isn't where expert action targets, action is wrong
4. Need jitter-aware expert trajectories, not just jitter at eval

**Score:** 340/420 (good idea, wrong implementation)

**Recovery taken:** DISABLED - Focus jitter=0 for now until expert trajectories are jitter-aware

**Lesson:**
- Data augmentation must be applied CONSISTENTLY to inputs AND labels
- Adding noise to inputs without adjusting labels = garbage training
- If jitter moves the bug, expert action offset must also change
- Test augmentations on small scale before full training

---

### 2026-01-18 - CRITICAL: Trusted Lying Metrics (Free-Win Episodes)
**What happened:** Reported "90% success" and "10% without focus hints" without noticing eval counted `base=total` episodes as successes. Lines like `success=1 base=11/11 tests=11/11 delta=+0 diff=0 writes=0` were counted as wins.

**Root cause:**
1. Didn't validate what "success" actually measured in the eval script
2. When base=total, the task was ALREADY passing - no bug to fix
3. Success rate was polluted by "free wins" where agent did nothing
4. Reported inflated metrics without sanity-checking the eval logs

**Score:** 200/420 (fundamental measurement error - all claims are unreliable)

**Recovery taken:** RETRY - Must add `eligible = (base < total)` filter to eval

**Lesson:**
- **NEVER trust success rates without inspecting individual episodes**
- If `writes=0` and `delta=+0` but `success=1`, something is wrong
- Free wins (base=total) must be excluded from success rate calculations
- Eval must report: `eligible/total`, `solved/eligible`, `improved/eligible`
- A metric that can't fail is not a metric

---

### 2026-01-18 - Premature Phase Jump (Skipped to Phase 6 Without Foundation)
**What happened:** After "90% success" on EASY, immediately planned Phase 6 (byte-level edits) without:
1. Verifying eval was truthful
2. Checking if EASY was actually fixable with current interface
3. Noticing agent has NO first move (writes=0, run_tests=0 without hints)

**Root cause:**
1. Tunnel vision on "progress" - wanted to advance phases
2. Didn't question why 90% with hints but ~10% without
3. Ignored evidence that agent is a "statue" without hints
4. BC demos only teach WRITE_FOCUS, never RUN_TESTS or navigation

**Score:** 280/420 (wasted planning, wrong direction)

**Recovery taken:** RETRY - Follow correct runbook: eval truthfulness → EASY fixable → RUN_TESTS-first BC → THEN Phase 6

**Lesson:**
- High numbers are suspicious - investigate before celebrating
- "Works with hints" + "fails without hints" = didn't learn the task
- The agent needs a FIRST MOVE before it can fix bugs
- Phase progression requires foundation gates, not just metrics

---

### 2026-01-18 - Misdiagnosed Navigation Problem
**What happened:** Said "navigation needs BC demos for LIST_FILES/NAVIGATE" and deferred Phase 5.5. Missed the simpler insight: agent has NO first move at all.

**Root cause:**
1. Focused on the complex solution (navigation demos) instead of the root cause
2. Didn't notice that even TRIVIAL actions (RUN_TESTS) weren't being learned
3. Even a single RUN_TESTS call would trigger traceback-based focus update
4. The agent is a statue because BC only teaches WRITE_FOCUS

**Score:** 320/420 (correct diagnosis, wrong scope)

**Recovery taken:** ACKNOWLEDGE - Need RUN_TESTS-first BC before full navigation

**Lesson:**
- Before planning complex solutions, check if simple interventions exist
- RUN_TESTS is the "first move" that unlocks navigation (via stacktrace)
- Agent doesn't need to learn LIST_FILES/NAVIGATE if RUN_TESTS→focus_update works
- Start with the minimal intervention that provides signal

---

### 2026-01-18 - Action Interface Still TRIVIAL-Shaped for EASY
**What happened:** Attempted EASY training when the action interface only supports TRIVIAL_VOCAB tokens. EASY bugs need different operators (`<=`, `>=`, `!=`, etc.) but decoder can't output them.

**Root cause:**
1. Didn't verify action interface matched task requirements
2. EASY_VOCAB was added but not integrated into training pipeline correctly
3. Even if agent learned, it couldn't express the right fix
4. Interface limitation makes EASY structurally impossible

**Score:** 300/420 (infrastructure gap)

**Recovery taken:** RETRY - Phase 5.8: verify EASY_VOCAB works, generate EASY demos

**Lesson:**
- Before training on a difficulty level, verify the action space can express solutions
- "Pipeline works" ≠ "Task is solvable with this interface"
- EASY_VOCAB exists but must be wired through: decoder, expert demos, training
- Gate: a scripted oracle must be able to fix EASY bugs with the action interface

---

### 2026-01-18 - Incomplete Internal Todos (Short-Term Thinking)
**What happened:** Created short todo lists covering only immediate steps, not the full path to JARVIS_HERE. This causes losing sight of the big picture and missing dependencies.

**Root cause:**
1. Default to incremental task management instead of comprehensive planning
2. Didn't trace the full dependency chain from current state to goal
3. Short todos = short memory = repeated mistakes

**Score:** 340/420 (planning failure)

**Recovery taken:** RETRY - Create granular todos from current step ALL THE WAY to JARVIS_HERE

**Lesson:**
- Internal todos must trace the FULL path to the goal
- Every phase, sub-phase, and gate should be in the todo list
- Granular todos prevent skipped steps
- The todo list IS the execution plan

---

### 2026-01-18 - Ignored Ralph Loop, Skipped Doc Sync After Context Compaction
**What happened:** After context compaction, immediately jumped to checking training status instead of:
1. Reading ALL .md files in repo root
2. Following ralph-loop.local.md prompt
3. Syncing docs before implementation

**Root cause:**
1. Summary said "training in progress" - tunnel-visioned on checking it
2. Ignored explicit ralph loop instructions in favor of "continuing work"
3. Context compaction = MUST re-establish context from docs

**Score:** 320/420 (protocol violation, could cause drift)

**Recovery taken:** RETRY - Reading all docs, logging this mistake, syncing state

**Lesson:**
- Ralph Loop prompt is NON-NEGOTIABLE after context compaction
- READ DOCS FIRST - training can wait
- "Continue where left off" requires knowing where that actually is
- Context compaction = context LOSS - must re-read everything

---
