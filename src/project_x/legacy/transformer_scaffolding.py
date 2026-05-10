"""LEGACY — Phase 1-6 transformer scaffolding kept as historical control.

NOT part of the organic Phase 9+ stack. Do not import from this module in any
organic-thesis code. The from-scratch organic encoder + HDC memory + agent
loop in `src/project_x/experiments/` is the active codebase per lain's
post-transformer thesis (2026-05-09 17:53 CEST: *"slow and methodical path...
organic and real from the core and the beginning. No borrowing other LLM
models, remember, we are moving past the transformer."*).

This file holds:
  - `GlobalMemory` — learned memory slots + softmax read
  - `LocalCausalAttention` — standard masked dot-product attention
  - `RoutedExperts` — tiny MoE for routing-stat experiments
  - `XBlock` — composition of the three above
  - `ProjectXModel` — seed transformer architecture used in Phase 1-6 ablations

It survives because:
  - The Phase 1-6 / Phase 7 ablation runs (long-range copy, dual-rate compressed
    memory, scale-sweep findings M-PROJECTX-006/007/009) reference it as the
    historical control architecture.
  - Future organic-vs-control benchmarks may want to compare against a known
    transformer baseline; quarantining here keeps that option open without
    polluting the organic stack with `import torch.nn` references.

Quarantined location 2026-05-10 by Phase 10 P6 / #00f. Original path:
`src/project_x/model.py`. Update any external import that still points at the
old path: `from project_x.model import X` → `from project_x.legacy.transformer_scaffolding import X`.
"""

from __future__ import annotations

import math

import torch
from torch import nn
from torch.nn import functional as F

from project_x.config import ModelConfig


class GlobalMemory(nn.Module):
    """Learned memory slots queried by every token before local mixing."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.memory = nn.Parameter(torch.randn(config.memory_slots, config.dim) * 0.02)
        self.query = nn.Linear(config.dim, config.dim, bias=False)
        self.out = nn.Linear(config.dim, config.dim, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        q = self.query(x)
        attn = torch.softmax(q @ self.memory.T / math.sqrt(x.shape[-1]), dim=-1)
        return self.out(attn @ self.memory)


class LocalCausalAttention(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.heads = config.heads
        self.head_dim = config.dim // config.heads
        if self.head_dim * config.heads != config.dim:
            raise ValueError("dim must be divisible by heads")
        self.qkv = nn.Linear(config.dim, config.dim * 3, bias=False)
        self.proj = nn.Linear(config.dim, config.dim, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, seq, dim = x.shape
        qkv = self.qkv(x).view(batch, seq, 3, self.heads, self.head_dim)
        q, k, v = qkv.unbind(dim=2)
        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)
        mask = torch.ones(seq, seq, device=x.device, dtype=torch.bool).tril()
        y = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        return self.proj(y.transpose(1, 2).contiguous().view(batch, seq, dim))


class RoutedExperts(nn.Module):
    """Tiny MoE block for testing routing, load metrics, and expert isolation."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.top_k = config.top_k_experts
        self.router = nn.Linear(config.dim, config.expert_count, bias=False)
        self.experts = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(config.dim, config.dim * 2),
                    nn.SiLU(),
                    nn.Linear(config.dim * 2, config.dim),
                )
                for _ in range(config.expert_count)
            ]
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        logits = self.router(x)
        weights, indices = torch.topk(torch.softmax(logits, dim=-1), self.top_k, dim=-1)
        out = torch.zeros_like(x)
        for rank in range(self.top_k):
            expert_ids = indices[..., rank]
            expert_weights = weights[..., rank].unsqueeze(-1)
            for expert_id, expert in enumerate(self.experts):
                mask = expert_ids == expert_id
                if mask.any():
                    out[mask] += expert(x[mask]) * expert_weights[mask]
        return out, logits


class XBlock(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.norm_a = nn.LayerNorm(config.dim)
        self.norm_m = nn.LayerNorm(config.dim)
        self.norm_e = nn.LayerNorm(config.dim)
        self.attn = LocalCausalAttention(config)
        self.memory = GlobalMemory(config)
        self.experts = RoutedExperts(config)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x = x + self.attn(self.norm_a(x))
        x = x + self.memory(self.norm_m(x))
        expert_delta, router_logits = self.experts(self.norm_e(x))
        x = x + expert_delta
        return x, router_logits


class ProjectXModel(nn.Module):
    """Seed architecture: local causality + global memory + routed transformation."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.config = config
        self.token = nn.Embedding(config.vocab_size, config.dim)
        self.position = nn.Embedding(config.max_seq_len, config.dim)
        self.blocks = nn.ModuleList([XBlock(config) for _ in range(config.depth)])
        self.norm = nn.LayerNorm(config.dim)
        self.head = nn.Linear(config.dim, config.vocab_size, bias=False)

    def forward(self, tokens: torch.Tensor) -> tuple[torch.Tensor, list[torch.Tensor]]:
        _, seq = tokens.shape
        if seq > self.config.max_seq_len:
            raise ValueError(f"seq_len {seq} exceeds max_seq_len {self.config.max_seq_len}")
        pos = torch.arange(seq, device=tokens.device).unsqueeze(0)
        x = self.token(tokens) + self.position(pos)
        router_logits = []
        for block in self.blocks:
            x, logits = block(x)
            router_logits.append(logits)
        return self.head(self.norm(x)), router_logits
