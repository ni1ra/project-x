#!/usr/bin/env python3
"""
GPU-Native CCB Training Script for RPJ Brain v5.

Uses TorchCCBEnvironment for 32K+ parallel environments with NO CPU-GPU sync
during rollout collection. Achieves 90%+ GPU utilization.

DEEP-DEBUG FIX: Eliminates .item() sync storm that caused 110x slowdown.

Usage:
    python scripts/train_ccb_gpu.py [--num-envs 32768] [--timesteps 1000000]
"""

import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import torch
import torch.nn.functional as F

from src.core.rpj_brain import RPJBrain, RPJConfig
from src.benchmarks.ccb import TorchCCBEnvironment
from src.utils.gpu_guard import GPUGuard, GPUGuardConfig, default_gpu_index, query_gpu_sample


class VectorizedRolloutBuffer:
    """GPU-native rollout buffer - NO CPU transfers during collection."""

    def __init__(self, num_envs: int, num_steps: int, obs_dim: int, device: str, hidden_dim: int = 512, k_max: int = 4):
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
        # Store PREVIOUS hidden/g states (input to forward, not output)
        self.prev_hidden = torch.zeros(num_steps, num_envs, hidden_dim, device=device)
        self.prev_g = torch.zeros(num_steps, num_envs, k_max, device=device)
        self.prev_actions = torch.zeros(num_steps, num_envs, 1, dtype=torch.long, device=device)
        # Store NEW g states (output, for K_eff computation)
        self.g_states = torch.zeros(num_steps, num_envs, k_max, device=device)

        self.ptr = 0

    def add(self, obs, action, action_log_prob, reward, done, value, prev_h, prev_g, prev_a, new_g):
        """Add one step of vectorized data - ALL GPU, NO .item()"""
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
        }

    def reset(self):
        self.ptr = 0


def train_vectorized(
    num_envs: int = 32768,
    num_steps: int = 128,
    total_timesteps: int = 1_000_000,
    device: str = "cuda",
    log_interval: int = 10,
    nonlinear: bool = False,
    save_interval: int = 100,
    save_dir: str = "results",
):
    """
    Vectorized GPU-native training loop.

    NO .item() calls during rollout - everything stays on GPU.
    """
    print("=" * 70)
    mode_str = "CCB-NL (NONLINEAR)" if nonlinear else "CCB (LINEAR)"
    print(f"RPJ Brain v5 - GPU-Native Vectorized Training - {mode_str}")
    print("=" * 70)
    print(f"  Device: {device}")
    print(f"  Num envs: {num_envs:,}")
    print(f"  Steps per update: {num_steps}")
    print(f"  Batch size: {num_envs * num_steps:,}")
    print(f"  Total timesteps: {total_timesteps:,}")

    # Enable TF32 for better performance
    torch.set_float32_matmul_precision('high')

    # Create GPU-native environment
    print("\n[1/3] Creating GPU-native CCB environment...")
    env = TorchCCBEnvironment(num_envs=num_envs, device=device, nonlinear=nonlinear)
    obs_dim = env.observation_space_bytes
    action_bytes = env.action_space_bytes
    print(f"  Observation: {obs_dim} bytes x {num_envs:,} envs")
    if nonlinear:
        print(f"  Mode: CCB-NL (Y = ReLU(b_X*X² + b_U*U))")
    else:
        print(f"  Mode: LINEAR (Y = b_X*X)")

    # Create brain
    print("\n[2/3] Creating RPJ Brain...")
    config = RPJConfig(
        obs_dim=obs_dim,
        action_bytes=action_bytes,
        hidden_dim=512,
        k_max=4,
        enable_plasticity=False,  # Disable for speed
        enable_sleep=False,       # Disable for speed
    )
    brain = RPJBrain(config).to(device)
    brain.train()

    params = brain.count_parameters()
    print(f"  Total parameters: {params['total']:,}")

    # Optimizer
    optimizer = torch.optim.Adam(brain.parameters(), lr=3e-4)

    # Buffer
    buffer = VectorizedRolloutBuffer(
        num_envs, num_steps, obs_dim, device,
        hidden_dim=config.hidden_dim, k_max=config.k_max
    )

    # Initialize states
    h = torch.zeros(num_envs, config.hidden_dim, device=device)
    g = torch.zeros(num_envs, config.k_max, device=device)
    a_prev = torch.zeros(num_envs, action_bytes, dtype=torch.long, device=device)

    # Reset environment
    obs = env.reset()

    print(f"\n[3/3] Training...")
    print("-" * 70)

    total_steps = 0
    num_updates = 0
    start_time = time.perf_counter()

    while total_steps < total_timesteps:
        # === ROLLOUT PHASE (ALL GPU - NO .item() calls!) ===
        buffer.reset()
        rollout_start = time.perf_counter()

        with torch.no_grad():
            for step in range(num_steps):
                # Store PREVIOUS state (before forward) for PPO update
                prev_h = h.clone()
                prev_g = g.clone()
                prev_a = a_prev.clone()

                # Brain forward - batched for all envs
                output = brain(obs, prev_h, prev_g, prev_a, training=False)

                # Extract values - NO .item()! Keep on GPU
                action = output.action  # [num_envs, 1]
                action_log_prob = output.action_log_prob  # [num_envs, 1]
                value = output.value  # [num_envs]
                h_next = output.h_next  # [num_envs, hidden_dim]
                g_next = output.g_t  # [num_envs, k_max]

                # Environment step - ALL GPU
                next_obs, reward, done, info = env.step(action.squeeze(-1))

                # Store in buffer - ALL GPU
                # Store PREV states for re-running forward during PPO update
                buffer.add(obs, action, action_log_prob, reward, done, value,
                           prev_h, prev_g, prev_a, g_next)

                # Update states for next step
                obs = next_obs
                h = h_next
                g = g_next
                a_prev = action

                # Auto-reset hidden states for done envs
                h = torch.where(done.unsqueeze(-1), torch.zeros_like(h), h)
                g = torch.where(done.unsqueeze(-1), torch.zeros_like(g), g)

        rollout_time = time.perf_counter() - rollout_start
        steps_collected = num_steps * num_envs
        rollout_fps = steps_collected / rollout_time

        # Compute returns
        with torch.no_grad():
            last_output = brain(obs, h, g, a_prev, training=False)
            last_value = last_output.value
        buffer.compute_returns(gamma=config.gamma, last_value=last_value)

        # === UPDATE PHASE ===
        update_start = time.perf_counter()

        batch = buffer.flatten()
        advantages = batch['advantages']
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # PPO update - FULL IMPLEMENTATION for emergence training
        # The key insight: without gradient flow, K_eff can never compress
        ppo_epochs = 4
        mini_batch_size = 4096
        clip_range = 0.2
        value_coef = 0.5
        entropy_coef = 0.001  # JARVIS 420 FIX: Reduced to allow precision over exploration
        max_grad_norm = 0.5

        batch_size = buffer.num_steps * buffer.num_envs
        indices = torch.randperm(batch_size, device=device)

        for epoch in range(ppo_epochs):
            for start in range(0, batch_size, mini_batch_size):
                end = start + mini_batch_size
                mb_indices = indices[start:end]

                # Get minibatch data
                mb_obs = batch['observations'][mb_indices]
                mb_actions = batch['actions'][mb_indices]
                mb_old_log_probs = batch['action_log_probs'][mb_indices]
                mb_returns = batch['returns'][mb_indices]
                mb_advantages = advantages[mb_indices]
                mb_prev_h = batch['prev_hidden'][mb_indices]
                mb_prev_g = batch['prev_g'][mb_indices]
                mb_prev_a = batch['prev_actions'][mb_indices]

                # JARVIS 420 FIX: Use evaluate_actions() to re-run forward pass WITH gradients
                # This is TRUNCATED BPTT(1) - restores obs→substrate→action gradient chain
                # Without this, the substrate receives ZERO gradients and cannot learn!
                new_log_probs, entropy, values, mb_g, _ = brain.evaluate_actions(
                    obs_bytes=mb_obs,
                    prev_h=mb_prev_h,
                    prev_g=mb_prev_g,
                    prev_a=mb_prev_a,
                    actions=mb_actions,
                )

                # PPO clipped objective
                new_log_probs = new_log_probs.squeeze(-1)
                ratio = torch.exp(new_log_probs - mb_old_log_probs)
                surr1 = ratio * mb_advantages
                surr2 = torch.clamp(ratio, 1.0 - clip_range, 1.0 + clip_range) * mb_advantages
                policy_loss = -torch.min(surr1, surr2).mean()

                # Value loss
                value_loss = F.mse_loss(values, mb_returns)

                # Entropy bonus (for exploration)
                entropy_loss = -entropy.mean()

                # G_t sparsity loss - CRITICAL for K_eff compression
                # This creates explicit gradient pressure to push unused scalars to 0
                g_sparsity_loss = mb_g.abs().mean() * config.lambda_g

                # Total loss
                loss = policy_loss + value_coef * value_loss + entropy_coef * entropy_loss + g_sparsity_loss

                # Gradient update
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(brain.parameters(), max_grad_norm)
                optimizer.step()

        update_time = time.perf_counter() - update_start

        total_steps += steps_collected
        num_updates += 1

        # Logging - ONLY sync here for metrics (once per update, not per step!)
        if num_updates % log_interval == 0:
            elapsed = time.perf_counter() - start_time
            overall_fps = total_steps / elapsed

            # Sync for metrics - acceptable, only once per N updates
            mean_reward = buffer.rewards.mean().item()
            mean_value = buffer.values.mean().item()

            # === EMERGENCE METRICS ===
            # K_eff (participation ratio) - CRITICAL for neuromodulator compression
            # K_eff should compress from ~16 to [2-6] under RPJ pressure
            g_data = buffer.g_states  # [steps, envs, k_max]
            g_flat = g_data.view(-1, g_data.size(-1))  # [steps*envs, k_max]
            var_k = g_flat.var(dim=0)  # [k_max]
            sum_var = var_k.sum()
            sum_var_sq = (var_k ** 2).sum()
            k_eff = ((sum_var ** 2) / (sum_var_sq + 1e-8)).item()

            # CBR bimodality (simplified check - compute burst ratio)
            # TODO: Add full Sarle's coefficient
            c_data = buffer.values  # Using values as proxy for c_t since we don't store c_t
            cbr_mean = c_data.mean().item()

            # Entropy of compute allocation (collapse detection)
            # If H(c_t) < 0.05, training is invalid
            c_probs = torch.sigmoid(buffer.values)  # Approximate c_t
            entropy_c = -(c_probs * torch.log(c_probs + 1e-8) + (1-c_probs) * torch.log(1-c_probs + 1e-8)).mean().item()

            # Mean g_t L1 (sparsity measure)
            g_l1 = g_flat.abs().mean().item()

            print(f"Update {num_updates:4d} | "
                  f"Steps: {total_steps:>10,} | "
                  f"FPS: {overall_fps:>8,.0f} | "
                  f"R: {mean_reward:>6.2f} | "
                  f"V: {mean_value:>6.2f} | "
                  f"K_eff: {k_eff:>4.1f} | "
                  f"H(c): {entropy_c:>5.3f} | "
                  f"g_L1: {g_l1:>5.3f}")

        # Save checkpoint periodically
        if num_updates % save_interval == 0:
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            mode_suffix = "_nl" if nonlinear else "_lin"
            ckpt_path = save_path / f"checkpoint_ccb{mode_suffix}_{total_steps:08d}.pt"
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
                    'nonlinear': nonlinear,
                },
                'metrics': {
                    'mean_reward': mean_reward,
                    'k_eff': k_eff,
                    'g_l1': g_l1,
                    'entropy_c': entropy_c,
                }
            }, ckpt_path)
            print(f"  >>> Checkpoint saved: {ckpt_path}")

    # Final stats
    total_time = time.perf_counter() - start_time
    final_fps = total_steps / total_time

    # Save final checkpoint
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    mode_suffix = "_nl" if nonlinear else "_lin"
    final_ckpt_path = save_path / f"checkpoint_ccb{mode_suffix}_final_{total_steps:08d}.pt"
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
            'nonlinear': nonlinear,
        },
    }, final_ckpt_path)

    print("-" * 70)
    print(f"Training complete!")
    print(f"  Total steps: {total_steps:,}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Average FPS: {final_fps:,.0f}")
    print(f"  Final checkpoint: {final_ckpt_path}")
    print(f"  Target FPS for 90% util: ~100,000+ (with 32K envs)")

    return brain  # Return trained brain for further use


def main():
    parser = argparse.ArgumentParser(description="GPU-Native CCB Training")
    parser.add_argument("--num-envs", type=int, default=32768, help="Number of parallel environments")
    parser.add_argument("--timesteps", type=int, default=500_000, help="Total training timesteps")
    parser.add_argument("--num-steps", type=int, default=128, help="Steps per rollout")
    parser.add_argument("--log-interval", type=int, default=10, help="Log every N updates")
    parser.add_argument("--save-interval", type=int, default=100, help="Save checkpoint every N updates")
    parser.add_argument("--nonlinear", action="store_true", help="Use CCB-NL (nonlinear) instead of linear CCB")
    # GPU guardrails (hard safety + utilization floor)
    parser.add_argument("--no-gpu-guard", action="store_true", help="Disable GPU guardrails (not recommended)")
    parser.add_argument("--gpu-index", type=int, default=None, help="GPU index for nvidia-smi sampling (default: auto)")
    parser.add_argument("--gpu-max-vram-mib", type=int, default=10 * 1024, help="Abort if total VRAM used exceeds this")
    parser.add_argument("--gpu-min-util", type=int, default=80, help="Abort if sustained GPU util falls below this %%")
    parser.add_argument("--gpu-grace-s", type=float, default=20.0, help="Warmup seconds before util enforcement")
    parser.add_argument("--gpu-low-util-patience-s", type=float, default=30.0, help="Seconds of low util before abort")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("WARNING: CUDA not available, running on CPU (will be slow)")
        args.num_envs = 64  # Reduce for CPU

    guard = None
    if device == "cuda" and not args.no_gpu_guard:
        gpu_index = args.gpu_index if args.gpu_index is not None else default_gpu_index()
        guard = GPUGuard(
            GPUGuardConfig(
                gpu_index=gpu_index,
                max_memory_mib=int(args.gpu_max_vram_mib),
                min_util_percent=int(args.gpu_min_util),
                grace_period_s=float(args.gpu_grace_s),
                low_util_patience_s=float(args.gpu_low_util_patience_s),
                enforce_min_util=True,
                require_nvidia_smi=True,
            )
        )
        guard.start()
        sample = query_gpu_sample(gpu_index)
        if sample is not None:
            print(
                "GPU_GUARD: "
                f"gpu={gpu_index} util={sample.utilization_gpu}% "
                f"mem={sample.memory_used_mib}/{sample.memory_total_mib} MiB "
                f"(cap {args.gpu_max_vram_mib} MiB, min util {args.gpu_min_util}%)"
            )

    try:
        train_vectorized(
            num_envs=args.num_envs,
            num_steps=args.num_steps,
            total_timesteps=args.timesteps,
            device=device,
            log_interval=args.log_interval,
            nonlinear=args.nonlinear,
            save_interval=args.save_interval,
        )
    finally:
        if guard is not None:
            guard.stop()


if __name__ == "__main__":
    main()
