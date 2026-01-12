#!/usr/bin/env python3
"""
CCB Training Script for RPJ Brain v2.

Runs the full training pipeline on the Confounded Causal Bandits environment.

Usage:
    python scripts/train_ccb.py [--timesteps N] [--device cpu/cuda]
"""

import argparse
import json
import os
from datetime import datetime

import torch

from src.core.ppo_trainer import create_trainer, PPOConfig
from src.benchmarks.ccb import CCBEnvironment


def main():
    parser = argparse.ArgumentParser(description="Train RPJ Brain on CCB")
    parser.add_argument("--timesteps", type=int, default=10000, help="Total training timesteps")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu or cuda)")
    parser.add_argument("--log-interval", type=int, default=10, help="Log every N updates")
    parser.add_argument("--save-stats", action="store_true", help="Save training stats to JSON")
    parser.add_argument("--save-checkpoint", action="store_true", help="Save model checkpoint")
    parser.add_argument("--checkpoint-interval", type=int, default=10000, help="Save checkpoint every N timesteps")
    args = parser.parse_args()

    print("=" * 60)
    print("RPJ Brain v2 - CCB Training")
    print("=" * 60)

    # Create environment
    print("\n[1/3] Creating CCB environment...")
    env = CCBEnvironment()
    print(f"  Observation: 8 bytes (Z + target_X)")
    print(f"  Action: 1 byte (predicted Y)")

    # Create brain and trainer
    print("\n[2/3] Creating RPJ Brain v2...")
    config = PPOConfig(
        num_steps_per_update=256,
        num_epochs=4,
        minibatch_size=64,
        sleep_train_freq=20,  # Sleep every 20 updates
    )
    brain, trainer = create_trainer(
        obs_dim=8,
        action_bytes=1,
        device=args.device,
    )
    trainer.config = config

    params = brain.count_parameters()
    print(f"\n  Parameter counts:")
    for name, count in params.items():
        print(f"    {name}: {count:,}")

    # Verify fast param budget
    if brain.plasticity is not None:
        fast = brain.plasticity.count_fast_parameters()
        total = params['total']
        budget = min(500_000, int(0.05 * total))
        status = "OK" if fast <= budget else "EXCEEDED!"
        print(f"\n  Fast param budget: {fast:,} / {budget:,} ({status})")

    # Train
    print(f"\n[3/3] Training for {args.timesteps:,} timesteps...")
    print("-" * 60)

    all_stats = []
    last_checkpoint_step = 0

    def callback(stats):
        """Track collapse and early divergence per JARVIS recommendation."""
        nonlocal last_checkpoint_step
        all_stats.append(stats)

        # Log collapse metric early (first 1000 timesteps)
        if stats['timesteps'] <= 1000 and stats['timesteps'] % 256 == 0:
            h = stats.get('collapse_entropy', 0)
            if h < 0.1:
                print(f"  [WARN] Low collapse entropy at step {stats['timesteps']}: H={h:.4f}")

        # Save checkpoint at intervals
        if args.save_checkpoint and stats['timesteps'] - last_checkpoint_step >= args.checkpoint_interval:
            last_checkpoint_step = stats['timesteps']
            ckpt_filename = f"checkpoint_{stats['timesteps']:06d}.pt"
            torch.save({
                'brain_state_dict': brain.state_dict(),
                'trainer_update_count': trainer.update_count,
                'timesteps': stats['timesteps'],
                'config': {
                    'obs_dim': 8,
                    'action_bytes': 1,
                },
            }, ckpt_filename)
            print(f"  [CHECKPOINT] Saved {ckpt_filename}")

    stats = trainer.train(
        env,
        total_timesteps=args.timesteps,
        log_interval=args.log_interval,
        callback=callback,
    )

    # Summary
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)

    final = stats[-1]
    print(f"\nFinal Stats:")
    print(f"  Timesteps: {final['timesteps']:,}")
    print(f"  Extrinsic Reward: {final.get('mean_extrinsic_reward', 0):.3f}")
    print(f"  RPJ Reward: {final.get('mean_rpj_reward', 0):.3f}")
    print(f"  Policy Loss: {final.get('policy_loss', 0):.4f}")
    print(f"  VAE Loss: {final.get('vae_loss', 0):.4f}")
    print(f"  Collapse H: {final.get('collapse_entropy', 0):.4f}")
    print(f"  Total Energy: {final.get('energy_J', 0):.2f} J")

    # Emergence metrics
    k_eff = final.get('K_eff', 16.0)
    cbr_b = final.get('cbr_bimodality', 0)
    k_status = "TARGET (2-6)" if 2 <= k_eff <= 6 else f"not compressed ({k_eff:.1f})"
    cbr_status = "BIMODAL" if cbr_b > 0.555 else "unimodal"
    print(f"\n  Emergence Metrics:")
    print(f"    K_eff: {k_eff:.2f} ({k_status})")
    print(f"    CBR_B: {cbr_b:.3f} ({cbr_status})")
    print(f"    k_r mean: {final.get('k_r_mean', 0):.2f}")
    print(f"    n_t mean: {final.get('n_t_mean', 0):.2f}")

    # Check for collapse
    min_collapse = min(s.get('collapse_entropy', 1.0) for s in all_stats)
    if min_collapse < 0.05:
        print(f"\n[WARN] Collapse detected! Minimum H(c_t) = {min_collapse:.4f}")
    else:
        print(f"\n[OK] No collapse detected. Min H(c_t) = {min_collapse:.4f}")

    # Save final checkpoint
    if args.save_checkpoint:
        final_ckpt = f"checkpoint_final_{final['timesteps']:06d}.pt"
        torch.save({
            'brain_state_dict': brain.state_dict(),
            'trainer_update_count': trainer.update_count,
            'timesteps': final['timesteps'],
            'config': {
                'obs_dim': 8,
                'action_bytes': 1,
            },
        }, final_ckpt)
        print(f"\nFinal checkpoint saved to: {final_ckpt}")

    # Save stats if requested
    if args.save_stats:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ccb_training_{timestamp}.json"

        # Convert tensors to floats for JSON serialization
        serializable_stats = []
        for s in all_stats:
            clean_s = {}
            for k, v in s.items():
                if isinstance(v, torch.Tensor):
                    clean_s[k] = v.item() if v.numel() == 1 else v.tolist()
                else:
                    clean_s[k] = v
            serializable_stats.append(clean_s)

        with open(filename, 'w') as f:
            json.dump(serializable_stats, f, indent=2)
        print(f"\nStats saved to: {filename}")

    print("\nDone!")


if __name__ == "__main__":
    main()
