"""
MF-1 Baseline: PPO + GRU Agent

The "Rat" - a simple model-free baseline to validate the training pipeline.
Uses the same byte interface and energy tracking as the full RPJ Brain.

Architecture:
- GRU encoder for observations
- Autoregressive action decoder
- Separate value head
- PPO training

Energy Constraint: Same energy budget as RPJ Brain (B_max_ep = 200J)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from src.core.byte_interface import phi, AutoregressiveActionDecoder
from src.energy.proxy import EnergyTracker, EnergyConfig, EnergyBudgetExceeded


@dataclass
class MF1Config:
    """Configuration for MF-1 baseline."""

    # Architecture
    hidden_dim: int = 256  # Smaller than full brain
    gru_layers: int = 1
    decoder_hidden: int = 64
    byte_embed_dim: int = 16

    # PPO hyperparameters (from BLUEPRINT.md)
    gamma: float = 0.999
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    lr: float = 3e-4
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 1.0

    # Training
    num_steps_per_update: int = 256
    num_epochs: int = 4
    minibatch_size: int = 64


class MF1Agent(nn.Module):
    """
    Model-Free Baseline Agent (MF-1).

    Simple PPO + GRU architecture for byte environments.
    """

    def __init__(
        self,
        obs_bytes: int,
        action_bytes: int,
        config: Optional[MF1Config] = None,
    ):
        super().__init__()

        self.config = config or MF1Config()
        self.obs_bytes = obs_bytes
        self.action_bytes = action_bytes

        # Observation encoder: bytes → hidden
        self.obs_encoder = nn.Linear(obs_bytes, self.config.hidden_dim)

        # GRU for temporal processing
        self.gru = nn.GRU(
            input_size=self.config.hidden_dim,
            hidden_size=self.config.hidden_dim,
            num_layers=self.config.gru_layers,
            batch_first=True,
        )

        # Value head
        self.value_head = nn.Linear(self.config.hidden_dim, 1)

        # Action decoder (autoregressive)
        self.action_decoder = AutoregressiveActionDecoder(
            hidden_dim=self.config.hidden_dim,
            decoder_hidden=self.config.decoder_hidden,
            byte_embed_dim=self.config.byte_embed_dim,
            num_action_bytes=action_bytes,
        )

        # Hidden state for recurrent processing
        self._hidden: Optional[torch.Tensor] = None

    def reset_hidden(self, batch_size: int = 1) -> None:
        """Reset GRU hidden state for new episode."""
        self._hidden = torch.zeros(
            self.config.gru_layers,
            batch_size,
            self.config.hidden_dim,
            device=next(self.parameters()).device,
        )

    def forward(
        self,
        obs: torch.Tensor,  # [batch, obs_bytes] uint8
        hidden: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass: observation → (action, log_prob, value, hidden).

        Args:
            obs: Byte observation [batch, obs_bytes]
            hidden: GRU hidden state [layers, batch, hidden]

        Returns:
            action: Sampled action bytes [batch, action_bytes]
            log_prob: Log probability of action [batch, action_bytes]
            value: State value [batch]
            hidden: Updated hidden state
        """
        batch_size = obs.size(0)

        if hidden is None:
            hidden = torch.zeros(
                self.config.gru_layers,
                batch_size,
                self.config.hidden_dim,
                device=obs.device,
            )

        # Encode observation (apply phi normalization)
        obs_normalized = phi(obs.float())  # [batch, obs_bytes] → [-1, 1]
        obs_embed = F.relu(self.obs_encoder(obs_normalized))  # [batch, hidden]

        # GRU step
        obs_embed = obs_embed.unsqueeze(1)  # [batch, 1, hidden]
        gru_out, hidden = self.gru(obs_embed, hidden)
        h = gru_out.squeeze(1)  # [batch, hidden]

        # Value prediction
        value = self.value_head(h).squeeze(-1)  # [batch]

        # Action sampling
        action, log_prob = self.action_decoder(h)

        return action, log_prob, value, hidden

    def get_value(
        self,
        obs: torch.Tensor,
        hidden: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Get value estimate for observation."""
        batch_size = obs.size(0)

        if hidden is None:
            hidden = torch.zeros(
                self.config.gru_layers,
                batch_size,
                self.config.hidden_dim,
                device=obs.device,
            )

        obs_normalized = phi(obs.float())
        obs_embed = F.relu(self.obs_encoder(obs_normalized))
        obs_embed = obs_embed.unsqueeze(1)
        gru_out, hidden = self.gru(obs_embed, hidden)
        h = gru_out.squeeze(1)

        value = self.value_head(h).squeeze(-1)

        return value, hidden

    def evaluate_actions(
        self,
        obs: torch.Tensor,
        actions: torch.Tensor,
        hidden: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Evaluate log probabilities and values for given obs-action pairs.

        Used during PPO update.

        Returns:
            log_probs: [batch, action_bytes]
            values: [batch]
            entropy: [batch]
        """
        batch_size = obs.size(0)

        if hidden is None:
            hidden = torch.zeros(
                self.config.gru_layers,
                batch_size,
                self.config.hidden_dim,
                device=obs.device,
            )

        obs_normalized = phi(obs.float())
        obs_embed = F.relu(self.obs_encoder(obs_normalized))
        obs_embed = obs_embed.unsqueeze(1)
        gru_out, _ = self.gru(obs_embed, hidden)
        h = gru_out.squeeze(1)

        value = self.value_head(h).squeeze(-1)
        log_probs = self.action_decoder.get_log_prob(h, actions)
        entropy = self.action_decoder.get_entropy(h)

        return log_probs, value, entropy


class RolloutBuffer:
    """Buffer for storing rollout data."""

    def __init__(self, buffer_size: int, obs_dim: int, action_dim: int, device: str = "cpu"):
        self.buffer_size = buffer_size
        self.device = device

        self.observations = torch.zeros((buffer_size, obs_dim), dtype=torch.float32, device=device)
        self.actions = torch.zeros((buffer_size, action_dim), dtype=torch.long, device=device)
        self.rewards = torch.zeros(buffer_size, device=device)
        self.values = torch.zeros(buffer_size, device=device)
        self.log_probs = torch.zeros((buffer_size, action_dim), device=device)
        self.dones = torch.zeros(buffer_size, device=device)
        self.advantages = torch.zeros(buffer_size, device=device)
        self.returns = torch.zeros(buffer_size, device=device)

        self.pos = 0
        self.full = False

    def add(
        self,
        obs: torch.Tensor,
        action: torch.Tensor,
        reward: float,
        value: float,
        log_prob: torch.Tensor,
        done: bool,
    ) -> None:
        """Add a transition to the buffer."""
        self.observations[self.pos] = obs.flatten()
        self.actions[self.pos] = action.flatten()
        self.rewards[self.pos] = reward
        self.values[self.pos] = value
        self.log_probs[self.pos] = log_prob.flatten()
        self.dones[self.pos] = float(done)

        self.pos += 1
        if self.pos >= self.buffer_size:
            self.full = True
            self.pos = 0

    def compute_returns_and_advantages(
        self,
        last_value: float,
        gamma: float = 0.999,
        gae_lambda: float = 0.95,
    ) -> None:
        """Compute GAE advantages and returns."""
        last_gae = 0

        for step in reversed(range(self.buffer_size)):
            if step == self.buffer_size - 1:
                next_value = last_value
            else:
                next_value = self.values[step + 1]

            next_non_terminal = 1.0 - self.dones[step]
            delta = self.rewards[step] + gamma * next_value * next_non_terminal - self.values[step]
            self.advantages[step] = last_gae = delta + gamma * gae_lambda * next_non_terminal * last_gae

        self.returns = self.advantages + self.values

    def get_batches(self, batch_size: int):
        """Generate minibatches for PPO update."""
        indices = torch.randperm(self.buffer_size)

        for start in range(0, self.buffer_size, batch_size):
            end = start + batch_size
            batch_indices = indices[start:end]

            yield (
                self.observations[batch_indices],
                self.actions[batch_indices],
                self.log_probs[batch_indices],
                self.returns[batch_indices],
                self.advantages[batch_indices],
            )

    def reset(self) -> None:
        """Reset buffer."""
        self.pos = 0
        self.full = False


class MF1Trainer:
    """
    PPO Trainer for MF-1 baseline.

    Includes energy tracking and budget enforcement.
    """

    def __init__(
        self,
        agent: MF1Agent,
        config: Optional[MF1Config] = None,
        energy_config: Optional[EnergyConfig] = None,
        device: str = "cpu",
    ):
        self.agent = agent.to(device)
        self.config = config or agent.config
        self.device = device

        # Energy tracking
        self.energy_tracker = EnergyTracker(energy_config)

        # Optimizer
        self.optimizer = torch.optim.Adam(
            agent.parameters(),
            lr=self.config.lr,
        )

        # Rollout buffer
        self.buffer = RolloutBuffer(
            buffer_size=self.config.num_steps_per_update,
            obs_dim=agent.obs_bytes,
            action_dim=agent.action_bytes,
            device=device,
        )

    def collect_rollout(
        self,
        env,
        num_steps: int,
    ) -> Dict[str, float]:
        """
        Collect rollout data from environment.

        Returns:
            Statistics dictionary
        """
        obs, info = env.reset()
        obs = torch.tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)

        hidden = None
        episode_rewards = []
        episode_lengths = []
        current_episode_reward = 0
        current_episode_length = 0

        for step in range(num_steps):
            with torch.no_grad():
                action, log_prob, value, hidden = self.agent(obs, hidden)

            # Track energy for forward pass
            self.energy_tracker.record_linear(self.agent.obs_bytes, self.config.hidden_dim, 1)
            self.energy_tracker.record_gru_step(self.config.hidden_dim, self.config.hidden_dim, 1)

            # Step environment
            action_np = action.squeeze(0).cpu().numpy()
            next_obs, reward, terminated, truncated, info = env.step(action_np)
            done = terminated or truncated

            # Store transition
            self.buffer.add(obs.squeeze(0), action.squeeze(0), reward, value.item(), log_prob.squeeze(0), done)

            current_episode_reward += reward
            current_episode_length += 1

            if done:
                episode_rewards.append(current_episode_reward)
                episode_lengths.append(current_episode_length)
                current_episode_reward = 0
                current_episode_length = 0

                obs, info = env.reset()
                obs = torch.tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
                hidden = None
            else:
                obs = torch.tensor(next_obs, dtype=torch.float32, device=self.device).unsqueeze(0)

            # Check energy budget
            if not self.energy_tracker.commit_step():
                raise EnergyBudgetExceeded("Episode energy budget exceeded!")

        # Compute last value for GAE
        with torch.no_grad():
            last_value, _ = self.agent.get_value(obs, hidden)

        self.buffer.compute_returns_and_advantages(
            last_value.item(),
            gamma=self.config.gamma,
            gae_lambda=self.config.gae_lambda,
        )

        return {
            "mean_reward": np.mean(episode_rewards) if episode_rewards else 0.0,
            "mean_length": np.mean(episode_lengths) if episode_lengths else 0.0,
            "num_episodes": len(episode_rewards),
        }

    def update(self) -> Dict[str, float]:
        """
        Perform PPO update on collected data.

        Returns:
            Training statistics
        """
        policy_losses = []
        value_losses = []
        entropy_losses = []

        for epoch in range(self.config.num_epochs):
            for (
                obs_batch,
                action_batch,
                old_log_probs,
                returns_batch,
                advantages_batch,
            ) in self.buffer.get_batches(self.config.minibatch_size):

                # Normalize advantages
                advantages_batch = (advantages_batch - advantages_batch.mean()) / (advantages_batch.std() + 1e-8)

                # Evaluate actions
                log_probs, values, entropy = self.agent.evaluate_actions(obs_batch, action_batch)

                # Sum log probs across action bytes
                log_probs_sum = log_probs.sum(dim=-1)
                old_log_probs_sum = old_log_probs.sum(dim=-1)

                # PPO loss
                ratio = torch.exp(log_probs_sum - old_log_probs_sum)
                surr1 = ratio * advantages_batch
                surr2 = torch.clamp(ratio, 1 - self.config.clip_epsilon, 1 + self.config.clip_epsilon) * advantages_batch
                policy_loss = -torch.min(surr1, surr2).mean()

                # Value loss
                value_loss = F.mse_loss(values, returns_batch)

                # Entropy loss
                entropy_loss = -entropy.mean()

                # Total loss
                loss = (
                    policy_loss
                    + self.config.value_coef * value_loss
                    + self.config.entropy_coef * entropy_loss
                )

                # Optimize
                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.agent.parameters(), self.config.max_grad_norm)
                self.optimizer.step()

                policy_losses.append(policy_loss.item())
                value_losses.append(value_loss.item())
                entropy_losses.append(-entropy_loss.item())

        self.buffer.reset()

        return {
            "policy_loss": np.mean(policy_losses),
            "value_loss": np.mean(value_losses),
            "entropy": np.mean(entropy_losses),
        }

    def train(
        self,
        env,
        total_timesteps: int,
        log_interval: int = 10,
    ) -> List[Dict[str, float]]:
        """
        Train the agent.

        Returns:
            List of training statistics per update
        """
        num_updates = total_timesteps // self.config.num_steps_per_update
        all_stats = []

        for update in range(num_updates):
            # Collect rollout
            rollout_stats = self.collect_rollout(env, self.config.num_steps_per_update)

            # Update policy
            update_stats = self.update()

            # Combine stats
            stats = {**rollout_stats, **update_stats}
            stats["update"] = update
            stats["timesteps"] = (update + 1) * self.config.num_steps_per_update
            stats["energy_J"] = self.energy_tracker.total_energy

            all_stats.append(stats)

            if (update + 1) % log_interval == 0:
                print(f"Update {update + 1}/{num_updates}")
                print(f"  Mean Reward: {stats['mean_reward']:.3f}")
                print(f"  Policy Loss: {stats['policy_loss']:.4f}")
                print(f"  Energy Used: {stats['energy_J']:.4f} J")

        return all_stats
