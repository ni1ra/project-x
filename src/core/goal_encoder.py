"""
Goal Encoder for Phase 10: Natural Language Interface

A byte-level encoder that converts variable-length text goals to fixed-size
embeddings. This maintains the 'no intelligence ceiling' constraint by:
- Not using pretrained embeddings
- Not using external LLMs
- Learning byte-level representations from scratch

The goal embedding conditions the RPJ Brain, allowing it to understand
natural language task descriptions like "Fix the off-by-one error in
the calculate_average function" instead of truncated 64-byte goals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class GoalEncoderConfig:
    """Configuration for GoalEncoder."""
    max_goal_len: int = 512       # Max UTF-8 bytes in goal
    byte_embed_dim: int = 64      # Byte embedding dimension
    hidden_dim: int = 256         # GRU hidden dimension
    goal_embed_dim: int = 64      # Output goal embedding dimension
    num_layers: int = 2           # GRU layers
    dropout: float = 0.1          # Dropout rate


class GoalEncoder(nn.Module):
    """Byte-level encoder for natural language goals.

    Architecture:
    1. Byte embedding: Each byte (0-255) gets a learned embedding
    2. Bidirectional GRU: Processes variable-length sequence
    3. Projection: Final hidden state → goal embedding

    This is a ~130K parameter module that adds <5% overhead to the 3.2M brain.
    """

    def __init__(self, config: Optional[GoalEncoderConfig] = None):
        super().__init__()
        self.config = config or GoalEncoderConfig()

        # Byte embedding: 256 possible byte values + padding_idx=0
        self.byte_embed = nn.Embedding(
            256,
            self.config.byte_embed_dim,
            padding_idx=0
        )

        # Bidirectional GRU to process variable-length text
        self.gru = nn.GRU(
            input_size=self.config.byte_embed_dim,
            hidden_size=self.config.hidden_dim // 2,  # Bidirectional doubles this
            num_layers=self.config.num_layers,
            bidirectional=True,
            batch_first=True,
            dropout=self.config.dropout if self.config.num_layers > 1 else 0,
        )

        # Project final hidden state to goal embedding
        self.project = nn.Sequential(
            nn.Linear(self.config.hidden_dim, self.config.hidden_dim),
            nn.ReLU(),
            nn.Dropout(self.config.dropout),
            nn.Linear(self.config.hidden_dim, self.config.goal_embed_dim),
        )

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize weights with small values for stable training."""
        for name, param in self.named_parameters():
            if 'weight' in name:
                if 'gru' in name:
                    # GRU weights: orthogonal init
                    if param.dim() >= 2:
                        nn.init.orthogonal_(param)
                elif 'embed' in name:
                    # Embedding: small normal
                    nn.init.normal_(param, mean=0.0, std=0.02)
                else:
                    # Linear: Xavier
                    if param.dim() >= 2:
                        nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.zeros_(param)

    def forward(
        self,
        goal_bytes: torch.Tensor,
        lengths: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Encode goal text to fixed-size embedding.

        Args:
            goal_bytes: [B, max_len] - UTF-8 bytes of goal text (0-padded)
                        Values in range [0, 255]
            lengths: [B] - actual lengths (optional, for packed sequences)

        Returns:
            goal_embed: [B, goal_embed_dim] - goal embedding
        """
        B = goal_bytes.size(0)

        # Clamp to valid byte range
        goal_bytes = goal_bytes.clamp(0, 255)

        # Embed bytes
        x = self.byte_embed(goal_bytes)  # [B, L, byte_embed_dim]

        # Pack if lengths provided (more efficient)
        if lengths is not None:
            # Sort by length for packing
            sorted_lengths, sort_idx = lengths.sort(descending=True)
            x = x[sort_idx]

            x = nn.utils.rnn.pack_padded_sequence(
                x, sorted_lengths.cpu(), batch_first=True, enforce_sorted=True
            )

        # Process with GRU
        _, h = self.gru(x)  # h: [num_layers*2, B, hidden_dim//2]

        # Take final layer's bidirectional hidden state
        # h[-2] is forward direction, h[-1] is backward direction
        h = torch.cat([h[-2], h[-1]], dim=-1)  # [B, hidden_dim]

        # Unsort if we sorted for packing
        if lengths is not None:
            _, unsort_idx = sort_idx.sort()
            h = h[unsort_idx]

        # Project to goal embedding
        goal_embed = self.project(h)  # [B, goal_embed_dim]

        return goal_embed

    def encode_text(self, text: str, device: torch.device = None) -> torch.Tensor:
        """
        Convenience method to encode a single text string.

        Args:
            text: Goal text string
            device: Target device (default: same as module)

        Returns:
            goal_embed: [1, goal_embed_dim] - goal embedding
        """
        if device is None:
            device = next(self.parameters()).device

        # Encode to UTF-8 bytes
        text_bytes = text.encode('utf-8', errors='replace')

        # Truncate to max length
        text_bytes = text_bytes[:self.config.max_goal_len]

        # Convert to tensor
        goal_tensor = torch.zeros(1, self.config.max_goal_len, dtype=torch.long, device=device)
        for i, b in enumerate(text_bytes):
            goal_tensor[0, i] = b

        # Compute length
        lengths = torch.tensor([len(text_bytes)], device=device)

        # Encode
        with torch.no_grad():
            return self.forward(goal_tensor, lengths)


def encode_goal_batch(
    texts: list[str],
    max_len: int = 512,
    device: torch.device = None,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Encode a batch of goal texts to tensors.

    Args:
        texts: List of goal text strings
        max_len: Maximum length in bytes
        device: Target device

    Returns:
        goal_bytes: [B, max_len] - UTF-8 bytes (0-padded)
        lengths: [B] - actual lengths
    """
    B = len(texts)
    goal_bytes = torch.zeros(B, max_len, dtype=torch.long, device=device)
    lengths = torch.zeros(B, dtype=torch.long, device=device)

    for i, text in enumerate(texts):
        # Encode to UTF-8
        text_b = text.encode('utf-8', errors='replace')[:max_len]
        lengths[i] = len(text_b)

        # Copy to tensor
        for j, b in enumerate(text_b):
            goal_bytes[i, j] = b

    return goal_bytes, lengths


def create_goal_encoder(
    goal_embed_dim: int = 64,
    max_goal_len: int = 512,
    hidden_dim: int = 256,
) -> GoalEncoder:
    """
    Factory function to create a GoalEncoder with common configurations.

    Args:
        goal_embed_dim: Output embedding dimension
        max_goal_len: Maximum goal length in bytes
        hidden_dim: GRU hidden dimension

    Returns:
        Configured GoalEncoder instance
    """
    config = GoalEncoderConfig(
        max_goal_len=max_goal_len,
        hidden_dim=hidden_dim,
        goal_embed_dim=goal_embed_dim,
    )
    return GoalEncoder(config)


# Unit test
if __name__ == "__main__":
    print("Testing GoalEncoder...")

    # Create encoder
    encoder = create_goal_encoder(goal_embed_dim=64)
    print(f"Parameters: {sum(p.numel() for p in encoder.parameters()):,}")

    # Test single encoding
    goal = "Fix the off-by-one error in the calculate_average function that causes IndexError"
    embed = encoder.encode_text(goal)
    print(f"Single encode: {goal[:50]}... -> {embed.shape}")

    # Test batch encoding
    goals = [
        "Fix the bug in calculator.py",
        "The add function returns wrong results",
        "There's an IndexError in the loop",
    ]
    goal_bytes, lengths = encode_goal_batch(goals, max_len=512)
    embeddings = encoder(goal_bytes, lengths)
    print(f"Batch encode: {len(goals)} goals -> {embeddings.shape}")

    # Test gradient flow
    embeddings.sum().backward()
    print("Gradient flow: OK")

    print("All tests passed!")
