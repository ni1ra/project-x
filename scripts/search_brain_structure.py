#!/usr/bin/env python3
"""
Phase 8: Brain Structure Search using Optuna

Searches for optimal heterogeneous brain structure (number of regions,
their properties) using the harness training loop as the inner objective.

Usage:
  PYTHONPATH=. .venv/bin/python scripts/search_brain_structure.py \
    --n-trials 30 --timesteps-per-trial 5000 --difficulty trivial

Reference: paper.md Appendix K "The Heterogeneous Brain Insight"
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
import random
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import asdict

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    import optuna
    from optuna.trial import Trial
except ImportError:
    print("Optuna not installed. Run: pip install optuna")
    sys.exit(1)

from src.core.structural_plasticity import (
    RegionConfig,
    Timescale,
    HeterogeneousSubstrate,
    StructuralPlasticityConfig,
    StructuralPlasticity,
    create_default_regions,
    create_homogeneous_baseline,
)
from src.harness.env import JarvisHarnessEnv, HarnessConfig, Task, VectorizedJarvisEnv
from src.harness.repo_generator import RepoGenerator, BugDifficulty, generate_task_batch
from src.harness.observations import OBS_TOTAL_BYTES
from src.harness.actions import ACTION_BYTES_V2
from src.core.byte_interface import phi, AutoregressiveActionDecoder
from src.harness.expert_trajectories import create_online_oracle_bc_dataset
from src.harness.actions import ActionType


class HeterogeneousBrain(nn.Module):
    """
    A complete brain using the HeterogeneousSubstrate.

    Wraps the heterogeneous substrate with action decoder and training utilities.
    """

    def __init__(
        self,
        substrate: HeterogeneousSubstrate,
        action_bytes: int = 64,
        vocab_size: int = 35,
    ):
        super().__init__()
        self.substrate = substrate
        self.action_bytes = action_bytes

        # Action decoder (conditions on g_t)
        self.action_decoder = AutoregressiveActionDecoder(
            hidden_dim=substrate.total_hidden_dim,
            num_action_bytes=action_bytes,
            k_max=substrate.k_max,
            obs_dim=substrate.obs_dim,
            vocab_size=vocab_size,
        )

        # VAE for latent encoding (simplified for structure search)
        self.vae_encoder = nn.Sequential(
            nn.Linear(substrate.obs_dim, 128),
            nn.ReLU(),
            nn.Linear(128, substrate.latent_dim * 2),  # mu, logvar
        )

    def init_state(
        self,
        batch_size: int,
        device: torch.device,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Initialize hidden state and global scalars."""
        h = self.substrate.init_hidden(batch_size, device)
        g = self.substrate.init_global_scalars(batch_size, device)
        return h, g

    def encode(self, phi_obs: torch.Tensor) -> torch.Tensor:
        """Encode observation to latent."""
        params = self.vae_encoder(phi_obs)
        mu, logvar = params.chunk(2, dim=-1)
        std = torch.exp(0.5 * logvar)
        z = mu + std * torch.randn_like(std)
        return z

    def forward(
        self,
        obs_bytes: torch.Tensor,
        h_t: torch.Tensor,
        g_prev: torch.Tensor,
        a_prev: torch.Tensor,
        training: bool = True,
    ) -> Dict[str, torch.Tensor]:
        """Forward pass."""
        # Normalize observation
        phi_obs = phi(obs_bytes)

        # Encode to latent
        z_t = self.encode(phi_obs)

        # Substrate forward
        output = self.substrate(
            phi_obs=phi_obs,
            z_t=z_t,
            a_prev=a_prev,
            h_t=h_t,
            g_prev=g_prev,
            training=training,
        )

        # Generate action
        action, action_log_prob, action_mu = self.action_decoder(
            output['h_next'],
            g_t=output['g_t'],
            num_bytes=self.action_bytes,
            greedy=not training,
            phi_obs=phi_obs,
        )

        # Value estimate
        value = self.substrate.get_value(output['h_next'], output['g_t'])

        return {
            'action': action,
            'action_log_prob': action_log_prob,
            'h_next': output['h_next'],
            'g_t': output['g_t'],
            'value': value,
            'energy': self.substrate.compute_total_energy(output),
        }


def sample_brain_structure(trial: Trial) -> List[RegionConfig]:
    """Sample a brain structure using Optuna trial."""
    num_regions = trial.suggest_int("num_regions", 2, 5)

    regions = []
    for i in range(num_regions):
        p = f"r{i}_"

        config = RegionConfig(
            name=f"region_{i}",
            width=trial.suggest_int(f"{p}width", 32, 256, step=32),
            sparsity=trial.suggest_float(f"{p}sparsity", 0.3, 1.0),
            fan_in_cap=trial.suggest_int(f"{p}fan_in", 8, 64, step=8),
            fan_out_cap=trial.suggest_int(f"{p}fan_out", 8, 64, step=8),
            timescale=Timescale(
                trial.suggest_categorical(f"{p}timescale", ["fast", "medium", "slow"])
            ),
            fast_weight_rank=trial.suggest_int(f"{p}rank", 0, 32, step=8),
            activation_cost=trial.suggest_float(f"{p}cost", 0.005, 0.05),
        )
        regions.append(config)

    return regions


def evaluate_structure(
    regions: List[RegionConfig],
    difficulty: BugDifficulty,
    num_tasks: int,
    timesteps: int,
    seed: int,
    device: torch.device,
) -> Dict[str, float]:
    """
    Evaluate a brain structure on the harness.

    Returns metrics dict with 'reward', 'energy', 'solve_rate'.
    """
    # Create substrate
    substrate = HeterogeneousSubstrate(
        regions=regions,
        obs_dim=OBS_TOTAL_BYTES,
        latent_dim=64,
        action_bytes=ACTION_BYTES_V2,
    )

    # Create brain
    brain = HeterogeneousBrain(
        substrate=substrate,
        action_bytes=ACTION_BYTES_V2,
        vocab_size=35,  # MEDIUM_VOCAB for HARD
    ).to(device)

    # BC Pre-training (quick version for structure search)
    bc_dataset = create_online_oracle_bc_dataset(
        num_tasks=30,
        difficulty=difficulty,
        seed=seed,
        seq_len=3,
    )

    # Quick BC training
    from torch.optim import Adam
    optimizer = Adam(brain.parameters(), lr=1e-3)
    brain.train()

    obs_flat = bc_dataset['observations'].view(-1, OBS_TOTAL_BYTES).to(device)
    action_flat = bc_dataset['action_bytes'].view(-1, ACTION_BYTES_V2).to(device)
    masks = bc_dataset['masks'].view(-1)
    valid_idx = masks.nonzero(as_tuple=True)[0]
    obs_flat = obs_flat[valid_idx]
    action_flat = action_flat[valid_idx]

    bc_correct = 0
    bc_total = 0

    for epoch in range(20):  # Quick 20 epochs
        perm = torch.randperm(len(obs_flat))
        for i in range(0, len(perm), 32):
            batch_idx = perm[i:i+32]
            batch_obs = obs_flat[batch_idx]
            batch_act = action_flat[batch_idx]

            h, g = brain.init_state(len(batch_idx), device)
            a_prev = torch.zeros(len(batch_idx), ACTION_BYTES_V2, dtype=torch.long, device=device)

            out = brain(batch_obs, h, g, a_prev, training=True)

            # Vocab loss for WRITE_FOCUS
            vocab_mask = batch_act[:, 0] == ActionType.WRITE_FOCUS.value
            if vocab_mask.any():
                vocab_targets = batch_act[vocab_mask, 25]
                # Get vocab logits from action_decoder
                vocab_head = getattr(brain.action_decoder, 'vocab_head', None)
                if vocab_head is not None:
                    from src.harness.observations import TERMINAL_BYTES, GOAL_BYTES, FS_BYTES
                    phi_obs = phi(batch_obs)
                    goal_start = TERMINAL_BYTES + GOAL_BYTES
                    goal_dim = 64
                    focus_start = TERMINAL_BYTES + GOAL_BYTES
                    focus_dim = FS_BYTES
                    goal_bytes = phi_obs[:, goal_start:goal_start + goal_dim]
                    focus_text = phi_obs[:, focus_start:focus_start + focus_dim]
                    vocab_logits = vocab_head(out['h_next'], goal_bytes, focus_text)
                    loss = F.cross_entropy(vocab_logits[vocab_mask], vocab_targets.long())
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()

                    # Track accuracy on last epoch
                    if epoch == 19:
                        preds = vocab_logits[vocab_mask].argmax(dim=-1)
                        bc_correct += (preds == vocab_targets).sum().item()
                        bc_total += vocab_mask.sum().item()

    bc_accuracy = bc_correct / max(1, bc_total)
    brain.eval()

    # Generate tasks
    temp_base = tempfile.mkdtemp(prefix="struct_search_")
    try:
        gen = RepoGenerator(seed=seed)
        repos = generate_task_batch(
            num_tasks=num_tasks,
            difficulty_range=(difficulty, difficulty),
            seed=seed,
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

        # Create environment
        config = HarnessConfig(
            obs_bytes=OBS_TOTAL_BYTES,
            action_bytes=ACTION_BYTES_V2,
            max_steps=50,  # Shorter episodes for search
            max_time_seconds=30,
            run_tests_on_reset=False,
            run_fast_tests=True,
            async_tests=True,
            force_write_focus=True,
        )
        env = JarvisHarnessEnv(config)

        # Run episodes
        total_reward = 0.0
        total_energy = 0.0
        solves = 0

        for task in tasks:
            env.set_task(task)
            obs = env.reset()

            h, g = brain.init_state(1, device)
            a_prev = torch.zeros(1, ACTION_BYTES_V2, dtype=torch.long, device=device)

            episode_reward = 0.0
            episode_energy = 0.0

            for step in range(config.max_steps):
                obs_t = obs.unsqueeze(0).to(device)

                with torch.no_grad():
                    out = brain(obs_t, h, g, a_prev, training=False)

                action_bytes = out['action'].clamp(0, 255).to(torch.uint8).squeeze(0).cpu()
                obs, reward, done, info = env.step(action_bytes)

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

        # Compute metrics
        avg_reward = total_reward / len(tasks)
        avg_energy = total_energy / len(tasks)
        solve_rate = solves / len(tasks)

        return {
            'reward': avg_reward,
            'energy': avg_energy,
            'solve_rate': solve_rate,
            'bc_accuracy': bc_accuracy,
            'num_params': sum(p.numel() for p in brain.parameters()),
        }

    finally:
        shutil.rmtree(temp_base, ignore_errors=True)


def create_objective(
    difficulty: BugDifficulty,
    num_tasks: int,
    timesteps: int,
    seed: int,
    device: torch.device,
):
    """Create Optuna objective function."""

    def objective(trial: Trial) -> float:
        # Sample structure
        regions = sample_brain_structure(trial)

        # Log structure info
        total_width = sum(r.width for r in regions)
        trial.set_user_attr("num_regions", len(regions))
        trial.set_user_attr("total_width", total_width)

        # Evaluate
        metrics = evaluate_structure(
            regions=regions,
            difficulty=difficulty,
            num_tasks=num_tasks,
            timesteps=timesteps,
            seed=seed + trial.number,  # Different seed per trial
            device=device,
        )

        # Log metrics
        trial.set_user_attr("solve_rate", metrics['solve_rate'])
        trial.set_user_attr("bc_accuracy", metrics['bc_accuracy'])
        trial.set_user_attr("num_params", metrics['num_params'])

        # Objective: BC accuracy + solve_rate - energy (RPJ principle)
        # BC accuracy is primary metric for structure search since eval needs full RL
        score = 100.0 * metrics['bc_accuracy'] + 10.0 * metrics['solve_rate'] - 0.1 * metrics['energy']
        return score

    return objective


def run_baseline_comparison(
    difficulty: BugDifficulty,
    num_tasks: int,
    timesteps: int,
    seed: int,
    device: torch.device,
) -> Dict[str, float]:
    """Run homogeneous baseline for comparison."""
    print("\n--- Running Homogeneous Baseline ---")

    baseline = create_homogeneous_baseline(
        total_hidden=512,
        num_regions=4,
        obs_dim=OBS_TOTAL_BYTES,
        latent_dim=64,
        action_bytes=ACTION_BYTES_V2,
    )

    # Convert to RegionConfig list
    regions = [
        RegionConfig(
            name=f"region_{i}",
            width=128,
            sparsity=1.0,
            timescale=Timescale.FAST,
        )
        for i in range(4)
    ]

    metrics = evaluate_structure(
        regions=regions,
        difficulty=difficulty,
        num_tasks=num_tasks,
        timesteps=timesteps,
        seed=seed,
        device=device,
    )

    print(f"Baseline results:")
    print(f"  BC Accuracy: {metrics['bc_accuracy']:.1%}")
    print(f"  Reward: {metrics['reward']:.2f}")
    print(f"  Energy: {metrics['energy']:.4f}")
    print(f"  Solve rate: {metrics['solve_rate']:.1%}")
    print(f"  Params: {metrics['num_params']:,}")

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Phase 8: Brain Structure Search")
    parser.add_argument("--n-trials", type=int, default=30, help="Number of Optuna trials")
    parser.add_argument("--timesteps-per-trial", type=int, default=5000, help="Timesteps per trial")
    parser.add_argument("--num-tasks", type=int, default=10, help="Tasks per evaluation")
    parser.add_argument("--difficulty", type=str, default="trivial",
                        choices=["trivial", "easy", "medium", "hard"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--study-name", type=str, default="jarvis_phase8_structure")
    parser.add_argument("--output", type=str, default="results/phase8_structure_search.json")
    parser.add_argument("--skip-baseline", action="store_true", help="Skip baseline comparison")
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
    print("PHASE 8: Brain Structure Search")
    print("=" * 60)
    print(f"Trials: {args.n_trials}")
    print(f"Timesteps/trial: {args.timesteps_per_trial}")
    print(f"Tasks/eval: {args.num_tasks}")
    print(f"Difficulty: {args.difficulty}")
    print(f"Device: {device}")
    print()

    # Run baseline first
    baseline_metrics = None
    if not args.skip_baseline:
        baseline_metrics = run_baseline_comparison(
            difficulty=difficulty,
            num_tasks=args.num_tasks,
            timesteps=args.timesteps_per_trial,
            seed=args.seed,
            device=device,
        )

    # Create Optuna study
    print("\n--- Running Structure Search ---")
    study = optuna.create_study(
        study_name=args.study_name,
        direction="maximize",
    )

    objective = create_objective(
        difficulty=difficulty,
        num_tasks=args.num_tasks,
        timesteps=args.timesteps_per_trial,
        seed=args.seed,
        device=device,
    )

    study.optimize(objective, n_trials=args.n_trials, show_progress_bar=True)

    # Extract best structure
    best_trial = study.best_trial
    best_params = best_trial.params
    num_regions = best_params["num_regions"]

    best_regions = []
    for i in range(num_regions):
        p = f"r{i}_"
        config = RegionConfig(
            name=f"region_{i}",
            width=best_params[f"{p}width"],
            sparsity=best_params[f"{p}sparsity"],
            fan_in_cap=best_params[f"{p}fan_in"],
            fan_out_cap=best_params[f"{p}fan_out"],
            timescale=Timescale(best_params[f"{p}timescale"]),
            fast_weight_rank=best_params[f"{p}rank"],
            activation_cost=best_params[f"{p}cost"],
        )
        best_regions.append(config)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nBest trial: #{best_trial.number}")
    print(f"Best score: {best_trial.value:.4f}")
    print(f"BC Accuracy: {best_trial.user_attrs.get('bc_accuracy', 0):.1%}")
    print(f"Solve rate: {best_trial.user_attrs.get('solve_rate', 0):.1%}")
    print(f"\nBest structure ({num_regions} regions):")
    for r in best_regions:
        print(f"  - {r.name}: width={r.width}, sparsity={r.sparsity:.2f}, "
              f"timescale={r.timescale.value}, rank={r.fast_weight_rank}")

    # Compare with baseline
    if baseline_metrics:
        baseline_score = (baseline_metrics['reward'] +
                         10.0 * baseline_metrics['solve_rate'] -
                         0.1 * baseline_metrics['energy'])
        improvement = (best_trial.value - baseline_score) / abs(baseline_score) * 100
        print(f"\nBaseline score: {baseline_score:.4f}")
        print(f"Improvement: {improvement:+.1f}%")

    # Save results
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    results = {
        "timestamp": datetime.now().isoformat(),
        "args": vars(args),
        "best_score": best_trial.value,
        "best_regions": [asdict(r) for r in best_regions],
        "best_params": best_params,
        "best_user_attrs": best_trial.user_attrs,
        "baseline_metrics": baseline_metrics,
        "all_trials": [
            {
                "number": t.number,
                "value": t.value,
                "params": t.params,
                "user_attrs": t.user_attrs,
            }
            for t in study.trials
        ],
    }

    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
