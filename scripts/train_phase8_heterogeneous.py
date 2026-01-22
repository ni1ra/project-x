#!/usr/bin/env python3
"""
Phase 8: Heterogeneous Brain Training

Trains the HeterogeneousBrain with optimal structure found by Optuna search.
Uses full BC pre-training + RL fine-tuning pipeline.

Usage:
  PYTHONPATH=. .venv/bin/python scripts/train_phase8_heterogeneous.py \
    --bc-epochs 50 --rl-steps 10000 --difficulty trivial

Reference: paper.md Appendix K, MISTAKES.md Phase 8 entries
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import random
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, List, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import Adam

from src.core.structural_plasticity import (
    RegionConfig,
    Timescale,
    HeterogeneousSubstrate,
    create_optimal_regions,
    create_default_regions,
)
from src.core.byte_interface import phi, AutoregressiveActionDecoder
from src.harness.env import JarvisHarnessEnv, HarnessConfig, Task
from src.harness.repo_generator import RepoGenerator, generate_task_batch
from src.harness.bug_templates import BugDifficulty
from src.harness.observations import OBS_TOTAL_BYTES, TERMINAL_BYTES, GOAL_BYTES, FS_BYTES
from src.harness.actions import ACTION_BYTES_V2, ActionType
from src.harness.expert_trajectories import create_online_oracle_bc_dataset


class HeterogeneousBrain(nn.Module):
    """
    Heterogeneous brain with optimized structure for JARVIS harness.

    Uses the HeterogeneousSubstrate with AutoregressiveActionDecoder.
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

        # VAE encoder (simplified)
        self.vae_encoder = nn.Sequential(
            nn.Linear(obs_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64 * 2),  # mu, logvar
        )

        self.action_bytes = action_bytes
        self.obs_dim = obs_dim

    def init_state(self, batch_size: int, device: torch.device):
        h = self.substrate.init_hidden(batch_size, device)
        g = self.substrate.init_global_scalars(batch_size, device)
        return h, g

    def encode(self, phi_obs: torch.Tensor) -> torch.Tensor:
        params = self.vae_encoder(phi_obs)
        mu, logvar = params.chunk(2, dim=-1)
        if self.training:
            std = torch.exp(0.5 * logvar)
            z = mu + std * torch.randn_like(std)
        else:
            z = mu
        return z

    def forward(
        self,
        obs_bytes: torch.Tensor,
        h_t: torch.Tensor,
        g_prev: torch.Tensor,
        a_prev: torch.Tensor,
        training: bool = True,
    ):
        phi_obs = phi(obs_bytes)
        z_t = self.encode(phi_obs)

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

        value = self.substrate.get_value(output['h_next'], output['g_t'])

        return {
            'action': action,
            'action_log_prob': action_log_prob,
            'action_mu': action_mu,
            'h_next': output['h_next'],
            'g_t': output['g_t'],
            'value': value,
            'energy': self.substrate.compute_total_energy(output),
        }

    def get_vocab_logits(
        self,
        obs_bytes: torch.Tensor,
        h_next: torch.Tensor,
    ):
        """Get vocab logits for BC training."""
        vocab_head = getattr(self.action_decoder, 'vocab_head', None)
        if vocab_head is None:
            return None

        phi_obs = phi(obs_bytes)
        goal_start = TERMINAL_BYTES
        goal_dim = GOAL_BYTES
        focus_start = TERMINAL_BYTES + GOAL_BYTES
        focus_dim = FS_BYTES

        goal_bytes = phi_obs[:, goal_start:goal_start + goal_dim]
        focus_text = phi_obs[:, focus_start:focus_start + focus_dim]

        return vocab_head(h_next, goal_bytes, focus_text)


def train_bc(
    brain: HeterogeneousBrain,
    difficulty: BugDifficulty,
    num_tasks: int,
    num_epochs: int,
    device: torch.device,
) -> Dict[str, float]:
    """BC pre-training phase."""
    print(f"\n=== BC Pre-training ({num_epochs} epochs, {num_tasks} tasks) ===")

    # Generate dataset
    dataset = create_online_oracle_bc_dataset(
        num_tasks=num_tasks,
        difficulty=difficulty,
        seed=42,
        seq_len=3,
    )

    print(f"Generated {dataset['num_trajectories']} trajectories")
    print(f"  WRITE_FOCUS: {dataset['num_write_focus']}, RUN_TESTS: {dataset['num_run_tests']}")

    # Flatten dataset
    obs_flat = dataset['observations'].view(-1, OBS_TOTAL_BYTES).to(device)
    action_flat = dataset['action_bytes'].view(-1, ACTION_BYTES_V2).to(device)
    masks = dataset['masks'].view(-1)
    valid_idx = masks.nonzero(as_tuple=True)[0]
    obs_flat = obs_flat[valid_idx]
    action_flat = action_flat[valid_idx]

    print(f"Dataset: {len(obs_flat)} valid samples")

    optimizer = Adam(brain.parameters(), lr=1e-3)
    brain.train()

    best_acc = 0.0
    best_loss = float('inf')

    for epoch in range(num_epochs):
        total_loss = 0.0
        correct = 0
        total = 0
        n_batches = 0

        perm = torch.randperm(len(obs_flat))
        for i in range(0, len(perm), 32):
            batch_idx = perm[i:i+32]
            batch_obs = obs_flat[batch_idx]
            batch_act = action_flat[batch_idx]

            h, g = brain.init_state(len(batch_idx), device)
            a_prev = torch.zeros(len(batch_idx), brain.action_bytes, dtype=torch.long, device=device)

            out = brain(batch_obs, h, g, a_prev, training=True)

            # Vocab loss for WRITE_FOCUS actions
            vocab_mask = batch_act[:, 0] == ActionType.WRITE_FOCUS.value
            if vocab_mask.any():
                vocab_targets = batch_act[vocab_mask, 25]
                vocab_logits = brain.get_vocab_logits(batch_obs, out['h_next'])

                if vocab_logits is not None:
                    loss = F.cross_entropy(vocab_logits[vocab_mask], vocab_targets.long())
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    total_loss += loss.item()
                    n_batches += 1

                    preds = vocab_logits[vocab_mask].argmax(dim=-1)
                    correct += (preds == vocab_targets).sum().item()
                    total += vocab_mask.sum().item()

        avg_loss = total_loss / max(1, n_batches)
        accuracy = correct / max(1, total)

        if accuracy > best_acc:
            best_acc = accuracy
        if avg_loss < best_loss:
            best_loss = avg_loss

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"  Epoch {epoch + 1}/{num_epochs}: Loss={avg_loss:.4f}, Acc={accuracy:.1%}")

    print(f"BC Training complete: Best Acc={best_acc:.1%}, Best Loss={best_loss:.4f}")
    return {'accuracy': best_acc, 'loss': best_loss}


def evaluate(
    brain: HeterogeneousBrain,
    difficulty: BugDifficulty,
    num_tasks: int,
    device: torch.device,
    max_steps: int = 50,
) -> Dict[str, float]:
    """Evaluate on generated tasks."""
    print(f"\n=== Evaluation ({num_tasks} tasks, difficulty={difficulty.name}) ===")

    brain.eval()

    # Generate tasks
    temp_base = tempfile.mkdtemp(prefix="phase8_eval_")
    try:
        gen = RepoGenerator(seed=123)  # Different seed from training
        repos = generate_task_batch(
            num_tasks=num_tasks,
            difficulty_range=(difficulty, difficulty),
            seed=123,
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

        config = HarnessConfig(
            obs_bytes=OBS_TOTAL_BYTES,
            action_bytes=ACTION_BYTES_V2,
            max_steps=max_steps,
            max_time_seconds=30,
            run_tests_on_reset=False,
            run_fast_tests=True,
            async_tests=True,
            force_write_focus=False,  # No forcing during eval!
            auto_focus_target=True,
        )
        env = JarvisHarnessEnv(config)

        solves = 0
        total_reward = 0.0
        total_energy = 0.0

        for task in tasks:
            env.set_task(task)
            obs = env.reset()

            h, g = brain.init_state(1, device)
            a_prev = torch.zeros(1, brain.action_bytes, dtype=torch.long, device=device)

            episode_reward = 0.0
            episode_energy = 0.0

            for step in range(max_steps):
                obs_t = obs.unsqueeze(0).to(device)

                with torch.no_grad():
                    out = brain(obs_t, h, g, a_prev, training=False)

                action = out['action'].clamp(0, 255).to(torch.uint8).squeeze(0).cpu()
                obs, reward, done, info = env.step(action)

                episode_reward += float(reward)
                episode_energy += out['energy'].item()

                h = out['h_next']
                g = out['g_t']
                a_prev = out['action']

                if done:
                    if info.get("done_reason") == "success":
                        solves += 1
                    break

            total_reward += episode_reward
            total_energy += episode_energy

        env.close()

        solve_rate = solves / len(tasks)
        avg_reward = total_reward / len(tasks)
        avg_energy = total_energy / len(tasks)

        print(f"  Solve rate: {solve_rate:.1%} ({solves}/{len(tasks)})")
        print(f"  Avg reward: {avg_reward:.2f}")
        print(f"  Avg energy: {avg_energy:.4f}")

        return {
            'solve_rate': solve_rate,
            'avg_reward': avg_reward,
            'avg_energy': avg_energy,
        }

    finally:
        shutil.rmtree(temp_base, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Phase 8: Heterogeneous Brain Training")
    parser.add_argument("--bc-epochs", type=int, default=50, help="BC pre-training epochs")
    parser.add_argument("--bc-tasks", type=int, default=200, help="Tasks for BC dataset")
    parser.add_argument("--eval-tasks", type=int, default=30, help="Tasks for evaluation")
    parser.add_argument("--difficulty", type=str, default="trivial",
                        choices=["trivial", "easy", "medium", "hard"])
    parser.add_argument("--use-optimal", action="store_true", default=True,
                        help="Use optimal structure from Optuna search")
    parser.add_argument("--use-default", action="store_true",
                        help="Use default heterogeneous regions")
    parser.add_argument("--use-uniform", action="store_true",
                        help="Use uniform (homogeneous) baseline")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = torch.device(args.device)
    difficulty_map = {
        "trivial": BugDifficulty.TRIVIAL,
        "easy": BugDifficulty.EASY,
        "medium": BugDifficulty.MEDIUM,
        "hard": BugDifficulty.HARD,
    }
    difficulty = difficulty_map[args.difficulty]

    print("=" * 60)
    print("PHASE 8: Heterogeneous Brain Training")
    print("=" * 60)
    print(f"Device: {device}")
    print(f"Difficulty: {args.difficulty}")
    print(f"BC: {args.bc_epochs} epochs, {args.bc_tasks} tasks")
    print(f"Eval: {args.eval_tasks} tasks")

    # Select regions
    if args.use_uniform:
        regions = [
            RegionConfig(name=f"uniform_{i}", width=128, sparsity=1.0, timescale=Timescale.FAST)
            for i in range(4)
        ]
        config_name = "uniform"
    elif args.use_default:
        regions = create_default_regions()
        config_name = "default"
    else:
        regions = create_optimal_regions()
        config_name = "optimal"

    print(f"\nConfiguration: {config_name}")
    print(f"Regions: {[r.name for r in regions]}")
    print(f"Total width: {sum(r.width for r in regions)}")

    # Create brain
    brain = HeterogeneousBrain(
        regions=regions,
        vocab_size=35,  # MEDIUM_VOCAB
    ).to(device)
    print(f"Parameters: {sum(p.numel() for p in brain.parameters()):,}")

    # BC Pre-training
    bc_metrics = train_bc(
        brain, difficulty, args.bc_tasks, args.bc_epochs, device
    )

    # Evaluation
    eval_metrics = evaluate(brain, difficulty, args.eval_tasks, device)

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Configuration: {config_name}")
    print(f"BC Accuracy: {bc_metrics['accuracy']:.1%}")
    print(f"Solve Rate: {eval_metrics['solve_rate']:.1%}")
    print(f"Avg Reward: {eval_metrics['avg_reward']:.2f}")
    print(f"Avg Energy: {eval_metrics['avg_energy']:.4f}")


if __name__ == "__main__":
    main()
