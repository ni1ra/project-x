"""
Intrinsic Drive Signals: Boredom and Stress

These signals are computed from the agent's own experience to drive
self-paced difficulty adjustment. No external scheduler needed.

Boredom (B) - "I need challenge":
    - Low RND novelty (environment too predictable)
    - Low reward variance (outcomes too stable)
    - Plateaued learning (no improvement despite success)

Stress (S) - "I need relief":
    - High prediction error (overwhelmed by novelty)
    - Low success rate (failing repeatedly)
    - Entropy collapse (giving up, one action dominates)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class BoredomConfig:
    """Configuration for boredom signal computation."""
    # Target levels (boredom rises when below these)
    novelty_target: float = 0.3       # R* - target RND error
    variance_target: float = 0.2      # sigma* - target reward variance
    performance_window: int = 100     # Episodes for delta_perf
    stagnation_threshold: float = 0.05  # Consider stalled if |delta| < this

    # Component weights (must sum to ~1.0 for interpretability)
    w_novelty: float = 0.4            # Weight for novelty component
    w_variance: float = 0.3           # Weight for variance component
    w_plateau: float = 0.3            # Weight for plateau component


@dataclass
class StressConfig:
    """Configuration for stress signal computation."""
    # Thresholds (stress rises when beyond these)
    pred_error_threshold: float = 0.7  # E* - RND error ceiling
    success_target: float = 0.3        # P* - minimum success rate
    entropy_target: float = 0.2        # H* - minimum entropy

    # Component weights
    v_pred_error: float = 0.3          # Weight for prediction error
    v_success: float = 0.4             # Weight for success rate
    v_entropy: float = 0.3             # Weight for entropy


def compute_boredom(
    novelty_ema: float,
    reward_variance: float,
    performance_delta: float,
    config: BoredomConfig,
    success_rate_ema: float = 1.0,
    competence_gate: float = 0.3,
) -> float:
    """
    Compute boredom signal from agent metrics.

    Each component is NORMALIZED to [0,1] before weighting:
    B = w1 * clamp((R* - R) / R*, 0, 1) +      # Novelty deficit ratio
        w2 * clamp((σ* - σ) / σ*, 0, 1) +      # Variance deficit ratio
        w3 * clamp((τ - |Δ|) / τ, 0, 1)        # Stagnation ratio

    Then gated by competence to prevent "bored but failing" spiral.

    Args:
        novelty_ema: EMA of RND prediction error (lower = more predictable)
        reward_variance: Std dev of recent rewards
        performance_delta: Change in success rate over window
            - positive = improving (not bored)
            - near-zero = stalled (bored)
            - negative = regressing (NOT bored - this is stress territory)
        config: Boredom signal configuration
        success_rate_ema: Current success rate for competence gating
        competence_gate: Minimum success rate before boredom can rise

    Returns:
        Boredom signal in [0, 1]
    """
    # Component 1: Low novelty - NORMALIZED to [0,1]
    if config.novelty_target > 0:
        novelty_term = max(0.0, min(1.0,
            (config.novelty_target - novelty_ema) / config.novelty_target
        ))
    else:
        novelty_term = 0.0

    # Component 2: Low variance - NORMALIZED to [0,1]
    if config.variance_target > 0:
        variance_term = max(0.0, min(1.0,
            (config.variance_target - reward_variance) / config.variance_target
        ))
    else:
        variance_term = 0.0

    # Component 3: Learning plateau - NORMALIZED to [0,1]
    # Boredom rises when |delta| is near zero (stagnation), not when declining
    if config.stagnation_threshold > 0:
        plateau_term = max(0.0, min(1.0,
            (config.stagnation_threshold - abs(performance_delta)) / config.stagnation_threshold
        ))
    else:
        plateau_term = 0.0

    B = (
        config.w_novelty * novelty_term +
        config.w_variance * variance_term +
        config.w_plateau * plateau_term
    )

    # Competence gate: prevent "bored but failing" spiral
    # Only allow boredom if agent is actually succeeding
    if competence_gate < 1.0:
        competence = max(0.0, min(1.0,
            (success_rate_ema - competence_gate) / (1.0 - competence_gate)
        ))
        B *= competence

    return min(1.0, B)  # Clamp to [0, 1]


def compute_stress(
    pred_error_ema: float,
    success_rate_ema: float,
    entropy_ema: float,
    config: StressConfig,
) -> float:
    """
    Compute stress signal from agent metrics.

    Each component is NORMALIZED to [0,1] before weighting:
    S = v1 * clamp((E - E*) / (1 - E*), 0, 1) +   # Prediction error excess ratio
        v2 * clamp((P* - P) / P*, 0, 1) +          # Success deficit ratio
        v3 * clamp((H* - H) / H*, 0, 1)            # Entropy deficit ratio

    Args:
        pred_error_ema: EMA of RND prediction error (higher = more overwhelmed)
        success_rate_ema: EMA of task completion rate
        entropy_ema: EMA of policy entropy
        config: Stress signal configuration

    Returns:
        Stress signal in [0, 1]
    """
    # Component 1: High prediction error - NORMALIZED to [0,1]
    # How much above threshold, as fraction of remaining headroom
    headroom = 1.0 - config.pred_error_threshold
    if headroom > 0:
        pred_error_term = max(0.0, min(1.0,
            (pred_error_ema - config.pred_error_threshold) / headroom
        ))
    else:
        pred_error_term = 0.0

    # Component 2: Low success rate - NORMALIZED to [0,1]
    if config.success_target > 0:
        success_term = max(0.0, min(1.0,
            (config.success_target - success_rate_ema) / config.success_target
        ))
    else:
        success_term = 0.0

    # Component 3: Entropy collapse - NORMALIZED to [0,1]
    if config.entropy_target > 0:
        entropy_term = max(0.0, min(1.0,
            (config.entropy_target - entropy_ema) / config.entropy_target
        ))
    else:
        entropy_term = 0.0

    S = (
        config.v_pred_error * pred_error_term +
        config.v_success * success_term +
        config.v_entropy * entropy_term
    )

    return min(1.0, S)  # Clamp to [0, 1]


@dataclass
class SignalTracker:
    """
    Tracks metrics over time for computing Boredom/Stress signals.

    Uses EMA (Exponential Moving Average) for smoothing to prevent
    oscillation from single-episode noise.
    """
    # EMA decay factor (0.1 = 10-episode effective window)
    ema_alpha: float = 0.1

    # Boredom components
    novelty_ema: float = 0.5
    reward_history: list[float] = field(default_factory=list)
    success_history: list[float] = field(default_factory=list)

    # Stress components
    pred_error_ema: float = 0.3
    success_rate_ema: float = 0.5
    entropy_ema: float = 0.5

    # Performance tracking
    performance_window: int = 100
    _episode_count: int = 0

    def update(
        self,
        success: bool,
        reward: float,
        novelty: float,
        entropy: float,
        pred_error: Optional[float] = None,
    ) -> None:
        """
        Update all tracked metrics after an episode.

        Args:
            success: Whether the episode succeeded
            reward: Total reward for the episode
            novelty: RND novelty signal (prediction error)
            entropy: Policy entropy
            pred_error: Optional separate prediction error (defaults to novelty)
        """
        self._episode_count += 1

        # Update EMAs
        self.novelty_ema = self._ema_update(self.novelty_ema, novelty)
        self.success_rate_ema = self._ema_update(
            self.success_rate_ema, 1.0 if success else 0.0
        )
        self.entropy_ema = self._ema_update(self.entropy_ema, entropy)
        self.pred_error_ema = self._ema_update(
            self.pred_error_ema,
            pred_error if pred_error is not None else novelty
        )

        # Track history for variance calculation
        self.reward_history.append(reward)
        self.success_history.append(1.0 if success else 0.0)

        # Keep history bounded
        max_history = self.performance_window * 2
        if len(self.reward_history) > max_history:
            self.reward_history = self.reward_history[-max_history:]
            self.success_history = self.success_history[-max_history:]

    def _ema_update(self, current: float, new_value: float) -> float:
        """Update EMA with new value."""
        return (1 - self.ema_alpha) * current + self.ema_alpha * new_value

    def get_reward_variance(self) -> float:
        """Compute variance of recent rewards."""
        if len(self.reward_history) < 2:
            return 0.5  # Default to neutral
        return float(np.std(self.reward_history[-self.performance_window:]))

    def get_performance_delta(self) -> float:
        """
        Compute change in success rate over the performance window.

        Returns:
            Positive = improving, Negative = declining, Zero = stable
        """
        if len(self.success_history) < self.performance_window:
            return 0.0  # Not enough data

        window = self.performance_window
        recent = self.success_history[-window // 2:]
        older = self.success_history[-window:-window // 2]

        if not older or not recent:
            return 0.0

        return float(np.mean(recent) - np.mean(older))

    def compute_signals(
        self,
        boredom_config: BoredomConfig,
        stress_config: StressConfig,
        competence_gate: float = 0.3,
    ) -> tuple[float, float]:
        """
        Compute both boredom and stress signals.

        Args:
            boredom_config: Configuration for boredom computation
            stress_config: Configuration for stress computation
            competence_gate: Minimum success rate before boredom can rise

        Returns:
            Tuple of (boredom, stress) in [0, 1]
        """
        boredom = compute_boredom(
            novelty_ema=self.novelty_ema,
            reward_variance=self.get_reward_variance(),
            performance_delta=self.get_performance_delta(),
            config=boredom_config,
            success_rate_ema=self.success_rate_ema,
            competence_gate=competence_gate,
        )

        stress = compute_stress(
            pred_error_ema=self.pred_error_ema,
            success_rate_ema=self.success_rate_ema,
            entropy_ema=self.entropy_ema,
            config=stress_config,
        )

        return boredom, stress

    def state_dict(self) -> dict:
        """Return state for checkpointing."""
        return {
            "novelty_ema": self.novelty_ema,
            "pred_error_ema": self.pred_error_ema,
            "success_rate_ema": self.success_rate_ema,
            "entropy_ema": self.entropy_ema,
            "reward_history": list(self.reward_history),
            "success_history": list(self.success_history),
            "episode_count": self._episode_count,
        }

    def load_state_dict(self, state: dict) -> None:
        """Load state from checkpoint."""
        self.novelty_ema = state.get("novelty_ema", 0.5)
        self.pred_error_ema = state.get("pred_error_ema", 0.3)
        self.success_rate_ema = state.get("success_rate_ema", 0.5)
        self.entropy_ema = state.get("entropy_ema", 0.5)
        self.reward_history = list(state.get("reward_history", []))
        self.success_history = list(state.get("success_history", []))
        self._episode_count = state.get("episode_count", 0)
