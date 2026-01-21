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

## 2026-01-19 - Deep-Debug Should Have Been Used Earlier

**What happened:**
Spent significant time running training with `--single-step` flag combined with `--bc-sequential`, which is fundamentally incompatible. The policy collapsed to 96.7% WRITE_FOCUS.

**Root cause:**
Did not apply the deep-debug protocol early enough. Instead of hypothesizing and testing, I ran multiple training attempts hoping the issue would resolve itself.

**The triple mismatch discovered via DEEP-DEBUG:**
1. Single-step mismatch: BC teaches 4-step sequences, RL only allows 1 step
2. Reward asymmetry: WRITE_FOCUS has dense reward, RUN_TESTS is sparse in single-step
3. Observation shift: BC step 1 has 83% filled obs vs step 0's 13% - RL never reaches step 1

**Lesson learned:**
- USE DEEP-DEBUG MUCH MORE, EARLIER in the debugging process
- When a training run shows unexpected behavior, don't retry with minor tweaks
- Create diagnostic traps to isolate hypotheses before running expensive training
- The DEEP-DEBUG protocol would have identified the root cause in minutes, not hours

---

### 2026-01-19 - CRITICAL: vocab_class_loss on Garbage Targets (75% of Samples)

**What happened:**
Added VocabClassificationHead to improve TRIVIAL_VOCAB token prediction. Applied vocab_class_loss to ALL BC samples. Result: model collapsed to 82% RUN_TESTS, SOLVED rate dropped from 23% to 12%.

**Root cause:**
1. vocab_class_loss used `target_actions[:, 25]` as the target (vocab_idx byte)
2. Byte 25 ONLY has meaning for WRITE_FOCUS actions (action_type == 16)
3. For RUN_TESTS (type 3) and COMPLETE_TASK (type 5), byte 25 is GARBAGE
4. BC distribution: ~50% RUN_TESTS, ~25% WRITE_FOCUS, ~25% COMPLETE_TASK
5. Training vocab loss on 75% garbage targets taught the model nonsense
6. Model learned to spam RUN_TESTS to minimize the garbage loss

**Score:** 250/420 (GRAVEYARD - actively hurt the model)

**Recovery taken:** FIXED - Added mask to only compute vocab_class_loss when action_type == 16

**Lesson:**
- When adding auxiliary losses, verify the TARGET is meaningful for ALL samples
- For action-byte losses, ALWAYS check which action types the byte applies to
- Action encoding: byte 0 = action_type, byte 1 = offset, byte 25 = vocab_idx (WRITE_FOCUS ONLY)
- A "helpful" auxiliary loss can DESTROY performance if applied to wrong data

---

### 2026-01-19 - Resumed Training Without BC Anchor (Policy Drift)

**What happened:**
After fixing vocab_class_loss masking, resumed training from a checkpoint. Training showed balanced action distribution (33% each for RT/WF/CT). But eval showed 0% SOLVED - model either does all-writes OR all-run_tests per episode.

**Root cause:**
1. Resumed training used `--bc-checkpoint` which loaded weights BUT set `bc_anchor_coef=0.0`
2. Without BC anchor during RL, policy drifted away from expert behavior
3. Balanced training distribution doesn't guarantee useful policy
4. The model learned something, but not the correct state→action mapping

**Score:** 300/420 (training was pointless - no BC anchor = no learning signal preservation)

**Recovery taken:** RETRY - Fresh training with `--bc-anchor-coef 0.1` explicitly set

**Lesson:**
- When resuming training, VERIFY all critical hyperparameters are preserved
- BC anchor is ESSENTIAL during RL for TRIVIAL tasks (sparse reward)
- Balanced action distribution ≠ correct policy
- Always check the training log for "bc_anchor_coef" when debugging RL issues

---

### 2026-01-19 - CRITICAL: "Lying Environment" Bug (PPO Sees Wrong Action-Reward Pairs)

**What happened:**
With env-side `--force-write-focus`, model trained to output 80% RUN_TESTS but eval showed 0% SOLVED. JARVIS Oracle diagnosed the root cause: PPO buffer recorded (original_action, forced_reward), creating a fundamental train/eval mismatch.

**Root cause:**
1. Agent outputs RUN_TESTS (Action 3)
2. Environment secretly swaps to WRITE_FOCUS (Action 16) and returns positive reward
3. PPO Buffer records: (Action=3, Reward=+1) ← **THE BUG**
4. Gradient update MAXIMIZES probability of RUN_TESTS (wrong!)
5. Result: Model outputs 80% RUN_TESTS, 15% WRITE_FOCUS during training
6. At eval WITHOUT forcing: Model outputs RUN_TESTS only, never writes code

**The fix (Upstream Teacher Forcing):**
```python
# BEFORE storing to PPO buffer:
if self.upstream_teacher_forcing and random.random() < self.force_write_focus_prob:
    action_to_store[:, 0] = 16  # Force WRITE_FOCUS
    # Recompute log_prob for forced action
    forced_log_prob = self.brain.action_decoder.get_log_prob(h_t, action_to_store, ...)
    log_prob_to_store = forced_log_prob
# Now PPO sees (forced_action, forced_log_prob, forced_reward) ← CORRECT
```

**Score:** 200/420 (GRAVEYARD - fundamental RL bug, wasted multiple training runs)

**Recovery taken:** RETRY - Implemented upstream teacher forcing with calibrated probability

**Lesson:**
- **NEVER let environment silently transform actions** - PPO must see what actually happened
- If you force an action, the forcing must happen BEFORE storing to PPO buffer
- The action and log_prob stored must MATCH what the environment actually executes
- "Forcing" that happens in env is LYING - PPO learns wrong associations
- When debugging RL, trace the full path: model output → buffer storage → gradient update

---

### 2026-01-20 - CRITICAL: Trained with --single-step But Evaluated Multi-Step

**What happened:**
Fix 10 (Corrective Imitation) showed excellent training metrics - WF chosen rate went from 14% → 41%, CI mismatch dropped from 86% → 40%. But evaluation showed 0% SOLVED because training used `--single-step` flag. Model learned to write OR run_tests, but not the sequence: write → run_tests → verify.

**Root cause:**
1. Training with `--single-step` teaches single-action behavior only
2. Model learned to output WRITE_FOCUS correctly when it saw a bug
3. But it never learned to RUN_TESTS after writing to verify the fix
4. Episodes in eval hit action_limit with either writes=5/run_tests=0 OR writes=0/run_tests=5
5. Model learned two "modes" not a coherent workflow

**Score:** 300/420 (correct approach, wrong hyperparameter - wasted training cycle)

**Recovery taken:** RETRY - Running training WITHOUT `--single-step` to teach full sequence

**Lesson:**
- **Eval settings must match training settings** - if you train single-step, you can't expect multi-step behavior
- Before running long training, verify the task structure matches desired eval behavior
- Single-step training teaches "what action to take" but NOT "when to sequence actions"
- For TRIVIAL bugs: need the loop WRITE → RUN_TESTS → (if pass) COMPLETE_TASK
- The CI approach works - but only teaches action SELECTION, not action SEQUENCING

---

### 2026-01-20 - Fix 10 Multi-Step Training with --force-write-focus Still Has h_t Mismatch

**What happened:**
Fix 10 multi-step training showed good metrics: WF chosen 25%, RT 62% during training. But eval showed WF 6.7%, RT 100%. Model spammed RUN_TESTS at eval, rarely writing.

**Root cause:**
1. Training used `--force-write-focus` which forces env to execute WRITE_FOCUS
2. CI loss teaches "output WRITE_FOCUS when oracle says so" - this worked
3. BUT the h_t trajectory during training was based on forced WRITE_FOCUS actions
4. At eval: no forcing → model outputs RUN_TESTS → different h_t → model keeps outputting RT
5. The train/eval h_t mismatch persists even with CI because forcing still happens

**Score:** 320/420 (CI works but --force-write-focus invalidates h_t trajectory)

**Recovery taken:** RETRY - Train without --force-write-focus. Let CI correct the model on its natural trajectory.

**Lesson:**
- **CI needs to operate on the model's natural h_t trajectory**
- If you force actions, CI learns "correct action GIVEN forced h_t" not "correct action GIVEN my h_t"
- The fix: Remove --force-write-focus entirely, let model explore, use CI to correct
- This is the same train/eval h_t mismatch that killed Fix 5-9 - forcing is the root cause

---

### 2026-01-20 - Fix 10b: Pure CI Alone Doesn't Transfer to Eval

**What happened:**
Fix 10b (pure CI, no --force-write-focus) showed excellent training metrics: WF 26%, RT 52%, CI mismatch dropping from 77% → 52%. But eval showed 0% writes and 100% RUN_TESTS in ALL 30 episodes.

**Root cause:**
1. CI teaches the model "output WRITE_FOCUS when oracle says so" during training
2. But at eval, the model starts with initial h_t and outputs RUN_TESTS
3. Once it outputs RUN_TESTS, h_t evolves into "RT mode" - an attractor state
4. The model never escapes the RT attractor because CI only provides supervision, no penalty for bad behavior
5. Training exploration (CI loss) happens, but the RL reward signal for RT is not sufficiently negative
6. RUN_TESTS gives small positive reward (seeing test output), creating a local optimum

**Score:** 300/420 (correct approach but missing negative signal for RT spam)

**Recovery taken:** RETRY - Fix 10c: Add RT streak penalty (-0.1 per RT after 2 consecutive)

**Lesson:**
- **CI provides positive guidance but no negative signal for exploitable behaviors**
- If an action has a local positive reward (RT shows test results), agent may spam it
- Need explicit penalty to break RT attractor: "after 2 consecutive RTs, penalty kicks in"
- The combination CI + RT penalty should work: CI teaches what to do, penalty teaches what NOT to do
- Pure supervised learning (CI) isn't enough when RL rewards create attractors

---

### 2026-01-21 - CRITICAL: Environment Checkpoint Violation (Used Wrong Python)

**What happened:**
Ran `nvidia-smi` and saw GPU available. Ran `python3 --version` and saw Python 3.12.3. Assumed CUDA was available. Started training - it ran on CPU with 0% GPU utilization.

**Root cause:**
1. `nvidia-smi` shows GPU exists but doesn't verify PyTorch can use it
2. System `python3` is NOT the venv Python with CUDA-enabled PyTorch
3. Should have run `python3 -c "import torch; print(torch.cuda.is_available())"`
4. **Violated ENVIRONMENT CHECKPOINT protocol** - checked hardware but not software

**Score:** 200/420 (L100 violation - wasted time, wrong environment)

**Recovery taken:** ABORT - Kill CPU training, use correct venv Python

**Lesson:**
- **ENVIRONMENT CHECKPOINT must verify CUDA IN PYTHON, not just nvidia-smi**
- The command is: `.venv/bin/python -c "import torch; print(torch.cuda.is_available())"`
- If CUDA=False, training WILL run on CPU and waste time
- "GPU exists" ≠ "PyTorch can use GPU"
- Always use `.venv/bin/python` not system `python3`

---

### 2026-01-21 - CRITICAL: No First Output After 7+ Minutes (Silent Training)

**What happened:**
Started self-paced smoke test. GPU showed 99% utilization. Waited 7+ minutes for first log output. Never came. Training was either stuck or output was completely buffered with no feedback.

**Root cause:**
1. Python stdout is BLOCK-BUFFERED when redirected to file (not line-buffered)
2. Did not use `python -u` for unbuffered output
3. Did not set a timeout for first output (should be <30 seconds)
4. Assumed "GPU busy = training working" without verifying output
5. v2 harness with pytest calls is SLOW - but 7 minutes for first output is unacceptable

**Score:** 150/420 (L100 violation - wasted 7+ minutes of GPU time without feedback)

**Recovery taken:** ABORT - Kill training, fix output buffering

**Lesson:**
- **ALWAYS use `python -u` for unbuffered output during training**
- **First log output MUST appear within 30 seconds** - if not, something is wrong
- **Set explicit timeout**: `timeout 60 python -u script.py || echo "STUCK"`
- "GPU busy" does NOT mean "training is progressing correctly"
- Silent training = blind training = waste of resources
- The command should be: `PYTHONPATH=. .venv/bin/python -u scripts/train_jarvis_harness.py ...`

---

### 2026-01-21 - CRITICAL: GPU Burn Same-Stream Blocking Caused 30x Slowdown

**What happened:**
Self-paced training hung after "Patience episodes: 1" with no output. Deep-debug found that `collect_rollout()` took 16.3s when it should take 0.5s - a 30x slowdown.

**Root cause:**
GPU burn in `collect_rollout()` queued 2000+ matmuls on the default CUDA stream BEFORE the brain forward pass:
```python
# Lines 1162-1164: Queue 10 burns before reset
for _ in range(10):
    self._gpu_burn(sync=False)  # 10 * 100 = 1000 matmuls

# Lines 1171-1172: Queue 10 MORE burns after reset
for _ in range(10):
    self._gpu_burn(sync=False)  # Another 1000 matmuls

# Line 1182: Brain forward - BLOCKS waiting for 2000 matmuls!
output = self.brain(obs, h, g, a_prev, training=True)
```

Even though `sync=False`, all ops on the same CUDA stream are serialized. The brain forward pass had to wait for 10+ seconds of GPU burn garbage math to complete first.

**Score:** 420/420 diagnosis (JARVIS confirmed)

**Recovery taken:** FIXED - Removed all GPU burns from `collect_rollout()`. Result: 74x speedup (16.3s → 0.22s).

**Lesson:**
- **GPU "async" operations are only async to the CPU, not to each other on the same stream**
- **Burns intended to "keep GPU busy during CPU ops" actually BLOCK subsequent GPU ops**
- With `async_tests=True`, env ops are already fast - burns solve a non-problem while creating a real one
- **Before adding GPU optimization hacks, verify they actually help** - don't assume
- The intention (keep GPU utilization high) was good, but the implementation (same-stream burn) was catastrophic
- **Deep-debug diagnostic traps are invaluable** - trap #6 (manual rollouts) vs trap #7 (trainer rollouts) isolated the exact cause

