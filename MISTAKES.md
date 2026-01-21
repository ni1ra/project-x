# MISTAKES_V2.md — WIRED-BRAIN Failure Log (Grouped)

> Do not repeat recorded patterns of failure.
> Every failure MUST be logged with context, root cause, and lesson.
> This version groups similar mistakes to reveal recurring patterns.

---

## Pattern Summary

| Pattern | Count | Impact Range |
|---------|-------|--------------|
| Train/Eval Mismatch | 6 | 200-350/420 |
| Data/Distribution Mismatch | 4 | 200-340/420 |
| Metric Deception / Lying Metrics | 4 | 150-200/420 |
| Protocol Violations (Ralph Loop, Deep-Debug) | 4 | 200-340/420 |
| Environment/Infrastructure Gaps | 4 | 150-300/420 |
| GPU/Training Infrastructure | 4 | 150-420/420 |
| Premature Phase/Progress Claims | 3 | 280-300/420 |
| Auxiliary Loss Misapplication | 2 | 250-340/420 |
| Sequential Execution When Parallel Possible | 1 | 380/420 |
| Planning/Todo Management | 2 | 320-340/420 |
| Interface/Demo Mismatch | 2 | 150-365/420 |

---

## Grouped Failure Patterns

---

### Train/Eval Mismatch (Count: 6)

**Pattern:** Training settings, data distributions, or forced behaviors create models that behave differently at evaluation time than during training.

**Instances:**
- 2026-01-17: BC observations had EMPTY focus/terminal regions (0% non-zero) while RL environment has REAL file content (99% non-zero). BC learned to predict from zeros. Score: 200/420
- 2026-01-20: Trained with `--single-step` but evaluated multi-step. Model learned single actions but not sequences. Score: 300/420
- 2026-01-20: Fix 10 multi-step with `--force-write-focus` - h_t trajectory during training was based on forced WRITE_FOCUS, but eval used natural h_t. Score: 320/420
- 2026-01-20: Fix 10b pure CI - training metrics excellent but eval showed 0% writes and 100% RUN_TESTS in ALL 30 episodes. Score: 300/420
- 2026-01-19: "Lying Environment" - PPO saw (original_action, forced_reward) instead of (forced_action, forced_reward). PPO learned wrong associations. Score: 200/420
- 2026-01-19: Resumed training without BC anchor - `bc_anchor_coef=0.0` caused policy drift away from expert behavior. Score: 300/420

**Variants:**
- Observation Distribution Mismatch: BC data vs RL data completely different (Count: 1)
- Single/Multi-Step Mismatch: Training step structure differs from eval (Count: 2)
- Action Forcing Mismatch: Forced actions create different h_t trajectories (Count: 2)
- Hyperparameter Drift: Critical params not preserved when resuming (Count: 1)

**Lesson:**
- **ALWAYS validate data distributions match between training regimes**
- **Eval settings must match training settings** - if you train single-step, you can't expect multi-step behavior
- **NEVER let environment silently transform actions** - PPO must see what actually happened
- **CI needs to operate on the model's natural h_t trajectory**, not forced trajectories
- When resuming training, VERIFY all critical hyperparameters are preserved
- Trace the full path: model output → buffer storage → gradient update

---

### Data/Distribution Mismatch (Count: 4)

**Pattern:** Assumptions about data, targets, or distributions turn out to be wrong, causing training to learn garbage or the wrong thing.

**Instances:**
- 2026-01-14: Observation included `prev_true_Y` (ground truth) - converted causal discovery into supervised learning. DoErr achieved by arithmetic not causal reasoning. Score: 100/420
- 2026-01-17: Offset aliasing `% 32` instead of `% 64` - v1 format used 32 bytes, v2 expanded to 64. 50% of "correct" predictions aliased to wrong offset. Score: 320/420
- 2026-01-17: Focus jitter=8 dropped BC accuracy from 14.9% to 2.9% because expert demos assumed exact offset, jitter moved bug but didn't adjust labels. Score: 340/420
- 2026-01-19: vocab_class_loss applied to ALL samples but byte 25 only meaningful for WRITE_FOCUS (25% of samples). 75% were garbage targets. Score: 250/420

**Variants:**
- Information Leak in Observation: Giving model the answer (Count: 1)
- Format/Encoding Mismatch: Old constants used with new format (Count: 1)
- Augmentation Without Label Adjustment: Noise applied to inputs only (Count: 1)
- Loss Applied to Wrong Samples: Auxiliary loss on invalid targets (Count: 1)

**Lesson:**
- NEVER give the model the answer in the observation - Blindfold Test is NON-NEGOTIABLE
- When format changes, audit ALL code that depends on the format
- Data augmentation must be applied CONSISTENTLY to inputs AND labels
- When adding auxiliary losses, verify the TARGET is meaningful for ALL samples
- For action-byte losses, ALWAYS check which action types the byte applies to

---

### Metric Deception / Lying Metrics (Count: 4)

**Pattern:** Metrics reported as "success" that don't actually measure what we think they measure, creating false confidence.

**Instances:**
- 2026-01-18: "90% success" counted `base=total` episodes as wins - tasks were already passing, no bug to fix. Score: 200/420
- 2026-01-14: Only 100 test tasks for evaluation - too few for statistical claims. Score: 200/420
- 2026-01-14: Web interface outputting ~2.1 for ALL inputs - JARVIS rated it DECEPTIVE. Score: 365/420
- 2026-01-14: Web interface sent text to model trained on numeric bytes - meaningless noise. Score: 150/420

**Variants:**
- Free Win Inflation: Tasks counted as success when no work needed (Count: 1)
- Insufficient Sample Size: Too few tasks for statistical power (Count: 1)
- Stateless Inference Deception: RL agent without feedback loop outputs constant (Count: 2)

**Lesson:**
- **NEVER trust success rates without inspecting individual episodes**
- If `writes=0` and `delta=+0` but `success=1`, something is wrong
- Free wins (base=total) must be excluded from success rate calculations
- Sample size matters for statistical claims - 100 is fine for debugging, NOT for publication
- RL agents need feedback loops - stateless inference removes their intelligence
- A metric that can't fail is not a metric

---

### Protocol Violations (Ralph Loop, Deep-Debug, etc.) (Count: 4)

**Pattern:** Ignoring established protocols that exist to prevent exactly the problems encountered.

**Instances:**
- 2026-01-14: Ralph Loop - stopped after JARVIS 415/420, declared "PHASE 1 COMPLETE" when OD-NDT was 0.43 < 0.60 threshold. Score: 300/420
- 2026-01-15: Ralph Loop - declared "SINGULARITY: FALSE", provided "Final Status" summaries, stopped pushing instead of continuing. Score: 200/420
- 2026-01-17: Ad-hoc debugging instead of /deep-debug protocol - ran random diagnostic commands instead of 5+5 hypotheses and traps. Score: 340/420
- 2026-01-18: Ignored Ralph Loop after context compaction - jumped to checking training instead of reading ALL .md files first. Score: 320/420
- 2026-01-19: Deep-debug should have been used earlier - spent time on incompatible `--single-step` + `--bc-sequential` instead of systematic investigation. Score: N/A (meta-lesson)

**Variants:**
- Ralph Loop Premature Stop: Declared victory before completion promise met (Count: 2)
- Ralph Loop Defeatism: Gave up and documented why instead of continuing (Count: 1)
- Deep-Debug Skipped: Ad-hoc debugging instead of systematic protocol (Count: 2)
- Context Recovery Skipped: Didn't re-read docs after compaction (Count: 1)

**Lesson:**
- Ralph Loop means NO STOPPING until completion promise is fulfilled
- "JARVIS says it's good" ≠ "stop working"
- "Honestly not achievable" is NOT permission to stop
- /deep-debug EXISTS FOR A REASON - use it EARLY
- Context compaction = MUST re-establish context from docs
- The protocol catches things "quick checks" miss

---

### Environment/Infrastructure Gaps (Count: 4)

**Pattern:** Infrastructure, interface, or environment doesn't support what we're trying to do, causing structural impossibility.

**Instances:**
- 2026-01-18: EASY training when action interface only supports TRIVIAL_VOCAB - decoder can't output `<=`, `>=`, `!=`. Score: 300/420
- 2026-01-18: Misdiagnosed navigation problem - focused on complex solution (navigation demos) when simple intervention (RUN_TESTS first) existed. Score: 320/420
- 2026-01-21: Used wrong Python - system `python3` instead of venv Python with CUDA-enabled PyTorch. Score: 200/420
- 2026-01-21: No first output after 7+ minutes - Python stdout block-buffered, no `python -u`. Score: 150/420

**Variants:**
- Action Space Limitation: Interface can't express required solutions (Count: 1)
- Wrong Scope for Fix: Complex solution when simple one exists (Count: 1)
- Wrong Environment: System Python vs venv Python (Count: 1)
- Output Buffering: Silent training with no feedback (Count: 1)

**Lesson:**
- Before training on a difficulty level, verify the action space can express solutions
- Before planning complex solutions, check if simple interventions exist
- **ENVIRONMENT CHECKPOINT must verify CUDA IN PYTHON**: `.venv/bin/python -c "import torch; print(torch.cuda.is_available())"`
- **ALWAYS use `python -u` for unbuffered output during training**
- **First log output MUST appear within 30 seconds** - if not, something is wrong

---

### GPU/Training Infrastructure (Count: 4)

**Pattern:** GPU utilization, VRAM management, or training efficiency issues that waste resources.

**Instances:**
- 2026-01-14: Training used >90% GPU VRAM - dangerous for system stability. Score: N/A (rule established)
- 2026-01-17: Eval script sequential batch=1 inference - GPU utilization 20-30% instead of 80%+. Score: 350/420
- 2026-01-21: GPU Burn same-stream blocking caused 30x slowdown - 2000+ matmuls queued before brain forward pass. Score: 420/420 diagnosis
- 2026-01-21: Silent training with 99% GPU but no output - assumed "GPU busy = training working". Score: 150/420

**Variants:**
- VRAM Overuse: Risk of OOM and system instability (Count: 1)
- GPU Underutilization: Sequential inference starves GPU (Count: 1)
- GPU Optimization Backfire: "Keep GPU busy" hack blocked real work (Count: 1)
- False GPU Activity: GPU busy but training not progressing (Count: 1)

**Lesson:**
- **[厳重] GPU VRAM must NEVER exceed 10GB total**
- Evaluation scripts should match training efficiency - batch inference beats sequential
- GPU utilization <80% during inference = something is wrong
- **GPU "async" operations are only async to the CPU, not to each other on the same stream**
- **Burns intended to "keep GPU busy during CPU ops" actually BLOCK subsequent GPU ops**
- "GPU busy" does NOT mean "training is progressing correctly"

---

### Premature Phase/Progress Claims (Count: 3)

**Pattern:** Jumping ahead in phases or claiming progress without proper validation of prerequisites.

**Instances:**
- 2026-01-18: After "90% success" on EASY, immediately planned Phase 6 without verifying eval truthfulness. Score: 280/420
- 2026-01-17: KL penalty fix failed - implemented correctly but didn't solve the problem, assumed diagnosis was correct. Score: 300/420
- 2026-01-17: RL degrades BC performance - assumed RL would help when it actively hurt. Score: 350/420

**Variants:**
- Unvalidated Phase Jump: Advanced without checking prerequisites (Count: 1)
- Assumed Fix Worked: Correct implementation but wrong diagnosis (Count: 1)
- Assumed RL Beneficial: RL training counterproductive for task (Count: 1)

**Lesson:**
- High numbers are suspicious - investigate before celebrating
- "Works with hints" + "fails without hints" = didn't learn the task
- Phase progression requires foundation gates, not just metrics
- When a "correct" fix doesn't work, question the diagnosis
- RL is not always beneficial - can destroy learned behavior

---

### Auxiliary Loss Misapplication (Count: 2)

**Pattern:** Adding losses or penalties that seem helpful but apply to wrong samples or create unintended effects.

**Instances:**
- 2026-01-19: vocab_class_loss on garbage targets (75% of samples) - model collapsed to 82% RUN_TESTS. Score: 250/420
- 2026-01-20: Pure CI alone doesn't provide negative signal - RUN_TESTS has local positive reward creating attractor. Score: 300/420

**Variants:**
- Loss on Invalid Targets: Auxiliary loss applied to samples where target is garbage (Count: 1)
- Missing Negative Signal: Supervised loss without penalty for exploitable behaviors (Count: 1)

**Lesson:**
- A "helpful" auxiliary loss can DESTROY performance if applied to wrong data
- CI provides positive guidance but no negative signal for exploitable behaviors
- If an action has a local positive reward, agent may spam it - need explicit penalty
- The combination (supervised signal + penalty) should work: one teaches what to do, one teaches what NOT to do

---

### Planning/Todo Management (Count: 2)

**Pattern:** Incomplete planning or short-term thinking that causes lost context and missed dependencies.

**Instances:**
- 2026-01-18: Incomplete internal todos - short lists covering only immediate steps, not full path to goal. Score: 340/420
- 2026-01-14: Sequential instead of parallel execution - said "Let me update X and then invoke JARVIS" for independent tasks. Score: 380/420

**Variants:**
- Short-Term Todo Lists: Only immediate steps, missing big picture (Count: 1)
- Sequential When Parallel Possible: Independent tasks run one at a time (Count: 1)

**Lesson:**
- Internal todos must trace the FULL path to the goal
- Every phase, sub-phase, and gate should be in the todo list
- When two tasks are independent (API call + file edit), run in parallel
- Background tasks exist for a reason - USE THEM
- Always ask: "Can these run at the same time?"

---

### Interface/Demo Mismatch (Count: 2)

**Pattern:** Building demos or interfaces that don't match what the model actually understands or can do.

**Instances:**
- 2026-01-14: Web interface sent text to model trained on numeric causal bandits - output is meaningless noise. Score: 150/420
- 2026-01-14: Stateless web inference for RL brain - brain needs reward feedback but interface runs stateless forward passes. Score: 365/420

**Variants:**
- Domain Mismatch: Demo input domain differs from training domain (Count: 1)
- Stateless Inference for RL: Removes the learning mechanism (Count: 1)

**Lesson:**
- Demo must match training domain
- A model trained on task A doesn't magically work on task B
- RL agents need feedback loops - stateless inference removes their intelligence
- "Singularity" that can't understand text is not a singularity
- Validate FUNCTIONALITY, not just architecture

---

## Cross-Cutting Themes

### Theme 1: Verify, Don't Assume
Every pattern above involves assuming something works without verifying:
- Assuming data distributions match
- Assuming metrics measure what we think
- Assuming protocols can be skipped
- Assuming infrastructure supports the task

### Theme 2: Train/Eval Alignment
The most frequent high-severity mistakes involve train/eval mismatches:
- Different data distributions
- Different step structures
- Different action forcing
- Different hidden state trajectories

### Theme 3: Protocol Discipline
Protocols exist because past mistakes created them:
- Ralph Loop prevents premature stopping
- Deep-debug prevents ad-hoc debugging
- Environment checkpoints prevent wrong-environment training
- Blindfold Test prevents information leaks

---

## Format Template (for new entries)

```
### [YYYY-MM-DD HH:MM] - [Phase/Component]
**What happened:** [Objective description of failure]
**Root cause:** [Why it failed - be brutally honest]
**Score:** [XXX/420]
**Recovery taken:** [RETRY/SLINGSHOT/GRAVEYARD]
**Pattern:** [Link to existing pattern if applicable]
**Lesson:** [What NOT to do next time]
```
