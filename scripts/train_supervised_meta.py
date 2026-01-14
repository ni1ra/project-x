#!/usr/bin/env python3
"""
SUPERVISED META-LEARNING Training Script

Fixes the "Complexity Collapse" issue identified by JARVIS:
- RL signal too sparse for precise function approximation
- Need direct supervision with true_Y

Key Changes from train_multitask_ccb.py:
1. SUPERVISED LOSS: CrossEntropy(action_logits, target_action) using true_Y
2. DEMO→SLEEP→TEST CURRICULUM: Explicit meta-learning structure
3. SLEEP MODULE ENABLED: For consolidation between phases

Target metrics:
- DoErr ≤ 0.05
- OD-NDT SR_novel ≥ 0.60

Usage:
    python scripts/train_supervised_meta.py [--timesteps 10000000]
"""

import argparse
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from src.core.rpj_brain import RPJBrain, RPJConfig
from src.benchmarks.multitask_ccb import TorchMultiTaskCCBEnvironment


def quantize_y_to_action(true_Y: torch.Tensor, nonlinear: bool = True) -> torch.Tensor:
    """
    Quantize continuous true_Y to action byte (0-255).

    For nonlinear CCB-NL:
        Y range is approximately [0.1, 1.65] (ReLU output)
        Action byte = clip((Y - 0.1) / 1.55 * 255, 0, 255)

    For linear CCB:
        Y range is approximately [-2, 2]
        Action byte = clip((Y + 2) / 4 * 255, 0, 255)
    """
    if nonlinear:
        action_byte = ((true_Y - 0.1) / 1.55 * 255).clamp(0, 255).long()
    else:
        action_byte = ((true_Y + 2) / 4 * 255).clamp(0, 255).long()
    return action_byte


def compute_k_eff(g_t: torch.Tensor) -> float:
    """Compute effective neuromodulator count via participation ratio."""
    g_flat = g_t.view(-1, g_t.size(-1))
    var_k = g_flat.var(dim=0)
    sum_var = var_k.sum()
    sum_var_sq = (var_k ** 2).sum()
    k_eff = ((sum_var ** 2) / (sum_var_sq + 1e-8)).item()
    return k_eff


def train_supervised_meta(
    num_envs: int = 4096,
    num_steps: int = 64,
    total_timesteps: int = 10_000_000,
    num_tasks: int = 100,
    device: str = "cuda",
    log_interval: int = 1,
    save_interval: int = 50,
    save_dir: str = "results",
    demo_steps: int = 10,
    test_steps: int = 10,
):
    """
    Supervised Meta-Learning Training for DoErr and OD-NDT.

    Training Loop Structure:
    1. Sample batch of tasks
    2. DEMO PHASE: Run with oracle actions, collect supervised signal
    3. SLEEP PHASE: Consolidate fast weights
    4. TEST PHASE: Evaluate predictions, backprop through entire sequence
    """
    print("=" * 70)
    print("RPJ Brain - SUPERVISED META-LEARNING (DoErr + OD-NDT Fix)")
    print("=" * 70)
    print(f"  Device: {device}")
    print(f"  Num envs: {num_envs:,}")
    print(f"  Num tasks: {num_tasks}")
    print(f"  Demo steps per task: {demo_steps}")
    print(f"  Test steps per task: {test_steps}")
    print(f"  Total timesteps: {total_timesteps:,}")

    torch.set_float32_matmul_precision('high')

    # Create Multi-Task environment
    print("\n[1/3] Creating Multi-Task CCB-NL environment...")
    env = TorchMultiTaskCCBEnvironment(
        num_envs=num_envs,
        num_tasks=num_tasks,
        switch_interval=demo_steps + test_steps,  # One task per episode
        device=device,
    )
    # Note: TorchMultiTaskCCBEnvironment always uses CCB-NL (nonlinear)
    obs_dim = env.observation_space_bytes
    action_bytes = env.action_space_bytes
    print(f"  Observation: {obs_dim} bytes x {num_envs:,} envs")
    print(f"  Mode: CCB-NL (Y = ReLU(b_X*X² + b_U*U))")

    # Create brain WITH SLEEP ENABLED
    print("\n[2/3] Creating RPJ Brain with Sleep Module...")
    config = RPJConfig(
        obs_dim=obs_dim,
        action_bytes=action_bytes,
        hidden_dim=512,
        k_max=4,
        lambda_g=0.01,
        enable_plasticity=True,
        enable_sleep=True,  # ENABLE SLEEP for consolidation
    )
    brain = RPJBrain(config).to(device)
    brain.train()

    params = brain.count_parameters()
    print(f"  Total parameters: {params['total']:,}")
    print(f"  Plasticity: ENABLED")
    print(f"  Sleep: ENABLED")

    optimizer = torch.optim.Adam(brain.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=total_timesteps // (num_envs * num_steps), eta_min=1e-5
    )

    # Initialize states
    h = torch.zeros(num_envs, config.hidden_dim, device=device)
    g = torch.zeros(num_envs, config.k_max, device=device)
    a_prev = torch.zeros(num_envs, action_bytes, dtype=torch.long, device=device)

    print(f"\n[3/3] Training with Demo→Sleep→Test curriculum...")
    print("-" * 70)
    print("Objective: Learn to predict E[Y|do(X)] via supervised meta-learning")
    print("-" * 70)

    total_steps = 0
    num_updates = 0
    start_time = time.perf_counter()
    k_eff_history = []
    loss_history = []
    doerr_history = []

    while total_steps < total_timesteps:
        # Reset environment (new batch of tasks)
        obs = env.reset()
        h = torch.zeros(num_envs, config.hidden_dim, device=device)
        g = torch.zeros(num_envs, config.k_max, device=device)
        a_prev = torch.zeros(num_envs, action_bytes, dtype=torch.long, device=device)

        total_loss = 0.0
        total_demo_loss = 0.0
        total_test_loss = 0.0
        total_error = 0.0
        all_g = []

        # ====== PHASE 1: DEMO (Teacher Forcing) ======
        # Feed oracle actions, compute supervised loss
        for step in range(demo_steps):
            # Forward pass
            output = brain(obs, h, g, a_prev, training=True)

            # Get oracle target (true_Y from environment)
            # We need to step to get true_Y, but use oracle action
            with torch.no_grad():
                # Compute true_Y for current X
                X_float = obs[:, 0].float() / 127.5 - 1  # Decode X from byte
                true_Y = F.relu(
                    env.current_b_X * X_float ** 2 + env.current_b_U * 0.5
                )  # E[Y|do(X)]
                target_action = quantize_y_to_action(true_Y, nonlinear=True)

            # Supervised loss on continuous action_mu (DIFFERENTIABLE!)
            # DEEP-DEBUG FIX: output.action is sampled (int64, non-differentiable)
            # output.action_mu is the continuous prediction from GaussianActionHead [batch]
            predicted_Y = output.action_mu / 255.0 * 1.55 + 0.1  # Scale action_mu to Y range
            demo_loss = F.mse_loss(predicted_Y, true_Y)
            total_demo_loss += demo_loss

            # Step environment with oracle action (for state progression)
            next_obs, reward, done, info = env.step(target_action)

            # Track error (DoErr metric)
            step_error = (predicted_Y - true_Y).abs().mean()
            total_error += step_error.item()

            # Update state
            h = output.h_next
            g = output.g_t
            a_prev = target_action.unsqueeze(-1)
            obs = next_obs
            all_g.append(g.clone())

            # Reset done envs
            h = torch.where(done.unsqueeze(-1), torch.zeros_like(h), h)
            g = torch.where(done.unsqueeze(-1), torch.zeros_like(g), g)

        # ====== PHASE 2: SLEEP (Consolidation) ======
        # Let sleep module process if available
        if brain.sleep is not None:
            with torch.no_grad():
                # Create pseudo-replay buffer from demo
                demo_g = torch.stack(all_g, dim=0)  # [demo_steps, batch, k_max]
                demo_h = h.clone()

                # Sleep consolidation (simplified - just scale fast weights)
                # In full implementation, would run sleep algorithm
                if brain.plasticity is not None:
                    # Apply gating based on g activity during demo
                    g_activity = demo_g.abs().mean(dim=0)  # [batch, k_max]
                    consolidation_signal = (g_activity > 0.01).float()

                    # Scale fast weights by consolidation signal (simplified)
                    brain.plasticity.recurrent_adapter.A *= 0.99
                    brain.plasticity.recurrent_adapter.B *= 0.99

        # ====== PHASE 3: TEST (Evaluate Transfer) ======
        # Continue in same task, but now evaluate prediction quality
        for step in range(test_steps):
            # Forward pass
            output = brain(obs, h, g, a_prev, training=True)

            # Get ground truth
            with torch.no_grad():
                X_float = obs[:, 0].float() / 127.5 - 1
                true_Y = F.relu(
                    env.current_b_X * X_float ** 2 + env.current_b_U * 0.5
                )
                target_action = quantize_y_to_action(true_Y, nonlinear=True)

            # Supervised loss on continuous action_mu (DIFFERENTIABLE!)
            predicted_Y = output.action_mu / 255.0 * 1.55 + 0.1
            test_loss = F.mse_loss(predicted_Y, true_Y)
            total_test_loss += test_loss

            # Step with PREDICTED action (not oracle)
            next_obs, reward, done, info = env.step(output.action.squeeze(-1))

            # Track error (this is what matters for DoErr)
            step_error = (predicted_Y - true_Y).abs().mean()
            total_error += step_error.item()

            # Update state
            h = output.h_next
            g = output.g_t
            a_prev = output.action
            obs = next_obs
            all_g.append(g.clone())

            h = torch.where(done.unsqueeze(-1), torch.zeros_like(h), h)
            g = torch.where(done.unsqueeze(-1), torch.zeros_like(g), g)

        # ====== COMPUTE TOTAL LOSS ======
        # Weight demo loss higher initially, test loss for transfer
        demo_weight = max(0.5, 1.0 - num_updates / 1000)  # Anneal demo weight
        test_weight = 1.0 - demo_weight + 0.5

        total_loss = demo_weight * total_demo_loss + test_weight * total_test_loss

        # Add sparsity penalty on g
        g_stack = torch.stack(all_g, dim=0)
        g_sparsity = g_stack.abs().mean() * config.lambda_g
        total_loss += g_sparsity

        # ====== BACKWARD PASS ======
        optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(brain.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        total_steps += num_envs * (demo_steps + test_steps)
        num_updates += 1

        # Compute metrics
        k_eff = compute_k_eff(g_stack)
        avg_error = total_error / (demo_steps + test_steps)
        k_eff_history.append(k_eff)
        loss_history.append(total_loss.item())
        doerr_history.append(avg_error)

        # Logging
        if num_updates % log_interval == 0:
            elapsed = time.perf_counter() - start_time
            fps = total_steps / elapsed

            print(f"Update {num_updates:4d} | "
                  f"Steps: {total_steps:>10,} | "
                  f"FPS: {fps:>7,.0f} | "
                  f"Loss: {total_loss.item():>6.3f} | "
                  f"DoErr: {avg_error:>6.4f} | "
                  f"K_eff: {k_eff:>4.2f} | "
                  f"LR: {scheduler.get_last_lr()[0]:.1e}")

        # Save checkpoint
        if num_updates % save_interval == 0:
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            ckpt_path = save_path / f"checkpoint_supervised_{total_steps:08d}.pt"
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
                    'supervised': True,
                },
                'k_eff_history': k_eff_history,
                'doerr_history': doerr_history,
            }, ckpt_path)
            print(f"  >>> Checkpoint saved: {ckpt_path}")

    # Final summary
    total_time = time.perf_counter() - start_time
    final_fps = total_steps / total_time

    # Final metrics
    k_eff_final = np.mean(k_eff_history[-10:])
    doerr_final = np.mean(doerr_history[-10:])

    print("-" * 70)
    print("SUPERVISED META-LEARNING Complete!")
    print("-" * 70)
    print(f"  Total steps: {total_steps:,}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Average FPS: {final_fps:,.0f}")

    print(f"\n=== METRICS ===")
    print(f"  K_eff (final): {k_eff_final:.2f} (target: [2-6])")
    print(f"  DoErr (final): {doerr_final:.4f} (target: ≤0.05)")

    # Pass/fail
    k_eff_pass = 2.0 <= k_eff_final <= 6.0
    doerr_pass = doerr_final <= 0.05

    print(f"\n=== VALIDATION ===")
    print(f"  K_eff in [2-6]: {'PASS' if k_eff_pass else 'FAIL'}")
    print(f"  DoErr ≤ 0.05:   {'PASS' if doerr_pass else 'FAIL'}")

    # Save final checkpoint
    final_ckpt_path = Path(save_dir) / f"checkpoint_supervised_final_{total_steps:08d}.pt"
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
            'supervised': True,
        },
        'k_eff_history': k_eff_history,
        'doerr_history': doerr_history,
        'final_metrics': {
            'k_eff': k_eff_final,
            'doerr': doerr_final,
            'k_eff_pass': k_eff_pass,
            'doerr_pass': doerr_pass,
        }
    }, final_ckpt_path)
    print(f"\n  Final checkpoint: {final_ckpt_path}")

    return brain


def main():
    parser = argparse.ArgumentParser(description="Supervised Meta-Learning Training")
    parser.add_argument("--num-envs", type=int, default=4096)
    parser.add_argument("--timesteps", type=int, default=10_000_000)
    parser.add_argument("--demo-steps", type=int, default=10)
    parser.add_argument("--test-steps", type=int, default=10)
    parser.add_argument("--log-interval", type=int, default=1)
    parser.add_argument("--save-interval", type=int, default=50)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("WARNING: CUDA not available, running on CPU")
        args.num_envs = 64

    train_supervised_meta(
        num_envs=args.num_envs,
        total_timesteps=args.timesteps,
        demo_steps=args.demo_steps,
        test_steps=args.test_steps,
        device=device,
        log_interval=args.log_interval,
        save_interval=args.save_interval,
    )


if __name__ == "__main__":
    main()
