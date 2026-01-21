#!/usr/bin/env python3
"""
Cross-Modal Training Script for RPJ Brain

WEED 420 WINNER: Train the brain to narrate its own CCB reasoning.

This script:
1. Loads the trained CCB brain (with emergence K_eff=5.28)
2. Fine-tunes on interleaved CCB + text sequences
3. Brain learns to describe its causal reasoning in language

Training Format:
- NUMERIC: [Z_byte, X_byte] -> [Y_byte] (backward compat)
- INTERLEAVE: <#[Z][X]@confound [desc]|do [desc]?> -> <#[Y]@effect [desc]>
- TEXT: @confound [desc]|do [desc]? -> @effect [desc]

The brain processes bytes autoregressively, one at a time.
Hidden state accumulates across the sequence.
"""

import argparse
import sys
import os
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.rpj_brain import RPJBrain, RPJConfig
from src.benchmarks.cross_modal_ccb import CrossModalCCBEnv, CrossModalConfig


def create_sequence_brain(base_checkpoint: str, device: torch.device) -> RPJBrain:
    """Load the base CCB brain and prepare for sequence processing.

    Args:
        base_checkpoint: Path to trained CCB checkpoint
        device: Torch device

    Returns:
        RPJBrain configured for byte-by-byte sequence processing
    """
    # Create brain with obs_dim=1 (one byte at a time)
    config = RPJConfig(
        obs_dim=1,  # Process one byte at a time
        action_bytes=1,  # Generate one byte at a time
        enable_plasticity=False,  # Disable for faster inference
        enable_sleep=False,
        num_envs=1,
    )

    brain = RPJBrain(config).to(device)

    # Load base checkpoint if it exists
    if os.path.exists(base_checkpoint):
        print(f"Loading base checkpoint: {base_checkpoint}")
        checkpoint = torch.load(base_checkpoint, map_location=device)

        # Load compatible weights (substrate, VAE, etc.)
        # Skip incompatible ones (obs_dim changed)
        state_dict = checkpoint.get("brain_state_dict", checkpoint)
        compatible_keys = []

        for key in state_dict.keys():
            try:
                # Try to get corresponding param shape
                param = brain.state_dict()[key]
                if param.shape == state_dict[key].shape:
                    compatible_keys.append(key)
            except KeyError:
                pass

        # Load only compatible weights
        filtered_dict = {k: state_dict[k] for k in compatible_keys}
        brain.load_state_dict(filtered_dict, strict=False)
        print(f"  Loaded {len(compatible_keys)}/{len(state_dict)} compatible weights")
    else:
        print(f"No checkpoint found at {base_checkpoint}, training from scratch")

    return brain


def process_sequence(
    brain: RPJBrain,
    input_bytes: torch.Tensor,
    target_bytes: torch.Tensor,
    seq_len: int,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Process a single sequence through the brain.

    Args:
        brain: RPJ Brain
        input_bytes: Input byte sequence [seq_len]
        target_bytes: Target byte sequence [seq_len]
        seq_len: Actual sequence length (before padding)
        device: Torch device

    Returns:
        loss: Cross-entropy loss
        k_eff: Effective neuromodulator count (emergence metric)
    """
    # Initialize state
    h, g = brain.init_state(batch_size=1, device=device)
    a_prev = torch.zeros(1, dtype=torch.long, device=device)

    total_loss = 0.0
    g_history = []

    # Process input sequence byte-by-byte
    for t in range(seq_len):
        obs_byte = input_bytes[t:t+1].unsqueeze(0)  # [1, 1]

        # Forward pass
        output = brain(obs_byte, h, g, a_prev, training=True)

        # Update state
        h = output.h_next
        g = output.g_t
        a_prev = output.action[:, 0]
        g_history.append(g)

        # Loss only on target positions (after input consumed)
        if t < len(target_bytes):
            target = target_bytes[t].unsqueeze(0)  # [1]
            # Use action_mu for cross-entropy (continuous prediction)
            pred_logits = output.action_mu.unsqueeze(-1)  # [1, 1]
            # For byte prediction, we need 256-way classification
            # But action_mu is continuous, so use MSE for now
            target_float = target.float() / 255.0  # Normalize to [0, 1]
            loss = F.mse_loss(torch.sigmoid(output.action_mu), target_float)
            total_loss += loss

    # Compute K_eff from g_history
    if g_history:
        g_stack = torch.stack(g_history, dim=0)  # [T, 1, k_max]
        g_mean = g_stack.mean(dim=0).squeeze(0)  # [k_max]
        p = F.softmax(g_mean, dim=-1)
        k_eff = 1.0 / (p ** 2).sum()
    else:
        k_eff = torch.tensor(1.0, device=device)

    return total_loss / max(1, seq_len), k_eff


def train_batch(
    brain: RPJBrain,
    inputs: torch.Tensor,
    targets: torch.Tensor,
    lens: torch.Tensor,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> dict:
    """Train on a batch of cross-modal sequences.

    Args:
        brain: RPJ Brain
        inputs: Input sequences [batch, max_seq_len]
        targets: Target sequences [batch, max_seq_len]
        lens: Sequence lengths [batch]
        optimizer: Optimizer
        device: Torch device

    Returns:
        Dict with loss and metrics
    """
    brain.train()
    optimizer.zero_grad()

    batch_size = inputs.size(0)
    total_loss = 0.0
    total_k_eff = 0.0

    # Process each sequence (could parallelize with proper batching)
    for i in range(batch_size):
        seq_len = lens[i].item()
        loss, k_eff = process_sequence(
            brain,
            inputs[i, :seq_len],
            targets[i, :seq_len],
            seq_len,
            device,
        )
        total_loss += loss
        total_k_eff += k_eff.item()

    # Backward
    avg_loss = total_loss / batch_size
    avg_loss.backward()
    optimizer.step()

    return {
        "loss": avg_loss.item(),
        "k_eff": total_k_eff / batch_size,
    }


def generate_response(
    brain: RPJBrain,
    input_bytes: bytes,
    max_length: int = 32,
    device: torch.device = None,
) -> bytes:
    """Generate a response given input bytes.

    Args:
        brain: Trained RPJ Brain
        input_bytes: Input byte string
        max_length: Maximum response length
        device: Torch device

    Returns:
        Generated response as bytes
    """
    brain.eval()
    device = device or next(brain.parameters()).device

    # Initialize state
    h, g = brain.init_state(batch_size=1, device=device)
    a_prev = torch.zeros(1, dtype=torch.long, device=device)

    # Process input sequence
    for byte_val in input_bytes:
        obs_byte = torch.tensor([[byte_val]], dtype=torch.long, device=device)
        output = brain(obs_byte, h, g, a_prev, training=False)
        h = output.h_next
        g = output.g_t
        a_prev = output.action[:, 0]

    # Generate response
    response = []
    for _ in range(max_length):
        # Use last action as next input (autoregressive)
        obs_byte = a_prev.unsqueeze(0).unsqueeze(0)  # [1, 1]
        output = brain(obs_byte, h, g, a_prev, training=False)

        # Get next byte
        next_byte = output.action[0, 0].item()
        response.append(next_byte)

        # Update state
        h = output.h_next
        g = output.g_t
        a_prev = output.action[:, 0]

        # Stop on end marker
        if next_byte == ord('>'):
            break

    return bytes(response)


def main():
    parser = argparse.ArgumentParser(description="Train Cross-Modal RPJ Brain")
    parser.add_argument("--base-checkpoint", type=str,
                        default="results/checkpoint_multitask_ccb_blindfold.pt",
                        help="Base CCB checkpoint to fine-tune")
    parser.add_argument("--num-envs", type=int, default=64,
                        help="Number of parallel environments")
    parser.add_argument("--steps", type=int, default=10000,
                        help="Training steps")
    parser.add_argument("--lr", type=float, default=1e-4,
                        help="Learning rate")
    parser.add_argument("--log-interval", type=int, default=10,
                        help="Logging interval")
    parser.add_argument("--save-interval", type=int, default=1000,
                        help="Checkpoint save interval")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 70)
    print("RPJ Brain - CROSS-MODAL TRAINING")
    print("=" * 70)
    print(f"  Device: {device}")
    print(f"  Base checkpoint: {args.base_checkpoint}")
    print(f"  Training steps: {args.steps}")
    print()

    # Create brain
    brain = create_sequence_brain(args.base_checkpoint, device)
    print(f"  Brain parameters: {sum(p.numel() for p in brain.parameters()):,}")
    print()

    # Create environment
    env_config = CrossModalConfig(num_envs=args.num_envs, device=str(device))
    env = CrossModalCCBEnv(env_config)

    # Optimizer
    optimizer = AdamW(brain.parameters(), lr=args.lr)

    # Training loop
    print("-" * 70)
    print("Training... (Cross-Modal Grounding)")
    print("-" * 70)

    start_time = time.time()

    for step in range(1, args.steps + 1):
        # Generate batch
        inputs, targets, lens = env.generate_batch()

        # Train
        metrics = train_batch(brain, inputs, targets, lens, optimizer, device)

        # Log
        if step % args.log_interval == 0:
            elapsed = time.time() - start_time
            sps = step * args.num_envs / elapsed
            print(f"Step {step:5d} | Loss: {metrics['loss']:.4f} | "
                  f"K_eff: {metrics['k_eff']:.2f} | SPS: {sps:.0f}")

        # Save
        if step % args.save_interval == 0:
            checkpoint_path = f"results/checkpoint_crossmodal_{step}.pt"
            torch.save({
                "brain_state_dict": brain.state_dict(),
                "step": step,
                "config": brain.config,
            }, checkpoint_path)
            print(f"  Saved: {checkpoint_path}")

            # Test generation
            test_input = b"@confound large pos|do small neg?"
            response = generate_response(brain, test_input, device=device)
            print(f"  Test: {test_input} -> {response}")

    # Final save
    final_path = "results/checkpoint_crossmodal_final.pt"
    torch.save({
        "brain_state_dict": brain.state_dict(),
        "step": args.steps,
        "config": brain.config,
    }, final_path)

    print("-" * 70)
    print("CROSS-MODAL TRAINING COMPLETE")
    print("-" * 70)
    print(f"  Final checkpoint: {final_path}")


if __name__ == "__main__":
    main()
