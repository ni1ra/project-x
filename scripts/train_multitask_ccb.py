#!/usr/bin/env python3
"""
Multi-Task CCB Training Script for Persistent Emergence.

Trains on DIVERSE tasks with varying (b_X, b_U) coefficients to test whether
K_eff stays elevated under task diversity (Persistent Emergence hypothesis).

Key difference from train_ccb_gpu.py:
- Uses TorchMultiTaskCCBEnvironment with 100 different task types
- Tasks switch periodically to maintain diversity
- Expected result: K_eff stays in [2-6] instead of habituating to ~1

Usage:
    python scripts/train_multitask_ccb.py [--num-envs 8192] [--timesteps 50000000]

Reference: BLUEPRINT.md Section 4.3
"""

import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import torch
import torch.nn.functional as F

from src.core.rpj_brain import RPJBrain, RPJConfig
from src.core.byte_interface import phi
from src.benchmarks.multitask_ccb import TorchMultiTaskCCBEnvironment


def compute_k_eff(g_t: torch.Tensor) -> float:
    """Compute effective neuromodulator count via participation ratio."""
    g_flat = g_t.view(-1, g_t.size(-1)) if g_t.dim() > 1 else g_t.unsqueeze(0)
    var_k = g_flat.var(dim=0)
    sum_var = var_k.sum()
    sum_var_sq = (var_k ** 2).sum()
    k_eff = ((sum_var ** 2) / (sum_var_sq + 1e-8)).item()
    return k_eff


class VectorizedRolloutBuffer:
    """GPU-native rollout buffer - NO CPU transfers during collection."""

    def __init__(self, num_envs: int, num_steps: int, obs_dim: int, device: str, hidden_dim: int = 512, k_max: int = 16):
        self.num_envs = num_envs
        self.num_steps = num_steps
        self.device = device
        self.hidden_dim = hidden_dim
        self.k_max = k_max

        # Pre-allocate GPU tensors
        self.observations = torch.zeros(num_steps, num_envs, obs_dim, dtype=torch.long, device=device)
        self.actions = torch.zeros(num_steps, num_envs, 1, dtype=torch.long, device=device)
        self.action_log_probs = torch.zeros(num_steps, num_envs, device=device)
        self.rewards = torch.zeros(num_steps, num_envs, device=device)
        self.dones = torch.zeros(num_steps, num_envs, dtype=torch.bool, device=device)
        self.values = torch.zeros(num_steps, num_envs, device=device)
        # Store PREVIOUS hidden/g states
        self.prev_hidden = torch.zeros(num_steps, num_envs, hidden_dim, device=device)
        self.prev_g = torch.zeros(num_steps, num_envs, k_max, device=device)
        self.prev_actions = torch.zeros(num_steps, num_envs, 1, dtype=torch.long, device=device)
        # Store NEW g states
        self.g_states = torch.zeros(num_steps, num_envs, k_max, device=device)
        # HYBRID TRAINING: Store true_Y for supervised auxiliary loss
        self.true_Y = torch.zeros(num_steps, num_envs, device=device)

        self.ptr = 0

    def add(self, obs, action, action_log_prob, reward, done, value, prev_h, prev_g, prev_a, new_g, true_Y=None):
        """Add one step of vectorized data - ALL GPU"""
        self.observations[self.ptr] = obs
        self.actions[self.ptr] = action
        self.action_log_probs[self.ptr] = action_log_prob.squeeze(-1)
        self.rewards[self.ptr] = reward
        self.dones[self.ptr] = done
        self.values[self.ptr] = value
        self.prev_hidden[self.ptr] = prev_h
        self.prev_g[self.ptr] = prev_g
        self.prev_actions[self.ptr] = prev_a
        self.g_states[self.ptr] = new_g
        # HYBRID TRAINING: Store true_Y
        if true_Y is not None:
            self.true_Y[self.ptr] = true_Y
        self.ptr += 1

    def compute_returns(self, gamma: float = 0.999, last_value: torch.Tensor = None):
        """Compute GAE returns - ALL GPU operations."""
        if last_value is None:
            last_value = torch.zeros(self.num_envs, device=self.device)

        returns = torch.zeros(self.num_steps + 1, self.num_envs, device=self.device)
        returns[-1] = last_value

        for t in reversed(range(self.num_steps)):
            mask = (~self.dones[t]).float()
            returns[t] = self.rewards[t] + gamma * returns[t + 1] * mask

        self.returns = returns[:-1]
        self.advantages = self.returns - self.values

    def flatten(self):
        """Flatten for batch processing."""
        batch_size = self.num_steps * self.num_envs
        return {
            'observations': self.observations.view(batch_size, -1),
            'actions': self.actions.view(batch_size, -1),
            'action_log_probs': self.action_log_probs.view(batch_size),
            'returns': self.returns.view(batch_size),
            'advantages': self.advantages.view(batch_size),
            'prev_hidden': self.prev_hidden.view(batch_size, -1),
            'prev_g': self.prev_g.view(batch_size, -1),
            'prev_actions': self.prev_actions.view(batch_size, -1),
            'g_states': self.g_states.view(batch_size, -1),
            # HYBRID TRAINING: Include true_Y for supervised loss
            'true_Y': self.true_Y.view(batch_size),
        }

    def reset(self):
        self.ptr = 0


def train_multitask(
    num_envs: int = 8192,
    num_steps: int = 128,
    total_timesteps: int = 50_000_000,
    num_tasks: int = 100,
    switch_interval: int = 500,
    device: str = "cuda",
    log_interval: int = 1,
    save_interval: int = 100,
    save_dir: str = "results",
):
    """
    Multi-Task CCB training for Persistent Emergence.
    """
    print("=" * 70)
    print("RPJ Brain v5 - HYBRID TRAINING (RL + Supervised Aux Loss)")
    print("=" * 70)
    print("  JARVIS 420 FIX: RL for K_eff emergence + Supervised for DoErr")
    print(f"  Device: {device}")
    print(f"  Num envs: {num_envs:,}")
    print(f"  Num tasks: {num_tasks}")
    print(f"  Task switch interval: {switch_interval} steps")
    print(f"  Steps per update: {num_steps}")
    print(f"  Batch size: {num_envs * num_steps:,}")
    print(f"  Total timesteps: {total_timesteps:,}")

    torch.set_float32_matmul_precision('high')

    # Create Multi-Task environment
    print("\n[1/3] Creating Multi-Task CCB environment...")
    env = TorchMultiTaskCCBEnvironment(
        num_envs=num_envs,
        num_tasks=num_tasks,
        switch_interval=switch_interval,
        device=device,
    )
    obs_dim = env.observation_space_bytes
    action_bytes = env.action_space_bytes
    print(f"  Observation: {obs_dim} bytes x {num_envs:,} envs")
    print(f"  Tasks: {num_tasks} different (b_X, b_U) configurations")

    # Create brain
    print("\n[2/3] Creating RPJ Brain...")
    config = RPJConfig(
        obs_dim=obs_dim,
        action_bytes=action_bytes,
        hidden_dim=512,
        k_max=16,  # JARVIS 420 FIX: Match BLUEPRINT.md Section 2.2
        lambda_g=0.05,  # JARVIS RAPID: 5x sparsity for CPU validation
        enable_plasticity=True,   # Enable for OD-NDT transfer
        enable_sleep=False,
        num_envs=num_envs,  # JARVIS 360→420: Per-env plasticity for proper sleep retention
    )
    brain = RPJBrain(config).to(device)
    brain.train()

    params = brain.count_parameters()
    print(f"  Total parameters: {params['total']:,}")

    optimizer = torch.optim.Adam(brain.parameters(), lr=3e-4)

    buffer = VectorizedRolloutBuffer(
        num_envs, num_steps, obs_dim, device,
        hidden_dim=config.hidden_dim, k_max=config.k_max
    )

    # Initialize states
    h = torch.zeros(num_envs, config.hidden_dim, device=device)
    g = torch.zeros(num_envs, config.k_max, device=device)
    a_prev = torch.zeros(num_envs, action_bytes, dtype=torch.long, device=device)

    obs = env.reset()

    print(f"\n[3/3] Training...")
    print("-" * 70)
    print("Hypothesis: K_eff should stay ELEVATED under task diversity")
    print("-" * 70)

    total_steps = 0
    num_updates = 0
    start_time = time.perf_counter()
    k_eff_history = []

    while total_steps < total_timesteps:
        buffer.reset()

        with torch.no_grad():
            for step in range(num_steps):
                prev_h = h.clone()
                prev_g = g.clone()
                prev_a = a_prev.clone()

                output = brain(obs, prev_h, prev_g, prev_a, training=False)

                action = output.action
                action_log_prob = output.action_log_prob
                value = output.value
                h_next = output.h_next
                g_next = output.g_t

                next_obs, reward, done, info = env.step(action.squeeze(-1))

                # HYBRID TRAINING: Capture true_Y from environment info
                true_Y = info['true_Y']

                # PLASTICITY FIX: Update fast weights via local Hebbian rule
                # This enables synaptic consolidation for sleep retention
                if brain.plasticity is not None:
                    phi_o_next = phi(next_obs)
                    # Need value_next for TD error computation
                    with torch.no_grad():
                        next_output = brain(next_obs, h_next, g_next, action, training=False)
                        value_next = next_output.value
                    # update_plasticity works on buffers via .data assignment
                    brain.update_plasticity(
                        h_t=prev_h,
                        phi_o_next=phi_o_next,
                        reward=reward,
                        value=value,
                        value_next=value_next,
                        g_t=g_next,
                    )

                buffer.add(obs, action, action_log_prob, reward, done, value,
                           prev_h, prev_g, prev_a, g_next, true_Y=true_Y)

                obs = next_obs
                h = h_next
                g = g_next
                a_prev = action

                h = torch.where(done.unsqueeze(-1), torch.zeros_like(h), h)
                g = torch.where(done.unsqueeze(-1), torch.zeros_like(g), g)

                # JARVIS 360→420 FIX: Per-env fast weight reset at episode boundaries
                # Now that we have batched plasticity, we can reset only finished episodes
                if done.any() and brain.plasticity is not None:
                    brain.plasticity.reset_envs(done)

        # Compute returns
        with torch.no_grad():
            last_output = brain(obs, h, g, a_prev, training=False)
            last_value = last_output.value
        buffer.compute_returns(gamma=config.gamma, last_value=last_value)

        # PPO update
        batch = buffer.flatten()
        advantages = batch['advantages']
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        ppo_epochs = 4
        mini_batch_size = 4096
        clip_range = 0.2
        value_coef = 0.5
        entropy_coef = 0.001
        max_grad_norm = 0.5
        # HYBRID TRAINING: Information Bottleneck + High Supervised (JARVIS 420)
        # Architecture fix: Dropout(0.5) on h_t in GaussianActionHead
        # This forces network to use g_t (neuromodulators) for stable prediction
        # JARVIS 415 FIX: Reduced from 10.0 to 0.5
        # At 10.0, supervised signal drowns RL → kills CBR bimodality
        # Agent becomes reflex machine (System 1) with no compute bursts
        max_supervised_coef = 0.5  # JARVIS: Balance RL exploration + supervised precision
        supervised_warmup_start = 0.0  # Start supervised immediately

        # Entropy annealing: reduce exploration as training progresses
        min_entropy_coef = 0.0001  # Final entropy coefficient (10x lower)
        entropy_decay_start = 0.30  # Start decaying at 30%
        progress = total_steps / total_timesteps
        if progress < entropy_decay_start:
            entropy_coef = 0.001
        else:
            decay_progress = (progress - entropy_decay_start) / (1.0 - entropy_decay_start)
            entropy_coef = 0.001 - (0.001 - min_entropy_coef) * decay_progress

        # JARVIS 415: Constant supervised coefficient (balanced with RL)
        supervised_coef = max_supervised_coef

        batch_size = buffer.num_steps * buffer.num_envs
        indices = torch.randperm(batch_size, device=device)

        for epoch in range(ppo_epochs):
            for start in range(0, batch_size, mini_batch_size):
                end = start + mini_batch_size
                mb_indices = indices[start:end]

                mb_obs = batch['observations'][mb_indices]
                mb_actions = batch['actions'][mb_indices]
                mb_old_log_probs = batch['action_log_probs'][mb_indices]
                mb_returns = batch['returns'][mb_indices]
                mb_advantages = advantages[mb_indices]
                mb_prev_h = batch['prev_hidden'][mb_indices]
                mb_prev_g = batch['prev_g'][mb_indices]
                mb_prev_a = batch['prev_actions'][mb_indices]
                # HYBRID TRAINING: Get true_Y for supervised loss
                mb_true_Y = batch['true_Y'][mb_indices]

                new_log_probs, entropy, values, mb_g, _, action_mu = brain.evaluate_actions(
                    obs_bytes=mb_obs,
                    prev_h=mb_prev_h,
                    prev_g=mb_prev_g,
                    prev_a=mb_prev_a,
                    actions=mb_actions,
                )

                new_log_probs = new_log_probs.squeeze(-1)
                ratio = torch.exp(new_log_probs - mb_old_log_probs)
                surr1 = ratio * mb_advantages
                surr2 = torch.clamp(ratio, 1.0 - clip_range, 1.0 + clip_range) * mb_advantages
                policy_loss = -torch.min(surr1, surr2).mean()

                value_loss = F.mse_loss(values, mb_returns)
                entropy_loss = -entropy.mean()
                g_sparsity_loss = mb_g.abs().mean() * config.lambda_g

                # HYBRID TRAINING: Supervised auxiliary loss for DoErr
                # JARVIS 420 FIX: Squeeze predicted_Y to match mb_true_Y shape
                # CRITICAL: Without squeeze, PyTorch broadcasts (N,1) vs (N,) to (N,N)
                # This forces network to learn global mean instead of task-specific target
                supervised_loss = torch.tensor(0.0, device=device)
                if action_mu is not None:
                    predicted_Y = (action_mu / 255.0 * 4.0).squeeze(-1)  # JARVIS: Match shape (N,)
                    supervised_loss = F.mse_loss(predicted_Y, mb_true_Y)

                loss = policy_loss + value_coef * value_loss + entropy_coef * entropy_loss + g_sparsity_loss + supervised_coef * supervised_loss

                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(brain.parameters(), max_grad_norm)
                optimizer.step()

        total_steps += num_steps * num_envs
        num_updates += 1

        # Logging
        if num_updates % log_interval == 0:
            elapsed = time.perf_counter() - start_time
            overall_fps = total_steps / elapsed

            mean_reward = buffer.rewards.mean().item()
            mean_value = buffer.values.mean().item()

            # K_eff computation
            g_data = buffer.g_states
            g_flat = g_data.view(-1, g_data.size(-1))
            var_k = g_flat.var(dim=0)
            sum_var = var_k.sum()
            sum_var_sq = (var_k ** 2).sum()
            k_eff = ((sum_var ** 2) / (sum_var_sq + 1e-8)).item()

            k_eff_history.append(k_eff)
            g_l1 = g_flat.abs().mean().item()

            # Task diversity check
            unique_tasks = env.current_task_ids.unique().numel()

            # HYBRID TRAINING: Compute DoErr from buffer
            # action predictions vs true_Y
            with torch.no_grad():
                # Use the last buffer's actions and true_Y
                action_bytes = buffer.actions.view(-1).float()
                true_Y_flat = buffer.true_Y.view(-1)
                # FIX: Use same action range as environment [0, 4.0]
                predicted_Y_flat = action_bytes / 255.0 * 4.0
                doerr = (predicted_Y_flat - true_Y_flat).abs().mean().item()

            # PLASTICITY: Log fast weight norms (mean across all envs for batched mode)
            fast_weight_norm = 0.0
            if brain.plasticity is not None:
                A = brain.plasticity.recurrent_adapter.A
                if A.dim() == 3:  # Batched: [num_envs, out_dim, rank]
                    # Mean norm across envs
                    per_env_norms = A.norm(dim=(1, 2))
                    fast_weight_norm = per_env_norms.mean().item()
                else:
                    fast_weight_norm = A.norm().item()

            print(f"Update {num_updates:4d} | "
                  f"Steps: {total_steps:>10,} | "
                  f"FPS: {overall_fps:>8,.0f} | "
                  f"R: {mean_reward:>6.2f} | "
                  f"K_eff: {k_eff:>4.1f} | "
                  f"DoErr: {doerr:>5.3f} | "
                  f"FW: {fast_weight_norm:.4f} | "
                  f"Tasks: {unique_tasks}")

        # Save checkpoint
        if num_updates % save_interval == 0:
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            ckpt_path = save_path / f"checkpoint_multitask_ccb_{total_steps:08d}.pt"
            torch.save({
                'brain_state_dict': brain.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'timesteps': total_steps,
                'num_updates': num_updates,
                'config': {
                    'obs_dim': config.obs_dim,
                    'action_bytes': config.action_bytes,
                    'hidden_dim': config.hidden_dim,
                    'k_max': config.k_max,
                    'num_tasks': num_tasks,
                    'multitask': True,
                },
                'metrics': {
                    'mean_reward': mean_reward,
                    'k_eff': k_eff,
                    'g_l1': g_l1,
                    'k_eff_history': k_eff_history[-100:],
                }
            }, ckpt_path)
            print(f"  >>> Checkpoint saved: {ckpt_path}")

    # Final summary
    total_time = time.perf_counter() - start_time
    final_fps = total_steps / total_time

    # K_eff analysis
    k_eff_array = torch.tensor(k_eff_history)
    k_eff_mean = k_eff_array.mean().item()
    k_eff_std = k_eff_array.std().item()
    k_eff_min = k_eff_array.min().item()
    k_eff_max = k_eff_array.max().item()

    # Save final checkpoint
    save_path = Path(save_dir)
    final_ckpt_path = save_path / f"checkpoint_multitask_ccb_final_{total_steps:08d}.pt"
    torch.save({
        'brain_state_dict': brain.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'timesteps': total_steps,
        'num_updates': num_updates,
        'config': {
            'obs_dim': config.obs_dim,
            'action_bytes': config.action_bytes,
            'hidden_dim': config.hidden_dim,
            'k_max': config.k_max,
            'num_tasks': num_tasks,
            'multitask': True,
        },
        'k_eff_history': k_eff_history,
    }, final_ckpt_path)

    print("-" * 70)
    print("MULTI-TASK CCB Training Complete!")
    print("-" * 70)
    print(f"  Total steps: {total_steps:,}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Average FPS: {final_fps:,.0f}")

    print(f"\n=== PERSISTENT EMERGENCE ANALYSIS ===")
    print(f"  K_eff mean: {k_eff_mean:.2f}")
    print(f"  K_eff std:  {k_eff_std:.2f}")
    print(f"  K_eff range: [{k_eff_min:.2f}, {k_eff_max:.2f}]")

    if k_eff_mean > 1.5:
        print(f"\n  [SUCCESS] K_eff elevated ({k_eff_mean:.1f}) - PERSISTENT EMERGENCE!")
        print(f"  Task diversity maintained neuromodulator engagement.")
    else:
        print(f"\n  [WARNING] K_eff low ({k_eff_mean:.1f}) - habituation occurred")
        print(f"  May need more task diversity or longer training.")

    print(f"\n  Final checkpoint: {final_ckpt_path}")

    return brain


def main():
    parser = argparse.ArgumentParser(description="Multi-Task CCB Training")
    parser.add_argument("--num-envs", type=int, default=8192, help="Number of parallel environments")
    parser.add_argument("--timesteps", type=int, default=50_000_000, help="Total training timesteps")
    parser.add_argument("--num-steps", type=int, default=128, help="Steps per rollout")
    parser.add_argument("--num-tasks", type=int, default=100, help="Number of task types")
    parser.add_argument("--switch-interval", type=int, default=500, help="Steps between task switches")
    parser.add_argument("--log-interval", type=int, default=1, help="Log every N updates")
    parser.add_argument("--save-interval", type=int, default=100, help="Save checkpoint every N updates")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("WARNING: CUDA not available, running on CPU (will be slow)")
        args.num_envs = 64

    train_multitask(
        num_envs=args.num_envs,
        num_steps=args.num_steps,
        total_timesteps=args.timesteps,
        num_tasks=args.num_tasks,
        switch_interval=args.switch_interval,
        device=device,
        log_interval=args.log_interval,
        save_interval=args.save_interval,
    )


if __name__ == "__main__":
    main()
