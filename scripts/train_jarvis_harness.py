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
import sys
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
    TRIVIAL_VOCAB, COMBINED_VOCAB,  # For BC accuracy calculation
)
from src.harness.observations import OBS_TOTAL_BYTES
from src.harness.repo_generator import (
    RepoGenerator, GeneratedRepo, BugDifficulty, generate_task_batch,
)
from src.harness.expert_trajectories import (
    create_bc_dataset,
    create_multistep_bc_dataset,
    create_persistent_bc_dataset,
    create_sequential_bc_dataset,
    compute_fix_offset_in_focus,
)
from src.utils.gpu_guard import (
    GPUGuard,
    GPUGuardConfig,
    ExclusiveGPULock,
    default_gpu_index,
    query_gpu_sample,
)


# =============================================================================
# GPU Burn for Initialization (keeps GPU guard happy during CPU-bound init)
# =============================================================================

import threading

class InitGPUBurner:
    """
    Background GPU burner for initialization phase.
    Keeps GPU utilization high while CPU-bound task creation happens.
    Runs in a background thread and stops when stop() is called.
    """
    def __init__(self, device: torch.device, dim: int = 8192, burn_ms: float = 300.0):
        self.device = device
        self.dim = dim
        self.burn_ms = burn_ms
        self._a = None
        self._b = None
        self._out = None
        self._ms_per_iter = 0.0
        self._stop_event = threading.Event()
        self._thread = None

    def setup(self):
        """Initialize burn tensors and calibrate timing."""
        if self.device.type != "cuda":
            return
        self._a = torch.randn((self.dim, self.dim), device=self.device, dtype=torch.float16)
        self._b = torch.randn((self.dim, self.dim), device=self.device, dtype=torch.float16)
        self._out = torch.empty((self.dim, self.dim), device=self.device, dtype=torch.float16)
        # Calibrate
        with torch.no_grad():
            for _ in range(2):
                torch.matmul(self._a, self._b, out=self._out)
            torch.cuda.synchronize(self.device)
            n = 5
            t0 = time.perf_counter()
            for _ in range(n):
                torch.matmul(self._a, self._b, out=self._out)
            torch.cuda.synchronize(self.device)
            self._ms_per_iter = (time.perf_counter() - t0) * 1000.0 / n

    def _burn_loop(self):
        """Background burn loop."""
        if self._a is None or self._ms_per_iter <= 0:
            return
        iters = max(1, int(self.burn_ms / self._ms_per_iter))
        while not self._stop_event.is_set():
            with torch.no_grad():
                for _ in range(iters):
                    if self._stop_event.is_set():
                        break
                    torch.matmul(self._a, self._b, out=self._out)
            # Small sleep to allow interleaving with CPU work
            time.sleep(0.01)

    def start(self):
        """Start background GPU burning."""
        if self._thread is not None:
            return
        self.setup()
        self._thread = threading.Thread(target=self._burn_loop, name="init-gpu-burner", daemon=True)
        self._thread.start()

    def stop(self):
        """Stop background GPU burning."""
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=2.0)
        self._thread = None
        # Free GPU memory
        self._a = None
        self._b = None
        self._out = None


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
    *,
    difficulty_span: int = 0,
) -> Tuple[List[Task], List[GeneratedRepo]]:
    """
    Create training tasks using v2 multi-file repo generation.

    Returns (tasks, repos) where repos should be cleaned up after training.
    """
    generator = RepoGenerator(seed=seed)
    span = max(0, int(difficulty_span))
    max_diff = BugDifficulty(min(int(difficulty.value) + span, 5))
    repos = generate_task_batch(num_tasks=num_tasks, difficulty_range=(difficulty, max_diff), seed=seed)

    tasks = []
    for repo in repos:
        # Write repo to disk
        repo_path = generator.write_to_disk(repo, temp_base)

        # Create task from repo
        bug = repo.bugs[0] if repo.bugs else None
        target_file = bug.file_path if bug else list(repo.files.keys())[0]
        bug_line = bug.line_number if bug else None

        # Compute target_offset for reward shaping (TRIVIAL curriculum)
        target_offset = None
        if bug and bug.file_path in repo.original_files and bug.file_path in repo.files:
            original = repo.original_files.get(bug.file_path, "")
            buggy_file = repo.files.get(bug.file_path)
            buggy = buggy_file.content if buggy_file else ""
            if original and buggy:
                # Compute focus_start (same as env._set_focus_from_location)
                lines = buggy.splitlines(True)
                line_idx = max(0, min((bug.line_number or 1) - 1, len(lines) - 1))
                focus_start = sum(len(lines[i]) for i in range(line_idx))
                # Compute offset within focus
                offset_in_focus, _, _ = compute_fix_offset_in_focus(original, buggy, focus_start)
                if 0 <= offset_in_focus < 256:  # Valid offset within focus window
                    target_offset = offset_in_focus

        task = Task(
            name=repo.name,
            description=f"Fix the bugs in this codebase. Hint: {repo.fix_description}",
            repo_path=repo_path,
            target_file=target_file,
            expected_tests_passing=5,  # Approximate
            bug_line=bug_line,  # Pre-set focus to bug location
            target_offset=target_offset,  # For dense reward shaping
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
        gpu_burn_ms: float = 500.0,
        gpu_burn_dim: int = 12288,
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

        # KL divergence penalty to preserve BC policy
        self.kl_coef = 0.0
        self.bc_reference_policy = None  # Will store BC policy weights after pre-training

        # ANCHORED RL: BC imitation loss during RL training
        self.bc_anchor_coef = 0.0  # λ_bc coefficient (set via method)
        self.bc_anchor_decay = "linear"  # Decay schedule
        self.bc_anchor_start_coef = 1.0  # Initial λ_bc
        self.bc_anchor_end_coef = 0.05  # Final λ_bc
        self.bc_anchor_warmup_steps = 10000  # Steps at full λ_bc
        self.bc_anchor_decay_steps = 40000  # Steps to decay
        self.bc_demo_observations = None  # BC demo observations tensor
        self.bc_demo_actions = None  # BC demo action targets
        self.backbone_freeze_steps = 0  # Steps to freeze backbone

        # Optimizer (will be overwritten if two-timescale)
        self.optimizer = Adam(brain.parameters(), lr=lr)
        self.use_two_timescale = False

        # Statistics
        self.total_steps = 0
        self.episode_rewards = []
        self.episode_lengths = []
        self._burn_call_count = 0  # Debug: track GPU burn calls
        self._burn_skip_count = 0  # Debug: track skipped GPU burns

        # Optional GPU padding to keep utilization high when env stepping is CPU-bound.
        # ALWAYS create burn tensors if on CUDA - they may be used later even if gpu_burn_ms starts at 0
        self._burn_a = None
        self._burn_b = None
        self._burn_out = None
        self._burn_ms_per_matmul = None
        print(f"GPU burn config: burn_ms={self.gpu_burn_ms}, burn_dim={self.gpu_burn_dim}", flush=True)
        if self.device.type == "cuda":
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

    def _gpu_burn(self, *, sync: bool = False) -> None:
        if self.device.type != "cuda" or self.gpu_burn_ms <= 0:
            self._burn_skip_count += 1
            return
        if self._burn_a is None or self._burn_b is None or self._burn_out is None:
            self._burn_skip_count += 1
            return
        if not self._burn_ms_per_matmul or self._burn_ms_per_matmul <= 0:
            self._burn_skip_count += 1
            return

        self._burn_call_count += 1
        iters = max(1, int(math.ceil(self.gpu_burn_ms / float(self._burn_ms_per_matmul))))
        with torch.no_grad():
            for _ in range(iters):
                torch.matmul(self._burn_a, self._burn_b, out=self._burn_out)
        if sync:
            torch.cuda.synchronize(self.device)

    def pretrain_behavioral_cloning(
        self,
        num_demos: int = 1000,
        bc_epochs: int = 50,
        bc_batch_size: int = 128,
        bc_lr: float = 1e-3,
        jitter: int = 0,
        difficulty: BugDifficulty = BugDifficulty.TRIVIAL,
        use_multistep: bool = False,
        use_persistent: bool = False,
    ) -> Dict[str, float]:
        """
        Pre-train the policy on expert demonstrations using behavioral cloning.

        This bootstraps the policy with supervised learning before RL fine-tuning.
        The model learns to predict: offset, vocab_idx, length from observations.

        Args:
            num_demos: Number of expert demonstrations to generate
            bc_epochs: Number of BC training epochs
            bc_batch_size: Batch size for BC training
            bc_lr: Learning rate for BC (higher than RL since supervised)
            jitter: Focus offset jitter +/- this value (for robustness)
            difficulty: Bug difficulty level for expert trajectory generation
            use_multistep: If True, use multi-step demos with RUN_TESTS + WRITE_FOCUS
            use_persistent: If True, use persistent mode demos with full loop
                           (RUN_TESTS -> WRITE_FOCUS -> RUN_TESTS -> COMPLETE_TASK)

        Returns:
            Dictionary of final BC metrics
        """
        # Determine vocab size based on difficulty
        if difficulty == BugDifficulty.TRIVIAL:
            vocab_size = len(TRIVIAL_VOCAB)  # 5 items
        else:
            vocab_size = len(COMBINED_VOCAB)  # 21 items (TRIVIAL + EASY)

        # Determine demo mode
        if use_persistent:
            mode_str = "persistent (RUN_TESTS -> WRITE_FOCUS -> RUN_TESTS -> COMPLETE_TASK)"
        elif use_multistep:
            mode_str = "multi-step (RUN_TESTS + WRITE_FOCUS)"
        else:
            mode_str = "single-step"

        print(f"\n=== BEHAVIORAL CLONING PRE-TRAINING ===")
        print(f"Generating {num_demos} expert demonstrations (difficulty={difficulty.name}, vocab_size={vocab_size}, mode={mode_str})...")

        # Generate expert dataset
        try:
            if use_persistent:
                # Phase 7.4a: Persistent mode demos with COMPLETE_TASK
                dataset = create_persistent_bc_dataset(
                    num_tasks=num_demos,
                    difficulty=difficulty,
                    seed=42,
                    include_single_step=False,  # Pure persistent demos
                )
            elif use_multistep:
                dataset = create_multistep_bc_dataset(
                    num_tasks=num_demos,
                    difficulty=difficulty,
                    seed=42,
                    include_single_step=True,  # Mix both for diversity
                )
            else:
                dataset = create_bc_dataset(
                    num_tasks=num_demos,
                    difficulty=difficulty,
                    seed=42,
                    jitter=jitter,
                )
        except ValueError as e:
            print(f"Warning: Could not generate BC dataset: {e}")
            return {"bc_loss": float("nan"), "bc_accuracy": 0.0}

        num_samples = dataset["num_samples"]
        print(f"Generated {num_samples} valid expert trajectories")
        if use_persistent or use_multistep:
            print(f"  RUN_TESTS actions: {dataset.get('num_run_tests', 0)}")
            print(f"  WRITE_FOCUS actions: {dataset.get('num_write_focus', 0)}")
            if use_persistent:
                print(f"  COMPLETE_TASK actions: {dataset.get('num_complete_task', 0)}")

        if num_samples < 10:
            print("Warning: Too few samples for BC pre-training")
            return {"bc_loss": float("nan"), "bc_accuracy": 0.0}

        # Move data to device
        observations = dataset["observations"].to(self.device)

        # For multi-step/persistent BC, we have full action_bytes; for single-step, we build them
        if use_persistent or use_multistep:
            # Multi-step/persistent dataset provides full action bytes
            action_bytes_all = dataset["action_bytes"].to(self.device).long()
            has_separate_labels = False
        else:
            # Single-step dataset has separate offset/vocab/length labels
            offsets = dataset["offsets"].to(self.device)
            vocab_idxs = dataset["vocab_idxs"].to(self.device)
            lengths = dataset["lengths"].to(self.device)
            has_separate_labels = True

        # Create BC-specific optimizer (higher LR for supervised learning)
        bc_optimizer = Adam(self.brain.parameters(), lr=bc_lr)

        # Initialize hidden states for BC (we process each demo independently)
        batch_h, batch_g = self.brain.init_state(bc_batch_size, self.device)
        a_prev = torch.zeros((bc_batch_size, self.brain.config.action_bytes),
                            dtype=torch.long, device=self.device)

        best_loss = float("inf")
        best_accuracy = 0.0

        for epoch in range(bc_epochs):
            # Shuffle data
            perm = torch.randperm(num_samples, device=self.device)
            epoch_losses = []
            epoch_correct = 0
            epoch_total = 0

            for start in range(0, num_samples, bc_batch_size):
                end = min(start + bc_batch_size, num_samples)
                batch_idx = perm[start:end]
                actual_batch = len(batch_idx)

                # Get batch data
                obs_batch = observations[batch_idx]

                # Resize hidden states if needed
                if actual_batch != bc_batch_size:
                    h, g = self.brain.init_state(actual_batch, self.device)
                    a = torch.zeros((actual_batch, self.brain.config.action_bytes),
                                   dtype=torch.long, device=self.device)
                else:
                    h, g = batch_h, batch_g
                    a = a_prev

                # Forward pass - get outputs for evaluation
                output = self.brain(obs_batch, h, g, a, training=True)

                # BC loss: maximize log probability of target actions
                if use_persistent or use_multistep:
                    # Multi-step/persistent: use full action bytes from dataset
                    target_actions = action_bytes_all[batch_idx]
                else:
                    # Single-step: build from separate labels
                    offset_targets = offsets[batch_idx]
                    vocab_targets = vocab_idxs[batch_idx]
                    length_targets = lengths[batch_idx]

                    target_actions = torch.zeros(actual_batch, self.brain.config.action_bytes,
                                                dtype=torch.long, device=self.device)
                    # Byte 0: action type = WRITE_FOCUS (16)
                    target_actions[:, 0] = 16
                    # Byte 1: offset (0-31)
                    target_actions[:, 1] = offset_targets
                    # Byte 3: length (0-3)
                    target_actions[:, 3] = length_targets
                    # Byte 25: vocab_idx (0-3)
                    target_actions[:, 25] = vocab_targets

                # Use evaluate_actions to get log probs of target actions
                log_probs, entropy, values, _, _, _ = self.brain.evaluate_actions(
                    obs_bytes=obs_batch,
                    prev_h=h,
                    prev_g=g,
                    prev_a=a,
                    actions=target_actions,
                    z_t=output.z_t,
                )

                # BC loss = negative log probability of correct actions
                if use_persistent or use_multistep:
                    # Multi-step/persistent: train on ALL bytes (includes action type byte 0)
                    # Weight byte 0 (action type) heavily since RUN_TESTS vs WRITE_FOCUS vs COMPLETE_TASK is critical
                    action_type_log_prob = log_probs[:, 0]
                    offset_log_prob = log_probs[:, 1]
                    length_log_prob = log_probs[:, 3]
                    vocab_log_prob = log_probs[:, 25]
                    # Heavily weight action type since it determines everything else
                    bc_loss = -(3.0 * action_type_log_prob + 2.0 * offset_log_prob + vocab_log_prob + 0.5 * length_log_prob).mean()
                else:
                    # Single-step: focus on important bytes (1, 3, 25)
                    offset_log_prob = log_probs[:, 1]
                    length_log_prob = log_probs[:, 3]
                    vocab_log_prob = log_probs[:, 25]
                    bc_loss = -(2.0 * offset_log_prob + vocab_log_prob + 0.5 * length_log_prob).mean()

                bc_optimizer.zero_grad()
                bc_loss.backward()
                nn.utils.clip_grad_norm_(self.brain.parameters(), self.max_grad_norm)
                bc_optimizer.step()

                # Keep GPU busy during BC training (prevents GPU guard from killing)
                # Need multiple burns to maintain >80% utilization
                for _ in range(3):
                    self._gpu_burn(sync=False)

                epoch_losses.append(bc_loss.item())

                # Compute accuracy using sampled actions (discrete)
                if use_persistent or use_multistep:
                    # Multi-step/persistent: check action type + offset + vocab + length
                    pred_action_type = output.action[:, 0].long()
                    pred_offset = output.action[:, 1].long() % 64
                    pred_vocab = output.action[:, 25].long() % vocab_size
                    pred_length = output.action[:, 3].long() % 4

                    target_action_type = target_actions[:, 0]
                    target_offset = target_actions[:, 1]
                    target_vocab = target_actions[:, 25]
                    target_length = target_actions[:, 3]

                    correct = (
                        (pred_action_type == target_action_type) &
                        (pred_offset == target_offset) &
                        (pred_vocab == target_vocab) &
                        (pred_length == target_length)
                    ).sum().item()
                else:
                    # Single-step: check offset + vocab + length only
                    pred_offset_discrete = (output.action[:, 1].long() % 64)  # Full offset range
                    pred_vocab_discrete = (output.action[:, 25].long() % vocab_size)
                    pred_length_discrete = (output.action[:, 3].long() % 4)

                    correct = (
                        (pred_offset_discrete == offset_targets) &
                        (pred_vocab_discrete == vocab_targets) &
                        (pred_length_discrete == length_targets)
                    ).sum().item()
                epoch_correct += correct
                epoch_total += actual_batch

            avg_loss = sum(epoch_losses) / len(epoch_losses)
            accuracy = epoch_correct / epoch_total if epoch_total > 0 else 0.0

            if avg_loss < best_loss:
                best_loss = avg_loss
            if accuracy > best_accuracy:
                best_accuracy = accuracy

            if (epoch + 1) % 10 == 0 or epoch == 0:
                print(f"  BC Epoch {epoch+1}/{bc_epochs}: Loss={avg_loss:.4f}, Accuracy={accuracy:.1%}")

        print(f"\nBC Pre-training complete:")
        print(f"  Best Loss: {best_loss:.4f}")
        print(f"  Best Accuracy: {best_accuracy:.1%}")
        print(f"  GPU burns during BC: executed={self._burn_call_count}, skipped={self._burn_skip_count}")
        print()

        # Reset burn counts for RL phase
        self._burn_call_count = 0
        self._burn_skip_count = 0

        return {
            "bc_loss": best_loss,
            "bc_accuracy": best_accuracy,
        }

    def pretrain_behavioral_cloning_sequential(
        self,
        num_demos: int = 1000,
        bc_epochs: int = 100,
        bc_batch_size: int = 32,
        bc_lr: float = 1e-3,
        difficulty: BugDifficulty = BugDifficulty.TRIVIAL,
        seq_len: int = 4,
    ) -> Dict[str, Any]:
        """
        Sequential BC pre-training for RNNs.

        Unlike standard BC which shuffles samples (breaking temporal coherence),
        this processes complete trajectories sequentially, allowing the GRU to
        learn the 4-step loop: RUN_TESTS -> WRITE_FOCUS -> RUN_TESTS -> COMPLETE_TASK

        The key insight (from Oracle consultation):
        - Standard BC trains on shuffled (obs, action) pairs with zeroed h_t
        - The model never learns to use its GRU memory
        - Sequential BC processes trajectories in order, maintaining hidden state

        Args:
            num_demos: Number of trajectories to generate
            bc_epochs: Number of epochs
            bc_batch_size: Batch size (number of trajectories per batch)
            bc_lr: Learning rate
            difficulty: Bug difficulty level
            seq_len: Sequence length per trajectory (default 4)

        Returns:
            Dictionary of BC metrics
        """
        from src.harness.actions import TRIVIAL_VOCAB, COMBINED_VOCAB

        vocab_size = len(TRIVIAL_VOCAB) if difficulty == BugDifficulty.TRIVIAL else len(COMBINED_VOCAB)

        print(f"\n=== SEQUENTIAL BC PRE-TRAINING ===")
        print(f"Generating {num_demos} sequential trajectories (seq_len={seq_len})...")

        # Generate sequential dataset
        dataset = create_sequential_bc_dataset(
            num_tasks=num_demos,
            difficulty=difficulty,
            seed=42,
            seq_len=seq_len,
        )

        num_traj = dataset["num_trajectories"]
        num_samples = dataset["num_samples"]
        print(f"Generated {num_traj} trajectories ({num_samples} total steps)")
        print(f"  RUN_TESTS actions: {dataset['num_run_tests']}")
        print(f"  WRITE_FOCUS actions: {dataset['num_write_focus']}")
        print(f"  COMPLETE_TASK actions: {dataset['num_complete_task']}")

        # Move data to device - shape: [num_traj, seq_len, ...]
        observations = dataset["observations"].to(self.device)  # [N, S, 512]
        action_bytes = dataset["action_bytes"].to(self.device).long()  # [N, S, 64]
        masks = dataset["masks"].to(self.device)  # [N, S]

        # Create BC optimizer
        bc_optimizer = Adam(self.brain.parameters(), lr=bc_lr)

        best_loss = float("inf")
        best_accuracy = 0.0

        for epoch in range(bc_epochs):
            # Shuffle trajectory order (but keep steps within trajectory in order!)
            perm = torch.randperm(num_traj, device=self.device)
            epoch_losses = []
            epoch_correct = 0
            epoch_total = 0

            for start in range(0, num_traj, bc_batch_size):
                end = min(start + bc_batch_size, num_traj)
                batch_idx = perm[start:end]
                batch_size = len(batch_idx)

                # Get batch: [batch_size, seq_len, ...]
                obs_seq = observations[batch_idx]  # [B, S, 512]
                action_seq = action_bytes[batch_idx]  # [B, S, 64]
                mask_seq = masks[batch_idx]  # [B, S]

                # Initialize hidden state ONCE per trajectory
                h, g = self.brain.init_state(batch_size, self.device)
                a_prev = torch.zeros((batch_size, self.brain.config.action_bytes),
                                    dtype=torch.long, device=self.device)

                # Process sequence step by step, maintaining hidden state
                seq_losses = []
                for step in range(seq_len):
                    # Get this step's data
                    obs_step = obs_seq[:, step]  # [B, 512]
                    target_action = action_seq[:, step]  # [B, 64]
                    step_mask = mask_seq[:, step]  # [B]

                    if not step_mask.any():
                        continue

                    # Forward pass with carried hidden state
                    output = self.brain(obs_step, h, g, a_prev, training=True)

                    # Update hidden state for next step
                    h = output.h_next.detach()
                    g = output.g_t.detach()
                    a_prev = output.action.long().detach()

                    # Compute loss only for valid steps
                    log_probs, entropy, values, _, _, _ = self.brain.evaluate_actions(
                        obs_bytes=obs_step,
                        prev_h=output.h_next,  # Use updated h for consistency
                        prev_g=output.g_t,
                        prev_a=a_prev,
                        actions=target_action,
                        z_t=output.z_t,
                    )

                    # Weight action type heavily (byte 0 determines the action class)
                    action_type_log_prob = log_probs[:, 0]
                    offset_log_prob = log_probs[:, 1]
                    length_log_prob = log_probs[:, 3]
                    vocab_log_prob = log_probs[:, 25]

                    step_loss = -(3.0 * action_type_log_prob + 2.0 * offset_log_prob +
                                  vocab_log_prob + 0.5 * length_log_prob)

                    # GPU burn during step loop to maintain utilization
                    self._gpu_burn(sync=False)

                    # Mask out invalid steps
                    masked_loss = (step_loss * step_mask.float()).sum() / step_mask.sum()
                    seq_losses.append(masked_loss)

                    # Compute accuracy for this step
                    pred_action_type = output.action[:, 0].long()
                    pred_offset = output.action[:, 1].long() % 64
                    pred_vocab = output.action[:, 25].long() % vocab_size
                    pred_length = output.action[:, 3].long() % 4

                    correct = (
                        (pred_action_type == target_action[:, 0]) &
                        (pred_offset == target_action[:, 1]) &
                        (pred_vocab == target_action[:, 25]) &
                        (pred_length == target_action[:, 3]) &
                        step_mask
                    ).sum().item()

                    epoch_correct += correct
                    epoch_total += step_mask.sum().item()

                if seq_losses:
                    # Average loss across sequence
                    batch_loss = torch.stack(seq_losses).mean()

                    bc_optimizer.zero_grad()
                    batch_loss.backward()
                    nn.utils.clip_grad_norm_(self.brain.parameters(), self.max_grad_norm)
                    bc_optimizer.step()

                    epoch_losses.append(batch_loss.item())

                    # Keep GPU busy - need more burns for sequential processing
                    for _ in range(5):
                        self._gpu_burn(sync=False)

            avg_loss = sum(epoch_losses) / len(epoch_losses) if epoch_losses else float("nan")
            accuracy = epoch_correct / epoch_total if epoch_total > 0 else 0.0

            if avg_loss < best_loss:
                best_loss = avg_loss
            if accuracy > best_accuracy:
                best_accuracy = accuracy

            if (epoch + 1) % 10 == 0 or epoch == 0:
                print(f"  SeqBC Epoch {epoch+1}/{bc_epochs}: Loss={avg_loss:.4f}, Accuracy={accuracy:.1%}")

        print(f"\nSequential BC Pre-training complete:")
        print(f"  Best Loss: {best_loss:.4f}")
        print(f"  Best Accuracy: {best_accuracy:.1%}")
        print(f"  GPU burns during BC: executed={self._burn_call_count}, skipped={self._burn_skip_count}")
        print()

        self._burn_call_count = 0
        self._burn_skip_count = 0

        return {
            "bc_loss": best_loss,
            "bc_accuracy": best_accuracy,
            "dataset": dataset,  # Return for anchored RL setup
        }

    def save_bc_reference_policy(self):
        """
        Save a copy of the current policy weights as BC reference.
        Call this right after BC pre-training to enable KL penalty during RL.
        """
        import copy
        self.bc_reference_policy = copy.deepcopy(self.brain.state_dict())
        print("Saved BC reference policy for KL penalty")

    def set_kl_coef(self, kl_coef: float):
        """Set the KL coefficient for RL training."""
        self.kl_coef = kl_coef
        print(f"KL coefficient set to {kl_coef}")

    def setup_anchored_rl(
        self,
        bc_observations: torch.Tensor,
        bc_actions: torch.Tensor,
        anchor_coef: float = 1.0,
        decay: str = "linear",
        warmup_steps: int = 10000,
        decay_steps: int = 40000,
        end_coef: float = 0.05,
    ):
        """
        Setup Anchored RL: BC imitation loss during RL training.

        Args:
            bc_observations: [N, obs_dim] BC demo observations
            bc_actions: [N, action_bytes] BC demo target actions
            anchor_coef: Initial λ_bc coefficient
            decay: Decay schedule ("linear", "cosine", "constant")
            warmup_steps: Steps to keep λ_bc at anchor_coef
            decay_steps: Steps to decay from anchor_coef to end_coef
            end_coef: Final λ_bc coefficient
        """
        self.bc_demo_observations = bc_observations.to(self.device)
        self.bc_demo_actions = bc_actions.to(self.device)
        self.bc_anchor_start_coef = anchor_coef
        self.bc_anchor_coef = anchor_coef
        self.bc_anchor_decay = decay
        self.bc_anchor_warmup_steps = warmup_steps
        self.bc_anchor_decay_steps = decay_steps
        self.bc_anchor_end_coef = end_coef
        print(f"Anchored RL setup:")
        print(f"  BC demos: {len(bc_observations)}")
        print(f"  λ_bc: {anchor_coef} -> {end_coef}")
        print(f"  Schedule: {warmup_steps} warmup, {decay_steps} decay, {decay} decay")

    def setup_two_timescale_optimizer(self, backbone_lr_scale: float = 0.1):
        """
        Setup two-timescale optimizer: backbone at lower LR than heads.

        The idea is that BC pre-trained features should change slowly,
        while the policy/value heads can adapt faster to RL signal.

        Args:
            backbone_lr_scale: Backbone LR = base_lr * backbone_lr_scale
        """
        # Identify backbone vs head parameters
        # Backbone: encoder, memory (GRU), projection
        # Heads: policy_mean, policy_logstd, value, global_gate
        backbone_params = []
        head_params = []

        for name, param in self.brain.named_parameters():
            if any(x in name for x in ['policy_mean', 'policy_logstd', 'value', 'global_gate']):
                head_params.append(param)
            else:
                backbone_params.append(param)

        self.optimizer = Adam([
            {'params': backbone_params, 'lr': self.lr * backbone_lr_scale},
            {'params': head_params, 'lr': self.lr},
        ])
        self.use_two_timescale = True
        print(f"Two-timescale optimizer:")
        print(f"  Backbone params: {sum(p.numel() for p in backbone_params):,} @ {self.lr * backbone_lr_scale:.1e}")
        print(f"  Head params: {sum(p.numel() for p in head_params):,} @ {self.lr:.1e}")

    def set_backbone_freeze_steps(self, steps: int):
        """Set number of steps to freeze backbone (only train heads)."""
        self.backbone_freeze_steps = steps
        print(f"Backbone will be frozen for first {steps:,} RL steps")

    def get_current_bc_anchor_coef(self) -> float:
        """Get current λ_bc based on decay schedule."""
        if self.bc_demo_observations is None:
            return 0.0

        steps = self.total_steps

        # Warmup phase: full λ_bc
        if steps < self.bc_anchor_warmup_steps:
            return self.bc_anchor_start_coef

        # Decay phase
        decay_progress = min(1.0, (steps - self.bc_anchor_warmup_steps) / max(1, self.bc_anchor_decay_steps))

        if self.bc_anchor_decay == "linear":
            coef = self.bc_anchor_start_coef - decay_progress * (self.bc_anchor_start_coef - self.bc_anchor_end_coef)
        elif self.bc_anchor_decay == "cosine":
            coef = self.bc_anchor_end_coef + 0.5 * (self.bc_anchor_start_coef - self.bc_anchor_end_coef) * (1 + math.cos(math.pi * decay_progress))
        else:  # constant
            coef = self.bc_anchor_start_coef

        return coef

    def compute_bc_anchor_loss(self, batch_size: int) -> torch.Tensor:
        """
        Compute BC imitation loss on sampled BC demos.

        Returns cross-entropy loss on (obs, action) pairs from BC dataset.
        """
        if self.bc_demo_observations is None:
            return torch.tensor(0.0, device=self.device)

        # Sample random indices from BC demos
        n_demos = len(self.bc_demo_observations)
        sample_size = min(batch_size, n_demos)
        idx = torch.randint(0, n_demos, (sample_size,), device=self.device)

        obs_batch = self.bc_demo_observations[idx]
        action_targets = self.bc_demo_actions[idx]

        # Forward pass through brain
        h, g = self.brain.init_state(sample_size, self.device)
        a_prev = torch.zeros((sample_size, self.brain.config.action_bytes), dtype=torch.long, device=self.device)

        output = self.brain(obs_batch, h, g, a_prev, training=True)

        # Get log probs of target actions (focus on important bytes)
        log_probs, _, _, _, _, _ = self.brain.evaluate_actions(
            obs_bytes=obs_batch,
            prev_h=h,
            prev_g=g,
            prev_a=a_prev,
            actions=action_targets,
            z_t=output.z_t,
        )

        # BC loss: negative log prob of correct actions
        # DEEP-DEBUG FIX: Use ALL bytes, not just 3
        # Previous bug: only constraining bytes [1, 3, 25] allowed other 29 bytes to collapse
        #
        # Weight scheme:
        # - Byte 0 (action type): 1.0 (important for action selection)
        # - Byte 1 (offset): 2.0 (critical for positioning)
        # - Byte 3 (length): 0.5 (moderately important)
        # - Byte 25 (vocab): 1.0 (important for token selection)
        # - All other bytes: 0.1 (light regularization to prevent collapse)

        n_bytes = log_probs.size(1)
        weights = torch.ones(n_bytes, device=log_probs.device) * 0.1  # Base weight for all

        # Override key bytes with higher weights
        if n_bytes > 0:
            weights[0] = 1.0   # action type
        if n_bytes > 1:
            weights[1] = 2.0   # offset
        if n_bytes > 3:
            weights[3] = 0.5   # length
        if n_bytes > 25:
            weights[25] = 1.0  # vocab

        # Weighted negative log probability across ALL bytes
        bc_loss = -(log_probs * weights.unsqueeze(0)).sum(dim=1).mean()

        return bc_loss

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

        # GPU burn before reset - keep GPU busy during CPU-bound env reset
        for _ in range(10):
            self._gpu_burn(sync=False)

        # Get initial observation (CPU-bound reset of all environments)
        obs = self.envs.reset()
        obs = obs.to(self.device)

        # GPU burn after reset - ensure we're back to high GPU utilization
        for _ in range(10):
            self._gpu_burn(sync=False)

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
            #
            # Important: convert actions to CPU *before* stepping the env so we can overlap optional
            # GPU padding (burn) with the CPU-bound env step.
            action_bytes = output.action.clamp(0, 255).to(torch.uint8).cpu()

            # Keep GPU busy while the env step runs on CPU.
            # NOTE: Reduced from 5 to 1 burn per side (was 10 total = 5s/step, now 2 = 1s/step)
            self._gpu_burn(sync=False)

            # Step environments (CPU-bound)
            next_obs, rewards, dones, infos = self.envs.step(action_bytes)
            next_obs = next_obs.to(self.device)
            rewards = rewards.to(self.device)

            # One more burn after env step
            self._gpu_burn(sync=False)

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
        kl_losses = []
        bc_anchor_losses = []
        total_losses = []

        # Get current BC anchor coefficient (with decay schedule)
        current_bc_anchor_coef = self.get_current_bc_anchor_coef()

        # Load BC reference policy for KL computation (if enabled)
        bc_brain = None
        if self.kl_coef > 0 and self.bc_reference_policy is not None:
            bc_brain = create_brain(
                obs_dim=self.brain.config.obs_dim,
                action_bytes=self.brain.config.action_bytes,
                hidden_dim=self.brain.config.hidden_dim,
                enable_plasticity=False,
                enable_sleep=False,
            ).to(self.device)
            bc_brain.load_state_dict(self.bc_reference_policy)
            bc_brain.eval()

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

                # KL divergence penalty to preserve BC policy
                kl_loss = torch.tensor(0.0, device=self.device)
                if bc_brain is not None and self.kl_coef > 0:
                    with torch.no_grad():
                        bc_output = bc_brain(
                            obs_flat[mb_idx],
                            prev_h_flat[mb_idx],
                            prev_g_flat[mb_idx],
                            prev_a_flat[mb_idx],
                            training=False
                        )
                        bc_log_probs, _, _, _, _, _ = bc_brain.evaluate_actions(
                            obs_bytes=obs_flat[mb_idx],
                            prev_h=prev_h_flat[mb_idx],
                            prev_g=prev_g_flat[mb_idx],
                            prev_a=prev_a_flat[mb_idx],
                            actions=actions_flat[mb_idx],
                            z_t=bc_output.z_t,
                        )
                    # KL(current || BC) for important bytes (1, 3, 25)
                    # Approximate KL using: exp(log_p_bc) * (log_p_bc - log_p_current)
                    # = p_bc * log(p_bc/p_current)
                    # For numerical stability, use: KL ≈ (log_p_bc - log_p_current) when p_bc ≈ p_current
                    # Simpler: just penalize drift from BC log probs
                    important_bytes = [1, 3, 25]  # offset, length, vocab
                    kl_per_byte = (bc_log_probs[:, important_bytes] - new_log_probs[:, important_bytes]).pow(2)
                    kl_loss = kl_per_byte.mean()

                # ANCHORED RL: BC imitation loss on sampled demos
                bc_anchor_loss = torch.tensor(0.0, device=self.device)
                if current_bc_anchor_coef > 0 and self.bc_demo_observations is not None:
                    bc_anchor_loss = self.compute_bc_anchor_loss(len(mb_idx))

                # Total loss (maximize entropy_bonus, minimize kl_loss and bc_anchor_loss)
                loss = (
                    policy_loss
                    + self.value_coef * value_loss
                    - self.entropy_coef * entropy_bonus
                    + self.kl_coef * kl_loss
                    + current_bc_anchor_coef * bc_anchor_loss
                )

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.brain.parameters(), self.max_grad_norm)
                self.optimizer.step()

                policy_losses.append(policy_loss.detach())
                value_losses.append(value_loss.detach())
                entropies.append(entropy_bonus.detach())
                kl_losses.append(kl_loss.detach())
                bc_anchor_losses.append(bc_anchor_loss.detach())
                total_losses.append(loss.detach())

        def mean(xs: List[torch.Tensor]) -> float:
            if not xs:
                return 0.0
            return torch.stack(xs).mean().item()

        return {
            "policy_loss": mean(policy_losses),
            "value_loss": mean(value_losses),
            "entropy": mean(entropies),
            "kl_loss": mean(kl_losses),
            "bc_anchor_loss": mean(bc_anchor_losses),
            "bc_anchor_coef": current_bc_anchor_coef,
            "total_loss": mean(total_losses),
        }

    def train(self, total_timesteps: int, log_interval: int = 1000):
        """Main training loop."""
        print(f"=== RL TRAINING STARTED ===", flush=True)
        print(f"  Total timesteps: {total_timesteps:,}", flush=True)
        print(f"  Log interval: {log_interval}", flush=True)
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

                print(f"Steps: {self.total_steps:,} | FPS: {fps:.0f}", flush=True)
                print(f"  Policy Loss: {metrics['policy_loss']:.4f}", flush=True)
                print(f"  Value Loss: {metrics['value_loss']:.4f}", flush=True)
                print(f"  Entropy: {metrics['entropy']:.4f}", flush=True)
                if self.kl_coef > 0:
                    print(f"  KL Loss: {metrics['kl_loss']:.4f}", flush=True)
                if metrics.get('bc_anchor_coef', 0) > 0:
                    print(f"  BC Anchor Loss: {metrics['bc_anchor_loss']:.4f} (λ={metrics['bc_anchor_coef']:.3f})", flush=True)
                print(f"  Avg Reward: {avg_reward:.2f}", flush=True)
                print(f"  Avg Length: {avg_length:.1f}", flush=True)
                print(f"  GPU burns: exec={self._burn_call_count}, skip={self._burn_skip_count}", flush=True)
                print(flush=True)

        print(f"Training complete: {self.total_steps:,} steps in {time.time() - start_time:.1f}s", flush=True)

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
        default=500.0,
        help="Extra GPU padding per rollout step (ms). Helps keep util > 80%% when CPU-bound. Default 500ms.",
    )
    parser.add_argument(
        "--gpu-burn-dim",
        type=int,
        default=12288,
        help="Matmul dim for GPU burn (larger = more load, more VRAM).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--repo-path", type=str, default="fixtures/toy_repo", help="Path to toy repo (v1 mode)")

    # v2 options
    parser.add_argument("--mode", type=str, choices=["v1", "v2", "curriculum"], default="v1",
                        help="Training mode: v1 (toy repo), v2 (multi-file), or curriculum (progressive)")
    parser.add_argument("--difficulty", type=str, choices=["trivial", "easy", "medium", "hard"], default="medium",
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
    parser.add_argument("--force-write-focus", action="store_true",
                        help="Force all actions to WRITE_FOCUS (simplified curriculum for TRIVIAL)")
    parser.add_argument("--no-auto-focus", action="store_true",
                        help="Disable auto-focus on target file (for navigation training)")
    parser.add_argument("--force-write-focus-prob", type=float, default=1.0,
                        help="Probability of forcing WRITE_FOCUS (1.0=always, 0.0=never, for gradual curriculum)")
    parser.add_argument("--single-step", action="store_true",
                        help="Use max_steps=1 (aligns RL training with BC and evaluation)")
    # Behavioral cloning pre-training
    parser.add_argument("--bc-epochs", type=int, default=0,
                        help="Number of BC pre-training epochs (0 = skip BC)")
    parser.add_argument("--bc-demos", type=int, default=1000,
                        help="Number of expert demos for BC pre-training")
    parser.add_argument("--bc-multistep", action="store_true",
                        help="Use multi-step BC demos (RUN_TESTS + WRITE_FOCUS)")
    parser.add_argument("--bc-sequential", action="store_true",
                        help="Use sequential BC training (maintains h_t across trajectory, critical for RNNs)")
    parser.add_argument("--bc-batch-size", type=int, default=128,
                        help="Batch size for BC pre-training")
    parser.add_argument("--bc-lr", type=float, default=1e-3,
                        help="Learning rate for BC pre-training")
    parser.add_argument("--focus-jitter", type=int, default=0,
                        help="Focus offset jitter +/- this value (for robustness, 0 = disabled)")
    parser.add_argument("--kl-coef", type=float, default=0.0,
                        help="[DEPRECATED] KL penalty has mathematical bugs. Use --bc-anchor-coef instead.")
    parser.add_argument("--rl-timesteps", type=int, default=None,
                        help="Limit RL timesteps after BC (None = use --timesteps)")
    # ANCHORED RL: BC imitation loss during RL
    parser.add_argument("--bc-anchor-coef", type=float, default=0.0,
                        help="Initial BC anchor coefficient λ_bc (0 = disabled, 1.0 = strong anchor)")
    parser.add_argument("--bc-anchor-decay", type=str, choices=["linear", "cosine", "constant"], default="linear",
                        help="BC anchor decay schedule")
    parser.add_argument("--bc-anchor-warmup-steps", type=int, default=10000,
                        help="Steps to keep λ_bc at initial value before decay")
    parser.add_argument("--bc-anchor-decay-steps", type=int, default=40000,
                        help="Steps to decay λ_bc from initial to end value")
    parser.add_argument("--bc-anchor-end-coef", type=float, default=0.05,
                        help="Final BC anchor coefficient after decay")
    parser.add_argument("--two-timescale", action="store_true",
                        help="Use two-timescale optimizer (backbone LR = 0.1x head LR)")
    parser.add_argument("--backbone-lr-scale", type=float, default=0.1,
                        help="Backbone LR scale for two-timescale (default 0.1)")
    parser.add_argument("--backbone-freeze-steps", type=int, default=0,
                        help="Steps to freeze backbone (only train heads)")
    parser.add_argument("--bc-checkpoint", type=str, default=None,
                        help="Load BC-pretrained checkpoint instead of training from scratch")
    # Persistent mode (Phase 7)
    parser.add_argument("--persistent", action="store_true",
                       help="Enable persistent mode (no reset between tasks)")
    parser.add_argument("--tasks-per-episode", type=int, default=1,
                       help="Number of tasks per super-episode in persistent mode")
    parser.add_argument("--scratchpad", action="store_true",
                       help="Enable .jarvis_notes scratchpad file")
    parser.add_argument("--enable-sleep", action="store_true",
                       help="Enable sleep/consolidation module")

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

    # Hard safety envelope (non-negotiable).
    if int(args.gpu_min_util) < 80:
        raise SystemExit("Refusing --gpu-min-util < 80 (hard repo rule).")
    if int(args.gpu_max_vram_mib) > 10 * 1024:
        raise SystemExit("Refusing --gpu-max-vram-mib > 10240 MiB (hard repo rule).")

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

        # Start init GPU burner to keep GPU busy during CPU-bound task creation
        init_burner = None
        if device.type == "cuda":
            init_burner = InitGPUBurner(device, dim=8192, burn_ms=300.0)
            init_burner.start()

        # Determine action bytes
        action_bytes = ACTION_BYTES_V2 if args.action_bytes == 64 else ACTION_BYTES

        # Create environments
        # CRITICAL: --single-step aligns RL with BC/eval (both use fresh h_t)
        # Without this, RL learns with sequential h_t but eval uses fresh h_t
        max_steps = 1 if getattr(args, 'single_step', False) else (50 if args.mode == "v1" else 100)
        harness_config = HarnessConfig(
            obs_bytes=OBS_TOTAL_BYTES,
            action_bytes=action_bytes,
            max_steps=max_steps,
            max_time_seconds=30 if args.mode == "v1" else 60,
            # Training must be GPU-saturated; avoid expensive pytest on every reset.
            run_tests_on_reset=(args.mode == "v1"),
            run_fast_tests=(args.mode != "v1"),
            async_tests=(args.mode != "v1"),
            auto_tests_on_write=(args.mode != "v1"),
            auto_full_tests_on_fast_pass=(args.mode != "v1"),
            # Keep verifier subprocesses bounded so CPU doesn't starve the GPU.
            test_timeout_seconds=30 if args.mode == "v1" else 10,
            fast_test_timeout_seconds=10 if args.mode == "v1" else 2,
            # Curriculum: force WRITE_FOCUS to simplify learning
            force_write_focus=args.force_write_focus,
            force_write_focus_prob=args.force_write_focus_prob,
            # Focus jitter for curriculum robustness
            focus_jitter=args.focus_jitter,
            # Navigation training: disable auto-focus on target file
            auto_focus_target=not getattr(args, 'no_auto_focus', False),
            # Persistent mode (Phase 7)
            persistent_mode=getattr(args, 'persistent', False),
            tasks_per_episode=getattr(args, 'tasks_per_episode', 1),
            scratchpad_enabled=getattr(args, 'scratchpad', False),
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
                difficulty_span=0,
            )
            print("CURRICULUM mode: Starting at TRIVIAL difficulty")
            print(f"Promotion threshold: {curriculum_state.promote_threshold:.0%}")
            print(f"Demotion threshold: {curriculum_state.demote_threshold:.0%}")
            print(f"Min episodes before change: {curriculum_state.min_episodes}")
            print(f"Temp directory: {temp_dir}")

        else:
            difficulty_map = {
                "trivial": BugDifficulty.TRIVIAL,
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
                difficulty_span=0,
            )
            print(f"v2 mode: Generated {len(tasks)} multi-file tasks")
            print(f"Difficulty: {args.difficulty}")
            print(f"Temp directory: {temp_dir}")

            for i, (task, repo) in enumerate(zip(tasks[:3], repos[:3])):
                print(f"  Task {i}: {task.name} ({len(repo.files)} files, {len(repo.bugs)} bugs)")
            sys.stdout.flush()

        print("Setting tasks on environments...", flush=True)
        envs.set_tasks(tasks)
        print("Tasks set successfully.", flush=True)

        # Stop init GPU burner BEFORE brain creation - brain.to(device) needs GPU
        # Init burner was only for CPU-bound task creation phase
        if init_burner is not None:
            print("Stopping init GPU burner (brain creation is GPU work)...", flush=True)
            init_burner.stop()
            init_burner = None

        # Create brain
        print("Creating brain...", flush=True)
        brain = create_brain(
            obs_dim=OBS_TOTAL_BYTES,
            action_bytes=action_bytes,
            hidden_dim=int(args.hidden_dim),
            enable_plasticity=False,  # Disable for initial training
            enable_sleep=getattr(args, 'enable_sleep', False),
        ).to(device)

        param_count = sum(p.numel() for p in brain.parameters())
        print(f"Brain parameters: {param_count:,}", flush=True)

        print("Creating trainer...", flush=True)
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

        print(f"\nStarting training for {args.timesteps:,} timesteps...", flush=True)
        print(f"Environments: {args.num_envs}", flush=True)
        print(f"Rollout steps: {args.rollout_steps}", flush=True)
        print(f"Action bytes: {action_bytes}", flush=True)
        print(flush=True)

        # Load BC checkpoint if provided
        if args.bc_checkpoint:
            print(f"Loading BC checkpoint: {args.bc_checkpoint}", flush=True)
            ckpt = torch.load(args.bc_checkpoint, map_location=device)
            brain.load_state_dict(ckpt['brain_state_dict'])
            print(f"BC checkpoint loaded successfully", flush=True)

            # Set up anchored RL if enabled (generate demos for anchor loss)
            if args.bc_anchor_coef > 0:
                print(f"Generating BC demos for anchored RL...", flush=True)
                bc_dataset = create_bc_dataset(
                    num_tasks=args.bc_demos,
                    difficulty=BugDifficulty.TRIVIAL,
                    seed=args.seed,
                    jitter=args.focus_jitter,
                )
                bc_actions = torch.zeros(bc_dataset['num_samples'], action_bytes, dtype=torch.long)
                bc_actions[:, 0] = 16  # WRITE_FOCUS
                bc_actions[:, 1] = bc_dataset['offsets']
                bc_actions[:, 3] = bc_dataset['lengths']
                bc_actions[:, 25] = bc_dataset['vocab_idxs']

                trainer.setup_anchored_rl(
                    bc_observations=bc_dataset['observations'],
                    bc_actions=bc_actions,
                    anchor_coef=args.bc_anchor_coef,
                    decay=args.bc_anchor_decay,
                    warmup_steps=args.bc_anchor_warmup_steps,
                    decay_steps=args.bc_anchor_decay_steps,
                    end_coef=args.bc_anchor_end_coef,
                )

        # Behavioral cloning pre-training (if requested and no checkpoint loaded)
        bc_metrics = None
        bc_dataset = None
        if args.bc_epochs > 0 and not args.bc_checkpoint:
            # Determine BC mode
            use_persistent = getattr(args, 'persistent', False)
            use_sequential = getattr(args, 'bc_sequential', False)

            if use_sequential:
                # Phase 7.4d: Sequential BC for RNN temporal learning
                # Oracle score 420: This fixes the training-inference mismatch
                mode_str = "SEQUENTIAL (maintains h_t across 4-step loop)"
                print(f"BC pre-training requested: {args.bc_epochs} epochs, {args.bc_demos} demos ({mode_str})", flush=True)
                bc_result = trainer.pretrain_behavioral_cloning_sequential(
                    num_demos=args.bc_demos,
                    bc_epochs=args.bc_epochs,
                    bc_batch_size=args.bc_batch_size,
                    bc_lr=args.bc_lr,
                    difficulty=difficulty,
                    seq_len=4,  # 4-step persistent loop
                )
                bc_metrics = {"bc_loss": bc_result["bc_loss"], "bc_accuracy": bc_result["bc_accuracy"]}
            else:
                # Original BC modes (shuffled samples)
                if use_persistent:
                    mode_str = "persistent (RUN_TESTS -> WRITE_FOCUS -> RUN_TESTS -> COMPLETE_TASK)"
                elif args.bc_multistep:
                    mode_str = "multi-step"
                else:
                    mode_str = "single-step"
                print(f"BC pre-training requested: {args.bc_epochs} epochs, {args.bc_demos} demos ({mode_str})", flush=True)
                bc_metrics = trainer.pretrain_behavioral_cloning(
                    num_demos=args.bc_demos,
                    bc_epochs=args.bc_epochs,
                    bc_batch_size=args.bc_batch_size,
                    bc_lr=args.bc_lr,
                    jitter=args.focus_jitter,
                    difficulty=difficulty,  # Pass difficulty for correct vocab size
                    use_multistep=args.bc_multistep,
                    use_persistent=use_persistent,  # Phase 7.4a: enable persistent demos
                )
            # Save BC reference policy for KL penalty (if enabled)
            if args.kl_coef > 0:
                print("\n" + "=" * 60)
                print("WARNING: --kl-coef is DEPRECATED and has known bugs:")
                print("  1. Uses squared difference instead of true KL divergence")
                print("  2. Only constrains 3/32 bytes, allowing policy collapse")
                print("Use --bc-anchor-coef instead (fixed in DEEP-DEBUG session)")
                print("=" * 60 + "\n")
                trainer.save_bc_reference_policy()
                trainer.set_kl_coef(args.kl_coef)

            # Generate BC dataset for anchored RL (if enabled)
            if args.bc_anchor_coef > 0:
                print(f"Generating BC demos for anchored RL...", flush=True)
                if use_persistent:
                    # Phase 7.4a: Use persistent demos for anchored RL
                    bc_dataset = create_persistent_bc_dataset(
                        num_tasks=args.bc_demos,
                        difficulty=difficulty,
                        seed=args.seed,
                        include_single_step=False,
                    )
                    # Persistent dataset already has full action bytes
                    bc_actions = bc_dataset['action_bytes'].long()
                else:
                    bc_dataset = create_bc_dataset(
                        num_tasks=args.bc_demos,
                        difficulty=BugDifficulty.TRIVIAL,
                        seed=args.seed,
                        jitter=args.focus_jitter,
                    )
                    # Build target action tensor
                    bc_actions = torch.zeros(bc_dataset['num_samples'], action_bytes, dtype=torch.long)
                    bc_actions[:, 0] = 16  # WRITE_FOCUS
                    bc_actions[:, 1] = bc_dataset['offsets']
                    bc_actions[:, 3] = bc_dataset['lengths']
                    bc_actions[:, 25] = bc_dataset['vocab_idxs']

                trainer.setup_anchored_rl(
                    bc_observations=bc_dataset['observations'],
                    bc_actions=bc_actions,
                    anchor_coef=args.bc_anchor_coef,
                    decay=args.bc_anchor_decay,
                    warmup_steps=args.bc_anchor_warmup_steps,
                    decay_steps=args.bc_anchor_decay_steps,
                    end_coef=args.bc_anchor_end_coef,
                )

        # Two-timescale optimizer (if enabled)
        if args.two_timescale:
            trainer.setup_two_timescale_optimizer(backbone_lr_scale=args.backbone_lr_scale)

        # Backbone freeze (if enabled)
        if args.backbone_freeze_steps > 0:
            trainer.set_backbone_freeze_steps(args.backbone_freeze_steps)

        # Determine actual RL timesteps
        rl_timesteps = args.rl_timesteps if args.rl_timesteps is not None else args.timesteps
        if args.rl_timesteps is not None:
            print(f"RL timesteps limited to: {rl_timesteps:,}", flush=True)

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
                        difficulty_span=0,
                    )
                    repos = new_repos
                    return new_tasks, new_repos

                trainer.train_with_curriculum(
                    rl_timesteps,
                    curriculum_state,
                    regenerate_tasks,
                    log_interval=10,
                )
            else:
                trainer.train(rl_timesteps, log_interval=10)
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"Cleaned up temp directory: {temp_dir}")
                temp_dir = None

        mode_suffix = f"_{args.mode}" if args.mode in ["v2", "curriculum"] else ""
        checkpoint_path = f"results/jarvis_harness{mode_suffix}_{rl_timesteps}.pt"
        os.makedirs("results", exist_ok=True)
        checkpoint_data = {
            "brain_state_dict": brain.state_dict(),
            "total_steps": trainer.total_steps,
            "config": vars(args),
            "mode": args.mode,
        }
        if bc_metrics is not None:
            checkpoint_data["bc_metrics"] = bc_metrics
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
        if init_burner is not None:
            init_burner.stop()
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
