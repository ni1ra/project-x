"""
RPJ Brain - The Complete Integrated System

This combines:
1. LN-GRU Substrate (the neural core)
2. Bits-Back VAE (compression/representation)
3. Byte Interface (content-free I/O)
4. RND/Intrinsic rewards (exploration)
5. Local Plasticity (fast weights within episodes)
6. Sleep/Offline Consolidation (replay + imagination)

This is the "agent" that will be trained on CCB and other environments.

Reference: BLUEPRINT.md Sections 2.2-2.8
"""

from __future__ import annotations

from typing import Tuple, NamedTuple, Optional, Dict, Any, List
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

from src.core.substrate import RPJSubstrate, SubstrateOutput, HIDDEN_DIM, LATENT_DIM, K_MAX
from src.core.vae import BitsBackVAE, VAEOutput
from src.core.byte_interface import phi, AutoregressiveActionDecoder
from src.core.plasticity import LocalPlasticity, PlasticityConfig
from src.core.sleep import SleepModule, SleepConfig


@dataclass
class RPJConfig:
    """Configuration for RPJ Brain."""
    obs_dim: int = 64
    action_bytes: int = 1
    hidden_dim: int = HIDDEN_DIM
    latent_dim: int = LATENT_DIM
    k_max: int = K_MAX

    # Reward coefficients (BLUEPRINT Section 2.7)
    lambda_E: float = 1.0       # Energy penalty
    lambda_mdl: float = 1.0     # Codelength penalty
    lambda_rnd: float = 0.1     # RND intrinsic (warmup)
    lambda_int: float = 0.1     # Info gain intrinsic (post-warmup)
    lambda_dyn: float = 1.0     # Dynamics model loss

    # Warmup
    T_warm: int = 50_000        # RND warmup steps

    # RND network dims
    rnd_hidden: int = 256
    rnd_output: int = 128

    # Plasticity
    enable_plasticity: bool = True
    adapter_rank: int = 16      # Fast weight adapter rank

    # Sleep
    enable_sleep: bool = True
    buffer_capacity: int = 100_000
    e_sleep_max: float = 0.1
    b_sleep: float = 100.0

    # Discount (BLUEPRINT: γ ≥ 0.999 for sleep credit assignment)
    gamma: float = 0.999


class RPJBrainOutput(NamedTuple):
    """Output from a single brain step."""
    # Actions
    action: torch.Tensor           # Action bytes [batch, action_bytes]
    action_log_prob: torch.Tensor  # Log prob [batch, action_bytes]

    # States for next step
    h_next: torch.Tensor           # Hidden state [batch, hidden_dim]
    g_t: torch.Tensor              # Global scalars [batch, k_max]

    # VAE outputs
    z_t: torch.Tensor              # Latent [batch, latent_dim]
    mu: torch.Tensor               # Posterior mean [batch, latent_dim]
    sigma: torch.Tensor            # Posterior std [batch, latent_dim]

    # Values and metrics
    value: torch.Tensor            # V(h_t) [batch]
    code_len: torch.Tensor         # CodeLen_t [batch]

    # Emergence metrics
    c_t: torch.Tensor              # Compute allocation [batch, 1]
    cbr_t: torch.Tensor            # Compute burst ratio [batch]
    bi_t: torch.Tensor             # Broadcast index [batch]

    # Compute decision log probs (for PPO)
    compute_log_prob: torch.Tensor # Log prob of (k_r, N) [batch]

    # Sleep
    omega_t: torch.Tensor          # Sleep probability [batch]
    is_sleeping: torch.Tensor      # Binary sleep indicator [batch]

    # Plasticity gate
    P_t: torch.Tensor              # Plasticity gate [batch]


class RNDNetwork(nn.Module):
    """
    Random Network Distillation for exploration.

    From BLUEPRINT Section 2.7:
    - 2-layer MLP 256→256→128 (ReLU)
    - Fixed random target, trained predictor
    - r^rnd_t = ||f_pred(φ(o_t)) - f_target(φ(o_t))||²
    """

    def __init__(self, obs_dim: int, hidden_dim: int = 256, output_dim: int = 128):
        super().__init__()

        # Fixed random target network
        self.target = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )
        # Freeze target
        for param in self.target.parameters():
            param.requires_grad = False

        # Trained predictor network
        self.predictor = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, phi_obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute RND intrinsic reward.

        Args:
            phi_obs: Normalized observation [batch, obs_dim]

        Returns:
            reward: RND intrinsic reward [batch]
            loss: Predictor loss for training [batch]
        """
        with torch.no_grad():
            target_feat = self.target(phi_obs)

        pred_feat = self.predictor(phi_obs)

        # MSE per sample (intrinsic reward = prediction error)
        error = ((pred_feat - target_feat.detach()) ** 2).mean(dim=-1)

        return error, error  # reward and loss are the same


class RPJBrain(nn.Module):
    """
    The Complete RPJ Brain.

    Combines all components into a single agent that:
    1. Observes bytes, emits bytes (content-free)
    2. Compresses observations via bits-back VAE
    3. Processes via sparse recurrent substrate
    4. Explores via RND (warmup) or info gain (post-warmup)
    5. Adapts within episodes via local plasticity
    6. Consolidates via sleep/offline replay
    7. Outputs value estimates for RL
    """

    def __init__(self, config: RPJConfig):
        super().__init__()

        self.config = config

        # Core substrate
        self.substrate = RPJSubstrate(
            obs_dim=config.obs_dim,
            latent_dim=config.latent_dim,
            hidden_dim=config.hidden_dim,
            k_max=config.k_max,
        )

        # VAE for compression
        self.vae = BitsBackVAE(
            obs_dim=config.obs_dim,
            hidden_dim=config.hidden_dim,
            latent_dim=config.latent_dim,
        )

        # Action decoder
        self.action_decoder = AutoregressiveActionDecoder(
            hidden_dim=config.hidden_dim,
            num_action_bytes=config.action_bytes,
        )

        # RND for exploration warmup
        self.rnd = RNDNetwork(
            obs_dim=config.obs_dim,
            hidden_dim=config.rnd_hidden,
            output_dim=config.rnd_output,
        )

        # Local plasticity (fast weights)
        if config.enable_plasticity:
            self.plasticity = LocalPlasticity(PlasticityConfig(
                hidden_dim=config.hidden_dim,
                obs_dim=config.obs_dim,
                k_max=config.k_max,
                adapter_rank=config.adapter_rank,
            ))
        else:
            self.plasticity = None

        # Sleep/offline consolidation
        if config.enable_sleep:
            self.sleep = SleepModule(SleepConfig(
                hidden_dim=config.hidden_dim,
                latent_dim=config.latent_dim,
                obs_dim=config.obs_dim,
                action_bytes=config.action_bytes,
                buffer_capacity=config.buffer_capacity,
                e_sleep_max=config.e_sleep_max,
                b_sleep=config.b_sleep,
            ))
        else:
            self.sleep = None

        # Step counter for warmup
        self.register_buffer('step_count', torch.tensor(0))

        # Cache for KL intrinsic computation
        self._prev_mu: Optional[torch.Tensor] = None
        self._prev_sigma: Optional[torch.Tensor] = None

        # Cache previous values for TD error computation
        self._prev_value: Optional[torch.Tensor] = None

    def init_state(
        self,
        batch_size: int,
        device: torch.device
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Initialize hidden state and global scalars for new episode.

        Returns:
            h: Initial hidden state [batch, hidden_dim]
            g: Initial global scalars [batch, k_max]
        """
        h = self.substrate.init_hidden(batch_size, device)
        g = self.substrate.init_global_scalars(batch_size, device)

        # Reset KL cache
        self._prev_mu = None
        self._prev_sigma = None
        self._prev_value = None

        # Reset fast weights at episode start
        if self.plasticity is not None:
            self.plasticity.reset_fast_weights()

        # Reset sleep energy tracking
        if self.sleep is not None:
            self.sleep.reset_episode()

        return h, g

    def forward(
        self,
        obs_bytes: torch.Tensor,
        h_t: torch.Tensor,
        g_prev: torch.Tensor,
        a_prev: torch.Tensor,
        training: bool = True,
    ) -> RPJBrainOutput:
        """
        Single brain step.

        Args:
            obs_bytes: Raw observation bytes [batch, obs_dim]
            h_t: Current hidden state [batch, hidden_dim]
            g_prev: Previous global scalars [batch, k_max]
            a_prev: Previous action bytes [batch] or [batch, action_bytes]
            training: Whether in training mode

        Returns:
            RPJBrainOutput with all outputs
        """
        batch_size = obs_bytes.size(0)
        device = obs_bytes.device

        # Normalize observation
        phi_obs = phi(obs_bytes)

        # Encode observation to latent
        vae_output = self.vae(h_t, phi_obs, obs_bytes)
        z_t = vae_output.z_t
        mu = vae_output.mu
        sigma = vae_output.sigma
        code_len = vae_output.code_len

        # Substrate forward pass
        # Flatten a_prev if needed
        if a_prev.dim() == 2:
            a_prev_flat = a_prev[:, 0]  # Take first byte
        else:
            a_prev_flat = a_prev

        substrate_out = self.substrate(
            phi_obs=phi_obs,
            z_t=z_t,
            a_prev=a_prev_flat,
            h_t=h_t,
            g_prev=g_prev,
            training=training,
        )

        # Get value estimate
        value = self.substrate.get_value(substrate_out.h_next)

        # Generate action
        action, action_log_prob = self.action_decoder(
            substrate_out.h_next,
            num_bytes=self.config.action_bytes,
            greedy=not training,
        )

        # Compute log prob of compute decisions (k_r, N)
        _, k_r, n_t, compute_log_prob = self.substrate.compute_allocator(
            h_t, training
        )

        # Sleep probability
        if self.sleep is not None:
            omega_t = self.sleep.get_sleep_probability(substrate_out.h_next)
            is_sleeping = self.sleep.is_sleeping(omega_t)
        else:
            omega_t = torch.zeros(batch_size, device=device)
            is_sleeping = torch.zeros(batch_size, dtype=torch.bool, device=device)

        # Plasticity gate
        if self.plasticity is not None:
            P_t = self.plasticity.plasticity_gate(substrate_out.g_t)
        else:
            P_t = torch.zeros(batch_size, device=device)

        # Update step counter
        if training:
            self.step_count += batch_size

        return RPJBrainOutput(
            action=action,
            action_log_prob=action_log_prob,
            h_next=substrate_out.h_next,
            g_t=substrate_out.g_t,
            z_t=z_t,
            mu=mu,
            sigma=sigma,
            value=value,
            code_len=code_len,
            c_t=substrate_out.c_t,
            cbr_t=substrate_out.cbr_t,
            bi_t=substrate_out.bi_t,
            compute_log_prob=compute_log_prob,
            omega_t=omega_t,
            is_sleeping=is_sleeping,
            P_t=P_t,
        )

    def compute_intrinsic_reward(
        self,
        phi_obs: torch.Tensor,
        mu: torch.Tensor,
        sigma: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute intrinsic reward (RND during warmup, info gain after).

        Args:
            phi_obs: Normalized observation [batch, obs_dim]
            mu: Current posterior mean [batch, latent_dim]
            sigma: Current posterior std [batch, latent_dim]

        Returns:
            intrinsic_reward: [batch]
        """
        in_warmup = self.step_count < self.config.T_warm

        if in_warmup:
            # RND intrinsic reward
            r_int, _ = self.rnd(phi_obs)
            return self.config.lambda_rnd * r_int
        else:
            # Information gain KL intrinsic reward
            if self._prev_mu is None:
                # First step after warmup, no KL
                r_int = torch.zeros(mu.size(0), device=mu.device)
            else:
                r_int = self.vae.compute_kl_intrinsic(
                    mu, sigma, self._prev_mu, self._prev_sigma
                )

            # Cache for next step
            self._prev_mu = mu.detach()
            self._prev_sigma = sigma.detach()

            return self.config.lambda_int * r_int

    def compute_reward_per_joule(
        self,
        extrinsic_reward: torch.Tensor,
        intrinsic_reward: torch.Tensor,
        energy_t: torch.Tensor,
        code_len_t: torch.Tensor,
        e_cap_step: float = 0.1,  # From BLUEPRINT: 200J / 2000 steps
    ) -> torch.Tensor:
        """
        Compute the full RPJ reward.

        From BLUEPRINT Section 2.7:
        r̃_t = r_t + λ_int * r^int_t
        J = Σ γ^t (r̃_t - λ_E * Ê_t - λ_mdl * Ĉ_t)

        Args:
            extrinsic_reward: Environment reward [batch]
            intrinsic_reward: RND or info gain reward [batch]
            energy_t: Energy used this step [batch]
            code_len_t: Codelength this step [batch]
            e_cap_step: Per-step energy cap (for normalization)

        Returns:
            rpj_reward: Full reward for RL [batch]
        """
        # Combined extrinsic + intrinsic
        r_tilde = extrinsic_reward + intrinsic_reward

        # Normalized energy penalty
        E_hat = energy_t / e_cap_step

        # Normalized codelength penalty
        # CodeLen_t is in nats, normalize by raw observation bits (8 * obs_dim)
        C_hat = code_len_t / (8 * self.config.obs_dim)

        # Full objective
        rpj_reward = r_tilde - self.config.lambda_E * E_hat - self.config.lambda_mdl * C_hat

        return rpj_reward

    def get_action_log_prob(
        self,
        h_t: torch.Tensor,
        actions: torch.Tensor,
    ) -> torch.Tensor:
        """Get log probability of given actions (for PPO)."""
        return self.action_decoder.get_log_prob(h_t, actions)

    def get_action_entropy(self, h_t: torch.Tensor) -> torch.Tensor:
        """Get action distribution entropy (for PPO entropy bonus)."""
        return self.action_decoder.get_entropy(h_t, self.config.action_bytes)

    def update_vae_target(self):
        """Update VAE target encoder via Polyak averaging."""
        self.vae.update_target()

    def get_vae_loss(
        self,
        h_t: torch.Tensor,
        phi_obs: torch.Tensor,
        obs_bytes: torch.Tensor
    ) -> torch.Tensor:
        """Get VAE training loss for direct SGD."""
        return self.vae.get_vae_loss(h_t, phi_obs, obs_bytes)

    def get_rnd_loss(self, phi_obs: torch.Tensor) -> torch.Tensor:
        """Get RND predictor loss for training."""
        _, loss = self.rnd(phi_obs)
        return loss.mean()

    def count_parameters(self) -> Dict[str, int]:
        """Count parameters by component."""
        result = {
            'substrate': sum(p.numel() for p in self.substrate.parameters()),
            'vae': sum(p.numel() for p in self.vae.parameters() if p.requires_grad),
            'action_decoder': sum(p.numel() for p in self.action_decoder.parameters()),
            'rnd': sum(p.numel() for p in self.rnd.predictor.parameters()),
        }

        if self.plasticity is not None:
            result['plasticity_slow'] = self.plasticity.count_slow_parameters()
            result['plasticity_fast'] = self.plasticity.count_fast_parameters()

        if self.sleep is not None:
            result['sleep'] = sum(p.numel() for p in self.sleep.parameters())

        result['total'] = sum(p.numel() for p in self.parameters() if p.requires_grad)

        return result

    def update_plasticity(
        self,
        h_t: torch.Tensor,
        phi_o_next: torch.Tensor,
        reward: torch.Tensor,
        value: torch.Tensor,
        value_next: torch.Tensor,
        g_t: torch.Tensor,
    ):
        """
        Update fast weights via local plasticity rule.

        Args:
            h_t: Hidden state [batch, hidden_dim]
            phi_o_next: Normalized next observation [batch, obs_dim]
            reward: Reward [batch]
            value: V(h_t) [batch]
            value_next: V(h_{t+1}) [batch]
            g_t: Global scalars [batch, k_max]
        """
        if self.plasticity is None:
            return

        # Compute TD error
        td_error = reward + self.config.gamma * value_next - value

        # Compute local error
        e_t = self.plasticity.compute_local_error(h_t, phi_o_next, td_error)

        # Update fast weights (using h_t as pre-activation for both)
        self.plasticity.update_fast_weights(e_t, h_t, h_t, g_t)

    def add_experience_to_replay(
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
        """Add experience to sleep replay buffer."""
        if self.sleep is not None:
            self.sleep.add_experience(
                obs=obs,
                action=action,
                reward=reward,
                next_obs=next_obs,
                done=done,
                energy=energy,
                code_len=code_len,
                z_t=z_t,
                td_error=td_error,
            )

    def do_sleep_step(
        self,
        batch_size: int = 32,
    ) -> Optional[torch.Tensor]:
        """
        Perform one sleep/consolidation step.

        This implements the imagination loop from BLUEPRINT Section 2.5:
        - Sample from replay buffer
        - Re-encode next_obs to get z_next target (using target encoder)
        - Train dynamics model via 1-step consistency

        Returns:
            dynamics_loss: Loss from imagination (if any)
        """
        if self.sleep is None or len(self.sleep.replay_buffer) < batch_size:
            return None

        # Sample from replay
        batch, weights, indices = self.sleep.sample_replay(batch_size)
        device = next(self.parameters()).device

        # Move to device
        z_t = batch['z_t'].to(device)
        actions = batch['actions'].to(device)
        next_obs = batch['next_obs'].to(device)

        # Re-encode next_obs to get z_next target
        # Use target encoder to prevent drift (BLUEPRINT Section 2.6)
        phi_o_next = phi(next_obs)

        # Need h_t to encode - use zeros for now (could improve with stored h_t)
        h_dummy = torch.zeros(batch_size, self.config.hidden_dim, device=device)

        # Encode using target encoder for stable targets
        z_next_target, _, _ = self.vae.encode(h_dummy, phi_o_next, use_target=True)

        # Compute 1-step dynamics loss
        dyn_loss = self.sleep.compute_dynamics_loss(z_t, actions, z_next_target)

        # Weight by importance sampling weights
        # Note: dynamics loss is already reduced to scalar by MSE, so we just multiply
        weighted_loss = dyn_loss * weights.mean().to(device)

        return weighted_loss

    def apply_synaptic_renormalization(self):
        """Apply synaptic renormalization after sleep."""
        if self.sleep is not None:
            self.sleep.synaptic_renormalization(self.substrate)
            self.sleep.synaptic_renormalization(self.action_decoder)


def create_brain(obs_dim: int, action_bytes: int = 1, **kwargs) -> RPJBrain:
    """Factory function to create RPJ Brain."""
    config = RPJConfig(obs_dim=obs_dim, action_bytes=action_bytes, **kwargs)
    return RPJBrain(config)


if __name__ == "__main__":
    # Quick sanity check
    print("Testing RPJ Brain v2 (with Plasticity + Sleep)...")

    obs_dim = 64
    batch_size = 4

    brain = create_brain(obs_dim=obs_dim, action_bytes=1)

    # Initialize state
    device = torch.device('cpu')
    h, g = brain.init_state(batch_size, device)

    # Dummy inputs
    obs = torch.randint(0, 256, (batch_size, obs_dim))
    a_prev = torch.randint(0, 256, (batch_size,))

    # Forward pass
    output = brain(obs, h, g, a_prev, training=True)

    print(f"\n=== Shapes ===")
    print(f"Action: {output.action.shape}")
    print(f"Hidden: {output.h_next.shape}")
    print(f"Latent: {output.z_t.shape}")
    print(f"Value: {output.value.shape}")

    print(f"\n=== Core Values ===")
    print(f"Action: {output.action.tolist()}")
    print(f"Value: {output.value.tolist()}")
    print(f"CodeLen: {output.code_len.tolist()}")
    print(f"CBR: {output.cbr_t.tolist()}")
    print(f"BI: {output.bi_t.tolist()}")

    print(f"\n=== Sleep & Plasticity ===")
    print(f"ω_t (sleep prob): {output.omega_t.tolist()}")
    print(f"Is sleeping: {output.is_sleeping.tolist()}")
    print(f"P_t (plasticity gate): {output.P_t.tolist()}")

    # Test intrinsic reward
    phi_obs = phi(obs)
    r_int = brain.compute_intrinsic_reward(phi_obs, output.mu, output.sigma)
    print(f"\nIntrinsic reward (RND): {r_int.tolist()}")

    # Test RPJ reward
    extrinsic = torch.randn(batch_size)
    energy = torch.rand(batch_size) * 0.05
    rpj = brain.compute_reward_per_joule(extrinsic, r_int, energy, output.code_len)
    print(f"RPJ reward: {rpj.tolist()}")

    # Test plasticity update
    obs_next = torch.randint(0, 256, (batch_size, obs_dim))
    phi_o_next = phi(obs_next)
    reward = torch.randn(batch_size)
    value_next = brain.substrate.get_value(output.h_next)

    brain.update_plasticity(
        h, phi_o_next, reward, output.value, value_next, output.g_t
    )
    print(f"\n✓ Plasticity update OK")
    print(f"Fast weight A norm: {brain.plasticity.recurrent_adapter.A.norm().item():.4f}")

    # Test replay buffer
    for i in range(10):
        brain.add_experience_to_replay(
            obs=obs[0],
            action=output.action[0],
            reward=float(reward[0].item()),
            next_obs=obs_next[0],
            done=False,
            energy=energy[0].item(),
            code_len=output.code_len[0].item(),
            z_t=output.z_t[0],
        )
    print(f"Replay buffer size: {len(brain.sleep.replay_buffer)}")

    # Parameter counts
    print(f"\n=== Parameters ===")
    params = brain.count_parameters()
    for name, count in params.items():
        print(f"{name}: {count:,}")

    # Verify fast param budget
    if brain.plasticity is not None:
        fast = brain.plasticity.count_fast_parameters()
        total = params['total']
        budget = min(500_000, int(0.05 * total))
        print(f"\nFast param budget: {fast:,} / {budget:,} ({'OK' if fast <= budget else 'EXCEEDED!'})")

    # Gradient test
    loss = output.value.sum() + output.code_len.mean()
    loss.backward()
    print(f"\n✓ Backward pass OK")

    print("\n✓ RPJ Brain v2 works!")
