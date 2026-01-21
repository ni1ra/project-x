"""
Self-Paced Difficulty Controller

Adjusts difficulty based on the balance of Boredom and Stress signals.
No external scheduler - the agent's own learning dynamics drive progression.

delta_d = K_b * B - K_s * S

- If B > S: Agent is bored -> increase difficulty
- If S > B: Agent is stressed -> decrease difficulty
- If B ~= S ~= 0: Agent in "flow state" -> maintain difficulty
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class ControllerConfig:
    """Configuration for self-paced difficulty controller."""
    # Sensitivity coefficients
    k_boredom: float = 5.0             # K_b - boredom response strength
    k_stress: float = 5.0              # K_s - stress response strength

    # Safeguards against oscillation
    hysteresis_margin: float = 0.1     # Dead-band width (no adjustment if |B-S| < margin)
    min_patience_episodes: int = 30    # Cooldown after difficulty change
    difficulty_jitter_std: float = 5.0 # Gaussian noise for sampling

    # Thresholds for triggering adjustment
    boredom_threshold: float = 0.3     # B must exceed this to increase difficulty
    stress_threshold: float = 0.3      # S must exceed this to decrease difficulty

    # Difficulty bounds
    min_difficulty: int = 1
    max_difficulty: int = 100

    # Thrashing detection
    thrash_window: int = 20            # Episodes to check for oscillation
    thrash_threshold: int = 3          # Max reversals before warning


class SelfPacedController:
    """
    Self-paced difficulty controller using intrinsic Boredom/Stress signals.

    The controller maintains a target difficulty and samples actual task
    difficulty from a Gaussian around the target for smooth transitions.
    """

    def __init__(
        self,
        config: ControllerConfig,
        initial_difficulty: float = 5.0,
    ):
        self.config = config
        self.difficulty_target: float = float(initial_difficulty)
        self.episodes_since_change: int = 0

        # History for thrashing detection
        self._adjustment_history: list[int] = []  # +1 for increase, -1 for decrease
        self._last_boredom: float = 0.0
        self._last_stress: float = 0.0

    def update(self, boredom: float, stress: float) -> int:
        """
        Update difficulty based on Boredom/Stress signals.

        Args:
            boredom: Boredom signal in [0, 1]
            stress: Stress signal in [0, 1]

        Returns:
            Sampled difficulty for next task
        """
        self.episodes_since_change += 1
        self._last_boredom = boredom
        self._last_stress = stress

        # Check patience window
        if self.episodes_since_change < self.config.min_patience_episodes:
            return self._sample_difficulty()

        # Compute drive difference
        delta = boredom - stress

        # Apply hysteresis - only adjust if signal is strong enough
        if abs(delta) < self.config.hysteresis_margin:
            return self._sample_difficulty()

        # Adjust difficulty based on dominant signal
        adjusted = False

        if delta > 0 and boredom > self.config.boredom_threshold:
            # Boredom dominates - increase difficulty
            delta_d = self.config.k_boredom * boredom
            self.difficulty_target = min(
                self.config.max_difficulty,
                self.difficulty_target + delta_d
            )
            self._adjustment_history.append(+1)
            adjusted = True

        elif delta < 0 and stress > self.config.stress_threshold:
            # Stress dominates - decrease difficulty
            delta_d = self.config.k_stress * stress
            self.difficulty_target = max(
                self.config.min_difficulty,
                self.difficulty_target - delta_d
            )
            self._adjustment_history.append(-1)
            adjusted = True

        if adjusted:
            self.episodes_since_change = 0
            self._check_thrashing()

        # Keep history bounded
        if len(self._adjustment_history) > self.config.thrash_window * 2:
            self._adjustment_history = self._adjustment_history[-self.config.thrash_window:]

        return self._sample_difficulty()

    def _sample_difficulty(self) -> int:
        """Sample actual difficulty with jitter for smooth transitions."""
        sampled = np.random.normal(
            self.difficulty_target,
            self.config.difficulty_jitter_std
        )
        return int(np.clip(
            sampled,
            self.config.min_difficulty,
            self.config.max_difficulty
        ))

    def _check_thrashing(self) -> Optional[str]:
        """
        Check for difficulty oscillation (thrashing).

        Returns warning message if thrashing detected.
        """
        if len(self._adjustment_history) < self.config.thrash_window:
            return None

        recent = self._adjustment_history[-self.config.thrash_window:]
        reversals = sum(
            1 for i in range(1, len(recent))
            if recent[i] != recent[i - 1]
        )

        if reversals >= self.config.thrash_threshold:
            return (
                f"Thrashing detected: {reversals} reversals in "
                f"{self.config.thrash_window} episodes. Consider increasing patience."
            )
        return None

    def get_warning(self) -> Optional[str]:
        """Get any current warning condition."""
        return self._check_thrashing()

    @property
    def current_difficulty(self) -> int:
        """Current target difficulty (rounded)."""
        return int(round(self.difficulty_target))

    def state_dict(self) -> dict:
        """Return state for checkpointing."""
        return {
            "difficulty_target": self.difficulty_target,
            "episodes_since_change": self.episodes_since_change,
            "adjustment_history": list(self._adjustment_history),
            "last_boredom": self._last_boredom,
            "last_stress": self._last_stress,
        }

    def load_state_dict(self, state: dict) -> None:
        """Load state from checkpoint."""
        self.difficulty_target = state.get("difficulty_target", 5.0)
        self.episodes_since_change = state.get("episodes_since_change", 0)
        self._adjustment_history = list(state.get("adjustment_history", []))
        self._last_boredom = state.get("last_boredom", 0.0)
        self._last_stress = state.get("last_stress", 0.0)

    def get_metrics(self) -> dict:
        """Get current metrics for logging."""
        return {
            "curriculum/difficulty_target": self.difficulty_target,
            "curriculum/boredom": self._last_boredom,
            "curriculum/stress": self._last_stress,
            "curriculum/episodes_since_change": self.episodes_since_change,
        }
