"""
Sleep/Offline Consolidation Module

This implements BLUEPRINT Section 2.5:
- Sleep trigger ω_t = σ(w_ω^T h_t + b_ω)
- Prioritized replay buffer with TD-priority
- Latent dynamics model f_dyn for imagination
- Synaptic renormalization
- Multi-step latent consistency training

Reference: BLUEPRINT.md Section 2.5
"""

from __future__ import annotations

from typing import Tuple, NamedTuple, Optional, List, Dict, Any
from dataclasses import dataclass
import random

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


# Constants from BLUEPRINT
LATENT_DIM = 64
HIDDEN_DIM = 512
BUFFER_CAPACITY = 100_000
PRIORITY_ALPHA = 0.6
PRIORITY_EPSILON = 1e-3
PRIORITY_BETA_START = 0.4
PRIORITY_BETA_END = 1.0
E_SLEEP_MAX = 0.1  # J/step
B_SLEEP = 100.0    # J total sleep budget per episode
RHO = 1.0          # Synaptic renormalization threshold
N_MAX = 5          # Max imagination steps


@dataclass
class SleepConfig:
    """Configuration for sleep module."""
    hidden_dim: int = HIDDEN_DIM
    latent_dim: int = LATENT_DIM
    obs_dim: int = 64
    action_bytes: int = 1

    # Replay buffer
    buffer_capacity: int = BUFFER_CAPACITY
    priority_alpha: float = PRIORITY_ALPHA
    priority_epsilon: float = PRIORITY_EPSILON
    beta_start: float = PRIORITY_BETA_START
    beta_end: float = PRIORITY_BETA_END

    # Energy
    e_sleep_max: float = E_SLEEP_MAX
    b_sleep: float = B_SLEEP

    # Renormalization
    rho: float = RHO

    # Imagination
    n_max: int = N_MAX
    lambda_dyn: float = 1.0


class Transition(NamedTuple):
    """Single transition stored in replay buffer."""
    obs: torch.Tensor        # o_t [obs_dim]
    action: torch.Tensor     # a_t [action_bytes]
    reward: float            # r_t
    next_obs: torch.Tensor   # o_{t+1} [obs_dim]
    done: bool               # terminal flag
    energy: float            # E_t
    code_len: float          # CodeLen_t
    z_t: torch.Tensor        # Latent z_t [latent_dim]


class SleepTrigger(nn.Module):
    """
    Sleep trigger: ω_t = σ(w_ω^T h_t + b_ω)

    Outputs probability of entering sleep mode.
    """

    def __init__(self, hidden_dim: int):
        super().__init__()

        self.w_omega = nn.Parameter(torch.zeros(hidden_dim))
        self.b_omega = nn.Parameter(torch.tensor(0.0))

        # Initialize to produce ω ≈ 0.1 initially (low sleep probability)
        nn.init.normal_(self.w_omega, std=0.01)
        self.b_omega.data.fill_(-2.0)  # sigmoid(-2) ≈ 0.12

    def forward(self, h_t: torch.Tensor) -> torch.Tensor:
        """
        Compute sleep probability.

        Args:
            h_t: Hidden state [batch, hidden_dim]

        Returns:
            omega_t: Sleep probability [batch]
        """
        return torch.sigmoid((h_t * self.w_omega).sum(dim=-1) + self.b_omega)


class LatentDynamicsModel(nn.Module):
    """
    Latent dynamics model: z̃_{t+1} = f_dyn(z_t, a_t)

    2-layer MLP 64→128→64 (ReLU) per BLUEPRINT.
    """

    def __init__(self, latent_dim: int, action_dim: int):
        super().__init__()

        self.input_dim = latent_dim + action_dim

        self.net = nn.Sequential(
            nn.Linear(self.input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, latent_dim),
        )

    def forward(
        self,
        z_t: torch.Tensor,
        a_t: torch.Tensor,
    ) -> torch.Tensor:
        """
        Predict next latent.

        Args:
            z_t: Current latent [batch, latent_dim]
            a_t: Action (normalized) [batch, action_dim]

        Returns:
            z_next_pred: Predicted next latent [batch, latent_dim]
        """
        # Normalize action to [-1, 1]
        if a_t.dtype in (torch.int32, torch.int64, torch.long):
            a_t = (a_t.float() / 127.5) - 1.0

        # Ensure action is float and has right shape
        if a_t.dim() == 1:
            a_t = a_t.unsqueeze(-1)

        x = torch.cat([z_t, a_t], dim=-1)
        return self.net(x)

    def multi_step_rollout(
        self,
        z_start: torch.Tensor,
        actions: torch.Tensor,
        n_steps: int,
    ) -> List[torch.Tensor]:
        """
        Roll out dynamics for multiple steps.

        Args:
            z_start: Starting latent [batch, latent_dim]
            actions: Actions for each step [batch, n_steps] or [batch, n_steps, action_dim]
            n_steps: Number of steps to roll out

        Returns:
            z_preds: List of predicted latents, len = n_steps
        """
        z_preds = []
        z_t = z_start

        for i in range(n_steps):
            if actions.dim() == 2:
                a_t = actions[:, i]
            else:
                a_t = actions[:, i, :]

            z_t = self.forward(z_t, a_t)
            z_preds.append(z_t)

        return z_preds


class PrioritizedReplayBuffer:
    """
    Prioritized Experience Replay buffer.

    Priority: p_i ∝ (|δ_i| + ε)^α
    Importance weights: w_i = (1 / (N * P(i)))^β / max(w)

    From BLUEPRINT Section 2.5.
    """

    def __init__(
        self,
        capacity: int = BUFFER_CAPACITY,
        alpha: float = PRIORITY_ALPHA,
        epsilon: float = PRIORITY_EPSILON,
    ):
        self.capacity = capacity
        self.alpha = alpha
        self.epsilon = epsilon

        self.buffer: List[Transition] = []
        self.priorities = np.zeros(capacity, dtype=np.float32)
        self.position = 0
        self.size = 0

    def add(
        self,
        transition: Transition,
        td_error: Optional[float] = None,
    ):
        """
        Add transition to buffer.

        Args:
            transition: The transition to add
            td_error: TD error for priority (uses max priority if None)
        """
        # Compute priority
        if td_error is None:
            # Use max priority for new transitions
            max_priority = self.priorities[:self.size].max() if self.size > 0 else 1.0
        else:
            max_priority = (abs(td_error) + self.epsilon) ** self.alpha

        if self.size < self.capacity:
            self.buffer.append(transition)
            self.size += 1
        else:
            self.buffer[self.position] = transition

        self.priorities[self.position] = max_priority
        self.position = (self.position + 1) % self.capacity

    def sample(
        self,
        batch_size: int,
        beta: float = PRIORITY_BETA_START,
    ) -> Tuple[List[Transition], torch.Tensor, np.ndarray]:
        """
        Sample batch with prioritized sampling.

        Args:
            batch_size: Number of transitions to sample
            beta: Importance sampling exponent

        Returns:
            transitions: List of sampled transitions
            weights: Importance sampling weights [batch_size]
            indices: Indices of sampled transitions
        """
        if self.size < batch_size:
            batch_size = self.size

        # Compute sampling probabilities
        priorities = self.priorities[:self.size]
        probs = priorities / priorities.sum()

        # Sample indices
        indices = np.random.choice(self.size, batch_size, p=probs, replace=False)

        # Compute importance sampling weights
        weights = (self.size * probs[indices]) ** (-beta)
        weights = weights / weights.max()  # Normalize
        weights = torch.tensor(weights, dtype=torch.float32)

        # Get transitions
        transitions = [self.buffer[i] for i in indices]

        return transitions, weights, indices

    def update_priorities(self, indices: np.ndarray, td_errors: np.ndarray):
        """Update priorities after learning."""
        for idx, td_error in zip(indices, td_errors):
            self.priorities[idx] = (abs(td_error) + self.epsilon) ** self.alpha

    def __len__(self) -> int:
        return self.size


class SleepModule(nn.Module):
    """
    Complete sleep/offline consolidation module.

    Combines:
    - Sleep trigger (ω_t)
    - Replay buffer
    - Latent dynamics model
    - Synaptic renormalization
    """

    def __init__(self, config: SleepConfig):
        super().__init__()

        self.config = config

        # Sleep trigger
        self.trigger = SleepTrigger(config.hidden_dim)

        # Latent dynamics model
        self.dynamics = LatentDynamicsModel(
            latent_dim=config.latent_dim,
            action_dim=config.action_bytes,
        )

        # Replay buffer (not a module, just storage)
        self.replay_buffer = PrioritizedReplayBuffer(
            capacity=config.buffer_capacity,
            alpha=config.priority_alpha,
            epsilon=config.priority_epsilon,
        )

        # Track sleep budget
        self.register_buffer('sleep_energy_used', torch.tensor(0.0))
        self.register_buffer('total_steps', torch.tensor(0))

        # Beta annealing
        self.register_buffer('training_steps', torch.tensor(0))
        self.total_training_steps = 1_000_000  # For beta annealing

    @property
    def beta(self) -> float:
        """Current importance sampling beta (annealed)."""
        progress = min(1.0, self.training_steps.item() / self.total_training_steps)
        return self.config.beta_start + progress * (self.config.beta_end - self.config.beta_start)

    def get_sleep_probability(self, h_t: torch.Tensor) -> torch.Tensor:
        """Get probability of entering sleep mode."""
        return self.trigger(h_t)

    def compute_sleep_energy(self, omega_t: torch.Tensor) -> torch.Tensor:
        """
        Compute energy cost of sleep.

        E^sleep_t = ω_t * E^sleep_max
        """
        return omega_t * self.config.e_sleep_max

    def is_sleeping(self, omega_t: torch.Tensor) -> torch.Tensor:
        """
        Determine if in sleep mode.

        Sleep is defined post-hoc as ω_t > 0.5
        """
        return omega_t > 0.5

    def add_experience(
        self,
        obs: torch.Tensor,
        action: torch.Tensor,
        reward: float,
        next_obs: torch.Tensor,
        done: bool,
        energy: float,
        code_len: float,
        z_t: torch.Tensor,
        td_error: Optional[float] = None,
    ):
        """Add experience to replay buffer."""
        transition = Transition(
            obs=obs.detach().cpu(),
            action=action.detach().cpu(),
            reward=reward,
            next_obs=next_obs.detach().cpu(),
            done=done,
            energy=energy,
            code_len=code_len,
            z_t=z_t.detach().cpu(),
        )
        self.replay_buffer.add(transition, td_error)

    def sample_replay(
        self,
        batch_size: int,
    ) -> Tuple[Dict[str, torch.Tensor], torch.Tensor, np.ndarray]:
        """
        Sample batch from replay buffer.

        Returns batched tensors ready for training.
        """
        transitions, weights, indices = self.replay_buffer.sample(batch_size, self.beta)

        # Stack into tensors
        obs = torch.stack([t.obs for t in transitions])
        actions = torch.stack([t.action for t in transitions])
        rewards = torch.tensor([t.reward for t in transitions])
        next_obs = torch.stack([t.next_obs for t in transitions])
        dones = torch.tensor([t.done for t in transitions], dtype=torch.float32)
        z_t = torch.stack([t.z_t for t in transitions])

        batch = {
            'obs': obs,
            'actions': actions,
            'rewards': rewards,
            'next_obs': next_obs,
            'dones': dones,
            'z_t': z_t,
        }

        return batch, weights, indices

    def compute_dynamics_loss(
        self,
        z_t: torch.Tensor,
        a_t: torch.Tensor,
        z_next_target: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute 1-step dynamics loss.

        L_dyn = ||f_dyn(z_t, a_t) - sg(z_{t+1})||²
        """
        z_next_pred = self.dynamics(z_t, a_t)
        return F.mse_loss(z_next_pred, z_next_target.detach())

    def compute_multistep_dynamics_loss(
        self,
        z_t: torch.Tensor,
        actions: torch.Tensor,
        z_targets: List[torch.Tensor],
        n_steps: int,
    ) -> torch.Tensor:
        """
        Compute multi-step dynamics loss.

        L_dyn^N = Σ_{i=1}^{N} ||f_dyn^{(i)}(z_t, a_{t:t+i-1}) - sg(z_{t+i})||²
        """
        z_preds = self.dynamics.multi_step_rollout(z_t, actions, n_steps)

        total_loss = torch.tensor(0.0, device=z_t.device)
        for pred, target in zip(z_preds, z_targets[:n_steps]):
            total_loss = total_loss + F.mse_loss(pred, target.detach())

        return total_loss

    def synaptic_renormalization(self, module: nn.Module):
        """
        Apply synaptic renormalization per neuron.

        For each column (incoming weights to neuron j):
        w_{·j} ← w_{·j} / max(1, ||w_{·j}||_2 / ρ)
        """
        rho = self.config.rho

        for name, param in module.named_parameters():
            if 'weight' in name and param.dim() == 2:
                # Renormalize each column (incoming weights to each output neuron)
                with torch.no_grad():
                    norms = param.norm(dim=1, keepdim=True)  # [out, 1]
                    scale = torch.clamp(norms / rho, min=1.0)
                    param.data = param.data / scale

    def reset_episode(self):
        """Reset sleep tracking at episode start."""
        self.sleep_energy_used.zero_()

    def can_sleep(self) -> bool:
        """Check if sleep budget allows more sleep."""
        return self.sleep_energy_used.item() < self.config.b_sleep

    def update_training_steps(self, n: int = 1):
        """Update training step counter for beta annealing."""
        self.training_steps += n


class SleepOutput(NamedTuple):
    """Output from sleep processing step."""
    omega_t: torch.Tensor       # Sleep probability [batch]
    is_sleeping: torch.Tensor   # Binary sleep indicator [batch]
    sleep_energy: torch.Tensor  # Energy used [batch]
    dynamics_loss: Optional[torch.Tensor]  # If did imagination


def create_sleep_module(obs_dim: int = 64, **kwargs) -> SleepModule:
    """Factory function for sleep module."""
    config = SleepConfig(obs_dim=obs_dim, **kwargs)
    return SleepModule(config)


if __name__ == "__main__":
    print("Testing Sleep Module...")

    batch_size = 4
    obs_dim = 64
    latent_dim = LATENT_DIM

    sleep = create_sleep_module(obs_dim=obs_dim)

    # Test sleep trigger
    h_t = torch.randn(batch_size, HIDDEN_DIM)
    omega = sleep.get_sleep_probability(h_t)
    print(f"\n=== Sleep Trigger ===")
    print(f"ω_t shape: {omega.shape}")
    print(f"ω_t values: {omega.tolist()}")
    assert omega.shape == (batch_size,)
    assert (omega >= 0).all() and (omega <= 1).all()

    # Test dynamics model
    z_t = torch.randn(batch_size, latent_dim)
    a_t = torch.randint(0, 256, (batch_size, 1))
    z_next = sleep.dynamics(z_t, a_t)
    print(f"\n=== Dynamics Model ===")
    print(f"z_next shape: {z_next.shape}")
    assert z_next.shape == (batch_size, latent_dim)

    # Test multi-step rollout
    actions = torch.randint(0, 256, (batch_size, 5))
    z_preds = sleep.dynamics.multi_step_rollout(z_t, actions, n_steps=5)
    print(f"Multi-step rollout: {len(z_preds)} predictions")
    assert len(z_preds) == 5

    # Test replay buffer
    print(f"\n=== Replay Buffer ===")
    for i in range(100):
        obs = torch.randint(0, 256, (obs_dim,))
        action = torch.randint(0, 256, (1,))
        next_obs = torch.randint(0, 256, (obs_dim,))
        z = torch.randn(latent_dim)
        sleep.add_experience(
            obs=obs,
            action=action,
            reward=float(i),
            next_obs=next_obs,
            done=(i % 20 == 19),
            energy=0.05,
            code_len=1.0,
            z_t=z,
            td_error=float(i % 10),
        )

    print(f"Buffer size: {len(sleep.replay_buffer)}")

    # Sample from buffer
    batch, weights, indices = sleep.sample_replay(batch_size=16)
    print(f"Sampled batch obs shape: {batch['obs'].shape}")
    print(f"Importance weights shape: {weights.shape}")

    # Test dynamics loss
    z_targets = [torch.randn(batch_size, latent_dim) for _ in range(5)]
    dyn_loss = sleep.compute_dynamics_loss(z_t, a_t, z_targets[0])
    print(f"\n=== Losses ===")
    print(f"1-step dynamics loss: {dyn_loss.item():.4f}")

    # Test multi-step loss
    ms_loss = sleep.compute_multistep_dynamics_loss(z_t, actions, z_targets, n_steps=3)
    print(f"3-step dynamics loss: {ms_loss.item():.4f}")

    # Test renormalization
    print(f"\n=== Synaptic Renormalization ===")
    test_module = nn.Linear(64, 32)
    test_module.weight.data *= 5  # Make weights large
    norm_before = test_module.weight.norm()
    sleep.synaptic_renormalization(test_module)
    norm_after = test_module.weight.norm()
    print(f"Weight norm before: {norm_before.item():.4f}")
    print(f"Weight norm after: {norm_after.item():.4f}")

    # Test gradient flow
    h_t = torch.randn(batch_size, HIDDEN_DIM, requires_grad=True)
    omega = sleep.get_sleep_probability(h_t)
    loss = omega.sum()
    loss.backward()
    assert h_t.grad is not None
    print(f"\n✓ Gradient flow OK")

    # Parameter count
    params = sum(p.numel() for p in sleep.parameters())
    print(f"\n=== Parameters ===")
    print(f"Total: {params:,}")

    print("\n✓ Sleep Module works!")
