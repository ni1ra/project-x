# BLUEPRINT: Unified Curriculum RL Framework

**Date:** 2026-01-20
**Status:** ⚠️ SUPERSEDED by `BLUEPRINT_SELF_PACED.md` (2026-01-21)

> **Note:** This document describes an external scheduler approach with CurriculumScheduler.
> The project philosophy ("We did not build these structures. We priced the resources, and
> the structures emerged.") led us to replace this with intrinsic Boredom/Stress signals.
> See `BLUEPRINT_SELF_PACED.md` for the current design.

## Overview

Replace the staged training approach (TRIVIAL → EASY → MEDIUM → etc.) with a continuous curriculum spanning difficulty d ∈ [1, 100]. This eliminates manual phase transitions, unifies reward functions across all levels, and adds intrinsic motivation (RND/curiosity) for exploration in sparse reward regimes.

## Reconnaissance

### Existing Patterns
- `CurriculumState` dataclass with binary threshold-based promotion/demotion
- `BugDifficulty` enum (TRIVIAL=1, EASY=2, MEDIUM=3, HARD=4, EXPERT=5)
- `HarnessConfig` with extensive shaping parameters
- `RPJBrain` includes `RNDNetwork` for intrinsic exploration
- `SleepModule` for offline consolidation

### Related Features
- `create_tasks_v2()` accepts difficulty parameter
- `force_write_focus_prob` for action space simplification
- `auto_focus_target` for observation simplification
- BC pretraining with `pretrain_behavioral_cloning*()`

### Constraints Found
- WSL environment (no direct GPU in development)
- Current curriculum uses discrete difficulty levels
- Reward shaping coefficients are fixed in `HarnessConfig`
- RND warmup (`T_warm`) is fixed at 50k steps

### Tech Stack
- Python 3.12.3
- PyTorch (PPO training)
- gymnasium-style environment
- Dataclass-based configuration

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED CURRICULUM SYSTEM                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐     ┌──────────────────────────────────┐  │
│  │ CurriculumConfig │────▶│     CurriculumScheduler          │  │
│  └──────────────────┘     │  - difficulty_tracker            │  │
│                           │  - success_rate_ema              │  │
│  ┌──────────────────┐     │  - intrinsic_coef_scheduler      │  │
│  │ IntrinsicModule  │◀────│  - reward_scaling_schedule       │  │
│  │  - RNDNetwork    │     └──────────────┬───────────────────┘  │
│  │  - novelty_bonus │                    │                      │
│  └────────┬─────────┘                    │                      │
│           │                              ▼                      │
│           │         ┌────────────────────────────────────┐      │
│           │         │      JarvisHarnessTrainer          │      │
│           └────────▶│  - collect_rollout()               │      │
│                     │  - train_step() with scheduler     │      │
│                     │  - unified_reward_computation()    │      │
│                     └────────────────┬───────────────────┘      │
│                                      │                          │
│                                      ▼                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              JarvisHarnessEnv (modified)                  │   │
│  │  - continuous_difficulty: int [1, 100]                    │   │
│  │  - scaffolding_decay: float [0, 1]                       │   │
│  │  - hint_probability: float [0, 1]                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
src/
├── curriculum/                    # NEW MODULE
│   ├── __init__.py
│   ├── scheduler.py               # CurriculumScheduler
│   ├── config.py                  # CurriculumConfig dataclass
│   ├── intrinsic.py               # IntrinsicRewardModule
│   └── difficulty_mapping.py      # d → task parameters mapping
│
├── harness/
│   ├── env.py                     # MODIFY: add continuous difficulty
│   ├── bug_templates.py           # MODIFY: parameterize by d
│   └── verifiers.py               # MODIFY: unified reward function
│
└── core/
    └── rpj_brain.py               # MODIFY: scheduler integration

scripts/
└── train_jarvis_harness.py        # MODIFY: scheduler integration
```

### Data Models

```python
# src/curriculum/config.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class CurriculumConfig:
    """Configuration for unified curriculum."""

    # Difficulty range
    min_difficulty: int = 1
    max_difficulty: int = 100
    initial_difficulty: int = 5

    # Success rate targeting (zone of proximal development)
    target_success_rate: float = 0.50
    success_rate_ema_alpha: float = 0.1

    # Difficulty adjustment
    promote_threshold: float = 0.70  # Success rate to increase difficulty
    demote_threshold: float = 0.30   # Success rate to decrease difficulty
    min_episodes_per_level: int = 20  # Min episodes before adjustment
    difficulty_step: int = 1          # Step size for adjustments

    # Probabilistic blending
    difficulty_noise_std: float = 5.0  # Gaussian noise for sampling

    # Intrinsic reward scheduling
    initial_intrinsic_coef: float = 0.5
    min_intrinsic_coef: float = 0.01
    intrinsic_decay_rate: float = 0.9999  # Per-step decay

    # Scaffolding decay
    initial_scaffolding: float = 1.0  # Full scaffolding at d=1
    scaffolding_decay_per_level: float = 0.02  # Decay per difficulty level

    # Interleaved replay for forgetting prevention
    replay_easy_prob: float = 0.1  # Probability of sampling easy task
    replay_difficulty_range: int = 20  # Sample from [d-20, d]


@dataclass
class SchedulerState:
    """Mutable state for curriculum scheduler."""
    current_difficulty: int = 5
    success_rate_ema: float = 0.5
    episodes_at_level: int = 0
    total_episodes: int = 0
    total_promotions: int = 0
    total_demotions: int = 0
    intrinsic_coef: float = 0.5

    # Per-difficulty tracking
    difficulty_stats: dict = None  # {d: {'successes': int, 'total': int}}

    def __post_init__(self):
        if self.difficulty_stats is None:
            self.difficulty_stats = {}


@dataclass
class SchedulerOutput:
    """Output from scheduler step."""
    next_difficulty: int
    sampled_difficulty: int  # After noise
    intrinsic_coef: float
    scaffolding_level: float  # [0, 1] - how much help
    force_focus_prob: float   # Probability of forcing WRITE_FOCUS
    hint_probability: float   # Probability of showing bug_line
    reward_scale: float       # Scale for test rewards
```

```python
# src/curriculum/difficulty_mapping.py
from dataclasses import dataclass
from typing import Tuple
from src.harness.bug_templates import BugDifficulty, BugCategory

@dataclass
class DifficultyParams:
    """Parameters derived from continuous difficulty d."""

    # Code complexity
    min_lines: int
    max_lines: int
    min_files: int
    max_files: int

    # Bug complexity
    bug_difficulty: BugDifficulty  # Mapped discrete difficulty
    allowed_categories: Tuple[BugCategory, ...]

    # Scaffolding
    provide_bug_line: bool
    auto_focus_target: bool
    force_write_focus_prob: float

    # Vocabulary
    use_trivial_vocab: bool
    vocab_size: int


def map_difficulty_to_params(d: int) -> DifficultyParams:
    """
    Map continuous difficulty d ∈ [1, 100] to task parameters.

    Design principles:
    - Smooth transitions (no sharp jumps)
    - Gradual scaffolding removal
    - Linear interpolation between anchor points
    """
    d = max(1, min(100, d))  # Clamp to [1, 100]

    # Code complexity (linear scaling)
    if d <= 10:
        min_lines, max_lines = 10, 50
        min_files, max_files = 1, 1
    elif d <= 30:
        t = (d - 10) / 20  # [0, 1]
        min_lines = int(10 + t * 40)  # 10 → 50
        max_lines = int(50 + t * 50)  # 50 → 100
        min_files, max_files = 1, 1 + int(t)
    elif d <= 50:
        t = (d - 30) / 20
        min_lines = int(50 + t * 50)   # 50 → 100
        max_lines = int(100 + t * 100) # 100 → 200
        min_files = 1 + int(t)
        max_files = 2 + int(t * 3)     # 2 → 5
    elif d <= 70:
        t = (d - 50) / 20
        min_lines = int(100 + t * 100) # 100 → 200
        max_lines = int(200 + t * 300) # 200 → 500
        min_files = 2 + int(t * 3)     # 2 → 5
        max_files = 5 + int(t * 5)     # 5 → 10
    else:  # d > 70
        t = (d - 70) / 30
        min_lines = int(200 + t * 300) # 200 → 500
        max_lines = int(500 + t * 500) # 500 → 1000+
        min_files = 5 + int(t * 5)     # 5 → 10
        max_files = 10 + int(t * 10)   # 10 → 20

    # Map to discrete BugDifficulty
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

    # Bug categories (expand with difficulty)
    if d <= 20:
        allowed_categories = (BugCategory.SYNTAX,)
    elif d <= 40:
        allowed_categories = (BugCategory.SYNTAX, BugCategory.LOGIC)
    elif d <= 60:
        allowed_categories = (BugCategory.SYNTAX, BugCategory.LOGIC, BugCategory.TYPE)
    elif d <= 80:
        allowed_categories = (BugCategory.SYNTAX, BugCategory.LOGIC, BugCategory.TYPE, BugCategory.IMPORT)
    else:
        allowed_categories = tuple(BugCategory)  # All categories

    # Scaffolding (gradual removal)
    provide_bug_line = d <= 15
    auto_focus_target = d <= 25
    force_write_focus_prob = max(0.0, 1.0 - (d - 1) / 30)  # 1.0 at d=1, 0.0 at d=31

    # Vocabulary
    use_trivial_vocab = d <= 10
    vocab_size = min(256, 5 + int((d - 1) * 2.5))  # 5 at d=1, 256 at d=100

    return DifficultyParams(
        min_lines=min_lines,
        max_lines=max_lines,
        min_files=min_files,
        max_files=max_files,
        bug_difficulty=bug_difficulty,
        allowed_categories=allowed_categories,
        provide_bug_line=provide_bug_line,
        auto_focus_target=auto_focus_target,
        force_write_focus_prob=force_write_focus_prob,
        use_trivial_vocab=use_trivial_vocab,
        vocab_size=vocab_size,
    )
```

```python
# src/curriculum/scheduler.py
import numpy as np
from typing import Dict, Optional
from .config import CurriculumConfig, SchedulerState, SchedulerOutput
from .difficulty_mapping import map_difficulty_to_params

class CurriculumScheduler:
    """
    Unified curriculum scheduler.

    Automatically adjusts difficulty based on agent performance,
    targeting a 50% success rate (zone of proximal development).
    """

    def __init__(self, config: CurriculumConfig):
        self.config = config
        self.state = SchedulerState(
            current_difficulty=config.initial_difficulty,
            intrinsic_coef=config.initial_intrinsic_coef,
        )
        self._rng = np.random.default_rng()

    def record_episode(self, success: bool, difficulty: int) -> None:
        """Record episode outcome for tracking."""
        # Update EMA of success rate
        outcome = 1.0 if success else 0.0
        self.state.success_rate_ema = (
            self.config.success_rate_ema_alpha * outcome +
            (1 - self.config.success_rate_ema_alpha) * self.state.success_rate_ema
        )

        # Track per-difficulty stats
        if difficulty not in self.state.difficulty_stats:
            self.state.difficulty_stats[difficulty] = {'successes': 0, 'total': 0}
        self.state.difficulty_stats[difficulty]['total'] += 1
        if success:
            self.state.difficulty_stats[difficulty]['successes'] += 1

        # Track episodes at current level
        if difficulty == self.state.current_difficulty:
            self.state.episodes_at_level += 1

        self.state.total_episodes += 1

        # Decay intrinsic coefficient
        self.state.intrinsic_coef = max(
            self.config.min_intrinsic_coef,
            self.state.intrinsic_coef * self.config.intrinsic_decay_rate
        )

    def should_adjust_difficulty(self) -> bool:
        """Check if we have enough data to adjust difficulty."""
        return self.state.episodes_at_level >= self.config.min_episodes_per_level

    def step(self) -> SchedulerOutput:
        """
        Compute next difficulty and associated parameters.

        Returns SchedulerOutput with:
        - next_difficulty: Base difficulty level
        - sampled_difficulty: Difficulty after noise (for task generation)
        - intrinsic_coef: Current intrinsic reward coefficient
        - scaffolding_level: How much help to provide [0, 1]
        - force_focus_prob: Probability of forcing WRITE_FOCUS action
        - hint_probability: Probability of showing bug_line hint
        - reward_scale: Scale factor for test rewards
        """
        d = self.state.current_difficulty

        # Difficulty adjustment (if enough episodes)
        if self.should_adjust_difficulty():
            sr = self.state.success_rate_ema

            if sr > self.config.promote_threshold:
                # Tasks too easy - increase difficulty
                new_d = min(self.config.max_difficulty, d + self.config.difficulty_step)
                if new_d != d:
                    self.state.current_difficulty = new_d
                    self.state.episodes_at_level = 0
                    self.state.total_promotions += 1

            elif sr < self.config.demote_threshold:
                # Tasks too hard - decrease difficulty
                new_d = max(self.config.min_difficulty, d - self.config.difficulty_step)
                if new_d != d:
                    self.state.current_difficulty = new_d
                    self.state.episodes_at_level = 0
                    self.state.total_demotions += 1

        d = self.state.current_difficulty

        # Probabilistic blending (sample around current difficulty)
        if self._rng.random() < self.config.replay_easy_prob:
            # Interleaved replay: sample easier task
            replay_min = max(1, d - self.config.replay_difficulty_range)
            sampled_d = self._rng.integers(replay_min, d + 1)
        else:
            # Normal sampling with Gaussian noise
            noise = self._rng.normal(0, self.config.difficulty_noise_std)
            sampled_d = int(np.clip(d + noise, 1, 100))

        # Get task parameters from difficulty mapping
        params = map_difficulty_to_params(sampled_d)

        # Compute scaffolding level
        scaffolding_level = max(0.0,
            self.config.initial_scaffolding -
            (d - 1) * self.config.scaffolding_decay_per_level
        )

        # Hint probability (decay with difficulty)
        hint_prob = 1.0 if params.provide_bug_line else 0.0

        # Reward scale (CONSTANT - per JARVIS feedback, dynamic scaling destabilizes Critic)
        reward_scale = 1.0  # Difficulty is intrinsic to task length, not reward magnitude

        return SchedulerOutput(
            next_difficulty=d,
            sampled_difficulty=sampled_d,
            intrinsic_coef=self.state.intrinsic_coef,
            scaffolding_level=scaffolding_level,
            force_focus_prob=params.force_write_focus_prob,
            hint_probability=hint_prob,
            reward_scale=reward_scale,
        )

    def state_dict(self) -> Dict:
        """Serialize scheduler state for checkpointing."""
        return {
            'current_difficulty': self.state.current_difficulty,
            'success_rate_ema': self.state.success_rate_ema,
            'episodes_at_level': self.state.episodes_at_level,
            'total_episodes': self.state.total_episodes,
            'total_promotions': self.state.total_promotions,
            'total_demotions': self.state.total_demotions,
            'intrinsic_coef': self.state.intrinsic_coef,
            'difficulty_stats': self.state.difficulty_stats,
        }

    def load_state_dict(self, state: Dict) -> None:
        """Restore scheduler state from checkpoint."""
        self.state.current_difficulty = state['current_difficulty']
        self.state.success_rate_ema = state['success_rate_ema']
        self.state.episodes_at_level = state['episodes_at_level']
        self.state.total_episodes = state['total_episodes']
        self.state.total_promotions = state['total_promotions']
        self.state.total_demotions = state['total_demotions']
        self.state.intrinsic_coef = state['intrinsic_coef']
        self.state.difficulty_stats = state.get('difficulty_stats', {})
```

```python
# src/curriculum/intrinsic.py
import torch
import torch.nn as nn
from typing import Tuple

class IntrinsicRewardModule(nn.Module):
    """
    Unified intrinsic reward computation.

    Combines:
    1. RND (Random Network Distillation) for novelty
    2. Optional: KL info-gain after warmup

    The intrinsic reward is scaled by scheduler's intrinsic_coef.
    """

    def __init__(
        self,
        obs_dim: int,
        hidden_dim: int = 256,
        output_dim: int = 128,
        normalize_rewards: bool = True,
    ):
        super().__init__()

        # Fixed random target network
        self.target = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )
        # Freeze target
        for p in self.target.parameters():
            p.requires_grad = False

        # Trainable predictor network
        self.predictor = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

        self.normalize_rewards = normalize_rewards

        # Running statistics for normalization
        self.register_buffer('reward_mean', torch.tensor(0.0))
        self.register_buffer('reward_var', torch.tensor(1.0))
        self.register_buffer('reward_count', torch.tensor(0.0))

    def forward(self, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute intrinsic reward and predictor loss.

        Args:
            obs: Observation tensor [batch, obs_dim] or [obs_dim]

        Returns:
            intrinsic_reward: Novelty bonus (before scaling)
            predictor_loss: MSE loss for training predictor
        """
        if obs.dim() == 1:
            obs = obs.unsqueeze(0)

        with torch.no_grad():
            target_features = self.target(obs)

        predictor_features = self.predictor(obs)

        # Intrinsic reward = prediction error
        error = (predictor_features - target_features).pow(2).sum(dim=-1)
        intrinsic_reward = error.detach()

        # Normalize rewards
        if self.normalize_rewards:
            intrinsic_reward = self._normalize(intrinsic_reward)

        # Loss for training predictor
        predictor_loss = error.mean()

        return intrinsic_reward, predictor_loss

    def _normalize(self, rewards: torch.Tensor) -> torch.Tensor:
        """Normalize rewards using running statistics."""
        # Update running stats
        batch_mean = rewards.mean()
        batch_var = rewards.var() + 1e-8
        batch_count = rewards.numel()

        delta = batch_mean - self.reward_mean
        total_count = self.reward_count + batch_count

        self.reward_mean = self.reward_mean + delta * batch_count / total_count
        m_a = self.reward_var * self.reward_count
        m_b = batch_var * batch_count
        M2 = m_a + m_b + delta.pow(2) * self.reward_count * batch_count / total_count
        self.reward_var = M2 / total_count
        self.reward_count = total_count

        # Normalize
        return (rewards - self.reward_mean) / (self.reward_var.sqrt() + 1e-8)
```

### Unified Reward Function

```python
# Modification to src/harness/verifiers.py

def compute_unified_reward(
    test_result: VerifierResult,
    lint_result: Optional[VerifierResult],
    diff_changed_lines: int,
    actions_taken: int,
    intrinsic_reward: float,
    scheduler_output: 'SchedulerOutput',
) -> float:
    """
    Unified reward function across all difficulty levels.

    Components:
    1. Extrinsic: test pass/fail, lint, diff quality
    2. Intrinsic: curiosity bonus (scaled by scheduler)
    3. Efficiency: step penalty (constant across levels)

    Args:
        test_result: Result from verifier
        lint_result: Optional lint result
        diff_changed_lines: Number of lines changed
        actions_taken: Steps taken in episode
        intrinsic_reward: Normalized intrinsic reward
        scheduler_output: Scheduler output with scaling factors

    Returns:
        Total reward (float)
    """
    # Extrinsic components (scaled by difficulty)
    scale = scheduler_output.reward_scale

    # Test reward
    if test_result.tests_total > 0:
        test_reward = scale * 2.0 * (test_result.tests_passing / test_result.tests_total)
    else:
        test_reward = 0.0

    # Success bonus (constant across levels - the carrot)
    success_bonus = 10.0 if test_result.passed else 0.0

    # Lint bonus
    lint_reward = 0.5 if (lint_result and lint_result.passed) else 0.0

    # Diff penalty (mild, constant)
    diff_penalty = -0.0001 * diff_changed_lines

    # Step penalty (constant)
    step_penalty = -0.01 * actions_taken

    # Intrinsic component (scaled by scheduler)
    intrinsic_component = scheduler_output.intrinsic_coef * intrinsic_reward

    # Total reward
    total = (
        test_reward +
        success_bonus +
        lint_reward +
        diff_penalty +
        step_penalty +
        intrinsic_component
    )

    return total
```

---

## Implementation Steps

### Phase 1: Foundation (Core Module)

- [ ] **Step 1: Create curriculum module structure**
  - Files: `src/curriculum/__init__.py`, `src/curriculum/config.py`
  - Depends on: None
  - Verify: `from src.curriculum import CurriculumConfig` works

- [ ] **Step 2: Implement difficulty mapping**
  - File: `src/curriculum/difficulty_mapping.py`
  - Depends on: Step 1
  - Verify: `map_difficulty_to_params(50)` returns valid `DifficultyParams`

- [ ] **Step 3: Implement CurriculumScheduler**
  - File: `src/curriculum/scheduler.py`
  - Depends on: Steps 1, 2
  - Verify: Scheduler adjusts difficulty based on mock episode data

- [ ] **Step 4: Implement IntrinsicRewardModule**
  - File: `src/curriculum/intrinsic.py`
  - Depends on: Step 1
  - Verify: Forward pass returns valid rewards and loss

### Phase 2: Environment Integration

- [ ] **Step 5: Add continuous difficulty to HarnessConfig**
  - File: `src/harness/env.py`
  - Depends on: Steps 1-3
  - Verify: `HarnessConfig(continuous_difficulty=50)` accepted

- [ ] **Step 6: Integrate difficulty params into task generation**
  - File: `src/harness/bug_templates.py`
  - Depends on: Steps 2, 5
  - Verify: `create_task(difficulty_params=...)` generates appropriate task

- [ ] **Step 7: Add unified reward function**
  - File: `src/harness/verifiers.py`
  - Depends on: Step 4
  - Verify: `compute_unified_reward()` computes correct total

### Phase 3: Training Loop Integration

- [ ] **Step 8: Add scheduler to JarvisHarnessTrainer**
  - File: `scripts/train_jarvis_harness.py`
  - Depends on: Steps 3, 7
  - Verify: Scheduler state updates after episodes

- [ ] **Step 9: Integrate intrinsic rewards into collect_rollout**
  - File: `scripts/train_jarvis_harness.py`
  - Depends on: Steps 4, 8
  - Verify: Intrinsic rewards logged and added to total reward

- [ ] **Step 10: Add checkpoint save/load for scheduler**
  - File: `scripts/train_jarvis_harness.py`
  - Depends on: Steps 8, 9
  - Verify: Scheduler state persists across training restarts

### Phase 4: CLI Integration

- [ ] **Step 11: Add curriculum CLI arguments**
  - File: `scripts/train_jarvis_harness.py`
  - Depends on: Steps 8-10
  - Verify: `--mode unified-curriculum` activates new system

- [ ] **Step 12: Add metrics logging for curriculum**
  - File: `scripts/train_jarvis_harness.py`
  - Depends on: Step 11
  - Verify: Logs show `difficulty`, `success_rate_ema`, `intrinsic_coef`

### Phase 5: Testing

- [ ] **Step 13: Unit tests for curriculum module**
  - File: `tests/test_curriculum.py`
  - Depends on: Steps 1-4
  - Verify: `pytest tests/test_curriculum.py` passes

- [ ] **Step 14: Integration test with short training run**
  - File: `tests/test_curriculum_integration.py`
  - Depends on: Steps 1-12
  - Verify: 1000-step training completes without errors

- [ ] **Step 15: Regression test against staged baseline**
  - File: `tests/test_curriculum_regression.py`
  - Depends on: Step 14
  - Verify: Success rate at d=10 matches TRIVIAL baseline

### Dependency Graph

```
[1] Module Structure ─┬→ [2] Difficulty Mapping ─┬→ [5] Env Config ─┬→ [6] Task Gen
                      │                          │                  │
                      │                          └→ [3] Scheduler ──┼→ [8] Trainer
                      │                                             │
                      └→ [4] Intrinsic Module ──────────────────────┘
                                                                    │
                                                                    ▼
                                                         [7] Unified Reward
                                                                    │
                                                                    ▼
                                               [9] Rollout Integration
                                                                    │
                                                                    ▼
                                               [10] Checkpointing
                                                                    │
                                                                    ▼
                                               [11] CLI ──→ [12] Logging
                                                                    │
                                                                    ▼
                                               [13] Unit Tests ──→ [14] Integration
                                                                    │
                                                                    ▼
                                               [15] Regression Test
```

---

## Acceptance Criteria

### Functional Requirements
- [ ] Scheduler automatically adjusts difficulty based on success rate
- [ ] Intrinsic rewards computed and added to total reward
- [ ] Difficulty spans d ∈ [1, 100] continuously
- [ ] Scaffolding (hints, focus, vocab) decays with difficulty
- [ ] Interleaved replay prevents catastrophic forgetting
- [ ] Training runs without manual phase transitions

### Performance Requirements
- [ ] No significant FPS degradation vs baseline
- [ ] Memory overhead < 10% for intrinsic module
- [ ] Checkpoint size increase < 1MB for scheduler state

### Quality Requirements
- [ ] All unit tests pass
- [ ] Integration test completes 10k steps
- [ ] Success rate at d=10 matches TRIVIAL baseline (>20%)
- [ ] Difficulty increases over time with training

---

## Test Requirements

### Unit Tests

```python
# tests/test_curriculum.py

def test_difficulty_mapping_bounds():
    """Verify d=1 and d=100 produce valid params."""
    p1 = map_difficulty_to_params(1)
    p100 = map_difficulty_to_params(100)

    assert p1.min_lines <= p1.max_lines
    assert p100.min_lines <= p100.max_lines
    assert p1.force_write_focus_prob > p100.force_write_focus_prob

def test_scheduler_promotes_on_success():
    """Verify scheduler increases difficulty when success_rate > threshold."""
    config = CurriculumConfig(min_episodes_per_level=5, promote_threshold=0.6)
    scheduler = CurriculumScheduler(config)

    for _ in range(5):
        scheduler.record_episode(success=True, difficulty=5)

    output = scheduler.step()
    assert scheduler.state.current_difficulty > 5

def test_scheduler_demotes_on_failure():
    """Verify scheduler decreases difficulty when success_rate < threshold."""
    config = CurriculumConfig(min_episodes_per_level=5, demote_threshold=0.3)
    scheduler = CurriculumScheduler(config)
    scheduler.state.current_difficulty = 30

    for _ in range(5):
        scheduler.record_episode(success=False, difficulty=30)

    output = scheduler.step()
    assert scheduler.state.current_difficulty < 30

def test_intrinsic_module_output_shape():
    """Verify intrinsic module produces correct output shapes."""
    module = IntrinsicRewardModule(obs_dim=512)
    obs = torch.randn(32, 512)

    reward, loss = module(obs)

    assert reward.shape == (32,)
    assert loss.shape == ()

def test_scheduler_state_dict_roundtrip():
    """Verify scheduler state can be saved and loaded."""
    config = CurriculumConfig()
    scheduler1 = CurriculumScheduler(config)
    scheduler1.record_episode(success=True, difficulty=10)
    scheduler1.record_episode(success=False, difficulty=10)

    state = scheduler1.state_dict()

    scheduler2 = CurriculumScheduler(config)
    scheduler2.load_state_dict(state)

    assert scheduler2.state.total_episodes == 2
```

### Integration Tests

```python
# tests/test_curriculum_integration.py

def test_training_with_unified_curriculum():
    """Run short training with unified curriculum."""
    # Setup
    config = CurriculumConfig(initial_difficulty=5)
    scheduler = CurriculumScheduler(config)

    # Mock environment
    for episode in range(100):
        # Simulate episode
        success = random.random() > 0.5
        scheduler.record_episode(success, scheduler.state.current_difficulty)
        output = scheduler.step()

        # Verify output is valid
        assert 1 <= output.sampled_difficulty <= 100
        assert 0.0 <= output.intrinsic_coef <= 1.0
        assert 0.0 <= output.force_focus_prob <= 1.0

    # Verify scheduler made adjustments
    assert scheduler.state.total_promotions + scheduler.state.total_demotions > 0
```

---

## JARVIS Validation

**Score:** 402/420 (EXCELLENT - HABITABLE)

**Key Strengths (per JARVIS):**
1. **Continuous Interpolation:** Eliminates 'Cliffs of Insanity' where jumping stages caused policy collapse
2. **Interleaved Replay:** `replay_easy_prob` prevents catastrophic forgetting - God-Tier architectural decision
3. **Scaffolding Decay:** Explicitly models removal of 'training wheels' (hints, focus, vocab)

**Weaknesses Identified:**
1. **Critic Destabilization (Reward Scaling):** Dynamic `reward_scale` (1.0→1.5) invalidates Critic's previous training
2. **Threshold Hysteresis:** Fixed 0.7/0.3 thresholds risk premature promotion on lucky streaks

**Critical Fix Applied:**

> **REMOVE DYNAMIC REWARD SCALING.** A solved task should always equal `1.0`. The difficulty itself (longer horizons, harder logic) makes the reward harder to obtain. If you absolutely must prioritize hard tasks, scale the *advantage* calculation, not the raw reward.

**Updated Design:**
```python
# BEFORE (problematic):
reward_scale = 1.0 + (d - 1) * 0.005  # 1.0 at d=1, 1.5 at d=100

# AFTER (stable):
reward_scale = 1.0  # Constant - difficulty is intrinsic to task length
```

---

## Environment Resources

- **Python:** 3.12.3 (venv at `.venv/`)
- **GPU:** Not available in WSL development (training requires GPU host)
- **Memory:** Standard development machine

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scheduler oscillates between difficulties | Medium | High | Use EMA smoothing, min_episodes gate |
| Intrinsic rewards overwhelm extrinsic | Medium | High | Decay intrinsic_coef, normalize rewards |
| Catastrophic forgetting at high d | Medium | Medium | Interleaved replay with 10% easy tasks |
| No gradient at very high difficulty | High | Medium | Start with intrinsic-heavy, decay over time |
| Performance degradation | Low | Medium | Profile intrinsic forward pass |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| d=10 success rate | >20% | Eval 100 tasks at d=10 |
| d=50 success rate | >10% | Eval 100 tasks at d=50 |
| Autonomous progression | d increases over 50k steps | Training logs |
| No forgetting | d=10 stays >15% after reaching d=50 | Periodic evaluation |
| FPS maintained | <10% degradation | Profile training loop |

---

Generated by /blueprint
Ready for /goapeshit execution
