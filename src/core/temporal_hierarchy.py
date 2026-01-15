"""
Temporal Hierarchy Module

Implements the JARVIS-recommended hierarchical temporal architecture:
- Fast GRU: Updates every step, sparse routed blocks
- Slow GRU: Updates when:
  - Clock tick (every k_slow steps), OR
  - Compute lever says "pay for slow", OR
  - Surprise signal spikes (prediction error from world model)

Combination:
  h = h_fast + gate * proj(h_slow)
  where gate = sigmoid(MLP([h_fast | h_slow]))

This lets slow state become "context gravity" instead of constant additive noise.

Reference: JARVIS roadmap consultation, Sprint 2 architecture
"""

from __future__ import annotations

from typing import Tuple, Optional, NamedTuple
from dataclasses import dataclass

import torch
import torch.nn as nn

from src.core.substrate import LNGRUCell, SparseRouter, K_MAX, NUM_BLOCKS, K_R_MAX


@dataclass
class HierarchyConfig:
    """Configuration for temporal hierarchy."""
    # Replication-critical constants (paper.md Appendix J)
    hidden_dim: int = 256
    k_max: int = K_MAX
    num_blocks: int = NUM_BLOCKS
    k_r_max: int = K_R_MAX

    # Slow state config
    k_slow: int = 10                  # Clock period for slow updates
    slow_hidden_dim: int = 256        # Slow GRU hidden size
    surprise_threshold: float = 0.5   # Surprise threshold for trigger
    gate_hidden_dim: int = 64         # Gate network hidden layer size
    policy_trigger_temp: float = 1.0  # Temperature for policy trigger sampling

    # Energy cost for slow update (higher than fast)
    slow_energy_multiplier: float = 2.0


class HierarchyOutput(NamedTuple):
    """Output from hierarchical substrate step."""
    h_combined: torch.Tensor    # Combined hidden state [batch, hidden_dim]
    h_fast: torch.Tensor        # Fast state [batch, hidden_dim]
    h_slow: torch.Tensor        # Slow state [batch, hidden_dim]
    g_t: torch.Tensor           # Global scalars [batch, k_max]
    gate_t: torch.Tensor        # Mixing gate [batch]
    slow_updated: torch.Tensor  # Binary: did slow update? [batch]
    surprise_t: torch.Tensor    # Surprise signal [batch]


class HierarchicalSubstrate(nn.Module):
    """
    Hierarchical Temporal Substrate.

    Combines fast (every-step) and slow (conditional) GRU layers with
    learned gated mixing. Slow updates are triggered by:
    1. Clock tick every k_slow steps
    2. Compute lever (policy decides to "pay" for slow)
    3. Surprise spike (world model prediction error)

    This creates temporal abstraction where slow state provides stable
    "context gravity" while fast state handles moment-to-moment processing.
    """

    def __init__(self, config: HierarchyConfig, obs_dim: int, latent_dim: int = 64):
        super().__init__()
        self.config = config
        self.obs_dim = obs_dim
        self.latent_dim = latent_dim

        # Input: [φ(o_t) || z_t || a_t || g_{t-1}]
        self.fast_input_dim = obs_dim + latent_dim + 1 + config.k_max

        # Fast GRU: updates every step with sparse routing
        self.fast_gru = LNGRUCell(self.fast_input_dim, config.hidden_dim)

        # Fast sparse router
        self.fast_router = SparseRouter(
            config.hidden_dim,
            config.num_blocks,
            config.k_r_max,
        )

        # Slow GRU: updates conditionally (input: fast hidden)
        self.slow_input_dim = config.hidden_dim
        self.slow_gru = LNGRUCell(self.slow_input_dim, config.slow_hidden_dim)

        # Slow→Fast projection (for gated mixing)
        self.slow_proj = nn.Linear(config.slow_hidden_dim, config.hidden_dim)

        # Gated mixing: h = h_fast + gate * proj(h_slow)
        # Gate = sigmoid(MLP([h_fast | h_slow]))
        self.gate_net = nn.Sequential(
            nn.Linear(config.hidden_dim + config.slow_hidden_dim, config.gate_hidden_dim),
            nn.ReLU(),
            nn.Linear(config.gate_hidden_dim, 1),
        )

        # Global scalar broadcast (shared for fast/slow)
        self.W_g = nn.Linear(config.hidden_dim, config.k_max)

        # Surprise predictor: predict fast state from slow state (stop-gradient on surprise usage)
        self.surprise_predictor = nn.Sequential(
            nn.Linear(config.slow_hidden_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, config.hidden_dim),
        )

        # Slow update policy: should we pay for slow this step?
        # Output: probability of triggering slow update
        self.slow_policy = nn.Linear(config.hidden_dim + config.slow_hidden_dim, 1)

        # Step counter for clock-based slow updates
        self.register_buffer('step_counter', torch.tensor(0))

        # K_eff bias staggering (same as original substrate)
        with torch.no_grad():
            self.W_g.bias.data = torch.linspace(-1.0, -4.0, config.k_max)

    def init_state(
        self,
        batch_size: int,
        device: torch.device
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Initialize hidden states.

        Returns:
            h_fast: Fast hidden [batch, hidden_dim]
            h_slow: Slow hidden [batch, hidden_dim]
            g: Global scalars [batch, k_max]
        """
        h_fast = torch.zeros(batch_size, self.config.hidden_dim, device=device)
        h_slow = torch.zeros(batch_size, self.config.slow_hidden_dim, device=device)
        g = torch.zeros(batch_size, self.config.k_max, device=device)
        return h_fast, h_slow, g

    def forward(
        self,
        phi_obs: torch.Tensor,
        z_t: torch.Tensor,
        a_prev: torch.Tensor,
        h_fast: torch.Tensor,
        h_slow: torch.Tensor,
        g_prev: torch.Tensor,
        k_r: torch.Tensor,
        training: bool = True,
        force_slow_update: bool = False,
    ) -> HierarchyOutput:
        """
        Hierarchical substrate forward pass.

        Args:
            phi_obs: Normalized observation [batch, obs_dim]
            z_t: Latent from VAE [batch, latent_dim]
            a_prev: Previous action byte [batch]
            h_fast: Fast hidden state [batch, hidden_dim]
            h_slow: Slow hidden state [batch, hidden_dim]
            g_prev: Previous global scalars [batch, k_max]
            k_r: Number of blocks to route [batch]
            training: Whether in training mode
            force_slow_update: Force slow update regardless of triggers

        Returns:
            HierarchyOutput with all states and metrics
        """
        batch_size = h_fast.size(0)
        device = h_fast.device

        # ============================================
        # STEP 1: Compute surprise (prediction error)
        # ============================================
        # Stop-gradient on surprise computation to prevent fast GRU from learning to minimize surprise.
        with torch.no_grad():
            predicted_fast = self.surprise_predictor(h_slow)
            surprise_t = ((h_fast - predicted_fast) ** 2).mean(dim=-1)  # [batch]

        # ============================================
        # STEP 2: Determine slow update trigger
        # ============================================
        # Three triggers:
        # 1. Clock tick every k_slow steps
        clock_trigger = (self.step_counter % self.config.k_slow == 0)

        # 2. Compute lever (policy decides)
        slow_policy_input = torch.cat([h_fast, h_slow], dim=-1)
        slow_policy_logit = self.slow_policy(slow_policy_input).squeeze(-1)  # [batch]
        p_policy = torch.sigmoid(slow_policy_logit / max(self.config.policy_trigger_temp, 1e-8))
        if training:
            # Stochastic during training
            policy_trigger = torch.bernoulli(p_policy)
        else:
            policy_trigger = (p_policy > 0.5).float()

        # 3. Surprise spike
        surprise_trigger = (surprise_t > self.config.surprise_threshold).float()

        # Combine triggers (OR logic)
        should_update_slow = (
            force_slow_update or
            clock_trigger or
            (policy_trigger + surprise_trigger > 0).any()
        )

        # Per-sample trigger for batched update
        slow_update_mask = (
            policy_trigger +
            surprise_trigger +
            float(clock_trigger)
        ).clamp(0, 1)  # [batch]

        if force_slow_update:
            slow_update_mask = torch.ones_like(slow_update_mask)

        # ============================================
        # STEP 3: Update slow state (if triggered)
        # ============================================
        slow_input = h_fast
        h_slow_candidate = self.slow_gru(slow_input, h_slow)

        # Apply update mask
        h_slow_next = (
            slow_update_mask.unsqueeze(-1) * h_slow_candidate +
            (1 - slow_update_mask.unsqueeze(-1)) * h_slow
        )

        # ============================================
        # STEP 4: Update fast state (always)
        # ============================================
        # Normalize a_prev
        if a_prev.dim() == 1:
            a_prev = a_prev.unsqueeze(-1)
        a_prev_float = a_prev.float() / 127.5 - 1.0

        # Fast input: [φ(o) || z || a || g_prev]
        fast_input = torch.cat([phi_obs, z_t, a_prev_float, g_prev], dim=-1)

        # Fast GRU step
        h_fast_candidate = self.fast_gru(fast_input, h_fast)

        # Sparse routing
        _, routing_mask = self.fast_router(h_fast, k_r, training)
        h_fast_next = self.fast_router.apply_routing(h_fast, h_fast_candidate, routing_mask)

        # ============================================
        # STEP 5: Gated mixing
        # ============================================
        # gate = sigmoid(MLP([h_fast | h_slow]))
        gate_input = torch.cat([h_fast_next, h_slow_next], dim=-1)
        gate_t = torch.sigmoid(self.gate_net(gate_input)).squeeze(-1)  # [batch]

        # Combined state: h = h_fast + gate * proj(h_slow)
        slow_contrib = self.slow_proj(h_slow_next)
        h_combined = h_fast_next + gate_t.unsqueeze(-1) * slow_contrib

        # ============================================
        # STEP 6: Global scalars from combined state
        # ============================================
        g_t = torch.sigmoid(self.W_g(h_combined))

        # Update step counter
        with torch.no_grad():
            self.step_counter.add_(1)

        return HierarchyOutput(
            h_combined=h_combined,
            h_fast=h_fast_next,
            h_slow=h_slow_next,
            g_t=g_t,
            gate_t=gate_t,
            slow_updated=slow_update_mask,
            surprise_t=surprise_t,
        )

    def compute_k_eff(self, g_t: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
        """Compute effective scalar count (participation ratio)."""
        if g_t.dim() == 3:
            g_flat = g_t.reshape(-1, g_t.size(-1))
        else:
            g_flat = g_t

        var_k = g_flat.var(dim=0)
        sum_var = var_k.sum()
        sum_var_sq = (var_k ** 2).sum()

        k_eff = (sum_var ** 2) / (sum_var_sq + eps)
        return k_eff

    def get_energy_cost(self, slow_updated: torch.Tensor, base_energy: float = 0.01) -> torch.Tensor:
        """
        Compute energy cost including slow update penalty.

        Args:
            slow_updated: Binary mask of slow updates [batch]
            base_energy: Base energy per step

        Returns:
            energy: Energy per sample [batch]
        """
        slow_cost = slow_updated * self.config.slow_energy_multiplier * base_energy
        return base_energy + slow_cost


def create_hierarchical_substrate(
    obs_dim: int,
    latent_dim: int = 64,
    **kwargs
) -> HierarchicalSubstrate:
    """Factory function to create hierarchical substrate."""
    config = HierarchyConfig(**kwargs)
    return HierarchicalSubstrate(config, obs_dim, latent_dim)


if __name__ == "__main__":
    # Quick sanity check
    print("Testing Hierarchical Substrate...")

    obs_dim = 64
    batch_size = 4
    latent_dim = 64

    config = HierarchyConfig()
    substrate = HierarchicalSubstrate(config, obs_dim, latent_dim)

    # Initialize
    h_fast, h_slow, g = substrate.init_state(batch_size, torch.device('cpu'))

    # Dummy inputs
    phi_obs = torch.randn(batch_size, obs_dim)
    z_t = torch.randn(batch_size, latent_dim)
    a_prev = torch.randint(0, 256, (batch_size,))
    k_r = torch.randint(1, 5, (batch_size,))

    # Forward
    output = substrate(phi_obs, z_t, a_prev, h_fast, h_slow, g, k_r, training=True)

    print(f"Parameters: {sum(p.numel() for p in substrate.parameters()):,}")
    print(f"h_combined shape: {output.h_combined.shape}")
    print(f"h_fast shape: {output.h_fast.shape}")
    print(f"h_slow shape: {output.h_slow.shape}")
    print(f"g_t shape: {output.g_t.shape}")
    print(f"Gate: {output.gate_t.tolist()}")
    print(f"Slow updated: {output.slow_updated.tolist()}")
    print(f"Surprise: {output.surprise_t.tolist()}")

    # K_eff check
    k_eff = substrate.compute_k_eff(output.g_t)
    print(f"K_eff: {k_eff.item():.2f}")

    # Gradient test
    loss = output.h_combined.sum() + output.g_t.sum()
    loss.backward()
    print("\n✓ Hierarchical Substrate works!")
