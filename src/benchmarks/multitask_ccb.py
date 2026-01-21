"""
Multi-Task CCB Environment for OD-NDT Evaluation

Implements the TaskEnvironment protocol required by the OD-NDT harness.
Each task_id corresponds to a unique SCM with different (b_X, b_U) coefficients.

Purpose: Test "Persistent Emergence" - whether K_eff stays elevated when
the brain must adapt to new task dynamics, unlike single-task CCB where
K_eff correctly habituates.

Reference: BLUEPRINT.md Section 4.3 (OD-NDT Protocol)
"""

from __future__ import annotations

from typing import Tuple, Dict, Any, Optional, List
from dataclasses import dataclass

import torch
import torch.nn as nn
import numpy as np


# =============================================================================
# GPU-Native Multi-Task CCB Environment (for training)
# =============================================================================

class TorchMultiTaskCCBEnvironment(nn.Module):
    """
    GPU-native vectorized Multi-Task CCB environment.

    Like TorchCCBEnvironment but with task diversity:
    - Each environment slot can have DIFFERENT (b_X, b_U) coefficients
    - Tasks switch periodically (every switch_interval steps)
    - Tests whether K_eff stays elevated under task diversity

    Purpose: Train for PERSISTENT EMERGENCE by maintaining task variety.
    """

    def __init__(
        self,
        num_envs: int = 8192,
        num_tasks: int = 100,
        num_interventions: int = 5,
        b_X_range: Tuple[float, float] = (0.2, 0.8),
        b_U_range: Tuple[float, float] = (0.1, 0.5),
        switch_interval: int = 500,  # Switch tasks every N steps
        device: str = "cuda",
        seed: int = 42,
    ):
        super().__init__()
        self.num_envs = num_envs
        self.num_tasks = num_tasks
        self.num_interventions = num_interventions
        self.b_X_range = b_X_range
        self.b_U_range = b_U_range
        self.switch_interval = switch_interval
        self.device = torch.device(device)

        # Generate task bank
        torch.manual_seed(seed)
        self.register_buffer("task_b_X", torch.zeros(num_tasks))
        self.register_buffer("task_b_U", torch.zeros(num_tasks))

        # Initialize task parameters with diversity (on correct device)
        task_b_X = torch.linspace(b_X_range[0], b_X_range[1], num_tasks, device=self.device)
        task_b_U = torch.linspace(b_U_range[0], b_U_range[1], num_tasks, device=self.device)
        # Shuffle to avoid correlation between task_id and params
        perm = torch.randperm(num_tasks, device=self.device)
        self.task_b_X = task_b_X[perm]
        self.task_b_U = task_b_U[perm]

        # State tensors (on GPU)
        self.register_buffer("current_task_ids", torch.zeros(num_envs, dtype=torch.long, device=self.device))
        self.register_buffer("current_b_X", torch.zeros(num_envs, device=self.device))
        self.register_buffer("current_b_U", torch.zeros(num_envs, device=self.device))
        self.register_buffer("current_Z", torch.zeros(num_envs, device=self.device))
        self.register_buffer("target_X", torch.zeros(num_envs, device=self.device))
        self.register_buffer("step_count", torch.zeros(num_envs, dtype=torch.long, device=self.device))
        self.register_buffer("global_step", torch.tensor(0, dtype=torch.long, device=self.device))

        # JARVIS 420 FIX: Track prev_true_Y for 1-shot task identification
        # Sign Problem: |Error| loses direction. Agent needs (prev_X, prev_Y) pair
        # to compute b_X via: Y = b_X * X² + noise → b_X ≈ Y / X²
        self.register_buffer("prev_true_Y", torch.zeros(num_envs, device=self.device))
        # Legacy: prev_error (kept for compatibility but not in obs)
        self.register_buffer("prev_error", torch.zeros(num_envs, device=self.device))
        # JARVIS 420 FIX: Track prev_X so agent can solve: Error = |true_Y - predicted_Y|
        # where true_Y = b_X * prev_X² + b_U * U
        # With prev_X and Error, agent can estimate b_X for task identification
        self.register_buffer("prev_X", torch.zeros(num_envs, device=self.device))
        # Legacy: prev_action (now provided as separate input to brain)
        self.register_buffer("prev_action", torch.zeros(num_envs, device=self.device))

    def _assign_tasks(self, mask: Optional[torch.Tensor] = None):
        """Assign random tasks to environments (or subset via mask)."""
        if mask is None:
            # Assign to all envs
            task_ids = torch.randint(0, self.num_tasks, (self.num_envs,), device=self.device)
            self.current_task_ids = task_ids
            self.current_b_X = self.task_b_X[task_ids]
            self.current_b_U = self.task_b_U[task_ids]
        else:
            # Assign only to masked envs
            num_to_assign = mask.sum().item()
            new_task_ids = torch.randint(0, self.num_tasks, (int(num_to_assign),), device=self.device)
            self.current_task_ids[mask] = new_task_ids
            self.current_b_X[mask] = self.task_b_X[new_task_ids]
            self.current_b_U[mask] = self.task_b_U[new_task_ids]

    def reset(self) -> torch.Tensor:
        """Reset all environments with random task assignments."""
        self._assign_tasks()
        self.current_Z = torch.randn(self.num_envs, device=self.device) * 0.5
        self.target_X = torch.rand(self.num_envs, device=self.device) * 4.0 - 2.0
        self.step_count.zero_()
        self.global_step.zero_()
        self.prev_true_Y.zero_()  # JARVIS 420 FIX: Reset for task identification
        self.prev_error.zero_()  # Legacy
        self.prev_X.zero_()  # JARVIS 420 FIX: Reset prev_X for task identification
        self.prev_action.zero_()  # Legacy
        return self._build_obs()

    def _build_obs(self) -> torch.Tensor:
        """Build byte observations from state.

        BLINDFOLD TEST: Observation is ONLY [Z_byte, X_byte] - 2 bytes.

        NO prev_true_Y or prev_X! The agent must learn causal structure
        from the REWARD SIGNAL alone, not from being given the answer.

        Previous implementation leaked prev_true_Y which converted causal
        discovery into simple arithmetic (b_X ≈ Y/X²). That's cheating.

        With blindfold: DoErr must stay low using ONLY:
        - Current confound Z
        - Target intervention X
        - Reward signal (negative absolute error)

        This is the TRUE test of causal understanding.
        """
        z_byte = ((self.current_Z.clamp(-2, 2) + 2) / 4 * 255).round().long()
        x_byte = ((self.target_X.clamp(-2, 2) + 2) / 4 * 255).round().long()
        return torch.stack([z_byte, x_byte], dim=1)

    def _compute_nonlinear_expectation(self, x: torch.Tensor, b_X: torch.Tensor, b_U: torch.Tensor) -> torch.Tensor:
        """
        Compute E[ReLU(b_X * x² + b_U * U)] analytically for U ~ N(0,1) (Gaussian).

        JARVIS PHYSICS FIX: BLUEPRINT specifies U ~ N(0,1), not Uniform.
        For ReLU(a + b*U) where U ~ N(0,1):
        E[ReLU(a + b*U)] = a * Φ(a/|b|) + |b| * φ(a/|b|)

        where Φ is standard normal CDF, φ is standard normal PDF.
        """
        a = b_X * x ** 2  # Always >= 0
        b = b_U.clamp(min=1e-8)  # Positive confounding coefficient

        # z = a / |b|
        z = a / b

        # Standard normal CDF: Φ(z) = 0.5 * (1 + erf(z / sqrt(2)))
        sqrt2 = 1.4142135623730951
        cdf = 0.5 * (1.0 + torch.erf(z / sqrt2))

        # Standard normal PDF: φ(z) = exp(-z²/2) / sqrt(2π)
        sqrt_2pi = 2.5066282746310002
        pdf = torch.exp(-0.5 * z ** 2) / sqrt_2pi

        # E[ReLU(a + bU)] = a * Φ(z) + |b| * φ(z)
        result = a * cdf + b * pdf

        # Handle edge case where b is very small → E[ReLU(a)] = ReLU(a)
        small_b_mask = b_U.abs() < 1e-8
        return torch.where(small_b_mask, torch.relu(a), result)

    def step(self, actions: torch.Tensor) -> tuple:
        """Step all environments with task-specific dynamics."""
        actions = actions.view(-1).float()

        # DEEP-DEBUG FIX: Extended action range [0, 4.0] to cover full target range
        # Previous: [0.1, 1.65] couldn't represent targets up to 3.2
        predicted_Y = actions / 255.0 * 4.0  # [0, 4.0]

        # True do-effect varies by task!
        true_Y = self._compute_nonlinear_expectation(
            self.target_X, self.current_b_X, self.current_b_U
        )

        # Compute error for feedback loop
        error = (predicted_Y - true_Y).abs()

        # Reward: negative absolute error
        rewards = -error

        # JARVIS 420 FIX (Sign Problem): Store true_Y for 1-shot task identification
        # Agent receives (prev_X, prev_Y) pair → can compute b_X directly
        self.prev_true_Y = true_Y.clone()
        # JARVIS 420 FIX: Store current X BEFORE generating new states
        self.prev_X = self.target_X.clone()
        # Legacy: keep for compatibility
        self.prev_error = error
        self.prev_action = actions.float()

        # Step count
        self.step_count += 1
        self.global_step += 1
        dones = self.step_count >= self.num_interventions

        # Generate new states
        new_Z = torch.randn(self.num_envs, device=self.device) * 0.5
        new_X = torch.rand(self.num_envs, device=self.device) * 4.0 - 2.0

        # Check for task switching (periodically assign new tasks)
        switch_due = (self.global_step % self.switch_interval == 0).item()
        if switch_due:
            self._assign_tasks()
            self.prev_true_Y.zero_()  # JARVIS 420 FIX: Reset on task switch
            self.prev_X.zero_()  # JARVIS 420 FIX: Reset prev_X on task switch
            self.prev_error.zero_()  # Legacy
            self.prev_action.zero_()  # Legacy

        # Update state
        self.current_Z = new_Z
        self.target_X = new_X
        self.step_count = torch.where(dones, torch.zeros_like(self.step_count), self.step_count)

        obs = self._build_obs()

        infos = {
            "predicted_Y": predicted_Y,
            "true_Y": true_Y,
            "error": error,
            "task_ids": self.current_task_ids,
            "b_X": self.current_b_X,
        }

        return obs, rewards, dones, infos

    @property
    def observation_space_bytes(self) -> int:
        return 2  # BLINDFOLD TEST: [Z, X] only - no answer leak

    @property
    def action_space_bytes(self) -> int:
        return 1


@dataclass
class MultiTaskConfig:
    """Configuration for multi-task CCB environment."""
    num_tasks: int = 1000         # EXPANDED: 1000 tasks for statistical validity
    steps_per_task: int = 10      # Steps before episode terminates
    b_X_range: Tuple[float, float] = (0.2, 0.8)  # Range for b_X coefficient
    b_U_range: Tuple[float, float] = (0.1, 0.5)  # Range for b_U coefficient
    success_threshold: float = 0.2  # Prediction error threshold for success
    nonlinear: bool = True        # Use CCB-NL (nonlinear) tasks
    seed: int = 42                # For reproducible task generation
    device: str = "cpu"


class MultiTaskCCBEnvironment:
    """
    Multi-Task CCB Environment implementing the TaskEnvironment protocol.

    Each task_id maps to a unique (b_X, b_U) coefficient pair.
    The oracle provides correct do-intervention predictions for any task.

    This tests whether the brain can:
    1. Quickly adapt to new task dynamics from a single demonstration
    2. Maintain plasticity (K_eff elevated) due to task diversity

    Protocol:
        TaskEnvironment.reset(task_id) → Initialize specific task
        TaskEnvironment.step(action) → Execute action, get reward
        TaskEnvironment.get_oracle_action(obs) → Expert action for demo
        TaskEnvironment.get_task_success() → Did the agent solve the task?
    """

    def __init__(self, config: Optional[MultiTaskConfig] = None):
        self.config = config or MultiTaskConfig()
        self.device = torch.device(self.config.device)

        # Generate task bank with deterministic seeding
        self._generate_task_bank()

        # Episode state
        self._current_task_id: int = 0
        self._current_b_X: float = 0.4
        self._current_b_U: float = 0.32
        self._step_count: int = 0
        self._cumulative_error: float = 0.0
        self._current_Z: float = 0.0
        self._current_X: float = 0.0
        # JARVIS 420 FIX: Track prev_Y and prev_X for 4-byte observation format
        self._prev_true_Y: float = 0.0
        self._prev_X: float = 0.0

        # Random state for env dynamics
        self.rng = np.random.default_rng(self.config.seed)

    def _generate_task_bank(self):
        """Generate the task bank with unique (b_X, b_U) for each task."""
        rng = np.random.default_rng(self.config.seed)

        self.task_bank = {}
        for task_id in range(self.config.num_tasks):
            b_X = rng.uniform(*self.config.b_X_range)
            b_U = rng.uniform(*self.config.b_U_range)
            self.task_bank[task_id] = {'b_X': b_X, 'b_U': b_U}

    def reset(self, task_id: Optional[int] = None) -> Tuple[torch.Tensor, Dict[str, Any]]:
        """
        Reset to a specific task.

        Args:
            task_id: Which task to initialize (0 to num_tasks-1)

        Returns:
            obs: Observation tensor [obs_dim]
            info: Metadata dictionary
        """
        if task_id is None:
            task_id = self.rng.integers(0, self.config.num_tasks)

        self._current_task_id = task_id
        task = self.task_bank[task_id]
        self._current_b_X = task['b_X']
        self._current_b_U = task['b_U']

        self._step_count = 0
        self._cumulative_error = 0.0
        # JARVIS 420 FIX: Reset prev tracking for 4-byte obs
        self._prev_true_Y = 0.0
        self._prev_X = 0.0

        # Generate initial observation
        self._current_Z = self.rng.standard_normal() * 0.5
        self._current_X = self.rng.uniform(-2, 2)

        obs = self._build_obs()

        info = {
            'task_id': task_id,
            'b_X': self._current_b_X,
            'b_U': self._current_b_U,
        }

        return obs, info

    def _build_obs(self) -> torch.Tensor:
        """Build 2-byte observation tensor from current state.

        BLINDFOLD TEST: Only [Z_byte, X_byte] - NO prev_true_Y!
        The agent must learn causal structure from reward signal alone.
        """
        # Quantize Z and X to bytes [0, 255]
        z_byte = int(np.clip((self._current_Z + 2) / 4 * 255, 0, 255))
        x_byte = int(np.clip((self._current_X + 2) / 4 * 255, 0, 255))

        return torch.tensor([z_byte, x_byte], dtype=torch.long, device=self.device)

    def _compute_true_effect(self, x: float) -> float:
        """
        Compute E[Y | do(X=x)] for current task.

        For nonlinear: E[ReLU(b_X * x² + b_U * U)] via analytic formula
        For linear: b_X * x
        """
        if self.config.nonlinear:
            return self._compute_nonlinear_expectation(x)
        else:
            return self._current_b_X * x

    def _compute_nonlinear_expectation(self, x: float) -> float:
        """
        Compute E[ReLU(b_X * x² + b_U * U)] analytically.

        For ReLU(a + b*Z) where Z ~ N(0,1):
        E[ReLU(a + b*Z)] = a * Φ(a/|b|) + |b| * φ(a/|b|)
        """
        a = self._current_b_X * x ** 2
        b = self._current_b_U

        if abs(b) < 1e-8:
            return max(0, a)

        z = a / abs(b)

        # Standard normal CDF and PDF
        from scipy.stats import norm
        cdf = norm.cdf(z)
        pdf = norm.pdf(z)

        return a * cdf + abs(b) * pdf

    def step(self, action: torch.Tensor) -> Tuple[torch.Tensor, float, bool, bool, Dict[str, Any]]:
        """
        Execute one step.

        Args:
            action: Action tensor (predicted Y as byte)

        Returns:
            obs: Next observation
            reward: Step reward (negative absolute error)
            terminated: True if episode done
            truncated: Always False
            info: Step metadata
        """
        self._step_count += 1

        # Decode action to prediction
        action_byte = int(action.item()) if action.numel() == 1 else int(action[0].item())

        if self.config.nonlinear:
            # Multi-task CCB-NL output range: [0.0, 4.0]
            # (Tasks can reach ~3.2+; the legacy [0.1, 1.65] range is too small.)
            predicted_Y = action_byte / 255.0 * 4.0
        else:
            # Linear output range: [-2, 2]
            predicted_Y = action_byte / 255.0 * 4.0 - 2.0

        # Compute true do-effect
        true_Y = self._compute_true_effect(self._current_X)

        # Error and reward
        error = abs(predicted_Y - true_Y)
        self._cumulative_error += error
        reward = -error

        # Check termination
        terminated = self._step_count >= self.config.steps_per_task

        # JARVIS 420 FIX: Store (prev_X, prev_Y) BEFORE updating state
        # This enables 4-byte obs for task identification
        self._prev_true_Y = true_Y
        self._prev_X = self._current_X

        # Generate next observation (if not terminated)
        if not terminated:
            self._current_Z = self.rng.standard_normal() * 0.5
            self._current_X = self.rng.uniform(-2, 2)

        obs = self._build_obs()

        info = {
            'step': self._step_count,
            'predicted_Y': predicted_Y,
            'true_Y': true_Y,
            'error': error,
        }

        return obs, reward, terminated, False, info

    def get_oracle_action(self, obs: torch.Tensor) -> torch.Tensor:
        """
        Get expert action for demonstration.

        The oracle knows the true SCM and provides the optimal prediction.

        Args:
            obs: Current observation [2] (Z_byte, X_byte)

        Returns:
            action: Oracle action tensor [1]
        """
        # Decode X from observation
        x_byte = obs[1].item() if obs.dim() == 1 else obs[0, 1].item()
        x_float = x_byte / 255.0 * 4.0 - 2.0  # [-2, 2]

        # Compute true do-effect
        true_Y = self._compute_true_effect(x_float)

        # Encode as action byte
        if self.config.nonlinear:
            # Multi-task CCB-NL: encode to [0.0, 4.0] range
            action_byte = int(np.clip(true_Y / 4.0 * 255, 0, 255))
        else:
            # Linear: encode to [-2, 2] range
            action_byte = int(np.clip((true_Y + 2) / 4 * 255, 0, 255))

        return torch.tensor([action_byte], dtype=torch.long, device=self.device)

    def get_task_success(self) -> bool:
        """
        Check if the current task was solved successfully.

        Success is defined as average error below threshold.
        """
        if self._step_count == 0:
            return False

        avg_error = self._cumulative_error / self._step_count
        return avg_error < self.config.success_threshold


def create_multitask_ccb(
    num_tasks: int = 1000,
    nonlinear: bool = True,
    device: str = "cpu",
    **kwargs,
) -> MultiTaskCCBEnvironment:
    """Factory function to create multi-task CCB environment."""
    config = MultiTaskConfig(
        num_tasks=num_tasks,
        nonlinear=nonlinear,
        device=device,
        **kwargs,
    )
    return MultiTaskCCBEnvironment(config)


def get_demo_and_test_task_ids(
    num_demo: int = 1,
    num_test: int = 100,
    num_tasks: int = 1000,
    seed: int = 42,
) -> Tuple[list, list]:
    """
    Get disjoint demo and test task IDs.

    Demo tasks are for demonstration collection.
    Test tasks are held-out for evaluation.
    """
    rng = np.random.default_rng(seed)
    all_ids = list(range(num_tasks))
    rng.shuffle(all_ids)

    demo_ids = all_ids[:num_demo]
    test_ids = all_ids[num_demo:num_demo + num_test]

    return demo_ids, test_ids


# =============================================================================
# Quick test
# =============================================================================

if __name__ == "__main__":
    print("Testing MultiTaskCCBEnvironment...")

    env = create_multitask_ccb(num_tasks=1000, nonlinear=True)

    # Test reset and step
    obs, info = env.reset(task_id=0)
    print(f"Task 0: b_X={info['b_X']:.3f}, b_U={info['b_U']:.3f}")
    print(f"Initial obs: {obs.tolist()}")

    # Test oracle action
    oracle_action = env.get_oracle_action(obs)
    print(f"Oracle action: {oracle_action.item()}")

    # Test step
    obs, reward, done, _, step_info = env.step(oracle_action)
    print(f"Step 1: reward={reward:.3f}, error={step_info['error']:.4f}")

    # Complete episode with oracle
    total_reward = reward
    while not done:
        oracle_action = env.get_oracle_action(obs)
        obs, reward, done, _, _ = env.step(oracle_action)
        total_reward += reward

    success = env.get_task_success()
    print(f"Episode complete: total_reward={total_reward:.3f}, success={success}")

    # Test different tasks
    print("\n=== Task Bank Sample ===")
    for task_id in [0, 50, 100, 150, 199]:
        obs, info = env.reset(task_id=task_id)
        print(f"Task {task_id}: b_X={info['b_X']:.3f}, b_U={info['b_U']:.3f}")

    # Test demo/test split
    demo_ids, test_ids = get_demo_and_test_task_ids()
    print(f"\nDemo tasks: {demo_ids}")
    print(f"Test tasks (first 5): {test_ids[:5]}...")
    print(f"Test tasks count: {len(test_ids)}")

    print("\n✓ MultiTaskCCBEnvironment works!")
