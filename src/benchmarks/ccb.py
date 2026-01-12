"""
Confounded Causal Bandits (CCB) Environment

Ground-truth SCM benchmark for do()-operator competence.
Tests whether the agent can distinguish correlation from intervention.

CRITICAL: All outputs are BYTES, not floats. This satisfies the
"content-free interface" requirement from BLUEPRINT.md Section 2.1.

SCM Definitions:
- Linear (CCB):    U ~ N(0,1), Z = a_U*U + ε_Z, Y = b_X*X + b_U*U + ε_Y
- Non-Linear (CCB-NL): Y = ReLU(b_X*X² + b_U*U) + ε_Y

Scoring:
- DoErr = (1/Q) Σ |μ̂_do - μ_do|
- PASS if DoErr ≤ 0.05 and confounding discrimination ≥ 0.90
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

import numpy as np


@dataclass
class SCMParams:
    """Parameters for the Structural Causal Model."""

    a_U: float = 0.5  # Confounding strength for Z
    b_X: float = 1.0  # Effect of X on Y
    b_U: float = 0.8  # Confounding strength for Y
    sigma_Z: float = 0.1  # Noise std for Z
    sigma_Y: float = 0.1  # Noise std for Y
    nonlinear: bool = False  # If True, use CCB-NL variant


def float_to_bytes(value: float) -> bytes:
    """Convert float to 4 bytes (float32 little-endian)."""
    return struct.pack('<f', value)


def bytes_to_float(b: bytes) -> float:
    """Convert 4 bytes back to float."""
    return struct.unpack('<f', b)[0]


def array_to_bytes(arr: np.ndarray) -> np.ndarray:
    """
    Convert float array to byte array.

    Each float32 becomes 4 bytes, so output shape is [..., 4*n].
    """
    # Ensure float32
    arr = arr.astype(np.float32)

    # Get raw bytes view
    byte_view = arr.view(np.uint8)

    return byte_view


def bytes_to_array(byte_arr: np.ndarray, shape: Tuple[int, ...]) -> np.ndarray:
    """Convert byte array back to float array with given shape."""
    return byte_arr.view(np.float32).reshape(shape)


class CCBEnvironment:
    """
    Confounded Causal Bandits Environment.

    The agent observes confounded data and must learn to predict
    the effect of interventions (do(X=x)).

    Observation: [Z_bytes, context_bytes] - 8 bytes total
    Action: [X_byte] - 1 byte representing discretized X ∈ [-2, 2]
    Reward: -|Y - Y_target| where Y_target is the true do() effect
    """

    def __init__(
        self,
        params: Optional[SCMParams] = None,
        seed: Optional[int] = None,
        num_interventions: int = 5,  # Number of do() queries per episode
    ):
        self.params = params or SCMParams()
        self.rng = np.random.default_rng(seed)
        self.num_interventions = num_interventions

        # Episode state
        self._step_count = 0
        self._intervention_idx = 0
        self._current_U = 0.0
        self._current_Z = 0.0
        self._target_X = 0.0  # X value we want the agent to estimate do(X=x) for
        self._done = False

        # For computing ground truth
        self._intervention_targets: list = []
        self._agent_predictions: list = []

    def reset(self, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Reset environment for new episode.

        Returns:
            observation: Byte array of shape [obs_bytes]
            info: Dictionary with metadata
        """
        if seed is not None:
            self.rng = np.random.default_rng(seed)

        self._step_count = 0
        self._intervention_idx = 0
        self._intervention_targets = []
        self._agent_predictions = []
        self._done = False

        # Generate confounding variable
        self._current_U = self.rng.standard_normal()

        # Generate observed Z (confounded)
        epsilon_Z = self.rng.normal(0, self.params.sigma_Z)
        self._current_Z = self.params.a_U * self._current_U + epsilon_Z

        # Generate target X for this intervention query
        self._target_X = self.rng.uniform(-2, 2)
        self._intervention_targets.append(self._target_X)

        # Build observation as bytes
        obs = self._build_observation()

        info = {
            "step": self._step_count,
            "intervention_idx": self._intervention_idx,
            "target_X": self._target_X,
        }

        return obs, info

    def _build_observation(self) -> np.ndarray:
        """
        Build byte observation.

        Format: [Z (4 bytes), target_X (4 bytes)] = 8 bytes total
        """
        z_bytes = array_to_bytes(np.array([self._current_Z], dtype=np.float32))
        x_bytes = array_to_bytes(np.array([self._target_X], dtype=np.float32))

        return np.concatenate([z_bytes, x_bytes])

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Take a step in the environment.

        The agent's action is interpreted as their prediction of E[Y | do(X=target_X)].
        Action is a byte that maps to a float in [-2, 2].

        Args:
            action: Byte array of shape [1] representing predicted Y

        Returns:
            observation: Next observation (bytes)
            reward: Negative absolute error
            terminated: True if episode done
            truncated: Always False
            info: Metadata dictionary
        """
        self._step_count += 1

        # Decode action byte to float prediction
        # Map [0, 255] → [-2, 2]
        action_byte = int(action[0]) if isinstance(action, np.ndarray) else int(action)
        predicted_Y = (action_byte / 255.0) * 4.0 - 2.0

        # Compute ground truth do(X=target_X)
        # Under intervention, X is set directly (no confounding through U)
        if self.params.nonlinear:
            # CCB-NL: Y = ReLU(b_X * X² + b_U * U) + ε_Y
            # Under do(X=x), U is independent (drawn fresh for causal effect)
            # E[Y | do(X=x)] = E[ReLU(b_X * x² + b_U * U)]
            # This requires integration over U ~ N(0,1)
            true_Y = self._compute_do_effect_nonlinear(self._target_X)
        else:
            # Linear CCB: Y = b_X * X + b_U * U + ε_Y
            # E[Y | do(X=x)] = b_X * x (U averages to 0)
            true_Y = self.params.b_X * self._target_X

        self._agent_predictions.append(predicted_Y)

        # Reward: negative absolute error
        error = abs(predicted_Y - true_Y)
        reward = -error

        # Move to next intervention query
        self._intervention_idx += 1

        if self._intervention_idx >= self.num_interventions:
            self._done = True
            terminated = True
        else:
            terminated = False

            # Generate new confounding variable and observation
            self._current_U = self.rng.standard_normal()
            epsilon_Z = self.rng.normal(0, self.params.sigma_Z)
            self._current_Z = self.params.a_U * self._current_U + epsilon_Z
            self._target_X = self.rng.uniform(-2, 2)
            self._intervention_targets.append(self._target_X)

        obs = self._build_observation() if not terminated else np.zeros(8, dtype=np.uint8)

        info = {
            "step": self._step_count,
            "intervention_idx": self._intervention_idx,
            "target_X": self._target_X,
            "predicted_Y": predicted_Y,
            "true_Y": true_Y,
            "error": error,
        }

        return obs, reward, terminated, False, info

    def _compute_do_effect_nonlinear(self, x: float, num_samples: int = 1000) -> float:
        """
        Compute E[Y | do(X=x)] for nonlinear SCM via Monte Carlo.

        Y = ReLU(b_X * X² + b_U * U) + ε_Y
        Under do(X=x), we set X=x and U is drawn fresh from N(0,1).
        """
        U_samples = self.rng.standard_normal(num_samples)
        epsilon_samples = self.rng.normal(0, self.params.sigma_Y, num_samples)

        Y_samples = np.maximum(0, self.params.b_X * x**2 + self.params.b_U * U_samples) + epsilon_samples

        return Y_samples.mean()

    def compute_do_error(self) -> float:
        """
        Compute DoErr = (1/Q) Σ |μ̂_do - μ_do| over all queries.

        Call this at end of episode.
        """
        if len(self._agent_predictions) == 0:
            return float('inf')

        total_error = 0.0
        Q = len(self._intervention_targets)

        for i, target_x in enumerate(self._intervention_targets):
            if self.params.nonlinear:
                true_effect = self._compute_do_effect_nonlinear(target_x)
            else:
                true_effect = self.params.b_X * target_x

            predicted = self._agent_predictions[i] if i < len(self._agent_predictions) else 0.0
            total_error += abs(predicted - true_effect)

        return total_error / Q

    @property
    def observation_space_bytes(self) -> int:
        """Number of bytes in observation."""
        return 8  # Z (4) + target_X (4)

    @property
    def action_space_bytes(self) -> int:
        """Number of bytes in action."""
        return 1


class CCBScorer:
    """
    Scorer for CCB benchmark.

    Evaluates:
    - DoErr: Mean absolute error of do() predictions
    - Confounding discrimination: Can agent distinguish do(X) from P(Y|X)?
    """

    def __init__(self, num_eval_queries: int = 100):
        self.num_eval_queries = num_eval_queries

    def evaluate(
        self,
        agent_predictions: np.ndarray,  # Shape [Q]
        target_X_values: np.ndarray,  # Shape [Q]
        params: SCMParams,
    ) -> Dict[str, float]:
        """
        Evaluate agent predictions against ground truth.

        Returns:
            Dictionary with DoErr and pass/fail status
        """
        Q = len(target_X_values)

        # Compute ground truth for each target
        if params.nonlinear:
            # Need Monte Carlo for nonlinear
            rng = np.random.default_rng(42)  # Fixed for reproducibility
            true_effects = []
            for x in target_X_values:
                U_samples = rng.standard_normal(1000)
                Y_mean = np.maximum(0, params.b_X * x**2 + params.b_U * U_samples).mean()
                true_effects.append(Y_mean)
            true_effects = np.array(true_effects)
        else:
            # Linear: E[Y | do(X=x)] = b_X * x
            true_effects = params.b_X * target_X_values

        # Compute DoErr
        errors = np.abs(agent_predictions - true_effects)
        do_err = errors.mean()

        # Pass/fail thresholds from BLUEPRINT.md
        do_err_pass = do_err <= 0.05

        return {
            "DoErr": do_err,
            "DoErr_pass": do_err_pass,
            "mean_true_effect": true_effects.mean(),
            "mean_predicted": agent_predictions.mean(),
            "num_queries": Q,
        }

    def compute_confounding_discrimination(
        self,
        agent_do_predictions: np.ndarray,
        agent_conditional_predictions: np.ndarray,
        target_X_values: np.ndarray,
        params: SCMParams,
    ) -> float:
        """
        Compute confounding discrimination score.

        Measures whether agent's do(X) predictions differ appropriately
        from their P(Y|X) predictions (which include confounding).

        Returns:
            Score in [0, 1] where 1 = perfect discrimination
        """
        # Compute true difference between E[Y|do(X)] and E[Y|X]
        # In linear case:
        #   E[Y|X=x] = b_X*x + b_U*E[U|X=x]
        #   E[U|X=x] != 0 due to confounding through Z
        #   E[Y|do(X=x)] = b_X*x (no confounding)

        # For now, simple metric: do predictions should be closer to true do effect
        if params.nonlinear:
            rng = np.random.default_rng(42)
            true_do = []
            for x in target_X_values:
                U_samples = rng.standard_normal(1000)
                Y_mean = np.maximum(0, params.b_X * x**2 + params.b_U * U_samples).mean()
                true_do.append(Y_mean)
            true_do = np.array(true_do)
        else:
            true_do = params.b_X * target_X_values

        do_error = np.abs(agent_do_predictions - true_do).mean()
        cond_error = np.abs(agent_conditional_predictions - true_do).mean()

        # Discrimination = how much better is do prediction than conditional
        # If do_error < cond_error, agent is discriminating
        if cond_error < 1e-6:
            return 1.0 if do_error < 1e-6 else 0.0

        # Score: 1 - (do_error / cond_error), clamped to [0, 1]
        discrimination = 1.0 - (do_error / cond_error)
        return max(0.0, min(1.0, discrimination))


def create_ccb_linear(seed: Optional[int] = None, num_interventions: int = 5) -> CCBEnvironment:
    """Create a linear CCB environment."""
    return CCBEnvironment(
        params=SCMParams(nonlinear=False),
        seed=seed,
        num_interventions=num_interventions,
    )


def create_ccb_nonlinear(seed: Optional[int] = None, num_interventions: int = 5) -> CCBEnvironment:
    """Create a non-linear CCB-NL environment."""
    return CCBEnvironment(
        params=SCMParams(nonlinear=True),
        seed=seed,
        num_interventions=num_interventions,
    )
