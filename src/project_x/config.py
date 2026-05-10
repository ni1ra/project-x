from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    """Small default config for CPU smoke tests and architecture prototyping."""

    vocab_size: int = 256
    dim: int = 128
    depth: int = 4
    heads: int = 4
    memory_slots: int = 16
    expert_count: int = 4
    top_k_experts: int = 2
    max_seq_len: int = 128
    dropout: float = 0.0


@dataclass(frozen=True)
class RunConfig:
    seed: int = 1337
    batch_size: int = 2
    seq_len: int = 32
    steps: int = 2

