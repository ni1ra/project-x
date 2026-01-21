# HANDOFF: WIRED-BRAIN Jarvis Harness v2

Generated: 2026-01-21 (v27 - **SELF-PACED DIFFICULTY CONTROL - IMPLEMENTED**)

---

## DOCUMENTATION STATUS

**All documents have been updated to reflect Self-Paced Difficulty Control:**

| Document | Section | Status |
|----------|---------|--------|
| `PLAN_TO_JARVIS.md` | "SELF-PACED DIFFICULTY CONTROL" section | ✅ UPDATED |
| `paper.md` | Appendix L | ✅ UPDATED |
| `README.md` | "Self-Paced Difficulty Control" section | ✅ UPDATED |
| `BLUEPRINT_UNIFIED_CURRICULUM.md` | Marked as SUPERSEDED | ✅ UPDATED |
| `BLUEPRINT_SELF_PACED.md` | New comprehensive blueprint | ✅ CREATED |

**Implementation complete:** `src/curriculum/` module added with Boredom/Stress signals.

---

## 1. PROJECT CONTEXT

### What Is This?
WIRED-BRAIN is building an autonomous coding agent ("Jarvis") using a 2.7M parameter recurrent neural network. The agent learns to fix bugs in code repositories through reinforcement learning, with **zero LLM dependencies**.

### Core Philosophy
> "We did not build these structures. We priced the resources, and the structures emerged."

This means: **NO external schedulers, NO hand-coded curricula, NO babysitting.** The agent's own internal signals drive its learning progression.

---

## 2. SELF-PACED DIFFICULTY CONTROL (NEW DESIGN)

### The Problem with External Scheduling

The previous design had a `CurriculumScheduler` that:
- Observed success rate externally
- Decided when to increase/decrease difficulty
- Used arbitrary thresholds (70% promote, 30% demote)

**This violates the project's philosophy.** We were engineering curriculum instead of letting it emerge.

### The Solution: Intrinsic Drives

Replace external scheduling with two **primal drives** the agent computes from its own experience:

#### Boredom Signal (B) — "I need challenge"
Triggers when the agent's world becomes too predictable:

| Component | Measurement | Boredom Rises When... |
|-----------|-------------|----------------------|
| Low Novelty | RND prediction error | Error consistently low (nothing new) |
| Low Variance | Std dev of recent rewards | Outcomes predictable |
| Plateaued Learning | Δ performance over time | No improvement despite success |

```python
B = w1 * max(0, R* - R_mean) +      # Success too high
    w2 * max(0, σ* - σ(rewards)) +  # Variance too low
    w3 * max(0, -Δ_perf)            # Learning stalled
```

#### Stress Signal (S) — "I need relief"
Triggers when the agent is overwhelmed:

| Component | Measurement | Stress Rises When... |
|-----------|-------------|---------------------|
| Rising Prediction Error | RND error trend | Encountering unpredictable situations |
| Low Success Rate | EMA of task completion | Failing repeatedly |
| Entropy Collapse | Policy entropy | Agent "gives up" (one action dominates) |

```python
S = v1 * max(0, E_pred - E*) +      # Prediction error too high
    v2 * max(0, P* - P_success) +   # Success rate too low
    v3 * max(0, H* - H)             # Entropy collapsed
```

### Dynamic Difficulty Adjustment

The difficulty parameter `d ∈ [1, 100]` adjusts based on the balance of drives:

```python
Δd = K_b * B - K_s * S

# If B > S: Agent is bored → increase difficulty
# If S > B: Agent is stressed → decrease difficulty
# If B ≈ S ≈ 0: Agent in "flow state" → maintain difficulty
```

### Safeguards Against Oscillation

| Safeguard | Implementation |
|-----------|----------------|
| **Hysteresis** | Dead-band where small B/S differences don't trigger changes |
| **Patience Window** | Minimum N episodes before any adjustment |
| **EMA Smoothing** | Signals based on moving averages, not single episodes |
| **Difficulty Jitter** | Sample tasks from Normal(d, σ=5) to smooth transitions |

### Why This Is Better

| Aspect | External Scheduler | Intrinsic Drives |
|--------|-------------------|------------------|
| Philosophy | Engineering | Emergence |
| Hyperparameters | Many thresholds to tune | Few coefficients |
| Adaptability | Fixed rules | Self-adjusting |
| Gaming resistance | Agent could exploit | Agent's own signals |
| Biological plausibility | None | Mimics curiosity/frustration |

---

## 3. CONTINUOUS DIFFICULTY PARAMETER

### Mapping d ∈ [1, 100] to Task Parameters

| d Range | Code Size | Files | Bug Type | Hints |
|---------|-----------|-------|----------|-------|
| 1-10 | 10-50 lines | 1 | Syntax | Full (bug_line, auto-focus) |
| 11-30 | 50-100 lines | 1-2 | Syntax/Logic | Partial (auto-focus only) |
| 31-50 | 100-200 lines | 2-5 | Logic/Type | None |
| 51-70 | 200-500 lines | 5-10 | State/Import | None |
| 71-100 | 500+ lines | 10+ | Design flaws | None |

### Smooth Interpolation

```python
def map_difficulty_to_params(d: int) -> DifficultyParams:
    """
    Linear interpolation between anchor points.
    d=30 to d=31 is imperceptible.
    d=10 to d=50 is substantial but gradual.
    """
```

---

## 4. IMPLEMENTATION ARCHITECTURE

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│              SELF-PACED DIFFICULTY CONTROL              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐      ┌─────────────────────────┐  │
│  │ Boredom Signal  │      │    Stress Signal        │  │
│  │ - RND novelty   │      │ - Success rate          │  │
│  │ - Reward var    │      │ - Prediction error      │  │
│  │ - Learning Δ    │      │ - Policy entropy        │  │
│  └────────┬────────┘      └───────────┬─────────────┘  │
│           │                           │                 │
│           └─────────┬─────────────────┘                 │
│                     ▼                                   │
│           ┌─────────────────┐                          │
│           │  Δd = K_b*B - K_s*S                        │
│           │  (with hysteresis & patience)              │
│           └────────┬────────┘                          │
│                    ▼                                    │
│           ┌─────────────────┐                          │
│           │ difficulty_target                          │
│           │ sampled_d ~ N(target, 5)                   │
│           └────────┬────────┘                          │
│                    ▼                                    │
│           ┌─────────────────┐                          │
│           │ Task Generation │                          │
│           │ map_difficulty_to_params(sampled_d)        │
│           └─────────────────┘                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### File Structure

```
src/
├── curriculum/
│   ├── __init__.py
│   ├── signals.py          # Boredom and Stress computation
│   ├── controller.py       # Self-paced difficulty adjustment
│   └── difficulty_mapping.py
│
├── harness/
│   ├── env.py              # Add continuous difficulty support
│   └── bug_templates.py    # Parameterize by d
│
└── core/
    └── rpj_brain.py        # RND for novelty signal
```

### Training Loop Integration

```python
# Pseudocode for self-paced training
difficulty_target = 5.0  # Start easy
episodes_since_change = 0

for episode in training:
    # Run episode
    metrics = run_episode(difficulty=int(difficulty_target))
    episodes_since_change += 1

    # Update EMAs
    success_ema.update(metrics.success)
    novelty_ema.update(metrics.intrinsic_reward)
    entropy_ema.update(metrics.policy_entropy)

    # Compute signals
    B = compute_boredom(success_ema, novelty_ema, reward_variance)
    S = compute_stress(success_ema, pred_error_ema, entropy_ema)

    # Self-paced adjustment (with safeguards)
    if episodes_since_change >= MIN_PATIENCE:
        if B - S > HYSTERESIS and B > B_HIGH:
            difficulty_target += K_b * B
            episodes_since_change = 0
        elif S - B > HYSTERESIS and S > S_HIGH:
            difficulty_target -= K_s * S
            episodes_since_change = 0

    # Clamp and sample
    difficulty_target = clip(difficulty_target, 1, 100)
    sampled_d = sample_normal(difficulty_target, std=5)

    # Generate next task
    next_task = generate_task(sampled_d)
```

---

## 5. CLI ARGUMENTS

New arguments for self-paced training:

```bash
python scripts/train_jarvis_harness.py \
    --self-paced \                    # Enable intrinsic drive control
    --boredom-coef 1.0 \              # K_b weight
    --stress-coef 1.0 \               # K_s weight
    --boredom-threshold 0.6 \         # B_HIGH trigger
    --stress-threshold 0.6 \          # S_HIGH trigger
    --hysteresis-margin 0.1 \         # Dead-band width
    --min-patience-episodes 30 \      # Cooldown after adjustment
    --difficulty-jitter 5.0 \         # Std dev for sampling
    --initial-difficulty 5            # Starting d
```

---

## 6. MONITORING AND LOGGING

### Required Metrics

Every N episodes, log:

```
Episode 2500: d=42, B=0.75, S=0.10, success=1, novelty=0.05, entropy=0.30
Episode 2550: d=45, B=0.50, S=0.00, success=1, novelty=0.02, entropy=0.25
Episode 2600: d=48, B=0.20, S=0.00, success=0, novelty=0.15, entropy=0.28
Episode 2650: d=48, B=0.00, S=0.40, success=0, novelty=0.20, entropy=0.22  # stress rising
Episode 2700: d=47, B=0.00, S=0.80, success=0, novelty=0.30, entropy=0.15  # difficulty decreased
```

### Warning Conditions

| Condition | Warning | Response |
|-----------|---------|----------|
| Difficulty oscillates 3+ times in 20 episodes | "⚠️ Thrashing detected" | Increase patience |
| Entropy < 0.1 | "⚠️ Entropy collapse" | Stress signal handles |
| Success rate = 0 for 50+ episodes | "⚠️ Complete failure" | Force difficulty decrease |
| B and S both high | "⚠️ Conflicting signals" | Increase smoothing |

---

## 7. EXPERIMENTAL VALIDATION

### Ablation Study

Compare self-paced vs baseline (threshold-based) curriculum:

| Metric | Self-Paced (Expected) | Baseline |
|--------|----------------------|----------|
| Max difficulty reached | Higher | Lower |
| Oscillations | Fewer | More |
| Entropy stability | Better | Worse |
| Forgetting (low-d performance) | Minimal | Risk |

### Evaluation Protocol

1. Train both for same timesteps
2. Evaluate on d ∈ {10, 30, 50, 70, 90}
3. Measure:
   - Success rate per difficulty
   - Time to reach d=50
   - Backward transfer (can still solve d=10?)
   - Policy entropy trajectory

---

## 8. KEY INSIGHT

**The RND curiosity signal IS the difficulty scheduler.**

When tasks are mastered:
- States become predictable → RND error drops → Boredom rises → Agent seeks harder tasks

When tasks are too hard:
- Outcomes are random → Can't learn patterns → Stress rises → Agent retreats

This is exactly how human curiosity works. We don't need an external scheduler—we just need to measure and respond to the agent's own learning dynamics.

---

## 9. FILES REQUIRING UPDATE

After implementing self-paced control, update these docs to match:

### PLAN_TO_JARVIS.md
- Replace "UNIFIED CURRICULUM RL FRAMEWORK" section
- Remove `CurriculumScheduler` references
- Add Boredom/Stress signal definitions
- Update implementation roadmap

### paper.md (Appendix L)
- Rewrite to emphasize intrinsic drives over external scheduling
- Add equations for B and S signals
- Discuss philosophical alignment with project thesis

### README.md
- Update "Unified Curriculum Framework" section
- Emphasize "no external scheduler" approach
- Add CLI arguments for self-paced mode

### BLUEPRINT_UNIFIED_CURRICULUM.md
- Major rewrite: remove `CurriculumScheduler` class
- Add `signals.py` and `controller.py` specifications
- Update implementation steps
- Re-validate with JARVIS

---

## 10. QUICK REFERENCE

### The Two Drives

| Drive | Meaning | Response |
|-------|---------|----------|
| **Boredom** | "This is too easy" | Seek challenge (↑ difficulty) |
| **Stress** | "This is too hard" | Seek relief (↓ difficulty) |

### The Golden Rule

> **Price curiosity correctly, and the curriculum emerges.**

No external scheduler. No arbitrary thresholds. The agent's own learning dynamics guide its progression through the difficulty landscape.

---

*Last updated: 2026-01-21*
*Status: Self-Paced Difficulty Control IMPLEMENTED. Ready for training.*
