"""
Cross-Modal Grounding for RPJ Brain - The "Narrator" System

WEED 420 WINNER: Train the brain to narrate its own CCB reasoning.

Design Philosophy:
- Brain is a 1.5M param SAVANT, not a general chatbot
- It can articulate ONLY what it understands: causal reasoning
- Interleave CCB numeric tasks with text descriptions
- Brain learns: "When I predict Y=0.3, I should say 'effect is small positive'"

The Intelligence Ceiling is RESPECTED:
- No LLM dependencies
- Brain does ALL reasoning itself
- Language is grounded in causal physics the brain already knows
"""

import torch
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional, Tuple, List
import random


@dataclass
class CrossModalConfig:
    """Configuration for Cross-Modal CCB training."""
    num_envs: int = 1024
    max_seq_len: int = 64  # Max bytes per sequence
    vocab_size: int = 256  # Byte-level (0-255)
    device: str = "cuda" if torch.cuda.is_available() else "cpu"

    # CCB parameters
    z_range: Tuple[float, float] = (-2.0, 2.0)
    x_range: Tuple[float, float] = (-2.0, 2.0)

    # Text mode probabilities
    numeric_only_prob: float = 0.3  # Pure CCB (backward compat)
    text_interleave_prob: float = 0.5  # CCB with text narration
    text_only_prob: float = 0.2  # Text-only queries/responses


# Domain-specific vocabulary for CCB narration
# Each "word" is stored as UTF-8 bytes
CAUSAL_VOCABULARY = {
    # Core causal terms
    "cause": b"cause",
    "effect": b"effect",
    "confound": b"confound",
    "intervention": b"do",  # do(X=x) notation
    "observe": b"see",

    # Magnitude descriptors
    "large": b"large",
    "small": b"small",
    "medium": b"medium",
    "zero": b"zero",
    "none": b"none",

    # Direction descriptors
    "positive": b"pos",
    "negative": b"neg",
    "increase": b"up",
    "decrease": b"down",

    # Structure markers
    "start": b"<",
    "end": b">",
    "separator": b"|",
    "numeric": b"#",
    "text": b"@",

    # Special tokens
    "query": b"?",
    "answer": b"=",
    "newline": b"\n",
}


def float_to_description(value: float) -> bytes:
    """Convert a float value to a text description.

    Examples:
        0.8 -> "large pos"
        -0.3 -> "small neg"
        0.0 -> "zero"
    """
    if abs(value) < 0.1:
        return b"zero"

    magnitude = b"small" if abs(value) < 0.5 else b"large"
    direction = b"pos" if value > 0 else b"neg"

    return magnitude + b" " + direction


def float_to_numeric_bytes(value: float) -> bytes:
    """Convert float to numeric byte representation.

    Encodes as: sign byte + magnitude byte
    Range: [-2, 2] -> [0, 255] for each component
    """
    # Clamp to valid range
    value = max(-2.0, min(2.0, value))

    # Encode as single byte in [0, 255]
    byte_val = int((value + 2.0) / 4.0 * 255)
    return bytes([byte_val])


class CrossModalCCBEnv:
    """
    Cross-Modal CCB Environment

    Generates training sequences that interleave numeric CCB with text.

    Sequence Types:
    1. NUMERIC_ONLY: [Z_byte, X_byte] -> [Y_byte]
       (Original CCB format for backward compatibility)

    2. TEXT_INTERLEAVE: [Z_byte, X_byte, "confound=", Z_text, "|", "do=", X_text, "?"] -> [Y_byte, "=", Y_text]
       (CCB with narration - teaches grounding)

    3. TEXT_ONLY: ["confound large pos|do small neg?"] -> ["effect small neg"]
       (Pure text queries - tests understanding)
    """

    def __init__(self, config: CrossModalConfig):
        self.config = config
        self.device = torch.device(config.device)

        # Initialize task parameters (CCB coefficients)
        self._sample_new_tasks()

        # Current state
        self.current_Z = torch.zeros(config.num_envs, device=self.device)
        self.current_X = torch.zeros(config.num_envs, device=self.device)

        # Sequence buffers
        self.input_seqs = []  # List of byte tensors
        self.target_seqs = []  # List of byte tensors

    def _sample_new_tasks(self):
        """Sample new CCB task coefficients."""
        self.b_X = torch.rand(self.config.num_envs, device=self.device) * 2 - 1  # [-1, 1]
        self.b_U = torch.rand(self.config.num_envs, device=self.device) * 2 - 1  # [-1, 1]

    def _compute_true_Y(self, X: torch.Tensor) -> torch.Tensor:
        """Compute true causal effect Y = b_X * X + noise."""
        noise = torch.randn_like(X) * 0.1
        return self.b_X * X + noise

    def generate_batch(self) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Generate a batch of cross-modal training sequences.

        Returns:
            input_bytes: (num_envs, max_seq_len) - padded input sequences
            target_bytes: (num_envs, max_seq_len) - padded target sequences
            seq_lens: (num_envs,) - actual lengths of each sequence
        """
        batch_inputs = []
        batch_targets = []
        batch_lens = []

        for env_idx in range(self.config.num_envs):
            # Decide sequence type
            r = random.random()

            if r < self.config.numeric_only_prob:
                inp, tgt = self._generate_numeric_only(env_idx)
            elif r < self.config.numeric_only_prob + self.config.text_interleave_prob:
                inp, tgt = self._generate_text_interleave(env_idx)
            else:
                inp, tgt = self._generate_text_only(env_idx)

            batch_inputs.append(inp)
            batch_targets.append(tgt)
            batch_lens.append(len(inp))

        # Pad to max length
        max_len = min(max(batch_lens), self.config.max_seq_len)

        padded_inputs = torch.zeros(self.config.num_envs, max_len, dtype=torch.long, device=self.device)
        padded_targets = torch.zeros(self.config.num_envs, max_len, dtype=torch.long, device=self.device)
        seq_lens = torch.tensor(batch_lens, dtype=torch.long, device=self.device)

        for i, (inp, tgt) in enumerate(zip(batch_inputs, batch_targets)):
            inp_len = min(len(inp), max_len)
            tgt_len = min(len(tgt), max_len)
            padded_inputs[i, :inp_len] = torch.tensor(list(inp[:inp_len]), dtype=torch.long, device=self.device)
            padded_targets[i, :tgt_len] = torch.tensor(list(tgt[:tgt_len]), dtype=torch.long, device=self.device)

        return padded_inputs, padded_targets, seq_lens

    def _generate_numeric_only(self, env_idx: int) -> Tuple[bytes, bytes]:
        """Generate pure numeric CCB sequence (original format)."""
        # Sample Z and X
        Z = random.uniform(*self.config.z_range)
        X = random.uniform(*self.config.x_range)

        # Compute true Y
        b_X = self.b_X[env_idx].item()
        Y = b_X * X + random.gauss(0, 0.1)

        # Encode as bytes
        Z_byte = float_to_numeric_bytes(Z)
        X_byte = float_to_numeric_bytes(X)
        Y_byte = float_to_numeric_bytes(Y)

        return Z_byte + X_byte, Y_byte

    def _generate_text_interleave(self, env_idx: int) -> Tuple[bytes, bytes]:
        """Generate CCB with text narration.

        Format: <#[Z][X]@confound [desc]|do [desc]?> -> <#[Y]@effect [desc]>

        Example: <#\x80\x60@confound zero|do small pos?> -> <#\x70@effect small neg>
        """
        # Sample Z and X
        Z = random.uniform(*self.config.z_range)
        X = random.uniform(*self.config.x_range)

        # Compute true Y
        b_X = self.b_X[env_idx].item()
        Y = b_X * X + random.gauss(0, 0.1)
        Y = max(-2.0, min(2.0, Y))  # Clamp

        # Build input sequence
        Z_byte = float_to_numeric_bytes(Z)
        X_byte = float_to_numeric_bytes(X)
        Z_desc = float_to_description(Z)
        X_desc = float_to_description(X)

        inp = b"<#" + Z_byte + X_byte + b"@confound " + Z_desc + b"|do " + X_desc + b"?>"

        # Build target sequence
        Y_byte = float_to_numeric_bytes(Y)
        Y_desc = float_to_description(Y)

        tgt = b"<#" + Y_byte + b"@effect " + Y_desc + b">"

        return inp, tgt

    def _generate_text_only(self, env_idx: int) -> Tuple[bytes, bytes]:
        """Generate pure text query/response.

        Format: @confound [desc]|do [desc]? -> @effect [desc]

        Example: @confound zero|do large pos? -> @effect large pos
        """
        # Sample Z and X
        Z = random.uniform(*self.config.z_range)
        X = random.uniform(*self.config.x_range)

        # Compute true Y
        b_X = self.b_X[env_idx].item()
        Y = b_X * X + random.gauss(0, 0.1)
        Y = max(-2.0, min(2.0, Y))

        # Build sequences
        Z_desc = float_to_description(Z)
        X_desc = float_to_description(X)
        Y_desc = float_to_description(Y)

        inp = b"@confound " + Z_desc + b"|do " + X_desc + b"?"
        tgt = b"@effect " + Y_desc

        return inp, tgt

    def step(self, actions: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, dict]:
        """Take a step in the environment (for RL compatibility).

        Args:
            actions: (num_envs,) predicted Y values as bytes

        Returns:
            obs: Next observation
            reward: Based on prediction error
            done: Episode termination flags
            info: Additional info dict
        """
        # For now, generate new batch and return
        # This maintains API compatibility with existing training code
        inputs, targets, lens = self.generate_batch()

        # Reward is based on how well actions match targets
        # For simplicity, use first target byte as the main signal
        target_first = targets[:, 0].float()
        pred = actions.float()

        # MSE-based reward (negative error)
        error = (pred - target_first) ** 2
        reward = -error

        # Always generate new samples (no episode termination)
        done = torch.zeros(self.config.num_envs, dtype=torch.bool, device=self.device)

        return inputs, reward, done, {"targets": targets, "lens": lens}


class CrossModalDataset:
    """Dataset wrapper for cross-modal training."""

    def __init__(self, config: CrossModalConfig, num_samples: int = 100000):
        self.env = CrossModalCCBEnv(config)
        self.num_samples = num_samples
        self.config = config

    def __len__(self):
        return self.num_samples

    def __iter__(self):
        """Yield batches of cross-modal sequences."""
        samples_generated = 0

        while samples_generated < self.num_samples:
            inputs, targets, lens = self.env.generate_batch()
            samples_generated += self.config.num_envs
            yield inputs, targets, lens

            # Resample tasks periodically for diversity
            if samples_generated % (self.config.num_envs * 10) == 0:
                self.env._sample_new_tasks()


def demo_sequences():
    """Demonstrate the cross-modal sequence generation."""
    config = CrossModalConfig(num_envs=5)
    env = CrossModalCCBEnv(config)

    print("=" * 60)
    print("CROSS-MODAL CCB SEQUENCE EXAMPLES")
    print("=" * 60)

    # Generate a few examples of each type
    for seq_type in ["numeric", "interleave", "text"]:
        print(f"\n--- {seq_type.upper()} MODE ---")

        for i in range(3):
            if seq_type == "numeric":
                inp, tgt = env._generate_numeric_only(i)
            elif seq_type == "interleave":
                inp, tgt = env._generate_text_interleave(i)
            else:
                inp, tgt = env._generate_text_only(i)

            print(f"Input:  {inp}")
            print(f"Target: {tgt}")
            print(f"Input (hex):  {inp.hex()}")
            print(f"Target (hex): {tgt.hex()}")
            print()


if __name__ == "__main__":
    demo_sequences()
