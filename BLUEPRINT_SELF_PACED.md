# BLUEPRINT: Self-Paced Difficulty Control

**Date:** 2026-01-21
**Status:** DESIGN COMPLETE - Ready for implementation
**Supersedes:** BLUEPRINT_UNIFIED_CURRICULUM.md (external scheduler approach)

---

## Executive Summary

Replace the external `CurriculumScheduler` (threshold-based promotion/demotion) with **intrinsic Boredom/Stress signals** that let the agent self-regulate difficulty. This aligns with the project philosophy:

> "We did not build these structures. We priced the resources, and the structures emerged."

**NO external schedulers. NO hand-coded curricula. NO babysitting.** The agent's own internal signals drive learning progression.

---

## 1. The Problem with External Scheduling

The existing `CurriculumState` class in `train_jarvis_harness.py`:
- Observes success rate externally
- Uses arbitrary thresholds (70% promote, 30% demote)
- Decides when to increase/decrease difficulty from outside the agent

**This violates the project's emergence philosophy.** We were engineering curriculum instead of letting it emerge from the agent's experience.

---

## 2. The Solution: Intrinsic Drives

Replace external scheduling with two **primal drives** computed from the agent's own experience:

### 2.1 Boredom Signal (B) — "I need challenge"

Triggers when the agent's world becomes too predictable:

| Component | Measurement | Boredom Rises When... |
|-----------|-------------|----------------------|
| Low Novelty | RND prediction error (EMA) | Error consistently low |
| Low Variance | Std dev of recent rewards | Outcomes too predictable |
| Plateaued Learning | Δ performance over window | No improvement despite success |

```python
@dataclass
class BoredomConfig:
    novelty_target: float = 0.3      # R* - target RND error
    variance_target: float = 0.2     # σ* - target reward variance
    performance_window: int = 100    # Episodes for Δ_perf

    w_novelty: float = 0.4           # Weight for novelty component
    w_variance: float = 0.3          # Weight for variance component
    w_plateau: float = 0.3           # Weight for plateau component

def compute_boredom(
    novelty_ema: float,
    reward_variance: float,
    performance_delta: float,
    config: BoredomConfig
) -> float:
    """
    B = w1 * max(0, R* - R_mean) +      # Novelty too low
        w2 * max(0, σ* - σ(rewards)) +  # Variance too low
        w3 * max(0, -Δ_perf)            # Learning stalled
    """
    novelty_term = max(0.0, config.novelty_target - novelty_ema)
    variance_term = max(0.0, config.variance_target - reward_variance)
    plateau_term = max(0.0, -performance_delta)

    B = (config.w_novelty * novelty_term +
         config.w_variance * variance_term +
         config.w_plateau * plateau_term)

    return min(1.0, B)  # Clamp to [0, 1]
```

### 2.2 Stress Signal (S) — "I need relief"

Triggers when the agent is overwhelmed:

| Component | Measurement | Stress Rises When... |
|-----------|-------------|---------------------|
| High Prediction Error | RND error trend | Encountering unpredictable situations |
| Low Success Rate | EMA of task completion | Failing repeatedly |
| Entropy Collapse | Policy entropy | Agent "gives up" (one action dominates) |

```python
@dataclass
class StressConfig:
    pred_error_threshold: float = 0.7   # E* - RND error ceiling
    success_target: float = 0.3         # P* - minimum success rate
    entropy_target: float = 0.2         # H* - minimum entropy

    v_pred_error: float = 0.3           # Weight for prediction error
    v_success: float = 0.4              # Weight for success rate
    v_entropy: float = 0.3              # Weight for entropy

def compute_stress(
    pred_error_ema: float,
    success_rate_ema: float,
    entropy_ema: float,
    config: StressConfig
) -> float:
    """
    S = v1 * max(0, E_pred - E*) +      # Prediction error too high
        v2 * max(0, P* - P_success) +   # Success rate too low
        v3 * max(0, H* - H)             # Entropy collapsed
    """
    pred_error_term = max(0.0, pred_error_ema - config.pred_error_threshold)
    success_term = max(0.0, config.success_target - success_rate_ema)
    entropy_term = max(0.0, config.entropy_target - entropy_ema)

    S = (config.v_pred_error * pred_error_term +
         config.v_success * success_term +
         config.v_entropy * entropy_term)

    return min(1.0, S)  # Clamp to [0, 1]
```

### 2.3 Dynamic Difficulty Adjustment

The difficulty parameter `d ∈ [1, 100]` adjusts based on the balance of drives:

```python
@dataclass
class ControllerConfig:
    k_boredom: float = 5.0           # K_b - boredom sensitivity
    k_stress: float = 5.0            # K_s - stress sensitivity
    hysteresis_margin: float = 0.1   # Dead-band width
    min_patience_episodes: int = 30  # Cooldown after adjustment
    difficulty_jitter_std: float = 5.0  # Gaussian noise for sampling

class SelfPacedController:
    def __init__(self, config: ControllerConfig, initial_difficulty: int = 5):
        self.config = config
        self.difficulty_target: float = float(initial_difficulty)
        self.episodes_since_change: int = 0

    def update(self, boredom: float, stress: float) -> int:
        """
        Δd = K_b * B - K_s * S

        If B > S: Agent is bored → increase difficulty
        If S > B: Agent is stressed → decrease difficulty
        If B ≈ S ≈ 0: Agent in "flow state" → maintain difficulty
        """
        self.episodes_since_change += 1

        # Check patience window
        if self.episodes_since_change < self.config.min_patience_episodes:
            return self._sample_difficulty()

        # Compute drive difference
        delta = boredom - stress

        # Apply hysteresis - only adjust if signal is strong enough
        if abs(delta) < self.config.hysteresis_margin:
            return self._sample_difficulty()

        # Adjust difficulty
        if delta > 0 and boredom > 0.3:  # Boredom threshold
            Δd = self.config.k_boredom * boredom
            self.difficulty_target = min(100.0, self.difficulty_target + Δd)
            self.episodes_since_change = 0
        elif delta < 0 and stress > 0.3:  # Stress threshold
            Δd = self.config.k_stress * stress
            self.difficulty_target = max(1.0, self.difficulty_target - Δd)
            self.episodes_since_change = 0

        return self._sample_difficulty()

    def _sample_difficulty(self) -> int:
        """Sample actual difficulty with jitter for smooth transitions."""
        import numpy as np
        sampled = np.random.normal(self.difficulty_target, self.config.difficulty_jitter_std)
        return int(np.clip(sampled, 1, 100))
```

---

## 3. Continuous Difficulty Mapping

Map `d ∈ [1, 100]` to task parameters with smooth interpolation:

| d Range | Code Size | Files | Bug Type | Hints |
|---------|-----------|-------|----------|-------|
| 1-10 | 10-50 lines | 1 | Syntax | Full (bug_line, auto-focus) |
| 11-30 | 50-100 lines | 1-2 | Syntax/Logic | Partial (auto-focus only) |
| 31-50 | 100-200 lines | 2-5 | Logic/Type | None |
| 51-70 | 200-500 lines | 5-10 | State/Import | None |
| 71-100 | 500+ lines | 10+ | Design flaws | None |

```python
# src/curriculum/difficulty_mapping.py

@dataclass
class DifficultyParams:
    """Task parameters derived from continuous difficulty d."""
    min_lines: int
    max_lines: int
    min_files: int
    max_files: int
    bug_difficulty: BugDifficulty
    provide_bug_line: bool
    auto_focus_target: bool
    force_write_focus_prob: float
    use_trivial_vocab: bool

def map_difficulty_to_params(d: int) -> DifficultyParams:
    """
    Smooth interpolation between anchor points.
    d=30 to d=31 is imperceptible.
    d=10 to d=50 is substantial but gradual.
    """
    d = max(1, min(100, d))

    # Code complexity (linear interpolation)
    if d <= 10:
        min_lines, max_lines = 10, 50
        min_files, max_files = 1, 1
    elif d <= 30:
        t = (d - 10) / 20
        min_lines = int(10 + t * 40)
        max_lines = int(50 + t * 50)
        min_files, max_files = 1, 1 + int(t)
    elif d <= 50:
        t = (d - 30) / 20
        min_lines = int(50 + t * 50)
        max_lines = int(100 + t * 100)
        min_files = 1 + int(t)
        max_files = 2 + int(t * 3)
    elif d <= 70:
        t = (d - 50) / 20
        min_lines = int(100 + t * 100)
        max_lines = int(200 + t * 300)
        min_files = 2 + int(t * 3)
        max_files = 5 + int(t * 5)
    else:
        t = (d - 70) / 30
        min_lines = int(200 + t * 300)
        max_lines = int(500 + t * 500)
        min_files = 5 + int(t * 5)
        max_files = 10 + int(t * 10)

    # Bug difficulty mapping
    if d <= 10:
        bug_difficulty = BugDifficulty.TRIVIAL
    elif d <= 30:
        bug_difficulty = BugDifficulty.EASY
    elif d <= 50:
        bug_difficulty = BugDifficulty.MEDIUM
    elif d <= 70:
        bug_difficulty = BugDifficulty.HARD
    else:
        bug_difficulty = BugDifficulty.EXPERT

    # Scaffolding (gradual removal)
    provide_bug_line = d <= 15
    auto_focus_target = d <= 25
    force_write_focus_prob = max(0.0, 1.0 - (d - 1) / 30)
    use_trivial_vocab = d <= 10

    return DifficultyParams(
        min_lines=min_lines,
        max_lines=max_lines,
        min_files=min_files,
        max_files=max_files,
        bug_difficulty=bug_difficulty,
        provide_bug_line=provide_bug_line,
        auto_focus_target=auto_focus_target,
        force_write_focus_prob=force_write_focus_prob,
        use_trivial_vocab=use_trivial_vocab,
    )
```

---

## 4. Architecture

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
│           │  SelfPacedController                       │
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
├── curriculum/                    # NEW MODULE
│   ├── __init__.py
│   ├── signals.py                 # Boredom/Stress computation
│   ├── controller.py              # SelfPacedController
│   └── difficulty_mapping.py      # d → task parameters
│
├── harness/
│   ├── env.py                     # MODIFY: accept continuous difficulty
│   └── bug_templates.py           # EXISTING: already supports difficulty
│
└── core/
    └── rpj_brain.py               # EXISTING: has RNDNetwork

scripts/
└── train_jarvis_harness.py        # MODIFY: integrate self-paced control
```

---

## 5. Implementation Steps

### Phase 1: Core Signals Module

- [ ] **Step 1: Create curriculum module structure**
  - Files: `src/curriculum/__init__.py`
  - Verify: Module imports work

- [ ] **Step 2: Implement signals.py**
  - Classes: `BoredomConfig`, `StressConfig`, `SignalTracker`
  - Functions: `compute_boredom()`, `compute_stress()`
  - Verify: Unit tests pass

- [ ] **Step 3: Implement controller.py**
  - Classes: `ControllerConfig`, `SelfPacedController`
  - Methods: `update()`, `_sample_difficulty()`, `state_dict()`, `load_state_dict()`
  - Verify: Controller adjusts difficulty based on mock signals

- [ ] **Step 4: Implement difficulty_mapping.py**
  - Classes: `DifficultyParams`
  - Functions: `map_difficulty_to_params()`
  - Verify: Smooth interpolation for d=1 to d=100

### Phase 2: Training Integration

- [ ] **Step 5: Add CLI arguments**
  - `--self-paced` flag to enable
  - `--boredom-coef`, `--stress-coef` for tuning
  - `--initial-difficulty` for starting point
  - `--hysteresis-margin`, `--min-patience-episodes` for safeguards

- [ ] **Step 6: Integrate into training loop**
  - Track success/failure after each episode
  - Compute B and S from episode metrics
  - Call controller.update() to get next difficulty
  - Generate tasks using map_difficulty_to_params()

- [ ] **Step 7: Add metrics logging**
  - Log: d, B, S, success, novelty, entropy per episode
  - Warnings for thrashing, entropy collapse, complete failure

### Phase 3: Documentation Update

- [ ] **Step 8: Update PLAN_TO_JARVIS.md**
  - Replace "UNIFIED CURRICULUM RL FRAMEWORK" section
  - Add Boredom/Stress signal definitions

- [ ] **Step 9: Update paper.md (Appendix L)**
  - Rewrite to emphasize intrinsic drives
  - Add equations for B and S

- [ ] **Step 10: Update README.md**
  - Update curriculum section
  - Add CLI arguments for self-paced mode

- [ ] **Step 11: Archive BLUEPRINT_UNIFIED_CURRICULUM.md**
  - Mark as superseded
  - Keep for historical reference

### Phase 4: Testing

- [ ] **Step 12: Unit tests**
  - Test signal computation
  - Test controller state machine
  - Test difficulty mapping continuity

- [ ] **Step 13: Integration test**
  - Short training run with self-paced mode
  - Verify difficulty adjusts based on performance

---

## 6. CLI Arguments

```bash
python scripts/train_jarvis_harness.py \
    --self-paced \                    # Enable intrinsic drive control
    --boredom-coef 5.0 \              # K_b weight
    --stress-coef 5.0 \               # K_s weight
    --boredom-threshold 0.3 \         # B_HIGH trigger
    --stress-threshold 0.3 \          # S_HIGH trigger
    --hysteresis-margin 0.1 \         # Dead-band width
    --min-patience-episodes 30 \      # Cooldown after adjustment
    --difficulty-jitter 5.0 \         # Std dev for sampling
    --initial-difficulty 5            # Starting d
```

---

## 7. Safeguards Against Oscillation

| Safeguard | Implementation |
|-----------|----------------|
| **Hysteresis** | Dead-band where small B/S differences don't trigger changes |
| **Patience Window** | Minimum 30 episodes before any adjustment |
| **EMA Smoothing** | Signals based on moving averages (α=0.1) |
| **Difficulty Jitter** | Sample from Normal(d, σ=5) for smooth transitions |

### Warning Conditions

| Condition | Warning | Response |
|-----------|---------|----------|
| Difficulty oscillates 3+ times in 20 episodes | "⚠️ Thrashing detected" | Increase patience |
| Entropy < 0.1 | "⚠️ Entropy collapse" | Stress signal handles |
| Success rate = 0 for 50+ episodes | "⚠️ Complete failure" | Force difficulty decrease |
| B and S both high | "⚠️ Conflicting signals" | Increase EMA smoothing |

---

## 8. Key Insight

**The RND curiosity signal IS the difficulty scheduler.**

When tasks are mastered:
- States become predictable → RND error drops → Boredom rises → Agent seeks harder tasks

When tasks are too hard:
- Outcomes are random → Can't learn patterns → Stress rises → Agent retreats

This is exactly how human curiosity works. We don't need an external scheduler—we just need to measure and respond to the agent's own learning dynamics.

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| d=10 success rate | >20% | Eval 100 tasks at d=10 |
| d=50 success rate | >10% | Eval 100 tasks at d=50 |
| Autonomous progression | d increases over 50k steps | Training logs |
| No forgetting | d=10 stays >15% after reaching d=50 | Periodic evaluation |
| Minimal thrashing | <3 reversals per 100 episodes | Training logs |

---

## 10. Comparison: External vs Intrinsic

| Aspect | External Scheduler (OLD) | Intrinsic Drives (NEW) |
|--------|-------------------------|------------------------|
| Philosophy | Engineering | Emergence |
| Hyperparameters | Many thresholds | Few coefficients |
| Adaptability | Fixed rules | Self-adjusting |
| Gaming resistance | Agent could exploit | Agent's own signals |
| Biological plausibility | None | Mimics curiosity/frustration |
| Codebase | `CurriculumState` class | `SelfPacedController` |

---

## 11. Files Requiring Update After Implementation

| File | Change |
|------|--------|
| `BLUEPRINT_UNIFIED_CURRICULUM.md` | Mark as SUPERSEDED |
| `PLAN_TO_JARVIS.md` | Update curriculum section |
| `paper.md` | Update Appendix L |
| `README.md` | Update curriculum documentation |
| `train_jarvis_harness.py` | Replace `CurriculumState` usage |

---

*Generated: 2026-01-21*
*Status: Ready for /goapeshit execution*
