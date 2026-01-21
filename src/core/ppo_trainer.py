"""
PPO Trainer for RPJ Brain v5.

This integrates:
1. PPO for policy/value learning on the RPJ objective J
2. Direct SGD for VAE (not through RL scalar rewards)
3. Local plasticity updates during rollouts
4. Sleep/offline consolidation
5. Compute decisions (k_r, N) included in PPO policy

From BLUEPRINT Section 2.7:
- J = Σ γ^t (r̃_t - λ_E * Ê_t - λ_mdl * Ĉ_t)
- PPO (clip=0.2, lr=3e-4, entropy=0.01)
- γ ≥ 0.999
- max_grad_norm = 1.0
- PopArt value normalization

Reference: BLUEPRINT.md Sections 2.7, 2.8
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F

from src.core.rpj_brain import RPJBrain, RPJConfig, RPJBrainOutput, create_brain
from src.core.byte_interface import phi
from src.energy.proxy import EnergyTracker, EnergyConfig, EnergyBudgetExceeded


@dataclass
class PPOConfig:
    """Configuration for PPO training."""
    # PPO hyperparameters (from BLUEPRINT)
    gamma: float = 0.999
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    lr_policy: float = 3e-4
    lr_vae: float = 1e-3
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 1.0

    # Training schedule
    num_steps_per_update: int = 256
    num_epochs: int = 8  # More epochs for finer optimization
    minibatch_size: int = 64

    # VAE training
    vae_train_freq: int = 1  # Train VAE every N PPO updates
    vae_batch_size: int = 64

    # Sleep parameters
    sleep_train_freq: int = 10  # Sleep every N PPO updates
    sleep_steps: int = 50  # Steps per sleep cycle
    sleep_dyn_lr: float = 1e-3

    # Target network update
    polyak_tau: float = 1e-3

    # Collapse detection (BLUEPRINT: H(c_t) < 0.05 = invalid)
    collapse_entropy_threshold: float = 0.05

    # Energy budget
    e_cap_step: float = 0.1  # 200J / 2000 steps


@dataclass
class PopArtNormalizer:
    """
    PopArt adaptive value normalization.

    Maintains running mean and std of value targets
    and de-normalizes outputs accordingly.
    """
    mean: float = 0.0
    std: float = 1.0
    count: int = 0
    beta: float = 3e-4  # Update rate

    def update(self, values: torch.Tensor):
        """Update running statistics."""
        batch_mean = values.mean().item()
        batch_var = values.var().item()
        batch_count = values.numel()

        if self.count == 0:
            self.mean = batch_mean
            self.std = max(batch_var ** 0.5, 1e-6)
            self.count = batch_count
        else:
            # Exponential moving average
            self.mean = (1 - self.beta) * self.mean + self.beta * batch_mean
            new_var = (1 - self.beta) * (self.std ** 2) + self.beta * batch_var
            self.std = max(new_var ** 0.5, 1e-6)
            self.count += batch_count

    def normalize(self, values: torch.Tensor) -> torch.Tensor:
        """Normalize values."""
        return (values - self.mean) / self.std

    def denormalize(self, values: torch.Tensor) -> torch.Tensor:
        """De-normalize values."""
        return values * self.std + self.mean


class RPJRolloutBuffer:
    """
    Rollout buffer for RPJ Brain.

    Stores all data needed for PPO + VAE + plasticity updates.
    """

    def __init__(
        self,
        buffer_size: int,
        obs_dim: int,
        action_bytes: int,
        hidden_dim: int,
        latent_dim: int,
        k_max: int,
        device: str = "cpu",
    ):
        self.buffer_size = buffer_size
        self.obs_dim = obs_dim
        self.action_bytes = action_bytes
        self.device = device

        # Observations and actions
        self.observations = torch.zeros((buffer_size, obs_dim), dtype=torch.long, device=device)
        self.next_observations = torch.zeros((buffer_size, obs_dim), dtype=torch.long, device=device)
        self.actions = torch.zeros((buffer_size, action_bytes), dtype=torch.long, device=device)

        # Rewards and values
        self.extrinsic_rewards = torch.zeros(buffer_size, device=device)
        self.intrinsic_rewards = torch.zeros(buffer_size, device=device)
        self.rpj_rewards = torch.zeros(buffer_size, device=device)
        self.values = torch.zeros(buffer_size, device=device)

        # Log probs
        self.action_log_probs = torch.zeros((buffer_size, action_bytes), device=device)
        self.compute_log_probs = torch.zeros(buffer_size, device=device)

        # Episode markers
        self.dones = torch.zeros(buffer_size, device=device)

        # Energy and codelength
        self.energies = torch.zeros(buffer_size, device=device)
        self.code_lens = torch.zeros(buffer_size, device=device)

        # Hidden states (for recurrent PPO)
        self.hidden_states = torch.zeros((buffer_size, hidden_dim), device=device)

        # TRUNCATED BPTT(1): Store PREVIOUS states to enable gradient flow to substrate
        # These are the inputs to brain.forward(), allowing us to re-run the forward pass
        # with gradients during PPO update (JARVIS 420 fix for broken gradient chain)
        self.prev_hidden = torch.zeros((buffer_size, hidden_dim), device=device)
        self.prev_g = torch.zeros((buffer_size, k_max), device=device)
        self.prev_actions = torch.zeros((buffer_size, action_bytes), dtype=torch.long, device=device)

        # Latents (for VAE loss)
        self.latents = torch.zeros((buffer_size, latent_dim), device=device)
        self.mus = torch.zeros((buffer_size, latent_dim), device=device)
        self.sigmas = torch.zeros((buffer_size, latent_dim), device=device)

        # Global scalars
        self.g_ts = torch.zeros((buffer_size, k_max), device=device)

        # Compute allocation (for collapse detection)
        self.c_ts = torch.zeros((buffer_size, 1), device=device)

        # Stored compute decisions (for proper PPO importance sampling)
        # CRITICAL: These are the actual sampled decisions, not recomputed
        self.k_rs = torch.zeros(buffer_size, dtype=torch.long, device=device)
        self.n_ts = torch.zeros(buffer_size, dtype=torch.long, device=device)

        # Computed after rollout
        self.advantages = torch.zeros(buffer_size, device=device)
        self.returns = torch.zeros(buffer_size, device=device)

        self.pos = 0
        self.full = False

    def add(
        self,
        obs: torch.Tensor,
        next_obs: torch.Tensor,
        action: torch.Tensor,
        extrinsic_reward: float,
        intrinsic_reward: float,
        rpj_reward: float,
        value: float,
        action_log_prob: torch.Tensor,
        compute_log_prob: float,
        done: bool,
        energy: float,
        code_len: float,
        hidden: torch.Tensor,
        z_t: torch.Tensor,
        mu: torch.Tensor,
        sigma: torch.Tensor,
        g_t: torch.Tensor,
        c_t: torch.Tensor,
        k_r: int,
        n_t: int,
        # TRUNCATED BPTT(1): Previous states for gradient flow
        prev_h: torch.Tensor,
        prev_g: torch.Tensor,
        prev_a: torch.Tensor,
    ):
        """Add a transition to the buffer."""
        self.observations[self.pos] = obs.flatten()
        self.next_observations[self.pos] = next_obs.flatten()
        self.actions[self.pos] = action.flatten()
        self.extrinsic_rewards[self.pos] = extrinsic_reward
        self.intrinsic_rewards[self.pos] = intrinsic_reward
        self.rpj_rewards[self.pos] = rpj_reward
        self.values[self.pos] = value
        self.action_log_probs[self.pos] = action_log_prob.flatten()
        self.compute_log_probs[self.pos] = compute_log_prob
        self.dones[self.pos] = float(done)
        self.energies[self.pos] = energy
        self.code_lens[self.pos] = code_len
        self.hidden_states[self.pos] = hidden.flatten()
        self.latents[self.pos] = z_t.flatten()
        self.mus[self.pos] = mu.flatten()
        self.sigmas[self.pos] = sigma.flatten()
        self.g_ts[self.pos] = g_t.flatten()
        self.c_ts[self.pos] = c_t.flatten()
        # Store compute decisions for proper PPO importance sampling
        self.k_rs[self.pos] = k_r
        self.n_ts[self.pos] = n_t
        # TRUNCATED BPTT(1): Store previous states for re-running forward pass with gradients
        self.prev_hidden[self.pos] = prev_h.flatten()
        self.prev_g[self.pos] = prev_g.flatten()
        self.prev_actions[self.pos] = prev_a.flatten()

        self.pos += 1
        if self.pos >= self.buffer_size:
            self.full = True
            self.pos = 0

    def compute_returns_and_advantages(
        self,
        last_value: float,
        gamma: float = 0.999,
        gae_lambda: float = 0.95,
    ):
        """Compute GAE advantages and returns using RPJ rewards."""
        last_gae = 0

        for step in reversed(range(self.buffer_size)):
            if step == self.buffer_size - 1:
                next_value = last_value
            else:
                next_value = self.values[step + 1]

            next_non_terminal = 1.0 - self.dones[step]
            delta = self.rpj_rewards[step] + gamma * next_value * next_non_terminal - self.values[step]
            self.advantages[step] = last_gae = delta + gamma * gae_lambda * next_non_terminal * last_gae

        self.returns = self.advantages + self.values

    def get_batches(self, batch_size: int):
        """Generate minibatches for PPO update."""
        indices = torch.randperm(self.buffer_size, device=self.device)

        for start in range(0, self.buffer_size, batch_size):
            end = min(start + batch_size, self.buffer_size)
            batch_indices = indices[start:end]

            yield {
                'observations': self.observations[batch_indices],
                'actions': self.actions[batch_indices],
                'action_log_probs': self.action_log_probs[batch_indices],
                'compute_log_probs': self.compute_log_probs[batch_indices],
                'returns': self.returns[batch_indices],
                'advantages': self.advantages[batch_indices],
                'hidden_states': self.hidden_states[batch_indices],
                'latents': self.latents[batch_indices],
                'g_ts': self.g_ts[batch_indices],
                # Stored compute decisions for proper importance sampling
                'k_rs': self.k_rs[batch_indices],
                'n_ts': self.n_ts[batch_indices],
                # TRUNCATED BPTT(1): Previous states for re-running forward pass
                'prev_hidden': self.prev_hidden[batch_indices],
                'prev_g': self.prev_g[batch_indices],
                'prev_actions': self.prev_actions[batch_indices],
            }

    def get_vae_batches(self, batch_size: int):
        """Generate minibatches for VAE training."""
        indices = torch.randperm(self.buffer_size, device=self.device)

        for start in range(0, self.buffer_size, batch_size):
            end = min(start + batch_size, self.buffer_size)
            batch_indices = indices[start:end]

            yield {
                'observations': self.observations[batch_indices],
                'hidden_states': self.hidden_states[batch_indices],
            }

    def compute_collapse_metric(self) -> float:
        """
        Compute entropy of compute allocation.

        From BLUEPRINT: H(c_t) < 0.05 = collapse = invalid run.
        """
        c = self.c_ts[:self.buffer_size if not self.full else self.buffer_size]
        c = c.clamp(1e-7, 1 - 1e-7)

        # Binary entropy
        entropy = -c * torch.log(c) - (1 - c) * torch.log(1 - c)
        return entropy.mean().item()

    def reset(self):
        """Reset buffer."""
        self.pos = 0
        self.full = False


class RPJTrainer:
    """
    PPO Trainer for RPJ Brain v5.

    Implements the complete training loop from BLUEPRINT Section 2.8.
    """

    def __init__(
        self,
        brain: RPJBrain,
        config: Optional[PPOConfig] = None,
        energy_config: Optional[EnergyConfig] = None,
        device: str = "cpu",
    ):
        self.brain = brain.to(device)
        self.config = config or PPOConfig()
        self.device = device

        # Energy tracking
        self.energy_tracker = EnergyTracker(energy_config)

        # Optimizers
        # Policy parameters (substrate + action decoder)
        policy_params = list(brain.substrate.parameters()) + list(brain.action_decoder.parameters())
        if brain.plasticity is not None:
            policy_params += list(brain.plasticity.parameters())
        if brain.sleep is not None:
            # Only train sleep trigger through RL, not dynamics model
            policy_params += list(brain.sleep.trigger.parameters())

        self.policy_optimizer = torch.optim.Adam(policy_params, lr=self.config.lr_policy)

        # VAE optimizer (direct SGD on ELBO)
        self.vae_optimizer = torch.optim.Adam(brain.vae.parameters(), lr=self.config.lr_vae)

        # RND optimizer (during warmup)
        self.rnd_optimizer = torch.optim.Adam(brain.rnd.predictor.parameters(), lr=self.config.lr_policy)

        # Sleep dynamics optimizer
        if brain.sleep is not None:
            self.sleep_optimizer = torch.optim.Adam(
                brain.sleep.dynamics.parameters(),
                lr=self.config.sleep_dyn_lr
            )
        else:
            self.sleep_optimizer = None

        # Rollout buffer
        self.buffer = RPJRolloutBuffer(
            buffer_size=self.config.num_steps_per_update,
            obs_dim=brain.config.obs_dim,
            action_bytes=brain.config.action_bytes,
            hidden_dim=brain.config.hidden_dim,
            latent_dim=brain.config.latent_dim,
            k_max=brain.config.k_max,
            device=device,
        )

        # Value normalization
        self.popart = PopArtNormalizer()

        # Statistics tracking
        self.update_count = 0
        self.total_steps = 0

    def collect_rollout(
        self,
        env,
        num_steps: int,
    ) -> Dict[str, float]:
        """
        Collect rollout data from environment with full RPJ Brain.

        Implements the per-step loop from BLUEPRINT Section 2.8.
        """
        obs, info = env.reset()
        obs = torch.tensor(obs, dtype=torch.long, device=self.device).unsqueeze(0)

        # Initialize brain state
        batch_size = 1
        h, g = self.brain.init_state(batch_size, self.device)
        a_prev = torch.zeros((batch_size, self.brain.config.action_bytes), dtype=torch.long, device=self.device)

        # Reset energy tracking for episode
        self.energy_tracker.reset_episode()

        episode_rewards = []
        episode_lengths = []
        episode_rpj_rewards = []
        current_episode_reward = 0
        current_episode_length = 0
        current_episode_rpj = 0

        prev_value = None

        # Emergence metrics tracking (verbose but not spammy)
        all_cbr = []      # Compute burst ratio
        all_k_r = []      # Routed block counts
        all_n_t = []      # Rollout step counts
        all_g_t = []      # Global scalars (for K_eff)

        for step in range(num_steps):
            # Brain forward pass
            with torch.no_grad():
                output = self.brain(obs, h, g, a_prev, training=True)

            # Track energy for this step - SCALED BY COMPUTE ALLOCATION
            # Per BLUEPRINT: Energy must depend on c_t/k_r for λ_E to create emergence pressure
            # k_r = number of routed blocks (1 to k_r_max=4)
            # Energy scales linearly with k_r: more blocks = more compute = more energy
            k_r = output.k_r.item() if output.k_r.numel() == 1 else output.k_r[0].item()
            k_r_max = 4  # From BLUEPRINT K_R_MAX
            num_blocks = 64  # From BLUEPRINT B=64

            # Base energy: fixed costs (embedding, LayerNorm, etc.)
            self.energy_tracker.record_linear(self.brain.config.obs_dim, self.brain.config.hidden_dim, 1)

            # Scaled energy: GRU blocks - only k_r out of num_blocks are active
            # Full GRU would be hidden_dim → hidden_dim, but sparse routing means
            # only (k_r / num_blocks) fraction of hidden units are updated
            active_fraction = k_r / num_blocks
            effective_hidden = int(self.brain.config.hidden_dim * active_fraction)
            self.energy_tracker.record_gru_step(
                self.brain.config.hidden_dim,
                max(effective_hidden, 1),  # At least 1 unit active
                1
            )
            energy_t = self.energy_tracker.step_energy

            # Commit step energy (may raise if budget exceeded)
            try:
                self.energy_tracker.commit_step()
            except EnergyBudgetExceeded:
                # End episode early if energy exceeded
                break

            # Step environment
            action_np = output.action.squeeze(0).cpu().numpy()
            next_obs, extrinsic_reward, terminated, truncated, info = env.step(action_np)
            done = terminated or truncated

            # Compute intrinsic reward
            phi_obs = phi(obs)
            intrinsic_reward = self.brain.compute_intrinsic_reward(
                phi_obs, output.mu, output.sigma
            ).item()

            # Compute full RPJ reward (includes g_t sparsity penalty for K_eff)
            rpj_reward = self.brain.compute_reward_per_joule(
                torch.tensor([extrinsic_reward], device=self.device),
                torch.tensor([intrinsic_reward], device=self.device),
                torch.tensor([energy_t], device=self.device),
                output.code_len,
                g_t=output.g_t,  # K_eff fix: pass g_t for sparsity penalty
                omega_t=output.omega_t,  # Sleep energy: wire ω_t into energy penalty
                e_cap_step=self.config.e_cap_step,
            ).item()

            # Store in buffer
            # CRITICAL: Store h_next, NOT h. Actions/values are computed from h_next
            # (see rpj_brain.py lines 326-333: action_decoder uses substrate_out.h_next)
            next_obs_tensor = torch.tensor(next_obs, dtype=torch.long, device=self.device).unsqueeze(0)
            # Extract k_r and n_t as scalars for storage
            k_r_val = output.k_r.item() if output.k_r.numel() == 1 else output.k_r[0].item()
            n_t_val = output.n_t.item() if output.n_t.numel() == 1 else output.n_t[0].item()

            # Track emergence metrics (verbose logging)
            all_cbr.append(output.cbr_t.item() if output.cbr_t.numel() == 1 else output.cbr_t[0].item())
            all_k_r.append(k_r_val)
            all_n_t.append(n_t_val)
            all_g_t.append(output.g_t.squeeze(0).cpu().numpy())

            self.buffer.add(
                obs=obs.squeeze(0),
                next_obs=next_obs_tensor.squeeze(0),
                action=output.action.squeeze(0),
                extrinsic_reward=extrinsic_reward,
                intrinsic_reward=intrinsic_reward,
                rpj_reward=rpj_reward,
                value=output.value.item(),
                action_log_prob=output.action_log_prob.squeeze(0),
                compute_log_prob=output.compute_log_prob.item(),
                done=done,
                energy=energy_t,
                code_len=output.code_len.item(),
                hidden=output.h_next.squeeze(0),  # FIX: Use h_next, not h
                z_t=output.z_t.squeeze(0),
                mu=output.mu.squeeze(0),
                sigma=output.sigma.squeeze(0),
                g_t=output.g_t.squeeze(0),
                c_t=output.c_t.squeeze(0),
                k_r=int(k_r_val),  # Store actual sampled k_r
                n_t=int(n_t_val),  # Store actual sampled n_t
                # TRUNCATED BPTT(1): Store PREVIOUS states (inputs to forward pass)
                # These enable re-running forward pass with gradients during PPO update
                prev_h=h.squeeze(0),   # Hidden state BEFORE forward pass
                prev_g=g.squeeze(0),   # Global scalars BEFORE forward pass
                prev_a=a_prev.unsqueeze(0) if a_prev.dim() == 0 else a_prev,  # Previous action
            )

            # Add to replay buffer for sleep
            if self.brain.sleep is not None:
                td_error = None
                if prev_value is not None:
                    td_error = abs(extrinsic_reward + self.config.gamma * output.value.item() - prev_value)
                self.brain.add_experience_to_replay(
                    obs=obs.squeeze(0),
                    action=output.action.squeeze(0),
                    reward=extrinsic_reward,
                    next_obs=next_obs_tensor.squeeze(0),
                    done=done,
                    energy=energy_t,
                    code_len=output.code_len.item(),
                    z_t=output.z_t.squeeze(0),
                    h_t=output.h_next.squeeze(0),  # Needed for stable next_obs encoding during sleep
                    td_error=td_error,
                )

            # Update plasticity (within-episode fast weights)
            if self.brain.plasticity is not None and not done:
                phi_o_next = phi(next_obs_tensor)
                with torch.no_grad():
                    next_output = self.brain(next_obs_tensor, output.h_next, output.g_t, output.action, training=False)
                self.brain.update_plasticity(
                    h_t=h,
                    phi_o_next=phi_o_next.squeeze(0),
                    reward=torch.tensor([extrinsic_reward], device=self.device),
                    value=output.value,
                    value_next=next_output.value,
                    g_t=output.g_t,
                )

            # Track episode stats
            current_episode_reward += extrinsic_reward
            current_episode_rpj += rpj_reward
            current_episode_length += 1
            prev_value = output.value.item()

            if done:
                episode_rewards.append(current_episode_reward)
                episode_rpj_rewards.append(current_episode_rpj)
                episode_lengths.append(current_episode_length)
                current_episode_reward = 0
                current_episode_rpj = 0
                current_episode_length = 0
                prev_value = None

                # Reset for new episode
                obs, info = env.reset()
                obs = torch.tensor(obs, dtype=torch.long, device=self.device).unsqueeze(0)
                h, g = self.brain.init_state(batch_size, self.device)
                a_prev = torch.zeros((batch_size, self.brain.config.action_bytes), dtype=torch.long, device=self.device)
                self.energy_tracker.reset_episode()
            else:
                obs = next_obs_tensor
                h = output.h_next
                g = output.g_t
                a_prev = output.action

            self.total_steps += 1

        # Compute last value for GAE
        with torch.no_grad():
            final_output = self.brain(obs, h, g, a_prev, training=False)
            last_value = final_output.value.item()

        self.buffer.compute_returns_and_advantages(
            last_value,
            gamma=self.config.gamma,
            gae_lambda=self.config.gae_lambda,
        )

        # Update PopArt normalizer
        self.popart.update(self.buffer.returns)

        # Check for collapse
        collapse_metric = self.buffer.compute_collapse_metric()

        # Compute emergence metrics (verbose logging)
        cbr_array = np.array(all_cbr) if all_cbr else np.array([1.0])
        k_r_array = np.array(all_k_r) if all_k_r else np.array([1])
        n_t_array = np.array(all_n_t) if all_n_t else np.array([0])
        g_t_array = np.array(all_g_t) if all_g_t else np.zeros((1, 16))

        # CBR bimodality: Ashman's D coefficient
        # D > 2 indicates bimodal, D < 2 indicates unimodal
        # Using simplified version: check for two distinct clusters
        cbr_sorted = np.sort(cbr_array)
        mid = len(cbr_sorted) // 2
        if mid > 0:
            cbr_low_mean = cbr_sorted[:mid].mean()
            cbr_high_mean = cbr_sorted[mid:].mean()
            cbr_low_std = cbr_sorted[:mid].std() + 1e-8
            cbr_high_std = cbr_sorted[mid:].std() + 1e-8
            # Bimodality index (higher = more bimodal)
            cbr_bimodality = abs(cbr_high_mean - cbr_low_mean) / (cbr_low_std + cbr_high_std)
        else:
            cbr_bimodality = 0.0

        # K_eff: Participation ratio over global scalar variances
        # K_eff = (Σ Var(g_k))² / Σ Var(g_k)²
        g_t_var = g_t_array.var(axis=0)  # Variance of each scalar across time
        var_sum = g_t_var.sum()
        var_sq_sum = (g_t_var ** 2).sum() + 1e-8
        k_eff = (var_sum ** 2) / var_sq_sum if var_sum > 0 else 0.0

        return {
            "mean_extrinsic_reward": np.mean(episode_rewards) if episode_rewards else 0.0,
            "mean_rpj_reward": np.mean(episode_rpj_rewards) if episode_rpj_rewards else 0.0,
            "mean_length": np.mean(episode_lengths) if episode_lengths else 0.0,
            "num_episodes": len(episode_rewards),
            "energy_J": self.energy_tracker.total_energy,
            "collapse_entropy": collapse_metric,
            # Emergence metrics
            "cbr_mean": float(cbr_array.mean()),
            "cbr_std": float(cbr_array.std()),
            "cbr_max": float(cbr_array.max()),
            "cbr_bimodality": float(cbr_bimodality),
            "k_r_mean": float(k_r_array.mean()),
            "n_t_mean": float(n_t_array.mean()),
            "K_eff": float(k_eff),
        }

    def update_policy(self) -> Dict[str, float]:
        """
        Perform PPO update on collected data.

        From BLUEPRINT: PPO (clip=0.2, lr=3e-4, entropy=0.01).
        """
        policy_losses = []
        value_losses = []
        entropy_losses = []
        compute_policy_losses = []

        for epoch in range(self.config.num_epochs):
            for batch in self.buffer.get_batches(self.config.minibatch_size):
                obs = batch['observations']
                actions = batch['actions']
                old_action_log_probs = batch['action_log_probs']
                old_compute_log_probs = batch['compute_log_probs']
                returns = batch['returns']
                advantages = batch['advantages']
                # CRITICAL FIX (Caveat 1): Use stored compute decisions
                stored_k_r = batch['k_rs']
                stored_n_t = batch['n_ts']
                # TRUNCATED BPTT(1): Get PREVIOUS states for re-running forward pass
                prev_h = batch['prev_hidden']
                prev_g = batch['prev_g']
                prev_a = batch['prev_actions']
                stored_z = batch['latents']  # JARVIS 420 FIX: Use stored latents

                # Normalize advantages
                advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

                # Normalize returns with PopArt
                normalized_returns = self.popart.normalize(returns)

                # TRUNCATED BPTT(1) FIX (JARVIS 420):
                # Re-run forward pass WITH GRADIENTS to restore obs→substrate→action chain.
                # The original code used detached hidden states, breaking gradient flow.
                # Without this, the substrate never learns and outputs random noise.
                # JARVIS 420 FIX #2: Pass stored_z to ensure substrate sees SAME context
                action_log_probs, entropy, values, g_t, h_next, _ = self.brain.evaluate_actions(
                    obs_bytes=obs,
                    prev_h=prev_h,
                    prev_g=prev_g,
                    prev_a=prev_a,
                    actions=actions,
                    z_t=stored_z,  # Prevents re-sampling noise from washing out signal
                )

                # CRITICAL FIX (Caveat 1): Compute log_prob of STORED (k_r, n_t) decisions
                # under current params, WITHOUT resampling new decisions.
                # This ensures proper importance sampling for compute allocation learning.
                # NOTE: We use h_next (from fresh forward pass) for consistency
                new_compute_log_probs = self.brain.substrate.compute_allocator.get_log_prob(
                    h_next, stored_k_r, stored_n_t
                )

                # Total log prob = action log prob + compute decision log prob
                # This ensures compute allocation is optimized via RL
                action_log_probs_sum = action_log_probs.sum(dim=-1)
                old_action_log_probs_sum = old_action_log_probs.sum(dim=-1)

                # Total old log prob (actions + compute)
                old_total_log_prob = old_action_log_probs_sum + old_compute_log_probs

                # Total new log prob (actions + compute)
                new_total_log_prob = action_log_probs_sum + new_compute_log_probs

                # PPO ratio using total log probs
                ratio = torch.exp(new_total_log_prob - old_total_log_prob)
                surr1 = ratio * advantages
                surr2 = torch.clamp(ratio, 1 - self.config.clip_epsilon, 1 + self.config.clip_epsilon) * advantages
                policy_loss = -torch.min(surr1, surr2).mean()

                # Value loss (with PopArt normalization)
                value_loss = F.mse_loss(values, normalized_returns)

                # Entropy loss
                entropy_loss = -entropy.mean()

                # Total loss
                loss = (
                    policy_loss
                    + self.config.value_coef * value_loss
                    + self.config.entropy_coef * entropy_loss
                )

                # Optimize
                self.policy_optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.brain.parameters(), self.config.max_grad_norm)
                self.policy_optimizer.step()

                policy_losses.append(policy_loss.item())
                value_losses.append(value_loss.item())
                entropy_losses.append(-entropy_loss.item())

        self.buffer.reset()

        return {
            "policy_loss": np.mean(policy_losses),
            "value_loss": np.mean(value_losses),
            "entropy": np.mean(entropy_losses),
        }

    def update_vae(self) -> Dict[str, float]:
        """
        Train VAE via direct SGD on ELBO (not through RL).

        From BLUEPRINT: "do not rely on PPO scalar rewards to train the decoder".
        """
        vae_losses = []
        rnd_losses = []

        for batch in self.buffer.get_vae_batches(self.config.vae_batch_size):
            obs = batch['observations']
            hidden = batch['hidden_states']

            phi_obs = phi(obs)

            # VAE loss (direct ELBO)
            vae_loss = self.brain.get_vae_loss(hidden, phi_obs, obs)

            self.vae_optimizer.zero_grad()
            vae_loss.backward()
            nn.utils.clip_grad_norm_(self.brain.vae.parameters(), self.config.max_grad_norm)
            self.vae_optimizer.step()

            vae_losses.append(vae_loss.item())

            # RND loss (during warmup)
            if self.brain.step_count < self.brain.config.T_warm:
                rnd_loss = self.brain.get_rnd_loss(phi_obs)

                self.rnd_optimizer.zero_grad()
                rnd_loss.backward()
                self.rnd_optimizer.step()

                rnd_losses.append(rnd_loss.item())

        # Update target encoder
        self.brain.update_vae_target()

        return {
            "vae_loss": np.mean(vae_losses),
            "rnd_loss": np.mean(rnd_losses) if rnd_losses else 0.0,
        }

    def do_sleep(self) -> Dict[str, float]:
        """
        Perform sleep/offline consolidation.

        From BLUEPRINT Section 2.5: replay + imagination + renormalization.
        """
        if self.brain.sleep is None:
            return {}

        dyn_losses = []

        for _ in range(self.config.sleep_steps):
            dyn_loss = self.brain.do_sleep_step(batch_size=self.config.minibatch_size)

            if dyn_loss is not None:
                self.sleep_optimizer.zero_grad()
                dyn_loss.backward()
                nn.utils.clip_grad_norm_(self.brain.sleep.dynamics.parameters(), self.config.max_grad_norm)
                self.sleep_optimizer.step()

                dyn_losses.append(dyn_loss.item())

        # Apply synaptic renormalization after sleep
        self.brain.apply_synaptic_renormalization()

        # Update beta for importance sampling
        self.brain.sleep.update_training_steps(self.total_steps)

        return {
            "dynamics_loss": np.mean(dyn_losses) if dyn_losses else 0.0,
        }

    def train(
        self,
        env,
        total_timesteps: int,
        log_interval: int = 10,
        callback=None,
    ) -> List[Dict[str, float]]:
        """
        Train the RPJ Brain.

        Args:
            env: Gym-like environment
            total_timesteps: Total training steps
            log_interval: How often to print stats
            callback: Optional callback(stats) called after each update

        Returns:
            List of training statistics per update
        """
        num_updates = total_timesteps // self.config.num_steps_per_update
        all_stats = []

        for update in range(num_updates):
            self.update_count += 1

            # Collect rollout
            rollout_stats = self.collect_rollout(env, self.config.num_steps_per_update)

            # Check for collapse
            if rollout_stats['collapse_entropy'] < self.config.collapse_entropy_threshold:
                print(f"WARNING: Compute allocation collapse detected! H(c_t)={rollout_stats['collapse_entropy']:.4f}")

            # Policy update
            policy_stats = self.update_policy()

            # VAE update
            if self.update_count % self.config.vae_train_freq == 0:
                vae_stats = self.update_vae()
            else:
                vae_stats = {}

            # Sleep/consolidation
            if self.update_count % self.config.sleep_train_freq == 0:
                sleep_stats = self.do_sleep()
            else:
                sleep_stats = {}

            # Combine stats
            stats = {
                **rollout_stats,
                **policy_stats,
                **vae_stats,
                **sleep_stats,
                "update": update,
                "timesteps": self.total_steps,
            }

            all_stats.append(stats)

            if callback:
                callback(stats)

            if (update + 1) % log_interval == 0:
                print(f"Update {update + 1}/{num_updates} | t={stats['timesteps']}")
                print(f"  Reward: ext={stats.get('mean_extrinsic_reward', 0):.3f}, rpj={stats.get('mean_rpj_reward', 0):.3f}")
                print(f"  Loss: policy={stats.get('policy_loss', 0):.4f}, vae={stats.get('vae_loss', 0):.4f}")
                print(f"  Energy: {stats.get('energy_J', 0):.4f} J | Collapse H: {stats.get('collapse_entropy', 0):.4f}")
                # Emergence metrics (verbose but informative)
                cbr_b = stats.get('cbr_bimodality', 0)
                k_eff = stats.get('K_eff', 0)
                k_r = stats.get('k_r_mean', 0)
                n_t = stats.get('n_t_mean', 0)
                cbr_status = "BIMODAL" if cbr_b > 0.555 else "unimodal"
                k_status = "TARGET" if 2 <= k_eff <= 6 else "not compressed"
                print(f"  Emergence: CBR_B={cbr_b:.3f} ({cbr_status}), K_eff={k_eff:.2f} ({k_status})")
                print(f"  Compute: k_r={k_r:.2f}, n_t={n_t:.2f}")

        return all_stats


def create_trainer(
    obs_dim: int,
    action_bytes: int = 1,
    device: str = "cpu",
    **brain_kwargs
) -> Tuple[RPJBrain, RPJTrainer]:
    """Factory function to create brain and trainer."""
    brain = create_brain(obs_dim=obs_dim, action_bytes=action_bytes, **brain_kwargs)
    trainer = RPJTrainer(brain, device=device)
    return brain, trainer


if __name__ == "__main__":
    # Quick sanity check
    print("Testing PPO Trainer for RPJ Brain v5...")

    from src.benchmarks.ccb import CCBEnvironment

    # Create simple CCB environment (byte observations)
    env = CCBEnvironment()

    # Create trainer with matching observation/action sizes
    brain, trainer = create_trainer(
        obs_dim=env.observation_space_bytes,
        action_bytes=env.action_space_bytes,
        device="cpu",
    )

    print(f"\n=== Brain Parameters ===")
    params = brain.count_parameters()
    for name, count in params.items():
        print(f"  {name}: {count:,}")

    # Run a few updates
    print(f"\n=== Running 2 updates ===")
    stats = trainer.train(env, total_timesteps=512, log_interval=1)

    print(f"\n=== Final Stats ===")
    final = stats[-1]
    print(f"  Timesteps: {final['timesteps']}")
    print(f"  RPJ Reward: {final.get('mean_rpj_reward', 0):.3f}")
    print(f"  Collapse H: {final.get('collapse_entropy', 0):.4f}")

    print("\n✓ PPO Trainer works!")
