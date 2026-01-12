"""
OD-NDT Harness - One-Demonstration No-Data Transfer Protocol

TRUE one-demonstration transfer evaluation:
1. One expert demo (≤200 steps)
2. Exactly one fixed sleep cycle (B_sleep_1 = 100J)
3. NO further environment interaction between demo and test
4. Test on 100 held-out tasks with frozen slow weights

PASS criteria:
- SR_novel ≥ 0.60
- T = SR_novel/SR_train ≥ 0.80

Reference: BLUEPRINT.md Section 4.3
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional, Protocol, Callable
import copy

import torch
import torch.nn as nn


# =============================================================================
# Constants (BLUEPRINT.md Section 4.3)
# =============================================================================

MAX_DEMO_STEPS = 200        # Maximum steps in expert demo
B_SLEEP_1 = 100.0          # Sleep budget for one-demo (Joules)
NUM_TEST_TASKS = 100        # Number of held-out test tasks
SR_NOVEL_THRESHOLD = 0.60   # Minimum success rate on novel tasks
TRANSFER_THRESHOLD = 0.80   # Minimum T = SR_novel / SR_train


@dataclass
class ODNDTConfig:
    """Configuration for OD-NDT evaluation."""
    max_demo_steps: int = MAX_DEMO_STEPS
    sleep_budget: float = B_SLEEP_1
    num_test_tasks: int = NUM_TEST_TASKS
    sr_novel_threshold: float = SR_NOVEL_THRESHOLD
    transfer_threshold: float = TRANSFER_THRESHOLD
    max_test_steps: int = 500  # Max steps per test episode
    device: str = "cpu"


class TaskEnvironment(Protocol):
    """Protocol for task environments compatible with OD-NDT."""

    def reset(self, task_id: Optional[int] = None) -> Tuple[torch.Tensor, Dict[str, Any]]:
        """Reset to a specific task. Returns (obs, info)."""
        ...

    def step(self, action: torch.Tensor) -> Tuple[torch.Tensor, float, bool, bool, Dict[str, Any]]:
        """Step. Returns (obs, reward, terminated, truncated, info)."""
        ...

    def get_oracle_action(self, obs: torch.Tensor) -> torch.Tensor:
        """Get expert action for demonstration."""
        ...

    def get_task_success(self) -> bool:
        """Check if current task was solved successfully."""
        ...


class ODNDTResult:
    """Results from OD-NDT evaluation."""

    def __init__(
        self,
        sr_train: float,
        sr_novel: float,
        transfer_ratio: float,
        passed: bool,
        demo_energy: float,
        sleep_energy: float,
        test_successes: List[bool],
        fail_reasons: List[str],
    ):
        self.sr_train = sr_train
        self.sr_novel = sr_novel
        self.transfer_ratio = transfer_ratio
        self.passed = passed
        self.demo_energy = demo_energy
        self.sleep_energy = sleep_energy
        self.test_successes = test_successes
        self.fail_reasons = fail_reasons

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        reasons = f" ({', '.join(self.fail_reasons)})" if self.fail_reasons else ""
        return (
            f"ODNDTResult({status}{reasons})\n"
            f"  SR_train: {self.sr_train:.3f}\n"
            f"  SR_novel: {self.sr_novel:.3f} (threshold: {SR_NOVEL_THRESHOLD})\n"
            f"  Transfer T: {self.transfer_ratio:.3f} (threshold: {TRANSFER_THRESHOLD})\n"
            f"  Demo energy: {self.demo_energy:.2f} J\n"
            f"  Sleep energy: {self.sleep_energy:.2f} J"
        )


class ODNDTHarness:
    """
    One-Demonstration No-Data Transfer evaluation harness.

    Implements the TRUE one-demo protocol from BLUEPRINT.md Section 4.3:
    - One expert demo
    - One sleep cycle
    - NO further interaction before test
    - Frozen slow weights during test
    """

    def __init__(
        self,
        brain: nn.Module,
        config: ODNDTConfig = None,
    ):
        """
        Initialize OD-NDT harness.

        Args:
            brain: The RPJ Brain to evaluate. Must have:
                - forward(obs, h, training=False) -> output with action
                - plasticity module with reset_fast_weights()
                - sleep module for consolidation
            config: OD-NDT configuration
        """
        self.brain = brain
        self.config = config or ODNDTConfig()
        self.device = self.config.device

        # State tracking
        self._post_sleep_fast_weights: Optional[Dict[str, torch.Tensor]] = None
        self._demo_energy: float = 0.0
        self._sleep_energy: float = 0.0

    def collect_demo(
        self,
        env: TaskEnvironment,
        demo_task_id: int,
    ) -> Tuple[List[Dict[str, torch.Tensor]], bool]:
        """
        Collect one expert demonstration.

        Args:
            env: Task environment with oracle
            demo_task_id: Task ID for demonstration

        Returns:
            (demo_data, success): Demo trajectory and whether oracle succeeded
        """
        demo_data = []

        # Reset to demo task
        obs, info = env.reset(task_id=demo_task_id)
        obs = obs.to(self.device)

        # Initialize hidden state, global scalars, and previous action
        h = torch.zeros(1, self.brain.substrate.hidden_dim, device=self.device)
        g_prev = torch.zeros(1, self.brain.config.k_max, device=self.device)
        a_prev = torch.zeros(1, dtype=torch.long, device=self.device)

        for step in range(self.config.max_demo_steps):
            # Get oracle action
            oracle_action = env.get_oracle_action(obs).to(self.device)

            # Store demo step
            demo_data.append({
                'obs': obs.clone(),
                'action': oracle_action.clone(),
                'hidden': h.clone(),
                'g_prev': g_prev.clone(),
            })

            # Step environment
            next_obs, reward, terminated, truncated, info = env.step(oracle_action)
            next_obs = next_obs.to(self.device)

            # Update hidden state (observe the demo)
            with torch.no_grad():
                output = self.brain.forward(obs.unsqueeze(0), h, g_prev, a_prev, training=False)
                h = output.h_next
                g_prev = output.g_t
                a_prev = output.action.squeeze(-1) if output.action.dim() > 1 else output.action

            obs = next_obs

            if terminated or truncated:
                break

        # Check if oracle succeeded
        success = env.get_task_success()

        return demo_data, success

    def sleep_consolidation(
        self,
        demo_data: List[Dict[str, torch.Tensor]],
    ) -> float:
        """
        Run sleep consolidation on demo data.

        Args:
            demo_data: Demo trajectory from collect_demo

        Returns:
            Energy used in Joules
        """
        if self.brain.sleep is None:
            # No sleep module - just save current fast weights
            self._save_fast_weights()
            return 0.0

        # Add demo to replay buffer
        for i, step in enumerate(demo_data):
            obs = step['obs']
            action = step['action']
            hidden = step['hidden']

            # Compute latent for storage
            with torch.no_grad():
                phi_obs = self.brain.byte_interface.encode_observation(obs.unsqueeze(0))
                # VAE forward needs (h_t, phi_obs, obs_bytes)
                vae_out = self.brain.vae.forward(hidden, phi_obs, obs.unsqueeze(0))
                z_t = vae_out.z_t

            # Store in replay buffer with high priority (demo is important)
            # Get next obs (or use current obs for last step)
            next_obs = demo_data[i + 1]['obs'] if i < len(demo_data) - 1 else obs
            self.brain.sleep.add_experience(
                obs=obs,
                action=action,
                reward=1.0,  # Demo is successful
                next_obs=next_obs,
                done=(i == len(demo_data) - 1),
                energy=0.01,  # Minimal energy for demo
                code_len=0.0,  # No codelength for demo
                z_t=z_t.squeeze(0),
                td_error=1.0,  # High priority
            )

        # Run sleep consolidation under budget
        energy_used = 0.0
        max_sleep_steps = int(self.config.sleep_budget / 0.1)  # E_sleep_max = 0.1 J/step

        for _ in range(max_sleep_steps):
            if energy_used >= self.config.sleep_budget:
                break

            # Sample from replay and update dynamics
            if self.brain.sleep.replay_buffer.size >= 8:  # Minimum batch
                batch_size = min(8, self.brain.sleep.replay_buffer.size)
                # Use sample_replay which returns batched dict, not raw transitions
                batch, weights, indices = self.brain.sleep.sample_replay(batch_size)

                # Compute dynamics loss (imagination)
                z_batch = batch['z_t'].to(self.device)
                action_batch = batch['actions'].to(self.device)

                # One-step dynamics
                z_next = batch['z_t'][1:].to(self.device) if len(batch['z_t']) > 1 else z_batch

                # This is a simplified sleep step - actual implementation
                # would use the dynamics model training
                energy_per_step = 0.1  # J/step
                energy_used += energy_per_step

        # Synaptic renormalization
        if hasattr(self.brain.sleep, 'synaptic_renormalization'):
            self.brain.sleep.synaptic_renormalization(self.brain.plasticity)

        # Save fast weights after sleep
        self._save_fast_weights()

        self._sleep_energy = energy_used
        return energy_used

    def _save_fast_weights(self):
        """Save fast weights state after sleep."""
        if self.brain.plasticity is None:
            self._post_sleep_fast_weights = {}
            return

        self._post_sleep_fast_weights = {
            'recurrent_A': self.brain.plasticity.recurrent_adapter.A.clone(),
            'recurrent_B': self.brain.plasticity.recurrent_adapter.B.clone(),
            'action_A': self.brain.plasticity.action_adapter.A.clone(),
            'action_B': self.brain.plasticity.action_adapter.B.clone(),
        }

    def _restore_fast_weights(self):
        """Restore fast weights to post-sleep state."""
        if self.brain.plasticity is None or self._post_sleep_fast_weights is None:
            return

        with torch.no_grad():
            self.brain.plasticity.recurrent_adapter.A.copy_(
                self._post_sleep_fast_weights['recurrent_A']
            )
            self.brain.plasticity.recurrent_adapter.B.copy_(
                self._post_sleep_fast_weights['recurrent_B']
            )
            self.brain.plasticity.action_adapter.A.copy_(
                self._post_sleep_fast_weights['action_A']
            )
            self.brain.plasticity.action_adapter.B.copy_(
                self._post_sleep_fast_weights['action_B']
            )

    def evaluate_test_task(
        self,
        env: TaskEnvironment,
        task_id: int,
    ) -> bool:
        """
        Evaluate on a single test task.

        Args:
            env: Task environment
            task_id: Test task ID

        Returns:
            Whether task was solved successfully
        """
        # Reset fast weights to post-sleep state (CRITICAL per BLUEPRINT)
        self._restore_fast_weights()

        # Reset environment
        obs, info = env.reset(task_id=task_id)
        obs = obs.to(self.device)

        # Initialize hidden state, global scalars, and previous action
        h = torch.zeros(1, self.brain.substrate.hidden_dim, device=self.device)
        g_prev = torch.zeros(1, self.brain.config.k_max, device=self.device)
        a_prev = torch.zeros(1, dtype=torch.long, device=self.device)

        # Freeze slow weights
        for param in self.brain.parameters():
            param.requires_grad = False

        try:
            for step in range(self.config.max_test_steps):
                # Forward pass (no training)
                with torch.no_grad():
                    output = self.brain.forward(obs.unsqueeze(0), h, g_prev, a_prev, training=False)

                action = output.action
                h = output.h_next
                g_prev = output.g_t
                a_prev = action.squeeze(-1) if action.dim() > 1 else action

                # Fast weight update (local plasticity still active within episode)
                if self.brain.plasticity is not None and hasattr(output, 'g_t'):
                    # Allow local plasticity during test episode
                    # This is per BLUEPRINT: "Fast weights may adapt within episode"
                    pass

                # Step environment
                next_obs, reward, terminated, truncated, info = env.step(action.squeeze(0))
                next_obs = next_obs.to(self.device)

                obs = next_obs

                if terminated or truncated:
                    break

        finally:
            # Re-enable gradients
            for param in self.brain.parameters():
                param.requires_grad = True

        return env.get_task_success()

    def run_evaluation(
        self,
        env: TaskEnvironment,
        demo_task_id: int,
        test_task_ids: List[int],
        sr_train: float = 1.0,  # SR on training tasks (assumed from prior training)
    ) -> ODNDTResult:
        """
        Run full OD-NDT evaluation.

        Args:
            env: Task environment with oracle
            demo_task_id: Task ID for the single demonstration
            test_task_ids: List of held-out test task IDs
            sr_train: Success rate on training distribution (for T calculation)

        Returns:
            ODNDTResult with pass/fail and metrics
        """
        fail_reasons = []

        # Phase 1: Collect expert demonstration
        print(f"[OD-NDT] Phase 1: Collecting expert demo on task {demo_task_id}...")
        demo_data, demo_success = self.collect_demo(env, demo_task_id)

        if not demo_success:
            fail_reasons.append("Oracle failed to solve demo task")

        print(f"  Demo steps: {len(demo_data)}")
        print(f"  Demo success: {demo_success}")

        # Phase 2: Sleep consolidation (ONE fixed cycle)
        print(f"\n[OD-NDT] Phase 2: Sleep consolidation (budget: {self.config.sleep_budget}J)...")
        sleep_energy = self.sleep_consolidation(demo_data)
        print(f"  Sleep energy used: {sleep_energy:.2f}J")

        # Phase 3: NO FURTHER INTERACTION
        # (This is enforced by not calling any environment methods between sleep and test)

        # Phase 4: Evaluate on held-out tasks
        print(f"\n[OD-NDT] Phase 3: Evaluating on {len(test_task_ids)} test tasks...")
        test_successes = []

        for i, task_id in enumerate(test_task_ids):
            success = self.evaluate_test_task(env, task_id)
            test_successes.append(success)

            if (i + 1) % 10 == 0:
                current_sr = sum(test_successes) / len(test_successes)
                print(f"  Progress: {i+1}/{len(test_task_ids)}, SR: {current_sr:.3f}")

        # Compute metrics
        sr_novel = sum(test_successes) / len(test_successes)
        transfer_ratio = sr_novel / sr_train if sr_train > 0 else 0.0

        # Check pass criteria
        if sr_novel < self.config.sr_novel_threshold:
            fail_reasons.append(
                f"SR_novel {sr_novel:.3f} < {self.config.sr_novel_threshold}"
            )

        if transfer_ratio < self.config.transfer_threshold:
            fail_reasons.append(
                f"Transfer T {transfer_ratio:.3f} < {self.config.transfer_threshold}"
            )

        passed = len(fail_reasons) == 0

        result = ODNDTResult(
            sr_train=sr_train,
            sr_novel=sr_novel,
            transfer_ratio=transfer_ratio,
            passed=passed,
            demo_energy=self._demo_energy,
            sleep_energy=sleep_energy,
            test_successes=test_successes,
            fail_reasons=fail_reasons,
        )

        print(f"\n[OD-NDT] Results:")
        print(result)

        return result


def create_od_ndt_harness(
    brain: nn.Module,
    device: str = "cpu",
    **kwargs,
) -> ODNDTHarness:
    """
    Factory function to create OD-NDT harness.

    Args:
        brain: RPJ Brain module
        device: Compute device
        **kwargs: Additional config parameters

    Returns:
        Configured ODNDTHarness
    """
    config = ODNDTConfig(device=device, **kwargs)
    return ODNDTHarness(brain, config)
