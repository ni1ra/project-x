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
import os
import time
import random
import tempfile
import shutil
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

        # Optimizer
        self.optimizer = Adam(brain.parameters(), lr=lr)

        # Statistics
        self.total_steps = 0
        self.episode_rewards = []
        self.episode_lengths = []

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
                    self.episode_rewards.append(rewards[i].item())
                    self.episode_lengths.append(info.get("step", 0))

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

        # PPO update (single epoch for simplicity)
        # Re-evaluate actions with gradients
        new_log_probs, entropy, new_values, _, _, _ = self.brain.evaluate_actions(
            obs_bytes=obs_flat,
            prev_h=prev_h_flat,
            prev_g=prev_g_flat,
            prev_a=prev_a_flat,
            actions=actions_flat,
            z_t=z_flat,
        )

        new_log_probs_sum = new_log_probs.sum(dim=-1)  # [T*B]
        old_log_probs_sum = old_log_probs_flat.sum(dim=-1)  # [T*B]

        # Policy loss (clipped)
        ratio = torch.exp(new_log_probs_sum - old_log_probs_sum)
        surr1 = ratio * advantages_flat
        surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantages_flat
        policy_loss = -torch.min(surr1, surr2).mean()

        # Value loss
        value_loss = F.mse_loss(new_values, returns_flat)

        # Entropy bonus
        entropy_loss = -entropy.mean()

        # Total loss
        loss = policy_loss + self.value_coef * value_loss + self.entropy_coef * entropy_loss

        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.brain.parameters(), self.max_grad_norm)
        self.optimizer.step()

        return {
            "policy_loss": policy_loss.item(),
            "value_loss": value_loss.item(),
            "entropy": -entropy_loss.item(),
            "total_loss": loss.item(),
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


def main():
    parser = argparse.ArgumentParser(description="Train Jarvis Harness")
    parser.add_argument("--num-envs", type=int, default=32, help="Number of parallel environments")
    parser.add_argument("--timesteps", type=int, default=100000, help="Total training timesteps")
    parser.add_argument("--rollout-steps", type=int, default=128, help="Steps per rollout")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--repo-path", type=str, default="fixtures/toy_repo", help="Path to toy repo (v1 mode)")

    # v2 options
    parser.add_argument("--mode", type=str, choices=["v1", "v2"], default="v1",
                        help="Training mode: v1 (toy repo) or v2 (multi-file generation)")
    parser.add_argument("--difficulty", type=str, choices=["easy", "medium", "hard"], default="medium",
                        help="Bug difficulty for v2 mode")
    parser.add_argument("--action-bytes", type=int, choices=[32, 64], default=32,
                        help="Action space size (32 for v1, 64 for v2)")
    args = parser.parse_args()

    # Set seed
    torch.manual_seed(args.seed)
    random.seed(args.seed)

    device = torch.device(args.device)
    print(f"Using device: {device}")
    print(f"Training mode: {args.mode}")

    # Determine action bytes
    action_bytes = ACTION_BYTES_V2 if args.action_bytes == 64 else ACTION_BYTES

    # Create environments
    harness_config = HarnessConfig(
        obs_bytes=OBS_TOTAL_BYTES,
        action_bytes=action_bytes,
        max_steps=50 if args.mode == "v1" else 100,  # More steps for v2
        max_time_seconds=30 if args.mode == "v1" else 60,
    )
    envs = VectorizedJarvisEnv(args.num_envs, harness_config)

    # Create tasks based on mode
    temp_dir = None
    repos = None

    if args.mode == "v1":
        # Legacy mode - use toy repo
        repo_path = os.path.join(os.path.dirname(__file__), "..", args.repo_path)
        tasks = create_tasks_legacy(repo_path, args.num_envs)
        print(f"v1 mode: Using toy repo at {repo_path}")
    else:
        # v2 mode - generate multi-file repos
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

        # Show some task info
        for i, (task, repo) in enumerate(zip(tasks[:3], repos[:3])):
            print(f"  Task {i}: {task.name} ({len(repo.files)} files, {len(repo.bugs)} bugs)")

    envs.set_tasks(tasks)

    # Create brain
    brain = create_brain(
        obs_dim=OBS_TOTAL_BYTES,
        action_bytes=action_bytes,
        enable_plasticity=False,  # Disable for initial training
        enable_sleep=False,       # Disable for initial training
    )
    brain = brain.to(device)

    param_count = sum(p.numel() for p in brain.parameters())
    print(f"Brain parameters: {param_count:,}")

    # Create trainer
    trainer = JarvisHarnessTrainer(
        brain=brain,
        envs=envs,
        device=device,
        lr=args.lr,
        rollout_steps=args.rollout_steps,
    )

    # Train
    print(f"\nStarting training for {args.timesteps:,} timesteps...")
    print(f"Environments: {args.num_envs}")
    print(f"Rollout steps: {args.rollout_steps}")
    print(f"Action bytes: {action_bytes}")
    print()

    try:
        trainer.train(args.timesteps, log_interval=10)
    finally:
        # Cleanup temp directory if created
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"Cleaned up temp directory: {temp_dir}")

    # Save checkpoint
    mode_suffix = f"_{args.mode}" if args.mode == "v2" else ""
    checkpoint_path = f"results/jarvis_harness{mode_suffix}_{args.timesteps}.pt"
    os.makedirs("results", exist_ok=True)
    torch.save({
        "brain_state_dict": brain.state_dict(),
        "total_steps": trainer.total_steps,
        "config": vars(args),
        "mode": args.mode,
    }, checkpoint_path)
    print(f"Saved checkpoint to {checkpoint_path}")

    # Cleanup
    envs.close()


if __name__ == "__main__":
    main()
