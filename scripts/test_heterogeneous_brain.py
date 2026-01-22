#!/usr/bin/env python3
"""
Test the HeterogeneousBrain with BC pre-training and evaluation.

This validates that the Phase 8 structural plasticity module can:
1. Create a heterogeneous brain
2. Train it with BC pre-training
3. Evaluate on the harness

Usage:
  PYTHONPATH=. .venv/bin/python scripts/test_heterogeneous_brain.py
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import tempfile
import shutil
from typing import List, Dict, Any, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import Adam

from src.core.structural_plasticity import (
    RegionConfig,
    Timescale,
    HeterogeneousSubstrate,
    create_default_regions,
    create_homogeneous_baseline,
)
from src.core.byte_interface import phi, AutoregressiveActionDecoder
from src.harness.env import JarvisHarnessEnv, HarnessConfig, Task
from src.harness.repo_generator import RepoGenerator, generate_task_batch
from src.harness.observations import OBS_TOTAL_BYTES
from src.harness.actions import ACTION_BYTES_V2, ActionType
from src.harness.expert_trajectories import create_online_oracle_bc_dataset
from src.harness.bug_templates import BugDifficulty


class SimpleHeterogeneousBrain(nn.Module):
    """
    Simplified heterogeneous brain for testing.
    Uses the HeterogeneousSubstrate but with simpler training interface.
    """

    def __init__(
        self,
        regions: List[RegionConfig],
        obs_dim: int = OBS_TOTAL_BYTES,
        action_bytes: int = ACTION_BYTES_V2,
        vocab_size: int = 35,
    ):
        super().__init__()

        self.substrate = HeterogeneousSubstrate(
            regions=regions,
            obs_dim=obs_dim,
            latent_dim=64,
            action_bytes=action_bytes,
        )

        self.action_decoder = AutoregressiveActionDecoder(
            hidden_dim=self.substrate.total_hidden_dim,
            num_action_bytes=action_bytes,
            k_max=self.substrate.k_max,
            obs_dim=obs_dim,
            vocab_size=vocab_size,
        )

        # Simple latent encoder (no VAE complexity for testing)
        self.latent_encoder = nn.Sequential(
            nn.Linear(obs_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
        )

        self.action_bytes = action_bytes
        self.obs_dim = obs_dim

    def init_state(self, batch_size: int, device: torch.device):
        h = self.substrate.init_hidden(batch_size, device)
        g = self.substrate.init_global_scalars(batch_size, device)
        return h, g

    def forward(
        self,
        obs_bytes: torch.Tensor,
        h_t: torch.Tensor,
        g_prev: torch.Tensor,
        a_prev: torch.Tensor,
        training: bool = True,
    ):
        phi_obs = phi(obs_bytes)
        z_t = self.latent_encoder(phi_obs)

        output = self.substrate(
            phi_obs=phi_obs,
            z_t=z_t,
            a_prev=a_prev,
            h_t=h_t,
            g_prev=g_prev,
            training=training,
        )

        action, action_log_prob, action_mu = self.action_decoder(
            output['h_next'],
            g_t=output['g_t'],
            num_bytes=self.action_bytes,
            greedy=not training,
            phi_obs=phi_obs,
        )

        return {
            'action': action,
            'action_log_prob': action_log_prob,
            'h_next': output['h_next'],
            'g_t': output['g_t'],
        }

    def get_vocab_logits(
        self,
        obs_bytes: torch.Tensor,
        h_t: torch.Tensor,
        g_prev: torch.Tensor,
        a_prev: torch.Tensor,
    ):
        """Get vocab logits for BC training."""
        phi_obs = phi(obs_bytes)
        z_t = self.latent_encoder(phi_obs)

        output = self.substrate(
            phi_obs=phi_obs,
            z_t=z_t,
            a_prev=a_prev,
            h_t=h_t,
            g_prev=g_prev,
            training=True,
        )

        vocab_head = getattr(self.action_decoder, 'vocab_head', None)
        if vocab_head is None:
            return None

        goal_start = self.action_decoder.goal_start
        goal_dim = self.action_decoder.goal_dim
        focus_text_start = self.action_decoder.focus_text_start
        focus_text_dim = self.action_decoder.focus_text_dim

        goal_bytes = phi_obs[:, goal_start:goal_start + goal_dim]
        focus_text = phi_obs[:, focus_text_start:focus_text_start + focus_text_dim]

        return vocab_head(output['h_next'], goal_bytes, focus_text)


def train_with_bc(
    brain: SimpleHeterogeneousBrain,
    num_tasks: int = 100,
    num_epochs: int = 30,
    device: torch.device = torch.device('cpu'),
) -> Dict[str, float]:
    """Train the brain with BC pre-training using online oracle dataset."""

    # Generate expert trajectories using online oracle
    print("Generating expert trajectories via online oracle...")
    dataset = create_online_oracle_bc_dataset(
        num_tasks=num_tasks,
        difficulty=BugDifficulty.TRIVIAL,
        seed=42,
        seq_len=3,
    )

    print(f"Generated {dataset['num_trajectories']} trajectories, {dataset['num_samples']} samples")
    print(f"  WRITE_FOCUS: {dataset['num_write_focus']}, RUN_TESTS: {dataset['num_run_tests']}, COMPLETE: {dataset['num_complete_task']}")

    # Flatten dataset: (num_traj, seq_len, ...) -> (num_samples, ...)
    obs_tensor = dataset['observations'].view(-1, OBS_TOTAL_BYTES).to(device)
    action_tensor = dataset['action_bytes'].view(-1, ACTION_BYTES_V2).to(device)
    masks = dataset['masks'].view(-1)

    # Filter to valid samples only
    valid_indices = masks.nonzero(as_tuple=True)[0]
    obs_tensor = obs_tensor[valid_indices]
    action_tensor = action_tensor[valid_indices]

    print(f"BC dataset: {len(obs_tensor)} valid samples")

    # Training loop
    optimizer = Adam(brain.parameters(), lr=1e-3)
    brain.train()

    best_acc = 0.0
    best_loss = float('inf')

    for epoch in range(num_epochs):
        total_loss = 0.0
        correct = 0
        total = 0

        # Process in batches
        batch_size = 32
        indices = list(range(len(obs_tensor)))
        random.shuffle(indices)

        for i in range(0, len(indices), batch_size):
            batch_indices = indices[i:i + batch_size]
            batch_obs = obs_tensor[batch_indices]
            batch_actions = action_tensor[batch_indices]

            h, g = brain.init_state(len(batch_indices), device)
            a_prev = torch.zeros(len(batch_indices), brain.action_bytes, dtype=torch.long, device=device)

            # Forward pass
            out = brain(batch_obs, h, g, a_prev, training=True)

            # Action prediction loss (byte-level)
            # Simplified: only train on action type (byte 0)
            action_type_logits = out['action_log_prob'][:, 0]  # Use log_prob as proxy
            action_type_target = batch_actions[:, 0]

            # Vocab loss for WRITE_FOCUS actions
            vocab_logits = brain.get_vocab_logits(batch_obs, h, g, a_prev)
            vocab_loss = torch.tensor(0.0, device=device)

            if vocab_logits is not None:
                # Find WRITE_FOCUS samples in this batch
                batch_vocab_mask = batch_actions[:, 0] == ActionType.WRITE_FOCUS.value
                if batch_vocab_mask.any():
                    vocab_targets = batch_actions[batch_vocab_mask, 25]
                    vocab_logits_masked = vocab_logits[batch_vocab_mask]
                    vocab_loss = F.cross_entropy(vocab_logits_masked, vocab_targets.long())

                    # Accuracy
                    preds = vocab_logits_masked.argmax(dim=-1)
                    correct += (preds == vocab_targets).sum().item()
                    total += batch_vocab_mask.sum().item()

            loss = vocab_loss
            if loss.item() > 0:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

        avg_loss = total_loss / max(1, len(indices) // batch_size)
        accuracy = correct / max(1, total)

        if accuracy > best_acc:
            best_acc = accuracy
        if avg_loss < best_loss:
            best_loss = avg_loss

        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch + 1}/{num_epochs}: Loss={avg_loss:.4f}, Accuracy={accuracy:.1%}")

    return {'accuracy': best_acc, 'loss': best_loss}


def evaluate(
    brain: SimpleHeterogeneousBrain,
    tasks: List[Task],
    env: JarvisHarnessEnv,
    device: torch.device = torch.device('cpu'),
    max_steps: int = 50,
) -> Dict[str, float]:
    """Evaluate the brain on tasks."""
    brain.eval()

    solves = 0
    total_reward = 0.0

    for task in tasks:
        env.set_task(task)
        obs = env.reset()

        h, g = brain.init_state(1, device)
        a_prev = torch.zeros(1, brain.action_bytes, dtype=torch.long, device=device)

        episode_reward = 0.0

        for _ in range(max_steps):
            obs_t = obs.unsqueeze(0).to(device)

            with torch.no_grad():
                out = brain(obs_t, h, g, a_prev, training=False)

            action = out['action'].clamp(0, 255).to(torch.uint8).squeeze(0).cpu()
            obs, reward, done, info = env.step(action)

            episode_reward += float(reward)
            h = out['h_next']
            g = out['g_t']
            a_prev = out['action']

            if done:
                if info.get("done_reason") == "success":
                    solves += 1
                break

        total_reward += episode_reward

    return {
        'solve_rate': solves / len(tasks),
        'avg_reward': total_reward / len(tasks),
    }


def main():
    print("=" * 60)
    print("Testing Heterogeneous Brain with BC Training")
    print("=" * 60)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    # Create tasks
    print("\nGenerating tasks...")
    temp_base = tempfile.mkdtemp(prefix="hetero_test_")
    try:
        gen = RepoGenerator(seed=42)
        repos = generate_task_batch(
            num_tasks=20,
            difficulty_range=(BugDifficulty.TRIVIAL, BugDifficulty.TRIVIAL),
            seed=42,
        )

        tasks = []
        for repo in repos:
            repo_path = gen.write_to_disk(repo, temp_base)
            bug = repo.bugs[0] if repo.bugs else None
            tasks.append(
                Task(
                    name=repo.name,
                    description=f"Fix bug: {repo.fix_description[:50]}",
                    repo_path=repo_path,
                    target_file=bug.file_path if bug else "models.py",
                    bug_line=bug.line_number if bug else None,
                )
            )

        print(f"Created {len(tasks)} tasks")

        # Create environment
        config = HarnessConfig(
            obs_bytes=OBS_TOTAL_BYTES,
            action_bytes=ACTION_BYTES_V2,
            max_steps=50,
            max_time_seconds=30,
            run_tests_on_reset=False,
            run_fast_tests=True,
            async_tests=True,
            force_write_focus=True,
            auto_focus_target=True,
        )
        env = JarvisHarnessEnv(config)

        # Test 1: Default heterogeneous regions
        print("\n--- Test 1: Default Heterogeneous Brain ---")
        default_regions = create_default_regions()
        print(f"Regions: {[r.name for r in default_regions]}")
        print(f"Total width: {sum(r.width for r in default_regions)}")

        brain_hetero = SimpleHeterogeneousBrain(
            regions=default_regions,
            vocab_size=35,
        ).to(device)
        print(f"Parameters: {sum(p.numel() for p in brain_hetero.parameters()):,}")

        train_metrics = train_with_bc(brain_hetero, num_tasks=50, num_epochs=30, device=device)
        print(f"BC Training: Accuracy={train_metrics['accuracy']:.1%}, Loss={train_metrics['loss']:.4f}")

        eval_metrics = evaluate(brain_hetero, tasks, env, device=device)
        print(f"Evaluation: Solve rate={eval_metrics['solve_rate']:.1%}, Avg reward={eval_metrics['avg_reward']:.2f}")

        # Test 2: Homogeneous baseline
        print("\n--- Test 2: Homogeneous Baseline ---")
        uniform_regions = [
            RegionConfig(name=f"region_{i}", width=128, sparsity=1.0, timescale=Timescale.FAST)
            for i in range(4)
        ]
        print(f"Regions: 4 uniform (width=128 each)")

        brain_homo = SimpleHeterogeneousBrain(
            regions=uniform_regions,
            vocab_size=35,
        ).to(device)
        print(f"Parameters: {sum(p.numel() for p in brain_homo.parameters()):,}")

        train_metrics_homo = train_with_bc(brain_homo, num_tasks=50, num_epochs=30, device=device)
        print(f"BC Training: Accuracy={train_metrics_homo['accuracy']:.1%}, Loss={train_metrics_homo['loss']:.4f}")

        eval_metrics_homo = evaluate(brain_homo, tasks, env, device=device)
        print(f"Evaluation: Solve rate={eval_metrics_homo['solve_rate']:.1%}, Avg reward={eval_metrics_homo['avg_reward']:.2f}")

        # Comparison
        print("\n" + "=" * 60)
        print("COMPARISON")
        print("=" * 60)
        print(f"{'Metric':<20} {'Heterogeneous':<15} {'Homogeneous':<15}")
        print("-" * 50)
        print(f"{'BC Accuracy':<20} {train_metrics['accuracy']:.1%}{'':<10} {train_metrics_homo['accuracy']:.1%}")
        print(f"{'Solve Rate':<20} {eval_metrics['solve_rate']:.1%}{'':<10} {eval_metrics_homo['solve_rate']:.1%}")
        print(f"{'Avg Reward':<20} {eval_metrics['avg_reward']:.2f}{'':<10} {eval_metrics_homo['avg_reward']:.2f}")

        env.close()

    finally:
        shutil.rmtree(temp_base, ignore_errors=True)

    print("\n Heterogeneous brain test complete!")


if __name__ == "__main__":
    main()
