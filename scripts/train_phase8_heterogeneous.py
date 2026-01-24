#!/usr/bin/env python3
"""
Phase 8: Heterogeneous Brain Training

Trains the HeterogeneousBrain with optimal structure found by Optuna search.
Uses full BC pre-training + RL fine-tuning pipeline.

PHASE 8 FIX (2026-01-24): Added entropy regularization and proper BC training
to prevent action collapse. Original version only trained vocab loss (byte 25),
not action type (byte 0), causing 0% solve rate. Now trains ALL important bytes.

Usage:
  PYTHONPATH=. .venv/bin/python scripts/train_phase8_heterogeneous.py \
    --bc-epochs 50 --difficulty easy --entropy-coef 0.2

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
from typing import Dict, Any, List, Tuple, Optional

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
from src.harness.expert_trajectories import create_sequential_bc_dataset


class HeterogeneousBrain(nn.Module):
    """
    Heterogeneous brain with optimized structure for JARVIS harness.

    Uses the HeterogeneousSubstrate with AutoregressiveActionDecoder.

    Phase 8 Fix: Added evaluate_actions() method for proper BC training
    with entropy regularization to prevent action collapse.
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
        self.vocab_size = vocab_size

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
            'phi_obs': phi_obs,
        }

    def evaluate_actions(
        self,
        obs_bytes: torch.Tensor,
        prev_h: torch.Tensor,
        prev_g: torch.Tensor,
        prev_a: torch.Tensor,
        actions: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Evaluate actions by re-running forward pass with gradients.

        Phase 8 Fix: This is critical for proper BC training. Without this,
        the heterogeneous model suffered action collapse (0% solve rate).

        Returns:
            log_probs: Log prob of actions [batch, action_bytes]
            entropy: Action distribution entropy [batch]
            values: Value estimates [batch]
            g_t: Global scalars [batch, k_max]
            h_next: New hidden state [batch, hidden_dim]
        """
        phi_obs = phi(obs_bytes)
        z_t = self.encode(phi_obs)

        output = self.substrate(
            phi_obs=phi_obs,
            z_t=z_t,
            a_prev=prev_a,
            h_t=prev_h,
            g_prev=prev_g,
            training=True,
        )

        h_next = output['h_next']
        g_t = output['g_t']

        # Get value estimate
        values = self.substrate.get_value(h_next, g_t)

        # Get log probs for all action bytes
        log_probs = self.action_decoder.get_log_prob(
            h_next, actions, g_t, phi_obs
        )

        # Get entropy for regularization
        entropy = self.action_decoder.get_entropy(
            h_next, self.action_bytes, g_t, phi_obs
        )

        return log_probs, entropy, values, g_t, h_next

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


def train_bc_sequential(
    brain: HeterogeneousBrain,
    difficulty: BugDifficulty,
    num_tasks: int,
    num_epochs: int,
    device: torch.device,
    entropy_coef: float = 0.01,  # Lower entropy coef - let BC signal dominate
    lr: float = 1e-3,
    batch_size: int = 32,  # Number of trajectories per batch
) -> Dict[str, float]:
    """
    SEQUENTIAL BC pre-training for RNNs.

    CRITICAL FIX (Phase 8): The original BC training shuffled samples and used fresh
    h_t for every batch. This meant the model never learned to use its GRU memory
    to track position in the 4-step loop (RUN_TESTS -> WRITE_FOCUS -> RUN_TESTS -> COMPLETE).

    This version processes complete trajectories sequentially, maintaining hidden state
    across steps. This is essential for RNN-based policies.

    Reference: MISTAKES.md L100 "Train/Eval Mismatch Pattern"
    """
    print(f"\n=== SEQUENTIAL BC Pre-training ===")
    print(f"  Epochs: {num_epochs}, Tasks: {num_tasks}")
    print(f"  Entropy coef: {entropy_coef}, LR: {lr}")
    print(f"  Batch size: {batch_size} trajectories")

    # Generate dataset - KEEP TRAJECTORY STRUCTURE
    seq_len = 4  # 4 steps for EASY: RUN_TESTS -> WRITE_FOCUS -> RUN_TESTS -> COMPLETE
    dataset = create_sequential_bc_dataset(
        num_tasks=num_tasks,
        difficulty=difficulty,
        seed=42,
        seq_len=seq_len,
    )

    num_traj = dataset['num_trajectories']
    print(f"Generated {num_traj} trajectories")
    print(f"  WRITE_FOCUS: {dataset['num_write_focus']}, RUN_TESTS: {dataset['num_run_tests']}")
    print(f"  COMPLETE_TASK: {dataset['num_complete_task']}")

    # Move data to device - PRESERVE TRAJECTORY STRUCTURE [num_traj, seq_len, ...]
    observations = dataset['observations'].to(device)  # [N, S, 512]
    action_bytes = dataset['action_bytes'].to(device).long()  # [N, S, 64]
    masks = dataset['masks'].to(device)  # [N, S]

    optimizer = Adam(brain.parameters(), lr=lr)
    brain.train()

    best_loss = float('inf')
    best_accuracy = 0.0

    for epoch in range(num_epochs):
        # Shuffle TRAJECTORY order (not steps within trajectory!)
        perm = torch.randperm(num_traj, device=device)
        epoch_losses = []
        epoch_correct_type = 0
        epoch_total_steps = 0
        epoch_vocab_correct = 0
        epoch_vocab_total = 0

        for start in range(0, num_traj, batch_size):
            end = min(start + batch_size, num_traj)
            batch_idx = perm[start:end]
            curr_batch_size = len(batch_idx)

            # Get batch: [batch_size, seq_len, ...]
            obs_seq = observations[batch_idx]  # [B, S, 512]
            action_seq = action_bytes[batch_idx]  # [B, S, 64]
            mask_seq = masks[batch_idx]  # [B, S]

            # Initialize hidden state ONCE per trajectory
            h, g = brain.init_state(curr_batch_size, device)
            a_prev = torch.zeros(curr_batch_size, brain.action_bytes, dtype=torch.long, device=device)

            # Process sequence step by step, MAINTAINING hidden state
            batch_loss = 0.0
            batch_steps = 0

            for step in range(seq_len):
                # Get this step's data
                obs_step = obs_seq[:, step]  # [B, 512]
                target_action = action_seq[:, step]  # [B, 64]
                step_mask = mask_seq[:, step]  # [B]

                if not step_mask.any():
                    continue

                # Save pre-update state (matches evaluation behavior)
                h_before = h.clone()
                g_before = g.clone()
                a_prev_before = a_prev.clone()

                # Forward pass to get h_next for state update
                output = brain(obs_step, h, g, a_prev, training=True)

                # Update hidden state for NEXT step (critical for sequential processing)
                h = output['h_next'].detach()
                g = output['g_t'].detach()
                a_prev = output['action'].long().detach()

                # Compute loss using PRE-update state (action was selected based on h_before)
                log_probs, entropy, values, _, _ = brain.evaluate_actions(
                    obs_step, h_before, g_before, a_prev_before, target_action
                )

                # Mask to only valid steps
                valid_log_probs = log_probs[step_mask]
                valid_targets = target_action[step_mask]
                valid_entropy = entropy[step_mask]

                if len(valid_log_probs) == 0:
                    continue

                # BC loss: negative log likelihood of correct actions
                # Weight action type (byte 0) most heavily since it determines WRITE_FOCUS vs RUN_TESTS
                action_type_log_prob = valid_log_probs[:, 0]
                offset_log_prob = valid_log_probs[:, 1]
                length_log_prob = valid_log_probs[:, 3]
                vocab_log_prob = valid_log_probs[:, 25]
                vocab_mode_log_prob = valid_log_probs[:, 26]

                step_bc_loss = -(
                    3.0 * action_type_log_prob +
                    2.0 * offset_log_prob +
                    1.0 * vocab_log_prob +
                    1.0 * vocab_mode_log_prob +
                    0.5 * length_log_prob
                ).mean()

                # CRITICAL: Direct vocab classification loss for WRITE_FOCUS
                # The autoregressive log_probs alone don't train vocab_head well
                # FIX: Use h_next (post-update state) to match evaluation behavior!
                # During eval, brain.forward() passes h_next to action_decoder for vocab
                vocab_write_mask = valid_targets[:, 0] == ActionType.WRITE_FOCUS.value
                if vocab_write_mask.any():
                    vocab_targets = valid_targets[vocab_write_mask, 25]
                    # Use h_next (output) instead of h_before to match evaluation
                    h_for_vocab = output['h_next'][step_mask]
                    vocab_logits = brain.get_vocab_logits(obs_step[step_mask], h_for_vocab)
                    if vocab_logits is not None and vocab_logits[vocab_write_mask].shape[0] > 0:
                        vocab_class_loss = F.cross_entropy(
                            vocab_logits[vocab_write_mask],
                            vocab_targets.long().clamp(0, brain.vocab_size - 1)
                        )
                        # Strong weight on vocab loss to overcome bias
                        step_bc_loss = step_bc_loss + 5.0 * vocab_class_loss

                        # Track vocab accuracy during training
                        with torch.no_grad():
                            pred_vocab = vocab_logits[vocab_write_mask].argmax(dim=-1)
                            epoch_vocab_correct += (pred_vocab == vocab_targets).sum().item()
                            epoch_vocab_total += vocab_write_mask.sum().item()

                # Entropy regularization (lower coef for sequential training)
                step_entropy = valid_entropy.mean()
                step_loss = step_bc_loss - entropy_coef * step_entropy

                batch_loss += step_loss
                batch_steps += 1

                # Track action type accuracy
                with torch.no_grad():
                    # Get predicted action type from forward pass
                    pred_types = output['action'][step_mask, 0]
                    correct = (pred_types == valid_targets[:, 0]).sum().item()
                    epoch_correct_type += correct
                    epoch_total_steps += step_mask.sum().item()

            if batch_steps > 0:
                # Average loss across steps in trajectory
                avg_batch_loss = batch_loss / batch_steps

                optimizer.zero_grad()
                avg_batch_loss.backward()
                nn.utils.clip_grad_norm_(brain.parameters(), 1.0)
                optimizer.step()

                epoch_losses.append(avg_batch_loss.item())

        # Epoch metrics
        avg_loss = sum(epoch_losses) / max(1, len(epoch_losses))
        accuracy = epoch_correct_type / max(1, epoch_total_steps)
        vocab_accuracy = epoch_vocab_correct / max(1, epoch_vocab_total)

        if avg_loss < best_loss:
            best_loss = avg_loss
        if accuracy > best_accuracy:
            best_accuracy = accuracy

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"  Epoch {epoch + 1}/{num_epochs}: Loss={avg_loss:.4f}, TypeAcc={accuracy:.1%}, VocabAcc={vocab_accuracy:.1%}")

    print(f"\nSequential BC Training complete:")
    print(f"  Best Loss: {best_loss:.4f}")
    print(f"  Best Type Accuracy: {best_accuracy:.1%}")

    return {'accuracy': best_accuracy, 'loss': best_loss, 'entropy': 0.0}


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
            force_write_focus=False,
            auto_focus_target=True,
        )
        env = JarvisHarnessEnv(config)

        solves = 0
        total_reward = 0.0
        total_energy = 0.0
        action_counts = {}
        vocab_predictions = []  # Track vocab byte predictions

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
                action_type = action[0].item()
                action_counts[action_type] = action_counts.get(action_type, 0) + 1

                # Track vocab predictions for WRITE_FOCUS
                if action_type == ActionType.WRITE_FOCUS.value:
                    vocab_idx = action[25].item()
                    vocab_mode = action[26].item()
                    vocab_predictions.append((vocab_idx, vocab_mode))

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
        print(f"  Action distribution: {action_counts}")

        # Show vocab distribution for WRITE_FOCUS
        if vocab_predictions:
            from collections import Counter
            vocab_counts = Counter([v[0] for v in vocab_predictions])
            print(f"  Vocab distribution (byte 25): {dict(vocab_counts.most_common(10))}")

        return {
            'solve_rate': solve_rate,
            'avg_reward': avg_reward,
            'avg_energy': avg_energy,
            'action_counts': action_counts,
        }

    finally:
        shutil.rmtree(temp_base, ignore_errors=True)


def create_larger_optimal_regions() -> List[RegionConfig]:
    """
    Create larger heterogeneous regions (512 total width).

    Phase 8 Fix 2: Original optimal regions had 384 total width,
    which may have reduced representational capacity below threshold.
    This version has 512 total width (same as homogeneous baseline).
    """
    return [
        RegionConfig(
            name="fast_perception",
            width=128,  # Was 96
            sparsity=0.74,
            fan_in_cap=40,
            fan_out_cap=16,
            timescale=Timescale.FAST,
            fast_weight_rank=24,
            activation_cost=0.036,
        ),
        RegionConfig(
            name="slow_memory",
            width=320,  # Was 224
            sparsity=0.48,
            fan_in_cap=16,
            fan_out_cap=64,
            timescale=Timescale.SLOW,
            fast_weight_rank=0,
            activation_cost=0.016,
        ),
        RegionConfig(
            name="fast_execution",
            width=64,  # Same
            sparsity=0.80,
            fan_in_cap=8,
            fan_out_cap=8,
            timescale=Timescale.FAST,
            fast_weight_rank=16,
            activation_cost=0.039,
        ),
    ]


def main():
    parser = argparse.ArgumentParser(description="Phase 8: Heterogeneous Brain Training")
    parser.add_argument("--bc-epochs", type=int, default=50, help="BC pre-training epochs")
    parser.add_argument("--bc-tasks", type=int, default=200, help="Tasks for BC dataset")
    parser.add_argument("--eval-tasks", type=int, default=30, help="Tasks for evaluation")
    parser.add_argument("--difficulty", type=str, default="easy",
                        choices=["trivial", "easy", "medium", "hard"])
    parser.add_argument("--use-optimal", action="store_true",
                        help="Use optimal structure from Optuna search (384 width)")
    parser.add_argument("--use-larger", action="store_true", default=True,
                        help="Use larger heterogeneous regions (512 width)")
    parser.add_argument("--use-default", action="store_true",
                        help="Use default heterogeneous regions")
    parser.add_argument("--use-uniform", action="store_true",
                        help="Use uniform (homogeneous) baseline")
    parser.add_argument("--entropy-coef", type=float, default=0.01,
                        help="Entropy coefficient (lower for sequential BC)")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save", type=str, default=None, help="Save checkpoint path")
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
    print("PHASE 8: Heterogeneous Brain Training with Entropy Fix")
    print("=" * 60)
    print(f"Device: {device}")
    print(f"Difficulty: {args.difficulty}")
    print(f"BC: {args.bc_epochs} epochs, {args.bc_tasks} tasks")
    print(f"Eval: {args.eval_tasks} tasks")
    print(f"Entropy coef: {args.entropy_coef}")

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
    elif args.use_optimal:
        regions = create_optimal_regions()
        config_name = "optimal"
    else:  # use_larger (default)
        regions = create_larger_optimal_regions()
        config_name = "larger_optimal"

    total_width = sum(r.width for r in regions)
    print(f"\nConfiguration: {config_name}")
    print(f"Regions: {[(r.name, r.width) for r in regions]}")
    print(f"Total width: {total_width}")

    # Create brain
    brain = HeterogeneousBrain(
        regions=regions,
        vocab_size=35,
    ).to(device)
    print(f"Parameters: {sum(p.numel() for p in brain.parameters()):,}")

    # Debug: verify vocab_head exists
    if hasattr(brain.action_decoder, 'vocab_head') and brain.action_decoder.vocab_head is not None:
        print(f"  Vocab head: ACTIVE (size={brain.action_decoder.vocab_size})")
    else:
        print(f"  Vocab head: MISSING (this will cause bad vocab predictions!)")

    # BC Pre-training with SEQUENTIAL processing (CRITICAL for RNNs)
    bc_metrics = train_bc_sequential(
        brain, difficulty, args.bc_tasks, args.bc_epochs, device,
        entropy_coef=args.entropy_coef, lr=args.lr, batch_size=32
    )

    # Evaluation
    eval_metrics = evaluate(brain, difficulty, args.eval_tasks, device)

    # Save checkpoint if requested
    if args.save:
        checkpoint = {
            "brain_state_dict": brain.state_dict(),
            "config_name": config_name,
            "regions": [(r.name, r.width, r.sparsity, r.timescale.value) for r in regions],
            "bc_metrics": bc_metrics,
            "eval_metrics": eval_metrics,
            "args": vars(args),
        }
        torch.save(checkpoint, args.save)
        print(f"\nSaved checkpoint to: {args.save}")

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Configuration: {config_name} (width={total_width})")
    print(f"BC Loss: {bc_metrics['loss']:.4f}")
    print(f"BC Vocab Accuracy: {bc_metrics['accuracy']:.1%}")
    print(f"BC Entropy: {bc_metrics['entropy']:.4f}")
    print(f"Solve Rate: {eval_metrics['solve_rate']:.1%}")
    print(f"Avg Reward: {eval_metrics['avg_reward']:.2f}")
    print(f"Avg Energy: {eval_metrics['avg_energy']:.4f}")

    # Phase 8 success criteria
    if eval_metrics['solve_rate'] > 0.75:
        print("\n SUCCESS: Heterogeneous brain exceeds 75% solve rate!")
    elif eval_metrics['solve_rate'] > 0.5:
        print("\n PROGRESS: Heterogeneous brain >50% (better than 0% collapse)")
    else:
        print("\n NEEDS WORK: Solve rate below 50%")


if __name__ == "__main__":
    main()
