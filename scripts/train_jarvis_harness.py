#!/usr/bin/env python3
"""
Jarvis Harness Training Script (v2)

Train the RPJ brain to operate tools in a repo-as-world environment.

v2 Update: Uses multi-file repo generation for harder, more realistic tasks.

This converts "cool emergence metrics" into "useful operator" by:
1. Giving the brain a real job (fix bugs, make tests pass)
2. Using hard verifiers (tests pass/fail, not model-based scoring)
3. Enforcing energy budgets (RPJ pressure preserved)
4. Rewarding minimal diffs (MDL-friendly editing)
5. Generating synthetic multi-file repos with injected bugs

Usage:
    PYTHONPATH=. ./.venv/bin/python scripts/train_jarvis_harness.py --num-envs 32 --timesteps 1000000
    PYTHONPATH=. ./.venv/bin/python scripts/train_jarvis_harness.py --mode v2 --difficulty medium
"""

from __future__ import annotations

import argparse
import math
import os
import time
import random
import tempfile
import shutil
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import Adam

from src.core.rpj_brain import RPJBrain, RPJConfig, create_brain, RPJBrainOutput
from src.core.byte_interface import phi
from src.harness.env import (
    JarvisHarnessEnv, HarnessConfig, Task, VectorizedJarvisEnv
)
from src.harness.actions import (
    ActionType, JarvisAction, encode_action, decode_action,
    ACTION_BYTES, ACTION_BYTES_V2,
)
from src.harness.observations import OBS_TOTAL_BYTES
from src.harness.repo_generator import (
    RepoGenerator, GeneratedRepo, BugDifficulty, generate_task_batch,
)
from src.utils.gpu_guard import (
    GPUGuard,
    GPUGuardConfig,
    ExclusiveGPULock,
    default_gpu_index,
    query_gpu_sample,
)


# =============================================================================
# Curriculum Learning
# =============================================================================

@dataclass
class CurriculumState:
    """Track curriculum learning state."""
    current_difficulty: BugDifficulty = BugDifficulty.TRIVIAL
    successes_at_level: int = 0
    failures_at_level: int = 0
    episodes_at_level: int = 0
    total_promotions: int = 0
    total_demotions: int = 0

    # Thresholds
    promote_threshold: float = 0.70  # Success rate to promote
    demote_threshold: float = 0.30   # Success rate to demote
    min_episodes: int = 50           # Min episodes before promotion decision

    def record_episode(self, success: bool):
        """Record episode outcome."""
        self.episodes_at_level += 1
        if success:
            self.successes_at_level += 1
        else:
            self.failures_at_level += 1

    @property
    def success_rate(self) -> float:
        """Current success rate at this difficulty level."""
        total = self.successes_at_level + self.failures_at_level
        if total == 0:
            return 0.0
        return self.successes_at_level / total

    def should_promote(self) -> bool:
        """Check if should promote to harder difficulty."""
        if self.episodes_at_level < self.min_episodes:
            return False
        if self.current_difficulty == BugDifficulty.EXPERT:
            return False  # Already at max
        return self.success_rate >= self.promote_threshold

    def should_demote(self) -> bool:
        """Check if should demote to easier difficulty."""
        if self.episodes_at_level < self.min_episodes:
            return False
        if self.current_difficulty == BugDifficulty.TRIVIAL:
            return False  # Already at min
        return self.success_rate <= self.demote_threshold

    def promote(self):
        """Promote to next difficulty level."""
        next_val = self.current_difficulty.value + 1
        if next_val <= 5:
            self.current_difficulty = BugDifficulty(next_val)
            self.successes_at_level = 0
            self.failures_at_level = 0
            self.episodes_at_level = 0
            self.total_promotions += 1
            return True
        return False

    def demote(self):
        """Demote to previous difficulty level."""
        prev_val = self.current_difficulty.value - 1
        if prev_val >= 1:
            self.current_difficulty = BugDifficulty(prev_val)
            self.successes_at_level = 0
            self.failures_at_level = 0
            self.episodes_at_level = 0
            self.total_demotions += 1
            return True
        return False


def create_tasks_legacy(repo_path: str, num_tasks: int = 1) -> List[Task]:
    """Create training tasks from the toy repo (legacy v1 mode)."""
    tasks = []
    for i in range(num_tasks):
        tasks.append(Task(
            name=f"fix_bugs_{i}",
            description="Fix the multiply function to return a * b. Run tests to verify.",
            repo_path=repo_path,
            target_file="calculator.py",
            expected_tests_passing=18,
        ))
    return tasks


def create_tasks_v2(
    num_tasks: int,
    difficulty: BugDifficulty,
    temp_base: str,
    seed: Optional[int] = None,
) -> Tuple[List[Task], List[GeneratedRepo]]:
    """
    Create training tasks using v2 multi-file repo generation.

    Returns (tasks, repos) where repos should be cleaned up after training.
    """
    generator = RepoGenerator(seed=seed)
    repos = generate_task_batch(
        num_tasks=num_tasks,
        difficulty_range=(difficulty, BugDifficulty(min(difficulty.value + 1, 5))),
        seed=seed,
    )

    tasks = []
    for repo in repos:
        # Write repo to disk
        repo_path = generator.write_to_disk(repo, temp_base)

        # Create task from repo
        bug = repo.bugs[0] if repo.bugs else None
        target_file = bug.file_path if bug else list(repo.files.keys())[0]

        task = Task(
            name=repo.name,
            description=f"Fix the bugs in this codebase. Hint: {repo.fix_description}",
            repo_path=repo_path,
            target_file=target_file,
            expected_tests_passing=5,  # Approximate
        )
        tasks.append(task)

    return tasks, repos


class JarvisHarnessTrainer:
    """
    PPO-style trainer for Jarvis Harness environment.

    Adapts the existing PPO training loop for the tool-using domain.
    """

    def __init__(
        self,
        brain: RPJBrain,
        envs: VectorizedJarvisEnv,
        device: torch.device,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        entropy_coef: float = 0.01,
        value_coef: float = 0.5,
        max_grad_norm: float = 1.0,
        rollout_steps: int = 128,
        update_epochs: int = 4,
        minibatch_size: int = 1024,
        gpu_burn_ms: float = 0.0,
        gpu_burn_dim: int = 4096,
    ):
        self.brain = brain
        self.envs = envs
        self.device = device
        self.num_envs = envs.num_envs

        # Hyperparameters
        self.lr = lr
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.entropy_coef = entropy_coef
        self.value_coef = value_coef
        self.max_grad_norm = max_grad_norm
        self.rollout_steps = rollout_steps
        self.update_epochs = update_epochs
        self.minibatch_size = minibatch_size
        self.gpu_burn_ms = float(gpu_burn_ms)
        self.gpu_burn_dim = int(gpu_burn_dim)

        # Optimizer
        self.optimizer = Adam(brain.parameters(), lr=lr)

        # Statistics
        self.total_steps = 0
        self.episode_rewards = []
        self.episode_lengths = []

        # Optional GPU padding to keep utilization high when env stepping is CPU-bound.
        self._burn_a = None
        self._burn_b = None
        self._burn_out = None
        self._burn_ms_per_matmul = None
        if self.device.type == "cuda" and self.gpu_burn_ms > 0:
            dim = max(256, int(self.gpu_burn_dim))
            self._burn_a = torch.randn((dim, dim), device=self.device, dtype=torch.float16)
            self._burn_b = torch.randn((dim, dim), device=self.device, dtype=torch.float16)
            self._burn_out = torch.empty((dim, dim), device=self.device, dtype=torch.float16)
            # Calibrate approximate ms per matmul so we can burn without per-iteration synchronizes.
            with torch.no_grad():
                for _ in range(2):
                    torch.matmul(self._burn_a, self._burn_b, out=self._burn_out)
                torch.cuda.synchronize(self.device)
                n = 8
                t0 = time.perf_counter()
                for _ in range(n):
                    torch.matmul(self._burn_a, self._burn_b, out=self._burn_out)
                torch.cuda.synchronize(self.device)
                self._burn_ms_per_matmul = (time.perf_counter() - t0) * 1000.0 / float(n)

    def _gpu_burn(self) -> None:
        if self.device.type != "cuda" or self.gpu_burn_ms <= 0:
            return
        if self._burn_a is None or self._burn_b is None or self._burn_out is None:
            return
        if not self._burn_ms_per_matmul or self._burn_ms_per_matmul <= 0:
            return

        iters = max(1, int(math.ceil(self.gpu_burn_ms / float(self._burn_ms_per_matmul))))
        with torch.no_grad():
            for _ in range(iters):
                torch.matmul(self._burn_a, self._burn_b, out=self._burn_out)
        torch.cuda.synchronize(self.device)

    def collect_rollout(self) -> Dict[str, torch.Tensor]:
        """
        Collect rollout data from all environments.

        Returns dictionary with all tensors needed for PPO update.
        """
        # Storage buffers
        obs_buffer = []
        actions_buffer = []
        log_probs_buffer = []
        rewards_buffer = []
        dones_buffer = []
        values_buffer = []

        # Hidden state storage for TRUNCATED BPTT(1)
        prev_h_buffer = []
        prev_g_buffer = []
        prev_a_buffer = []
        z_buffer = []

        # Episode completion tracking for curriculum learning
        episode_returns = []  # List of (timestep, batch_idx, episode_return)

        # Initialize hidden states
        batch_size = self.num_envs
        h, g = self.brain.init_state(batch_size, self.device)
        a_prev = torch.zeros((batch_size, self.brain.config.action_bytes), dtype=torch.long, device=self.device)

        # Get initial observation
        obs = self.envs.reset()
        obs = obs.to(self.device)

        for step in range(self.rollout_steps):
            # Store pre-step state for BPTT
            prev_h_buffer.append(h.clone())
            prev_g_buffer.append(g.clone())
            prev_a_buffer.append(a_prev.clone())

            # Brain forward pass
            with torch.no_grad():
                output = self.brain(obs, h, g, a_prev, training=True)

            # Store latent for evaluate_actions
            z_buffer.append(output.z_t.clone())

            # Use the brain's full action bytes directly (32-byte tool-action policy).
            action_bytes = output.action.clamp(0, 255).to(torch.uint8)

            # Step environments
            next_obs, rewards, dones, infos = self.envs.step(action_bytes)
            next_obs = next_obs.to(self.device)
            rewards = rewards.to(self.device)
            self._gpu_burn()

            # Store data
            obs_buffer.append(obs.clone())
            actions_buffer.append(output.action.clone())
            log_probs_buffer.append(output.action_log_prob.clone())
            rewards_buffer.append(rewards)
            dones_buffer.append(dones.to(self.device))
            values_buffer.append(output.value.clone())

            # Update state
            h = output.h_next
            g = output.g_t
            a_prev = output.action
            obs = next_obs

            self.total_steps += self.num_envs

            # Track episode stats
            for i, info in enumerate(infos):
                if dones[i]:
                    # Use cumulative episode_return, not step reward
                    ep_return = info.get("episode_return", rewards[i].item())
                    self.episode_rewards.append(ep_return)
                    self.episode_lengths.append(info.get("step", 0))
                    # Track for curriculum learning
                    episode_returns.append((step, i, ep_return))

        # Get bootstrap value
        with torch.no_grad():
            final_output = self.brain(obs, h, g, a_prev, training=False)
            bootstrap_value = final_output.value

        # Stack buffers
        return {
            "obs": torch.stack(obs_buffer),  # [T, B, obs_dim]
            "actions": torch.stack(actions_buffer),  # [T, B, action_bytes]
            "log_probs": torch.stack(log_probs_buffer),  # [T, B, action_bytes]
            "rewards": torch.stack(rewards_buffer),  # [T, B]
            "dones": torch.stack(dones_buffer),  # [T, B]
            "values": torch.stack(values_buffer),  # [T, B]
            "bootstrap_value": bootstrap_value,  # [B]
            "prev_h": torch.stack(prev_h_buffer),  # [T, B, hidden_dim]
            "prev_g": torch.stack(prev_g_buffer),  # [T, B, k_max]
            "prev_a": torch.stack(prev_a_buffer),  # [T, B, action_bytes]
            "z_t": torch.stack(z_buffer),  # [T, B, latent_dim]
            "episode_returns": episode_returns,  # List of (timestep, batch_idx, episode_return)
        }

    def compute_gae(self, rollout: Dict[str, torch.Tensor]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute Generalized Advantage Estimation.

        Returns:
            advantages: [T, B]
            returns: [T, B]
        """
        T = self.rollout_steps
        rewards = rollout["rewards"]
        values = rollout["values"]
        dones = rollout["dones"]
        bootstrap = rollout["bootstrap_value"]

        advantages = torch.zeros_like(rewards)
        gae = torch.zeros(self.num_envs, device=self.device)

        for t in reversed(range(T)):
            if t == T - 1:
                next_value = bootstrap
            else:
                next_value = values[t + 1]

            delta = rewards[t] + self.gamma * next_value * (~dones[t]).float() - values[t]
            gae = delta + self.gamma * self.gae_lambda * (~dones[t]).float() * gae
            advantages[t] = gae

        returns = advantages + values
        return advantages, returns

    def update(self, rollout: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """
        Perform PPO update.

        Returns dictionary of loss metrics.
        """
        # Compute advantages
        advantages, returns = self.compute_gae(rollout)

        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # Flatten for update
        T, B = self.rollout_steps, self.num_envs
        obs_flat = rollout["obs"].view(T * B, -1)
        actions_flat = rollout["actions"].view(T * B, -1)
        old_log_probs_flat = rollout["log_probs"].view(T * B, -1)
        advantages_flat = advantages.view(T * B)
        returns_flat = returns.view(T * B)
        prev_h_flat = rollout["prev_h"].view(T * B, -1)
        prev_g_flat = rollout["prev_g"].view(T * B, -1)
        prev_a_flat = rollout["prev_a"].view(T * B, -1)
        z_flat = rollout["z_t"].view(T * B, -1)

        batch_size = T * B
        minibatch = max(1, min(self.minibatch_size, batch_size))

        policy_losses = []
        value_losses = []
        entropies = []
        total_losses = []

        for _ in range(self.update_epochs):
            indices = torch.randperm(batch_size, device=self.device)
            for start in range(0, batch_size, minibatch):
                mb_idx = indices[start:start + minibatch]

                # Re-evaluate actions with gradients (TRUNCATED BPTT(1): per-step prev state)
                new_log_probs, entropy, new_values, _, _, _ = self.brain.evaluate_actions(
                    obs_bytes=obs_flat[mb_idx],
                    prev_h=prev_h_flat[mb_idx],
                    prev_g=prev_g_flat[mb_idx],
                    prev_a=prev_a_flat[mb_idx],
                    actions=actions_flat[mb_idx],
                    z_t=z_flat[mb_idx],
                )

                new_log_probs_sum = new_log_probs.sum(dim=-1)
                old_log_probs_sum = old_log_probs_flat[mb_idx].sum(dim=-1)

                ratio = torch.exp(new_log_probs_sum - old_log_probs_sum)
                adv = advantages_flat[mb_idx]
                surr1 = ratio * adv
                surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * adv
                policy_loss = -torch.min(surr1, surr2).mean()

                value_loss = F.mse_loss(new_values, returns_flat[mb_idx])
                entropy_bonus = entropy.mean()

                # Total loss (maximize entropy_bonus)
                loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy_bonus

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.brain.parameters(), self.max_grad_norm)
                self.optimizer.step()

                policy_losses.append(policy_loss.detach())
                value_losses.append(value_loss.detach())
                entropies.append(entropy_bonus.detach())
                total_losses.append(loss.detach())

        def mean(xs: List[torch.Tensor]) -> float:
            if not xs:
                return 0.0
            return torch.stack(xs).mean().item()

        return {
            "policy_loss": mean(policy_losses),
            "value_loss": mean(value_losses),
            "entropy": mean(entropies),
            "total_loss": mean(total_losses),
        }

    def train(self, total_timesteps: int, log_interval: int = 1000):
        """Main training loop."""
        start_time = time.time()
        updates = 0

        while self.total_steps < total_timesteps:
            # Collect rollout
            rollout = self.collect_rollout()

            # PPO update
            metrics = self.update(rollout)

            updates += 1

            # Logging
            if updates % log_interval == 0:
                elapsed = time.time() - start_time
                fps = self.total_steps / elapsed

                avg_reward = sum(self.episode_rewards[-100:]) / max(len(self.episode_rewards[-100:]), 1)
                avg_length = sum(self.episode_lengths[-100:]) / max(len(self.episode_lengths[-100:]), 1)

                print(f"Steps: {self.total_steps:,} | FPS: {fps:.0f}")
                print(f"  Policy Loss: {metrics['policy_loss']:.4f}")
                print(f"  Value Loss: {metrics['value_loss']:.4f}")
                print(f"  Entropy: {metrics['entropy']:.4f}")
                print(f"  Avg Reward: {avg_reward:.2f}")
                print(f"  Avg Length: {avg_length:.1f}")
                print()

        print(f"Training complete: {self.total_steps:,} steps in {time.time() - start_time:.1f}s")

    def train_with_curriculum(
        self,
        total_timesteps: int,
        curriculum: CurriculumState,
        task_regenerator: callable,
        log_interval: int = 1000,
    ):
        """
        Training loop with curriculum learning.

        Args:
            total_timesteps: Total training timesteps
            curriculum: CurriculumState tracker
            task_regenerator: Function(difficulty) -> (tasks, repos) to regenerate tasks
            log_interval: How often to log
        """
        start_time = time.time()
        updates = 0
        difficulty_names = {
            BugDifficulty.TRIVIAL: "TRIVIAL",
            BugDifficulty.EASY: "EASY",
            BugDifficulty.MEDIUM: "MEDIUM",
            BugDifficulty.HARD: "HARD",
            BugDifficulty.EXPERT: "EXPERT",
        }

        print(f"\n=== CURRICULUM TRAINING ===")
        print(f"Starting at: {difficulty_names[curriculum.current_difficulty]}")

        while self.total_steps < total_timesteps:
            # Collect rollout
            rollout = self.collect_rollout()

            # Track curriculum outcomes from episode completions
            # Use cumulative episode_return (not step reward) for success metric
            for (timestep, batch_idx, ep_return) in rollout["episode_returns"]:
                # Success if cumulative episode return > 5.0
                success = ep_return > 5.0
                curriculum.record_episode(success)

            # Check for difficulty changes
            difficulty_changed = False
            old_difficulty = curriculum.current_difficulty

            if curriculum.should_promote():
                # Capture stats BEFORE promote() resets them
                old_sr = curriculum.success_rate
                old_eps = curriculum.episodes_at_level
                old_diff = difficulty_names[curriculum.current_difficulty]
                if curriculum.promote():
                    print(f"\n🚀 PROMOTED from {old_diff} to {difficulty_names[curriculum.current_difficulty]}!")
                    print(f"   Success rate was: {old_sr:.1%} ({old_eps} episodes)")
                    print(f"   Total promotions: {curriculum.total_promotions}")
                    difficulty_changed = True

            elif curriculum.should_demote():
                # Capture stats BEFORE demote() resets them
                old_sr = curriculum.success_rate
                old_eps = curriculum.episodes_at_level
                old_diff = difficulty_names[curriculum.current_difficulty]
                if curriculum.demote():
                    print(f"\n⬇️  DEMOTED from {old_diff} to {difficulty_names[curriculum.current_difficulty]}")
                    print(f"   Success rate was: {old_sr:.1%} ({old_eps} episodes)")
                    print(f"   Total demotions: {curriculum.total_demotions}")
                    difficulty_changed = True

            # Regenerate tasks if difficulty changed
            if difficulty_changed:
                new_tasks, new_repos = task_regenerator(curriculum.current_difficulty)
                self.envs.set_tasks(new_tasks)
                print(f"   Regenerated {len(new_tasks)} tasks at {difficulty_names[curriculum.current_difficulty]}")

            # PPO update
            metrics = self.update(rollout)

            updates += 1

            # Logging
            if updates % log_interval == 0:
                elapsed = time.time() - start_time
                fps = self.total_steps / elapsed

                avg_reward = sum(self.episode_rewards[-100:]) / max(len(self.episode_rewards[-100:]), 1)
                avg_length = sum(self.episode_lengths[-100:]) / max(len(self.episode_lengths[-100:]), 1)

                print(f"Steps: {self.total_steps:,} | FPS: {fps:.0f} | Difficulty: {difficulty_names[curriculum.current_difficulty]}")
                print(f"  Policy Loss: {metrics['policy_loss']:.4f}")
                print(f"  Value Loss: {metrics['value_loss']:.4f}")
                print(f"  Entropy: {metrics['entropy']:.4f}")
                print(f"  Avg Reward: {avg_reward:.2f}")
                print(f"  Avg Length: {avg_length:.1f}")
                print(f"  Curriculum: SR={curriculum.success_rate:.1%} ({curriculum.episodes_at_level} eps)")
                print(f"  Promotions: {curriculum.total_promotions} | Demotions: {curriculum.total_demotions}")
                print()

        print(f"\nTraining complete: {self.total_steps:,} steps in {time.time() - start_time:.1f}s")
        print(f"Final difficulty: {difficulty_names[curriculum.current_difficulty]}")
        print(f"Total promotions: {curriculum.total_promotions}")
        print(f"Total demotions: {curriculum.total_demotions}")


def main():
    parser = argparse.ArgumentParser(description="Train Jarvis Harness")
    parser.add_argument("--num-envs", type=int, default=32, help="Number of parallel environments")
    parser.add_argument("--timesteps", type=int, default=100000, help="Total training timesteps")
    parser.add_argument("--rollout-steps", type=int, default=128, help="Steps per rollout")
    parser.add_argument("--ppo-epochs", type=int, default=4, help="PPO update epochs per rollout (more = more GPU work)")
    parser.add_argument("--minibatch-size", type=int, default=1024, help="Minibatch size for PPO updates")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    parser.add_argument("--entropy-coef", type=float, default=0.01,
                        help="Entropy coefficient (lower = less exploration)")
    parser.add_argument(
        "--hidden-dim",
        type=int,
        default=512,
        help="RPJ hidden dim (higher = more GPU work; keep VRAM < 10GB total)",
    )
    parser.add_argument(
        "--gpu-burn-ms",
        type=float,
        default=0.0,
        help="Extra GPU padding per rollout step (ms). Helps keep util > floor when CPU-bound.",
    )
    parser.add_argument(
        "--gpu-burn-dim",
        type=int,
        default=4096,
        help="Matmul dim for GPU burn (larger = more load, more VRAM).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--repo-path", type=str, default="fixtures/toy_repo", help="Path to toy repo (v1 mode)")

    # v2 options
    parser.add_argument("--mode", type=str, choices=["v1", "v2", "curriculum"], default="v1",
                        help="Training mode: v1 (toy repo), v2 (multi-file), or curriculum (progressive)")
    parser.add_argument("--difficulty", type=str, choices=["easy", "medium", "hard"], default="medium",
                        help="Bug difficulty for v2 mode (starting difficulty for curriculum)")
    parser.add_argument("--action-bytes", type=int, choices=[32, 64], default=32,
                        help="Action space size (32 for v1, 64 for v2)")
    # Curriculum options
    parser.add_argument("--promote-threshold", type=float, default=0.70,
                        help="Success rate threshold for promotion (curriculum mode)")
    parser.add_argument("--demote-threshold", type=float, default=0.30,
                        help="Success rate threshold for demotion (curriculum mode)")
    parser.add_argument("--min-episodes", type=int, default=50,
                        help="Minimum episodes before promotion/demotion decision")
    # GPU guardrails (hard safety + utilization floor)
    parser.add_argument("--no-gpu-guard", action="store_true", help="Disable GPU guardrails (not recommended)")
    parser.add_argument("--gpu-index", type=int, default=None, help="GPU index for nvidia-smi sampling (default: auto)")
    parser.add_argument("--gpu-max-vram-mib", type=int, default=10 * 1024, help="Abort if total VRAM used exceeds this")
    parser.add_argument("--gpu-min-util", type=int, default=80, help="Abort if sustained GPU util falls below this %%")
    parser.add_argument("--gpu-grace-s", type=float, default=20.0, help="Warmup seconds before util enforcement")
    parser.add_argument("--gpu-low-util-patience-s", type=float, default=30.0, help="Seconds of low util before abort")
    args = parser.parse_args()

    if args.no_gpu_guard:
        raise SystemExit("Refusing to run with --no-gpu-guard (hard repo rule).")

    # Set seed
    torch.manual_seed(args.seed)
    random.seed(args.seed)

    device = torch.device(args.device)
    print(f"Using device: {device}")
    print(f"Training mode: {args.mode}")

    gpu_index = args.gpu_index if args.gpu_index is not None else default_gpu_index()
    gpu_lock = None
    guard = None
    envs = None
    temp_dir = None

    try:
        if device.type == "cuda":
            gpu_lock = ExclusiveGPULock(gpu_index=gpu_index)
            gpu_lock.acquire()
            print(f"GPU_LOCK: acquired {gpu_lock.path}")

        if device.type == "cuda" and not args.no_gpu_guard:
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

        # Determine action bytes
        action_bytes = ACTION_BYTES_V2 if args.action_bytes == 64 else ACTION_BYTES

        # Create environments
        harness_config = HarnessConfig(
            obs_bytes=OBS_TOTAL_BYTES,
            action_bytes=action_bytes,
            max_steps=50 if args.mode == "v1" else 100,  # More steps for v2
            max_time_seconds=30 if args.mode == "v1" else 60,
            # Training must be GPU-saturated; avoid expensive pytest on every reset.
            run_tests_on_reset=(args.mode == "v1"),
            run_fast_tests=(args.mode != "v1"),
            # Keep verifier subprocesses bounded so CPU doesn't starve the GPU.
            test_timeout_seconds=30 if args.mode == "v1" else 20,
            fast_test_timeout_seconds=10 if args.mode == "v1" else 5,
        )
        envs = VectorizedJarvisEnv(args.num_envs, harness_config)

        # Create tasks based on mode
        repos = None
        curriculum_state = None

        if args.mode == "v1":
            repo_path = os.path.join(os.path.dirname(__file__), "..", args.repo_path)
            tasks = create_tasks_legacy(repo_path, args.num_envs)
            print(f"v1 mode: Using toy repo at {repo_path}")

        elif args.mode == "curriculum":
            curriculum_state = CurriculumState(
                current_difficulty=BugDifficulty.TRIVIAL,
                promote_threshold=args.promote_threshold,
                demote_threshold=args.demote_threshold,
                min_episodes=args.min_episodes,
            )
            temp_dir = tempfile.mkdtemp(prefix="jarvis_curriculum_")
            tasks, repos = create_tasks_v2(
                num_tasks=args.num_envs,
                difficulty=curriculum_state.current_difficulty,
                temp_base=temp_dir,
                seed=args.seed,
            )
            print("CURRICULUM mode: Starting at TRIVIAL difficulty")
            print(f"Promotion threshold: {curriculum_state.promote_threshold:.0%}")
            print(f"Demotion threshold: {curriculum_state.demote_threshold:.0%}")
            print(f"Min episodes before change: {curriculum_state.min_episodes}")
            print(f"Temp directory: {temp_dir}")

        else:
            difficulty_map = {
                "easy": BugDifficulty.EASY,
                "medium": BugDifficulty.MEDIUM,
                "hard": BugDifficulty.HARD,
            }
            difficulty = difficulty_map[args.difficulty]

            temp_dir = tempfile.mkdtemp(prefix="jarvis_train_")
            tasks, repos = create_tasks_v2(
                num_tasks=args.num_envs,
                difficulty=difficulty,
                temp_base=temp_dir,
                seed=args.seed,
            )
            print(f"v2 mode: Generated {len(tasks)} multi-file tasks")
            print(f"Difficulty: {args.difficulty}")
            print(f"Temp directory: {temp_dir}")

            for i, (task, repo) in enumerate(zip(tasks[:3], repos[:3])):
                print(f"  Task {i}: {task.name} ({len(repo.files)} files, {len(repo.bugs)} bugs)")

        envs.set_tasks(tasks)

        # Create brain
        brain = create_brain(
            obs_dim=OBS_TOTAL_BYTES,
            action_bytes=action_bytes,
            hidden_dim=int(args.hidden_dim),
            enable_plasticity=False,  # Disable for initial training
            enable_sleep=False,       # Disable for initial training
        ).to(device)

        param_count = sum(p.numel() for p in brain.parameters())
        print(f"Brain parameters: {param_count:,}")

        trainer = JarvisHarnessTrainer(
            brain=brain,
            envs=envs,
            device=device,
            lr=args.lr,
            entropy_coef=args.entropy_coef,
            rollout_steps=args.rollout_steps,
            update_epochs=args.ppo_epochs,
            minibatch_size=args.minibatch_size,
            gpu_burn_ms=args.gpu_burn_ms,
            gpu_burn_dim=args.gpu_burn_dim,
        )

        print(f"\nStarting training for {args.timesteps:,} timesteps...")
        print(f"Environments: {args.num_envs}")
        print(f"Rollout steps: {args.rollout_steps}")
        print(f"Action bytes: {action_bytes}")
        print()

        try:
            if args.mode == "curriculum" and curriculum_state is not None:
                def regenerate_tasks(difficulty: BugDifficulty):
                    nonlocal temp_dir, repos
                    if temp_dir and os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    temp_dir = tempfile.mkdtemp(prefix="jarvis_curriculum_")
                    new_tasks, new_repos = create_tasks_v2(
                        num_tasks=args.num_envs,
                        difficulty=difficulty,
                        temp_base=temp_dir,
                        seed=random.randint(0, 2**31),
                    )
                    repos = new_repos
                    return new_tasks, new_repos

                trainer.train_with_curriculum(
                    args.timesteps,
                    curriculum_state,
                    regenerate_tasks,
                    log_interval=10,
                )
            else:
                trainer.train(args.timesteps, log_interval=10)
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"Cleaned up temp directory: {temp_dir}")
                temp_dir = None

        mode_suffix = f"_{args.mode}" if args.mode in ["v2", "curriculum"] else ""
        checkpoint_path = f"results/jarvis_harness{mode_suffix}_{args.timesteps}.pt"
        os.makedirs("results", exist_ok=True)
        checkpoint_data = {
            "brain_state_dict": brain.state_dict(),
            "total_steps": trainer.total_steps,
            "config": vars(args),
            "mode": args.mode,
        }
        if curriculum_state is not None:
            checkpoint_data["curriculum"] = {
                "final_difficulty": curriculum_state.current_difficulty.name,
                "total_promotions": curriculum_state.total_promotions,
                "total_demotions": curriculum_state.total_demotions,
                "final_success_rate": curriculum_state.success_rate,
            }
        torch.save(checkpoint_data, checkpoint_path)
        print(f"Saved checkpoint to {checkpoint_path}")
    finally:
        if guard is not None:
            guard.stop()
        if envs is not None:
            envs.close()
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        if gpu_lock is not None:
            gpu_lock.release()


if __name__ == "__main__":
    main()
