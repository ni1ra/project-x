"""
LN-GRU Recurrent Substrate - THE ACTUAL BRAIN

This is the core neural substrate that demonstrates architectural emergence
from reward-per-joule optimization. It's a homogeneous sparse recurrent
network - no named modules, no hand-built "consciousness" - just:
- LayerNorm GRU with blockwise sparse routing
- Global scalar broadcast g_t
- Learned compute allocation c_t

Brain-like structure (conscious/unconscious, neuromodulators, sleep) must
EMERGE from RPJ pressure, not be hard-coded.

Reference: BLUEPRINT.md Section 2.2
"""

from __future__ import annotations

import math
from typing import Tuple, Optional, NamedTuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Binomial


# =============================================================================
# Architectural Constants (BLUEPRINT.md Section 2.2)
# =============================================================================

HIDDEN_DIM = 512        # d - substrate hidden dimension
K_MAX = 16              # Maximum global scalars
LATENT_DIM = 64         # dim(z_t)
K_R_MAX = 4             # Maximum routed blocks per step
N_MAX = 5               # Maximum internal rollout steps
NUM_BLOCKS = 64         # B - number of routing blocks
GUMBEL_TAU = 1.0        # Fixed temperature (no annealing)


class SubstrateOutput(NamedTuple):
    """Output from a single substrate forward step."""
    h_next: torch.Tensor          # Next hidden state [batch, d]
    g_t: torch.Tensor             # Global scalars [batch, K_max]
    c_t: torch.Tensor             # Compute allocation [batch, 1]
    k_r: torch.Tensor             # Routed blocks count [batch]
    n_t: torch.Tensor             # Rollout step count [batch] - for PPO stored decisions
    routing_mask: torch.Tensor    # Block routing mask [batch, B]
    cbr_t: torch.Tensor           # Compute burst ratio [batch]
    bi_t: torch.Tensor            # Broadcast index [batch]
    compute_log_prob: torch.Tensor  # Log prob of (k_r, N) decisions [batch]


class LNGRUCell(nn.Module):
    """
    LayerNorm GRU Cell - the core recurrent unit.

    From BLUEPRINT.md Section 2.2:
    - Pre-activation LayerNorm on h_t
    - LayerNorm inside reset gate path

    Equations:
        h̄_t = LN(h_t)
        z = σ(W_z x_t + U_z h̄_t)        # update gate
        r = σ(W_r x_t + U_r h̄_t)        # reset gate
        h̃ = tanh(W_h x_t + U_h LN(r ⊙ h̄_t))
        h'_{t+1} = (1-z) ⊙ h_t + z ⊙ h̃
    """

    def __init__(self, input_dim: int, hidden_dim: int = HIDDEN_DIM):
        super().__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim

        # LayerNorm for hidden state (pre-activation)
        self.ln_h = nn.LayerNorm(hidden_dim)

        # LayerNorm for reset gate path
        self.ln_reset = nn.LayerNorm(hidden_dim)

        # Input projections (combined for efficiency)
        # [z_gate, r_gate, h_candidate]
        self.W_input = nn.Linear(input_dim, 3 * hidden_dim)

        # Hidden projections (combined for efficiency)
        self.U_hidden = nn.Linear(hidden_dim, 3 * hidden_dim, bias=False)

    def forward(
        self,
        x_t: torch.Tensor,
        h_t: torch.Tensor
    ) -> torch.Tensor:
        """
        Single GRU step with LayerNorm.

        Args:
            x_t: Input [batch, input_dim]
            h_t: Previous hidden state [batch, hidden_dim]

        Returns:
            h_next: Next hidden state [batch, hidden_dim]
        """
        # Pre-activation LayerNorm
        h_bar = self.ln_h(h_t)

        # Compute all input projections at once
        input_proj = self.W_input(x_t)
        W_z, W_r, W_h = input_proj.chunk(3, dim=-1)

        # Compute all hidden projections at once
        hidden_proj = self.U_hidden(h_bar)
        U_z, U_r, U_h = hidden_proj.chunk(3, dim=-1)

        # Update gate: z = σ(W_z x + U_z h̄)
        z = torch.sigmoid(W_z + U_z)

        # Reset gate: r = σ(W_r x + U_r h̄)
        r = torch.sigmoid(W_r + U_r)

        # Candidate: h̃ = tanh(W_h x + U_h LN(r ⊙ h̄))
        reset_h = self.ln_reset(r * h_bar)
        h_tilde = torch.tanh(W_h + self.U_hidden(reset_h).chunk(3, dim=-1)[2])

        # Output: h' = (1-z) ⊙ h + z ⊙ h̃
        h_next = (1 - z) * h_t + z * h_tilde

        return h_next


class SparseRouter(nn.Module):
    """
    Blockwise Sparse Routing with Gumbel-Softmax.

    From BLUEPRINT.md Section 2.2:
    - Partition substrate into B=64 equal blocks
    - Route k_r(t) blocks per step via TopK
    - Use Gumbel-Softmax (τ=1.0) for differentiable training
    - Straight-through hard TopK mask on forward
    """

    def __init__(
        self,
        hidden_dim: int = HIDDEN_DIM,
        num_blocks: int = NUM_BLOCKS,
        k_r_max: int = K_R_MAX,
        tau: float = GUMBEL_TAU
    ):
        super().__init__()

        self.hidden_dim = hidden_dim
        self.num_blocks = num_blocks
        self.k_r_max = k_r_max
        self.tau = tau
        self.block_size = hidden_dim // num_blocks

        assert hidden_dim % num_blocks == 0, \
            f"hidden_dim ({hidden_dim}) must be divisible by num_blocks ({num_blocks})"

        # Router: h_t -> block scores
        self.router = nn.Linear(hidden_dim, num_blocks)

    def forward(
        self,
        h_t: torch.Tensor,
        k_r: torch.Tensor,
        training: bool = True
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute routing mask for blocks.

        Args:
            h_t: Hidden state [batch, hidden_dim]
            k_r: Number of blocks to route [batch] (integers)
            training: Whether to use Gumbel-Softmax

        Returns:
            soft_weights: Soft routing weights [batch, num_blocks]
            hard_mask: Hard TopK mask [batch, num_blocks]
        """
        batch_size = h_t.size(0)

        # Get router scores
        scores = self.router(h_t)  # [batch, num_blocks]

        if training:
            # Gumbel-Softmax for differentiable sampling
            soft_weights = F.gumbel_softmax(scores, tau=self.tau, hard=False)
        else:
            soft_weights = F.softmax(scores, dim=-1)

        # Hard TopK mask (straight-through)
        # Handle variable k_r per sample
        hard_mask = torch.zeros_like(soft_weights)

        for i in range(batch_size):
            k = int(k_r[i].item())
            if k > 0:
                _, topk_indices = torch.topk(scores[i], k)
                hard_mask[i, topk_indices] = 1.0

        # Straight-through: hard forward, soft backward
        if training:
            hard_mask = hard_mask - soft_weights.detach() + soft_weights

        return soft_weights, hard_mask

    def apply_routing(
        self,
        h_current: torch.Tensor,
        h_next: torch.Tensor,
        mask: torch.Tensor
    ) -> torch.Tensor:
        """
        Apply blockwise routing mask.

        For each block b:
            h_{t+1}^{(b)} = m_b * h_{next}^{(b)} + (1-m_b) * h_current^{(b)}

        Args:
            h_current: Current hidden state [batch, hidden_dim]
            h_next: Candidate next state [batch, hidden_dim]
            mask: Block routing mask [batch, num_blocks]

        Returns:
            Routed hidden state [batch, hidden_dim]
        """
        batch_size = h_current.size(0)

        # Expand mask to match hidden dimensions
        # mask: [batch, num_blocks] -> [batch, hidden_dim]
        mask_expanded = mask.repeat_interleave(self.block_size, dim=-1)

        # Apply routing
        h_routed = mask_expanded * h_next + (1 - mask_expanded) * h_current

        return h_routed


class ComputeAllocator(nn.Module):
    """
    Learned Compute Allocation.

    From BLUEPRINT.md Section 2.2:
    - c_t = σ(w_c^T h_t) ∈ [0,1]
    - k_r(t) = 1 + Binomial(k_r_max-1, c_t)  [train]
    - k_r(t) = round(c_t * (k_r_max-1))      [eval]
    - N(t) ~ Binomial(N_max, c_t)            [train]
    - N(t) = round(c_t * N_max)              [eval]

    The log-probabilities of (k_r, N) are included in PPO's objective
    to make compute allocation learnable.
    """

    def __init__(
        self,
        hidden_dim: int = HIDDEN_DIM,
        k_r_max: int = K_R_MAX,
        n_max: int = N_MAX
    ):
        super().__init__()

        self.hidden_dim = hidden_dim
        self.k_r_max = k_r_max
        self.n_max = n_max

        # Compute scale: c_t = σ(w_c^T h_t)
        self.w_c = nn.Linear(hidden_dim, 1)

    def forward(
        self,
        h_t: torch.Tensor,
        training: bool = True
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Compute allocation decisions.

        Args:
            h_t: Hidden state [batch, hidden_dim]
            training: Whether to use stochastic sampling

        Returns:
            c_t: Compute scale [batch, 1]
            k_r: Number of routed blocks [batch]
            n_t: Number of rollout steps [batch]
            log_prob: Log probability of (k_r, n_t) [batch]
        """
        batch_size = h_t.size(0)
        device = h_t.device

        # Compute scale
        c_t = torch.sigmoid(self.w_c(h_t))  # [batch, 1]
        c_t_squeezed = c_t.squeeze(-1)  # [batch]

        if training:
            # Binomial sampling for k_r
            # k_r(t) = 1 + Binomial(k_r_max-1, c_t)
            k_r_dist = Binomial(
                total_count=self.k_r_max - 1,
                probs=c_t_squeezed.clamp(1e-6, 1 - 1e-6)
            )
            k_r_sample = k_r_dist.sample()
            k_r = 1 + k_r_sample  # At least 1 block routed

            # Binomial sampling for N
            # N(t) ~ Binomial(N_max, c_t)
            n_dist = Binomial(
                total_count=self.n_max,
                probs=c_t_squeezed.clamp(1e-6, 1 - 1e-6)
            )
            n_t = n_dist.sample()

            # Log probability for PPO
            log_prob_k = k_r_dist.log_prob(k_r_sample)
            log_prob_n = n_dist.log_prob(n_t)
            log_prob = log_prob_k + log_prob_n
        else:
            # Deterministic rounding for eval
            k_r = torch.round(c_t_squeezed * (self.k_r_max - 1) + 0.5).long()
            k_r = k_r.clamp(1, self.k_r_max)

            n_t = torch.round(c_t_squeezed * self.n_max + 0.5).long()
            n_t = n_t.clamp(0, self.n_max)

            log_prob = torch.zeros(batch_size, device=device)

        return c_t, k_r, n_t, log_prob

    def get_log_prob(
        self,
        h_t: torch.Tensor,
        k_r: torch.Tensor,
        n_t: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute log probability of given (k_r, n_t) decisions.

        Used by PPO to compute importance ratio without resampling.

        Args:
            h_t: Hidden state [batch, hidden_dim]
            k_r: Stored routed block count [batch]
            n_t: Stored rollout step count [batch]

        Returns:
            log_prob: Log probability of (k_r, n_t) [batch]
        """
        # Compute c_t from current params
        c_t = torch.sigmoid(self.w_c(h_t))  # [batch, 1]
        c_t_squeezed = c_t.squeeze(-1).clamp(1e-6, 1 - 1e-6)  # [batch]

        # k_r was stored as 1 + sample, so k_r_sample = k_r - 1
        k_r_sample = (k_r - 1).float().clamp(0, self.k_r_max - 1)

        # Create distributions with current c_t
        k_r_dist = Binomial(
            total_count=self.k_r_max - 1,
            probs=c_t_squeezed
        )
        n_dist = Binomial(
            total_count=self.n_max,
            probs=c_t_squeezed
        )

        # Compute log probs of the stored values
        log_prob_k = k_r_dist.log_prob(k_r_sample)
        log_prob_n = n_dist.log_prob(n_t.float().clamp(0, self.n_max))
        log_prob = log_prob_k + log_prob_n

        return log_prob


class GlobalScalarBroadcast(nn.Module):
    """
    Learned Global Scalar Broadcast g_t.

    From BLUEPRINT.md Section 2.3:
    - g_t = σ(W_g h_t + b_g) ∈ [0,1]^K_max
    - These are the "neuromodulator candidates"
    - K_eff (participation ratio) should compress to 2-6 under RPJ
    """

    def __init__(
        self,
        hidden_dim: int = HIDDEN_DIM,
        k_max: int = K_MAX
    ):
        super().__init__()

        self.hidden_dim = hidden_dim
        self.k_max = k_max

        self.W_g = nn.Linear(hidden_dim, k_max)

    def forward(self, h_t: torch.Tensor) -> torch.Tensor:
        """
        Compute global scalar broadcast.

        Args:
            h_t: Hidden state [batch, hidden_dim]

        Returns:
            g_t: Global scalars [batch, K_max]
        """
        return torch.sigmoid(self.W_g(h_t))

    @staticmethod
    def compute_k_eff(g_t: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
        """
        Compute effective scalar count (participation ratio).

        K_eff = (Σ Var(g_k))² / (Σ Var(g_k)² + ε)

        Target emergence: 2 ≤ K_eff ≤ 6

        Args:
            g_t: Global scalars [batch, K_max] or [time, batch, K_max]

        Returns:
            K_eff: Scalar participation ratio
        """
        # Compute variance across batch (or time×batch)
        if g_t.dim() == 3:
            # [time, batch, K_max] -> flatten first two dims
            g_flat = g_t.reshape(-1, g_t.size(-1))
        else:
            g_flat = g_t

        var_k = g_flat.var(dim=0)  # [K_max]

        sum_var = var_k.sum()
        sum_var_sq = (var_k ** 2).sum()

        k_eff = (sum_var ** 2) / (sum_var_sq + eps)

        return k_eff


class RPJSubstrate(nn.Module):
    """
    The RPJ Brain Substrate - The Actual Neural Network.

    A homogeneous sparse recurrent network that should develop
    brain-like structure (conscious/unconscious modes, neuromodulators,
    sleep) through reward-per-joule optimization pressure alone.

    This is NOT a modular system with named components. It's a single
    substrate where structure EMERGES from the objective.

    Architecture from BLUEPRINT.md Section 2.2:
    - LN-GRU recurrent core
    - Blockwise sparse routing (B=64 blocks, k_r_max=4)
    - Global scalar broadcast g_t (K_max=16)
    - Compute allocation c_t
    - Integrated with latent z_t from VAE
    """

    def __init__(
        self,
        obs_dim: int,
        latent_dim: int = LATENT_DIM,
        hidden_dim: int = HIDDEN_DIM,
        num_blocks: int = NUM_BLOCKS,
        k_r_max: int = K_R_MAX,
        n_max: int = N_MAX,
        k_max: int = K_MAX,
    ):
        super().__init__()

        self.obs_dim = obs_dim
        self.latent_dim = latent_dim
        self.hidden_dim = hidden_dim
        self.num_blocks = num_blocks
        self.k_r_max = k_r_max
        self.n_max = n_max
        self.k_max = k_max

        # Input: [φ(o_t) || z_t || a_t || g_t]
        # Note: a_t size depends on action space, assume 1 byte for now
        # g_t from previous step (or zeros initially)
        self.input_dim = obs_dim + latent_dim + 1 + k_max

        # Core recurrent unit
        self.gru_cell = LNGRUCell(self.input_dim, hidden_dim)

        # Sparse routing
        self.router = SparseRouter(hidden_dim, num_blocks, k_r_max)

        # Compute allocation
        self.compute_allocator = ComputeAllocator(hidden_dim, k_r_max, n_max)

        # Global scalar broadcast
        self.global_broadcast = GlobalScalarBroadcast(hidden_dim, k_max)

        # Value head: V([h_t || g_t]) - conditions on g_t for K_eff gradient flow
        self.value_head = nn.Linear(hidden_dim + k_max, 1)

        # Running statistics for CBR computation
        self.register_buffer('c_running_mean', torch.tensor(0.5))
        self.register_buffer('c_running_count', torch.tensor(0.0))

    def init_hidden(self, batch_size: int, device: torch.device) -> torch.Tensor:
        """Initialize hidden state."""
        return torch.zeros(batch_size, self.hidden_dim, device=device)

    def init_global_scalars(self, batch_size: int, device: torch.device) -> torch.Tensor:
        """Initialize global scalars (zeros for first step)."""
        return torch.zeros(batch_size, self.k_max, device=device)

    def forward(
        self,
        phi_obs: torch.Tensor,
        z_t: torch.Tensor,
        a_prev: torch.Tensor,
        h_t: torch.Tensor,
        g_prev: torch.Tensor,
        training: bool = True
    ) -> SubstrateOutput:
        """
        Single substrate step.

        Args:
            phi_obs: Normalized observation [batch, obs_dim]
            z_t: Latent from VAE [batch, latent_dim]
            a_prev: Previous action (byte) [batch, 1] or [batch]
            h_t: Current hidden state [batch, hidden_dim]
            g_prev: Previous global scalars [batch, k_max]
            training: Whether in training mode

        Returns:
            SubstrateOutput containing next state and metrics
        """
        batch_size = h_t.size(0)
        device = h_t.device

        # Ensure a_prev is the right shape
        if a_prev.dim() == 1:
            a_prev = a_prev.unsqueeze(-1)
        a_prev_float = a_prev.float() / 127.5 - 1.0  # Normalize to [-1, 1]

        # Concatenate input: [φ(o_t) || z_t || a_t || g_{t-1}]
        x_t = torch.cat([phi_obs, z_t, a_prev_float, g_prev], dim=-1)

        # Compute allocation BEFORE routing (from current h_t)
        c_t, k_r, n_t, compute_log_prob = self.compute_allocator(h_t, training)

        # Get routing mask
        soft_weights, hard_mask = self.router(h_t, k_r, training)

        # GRU step (candidate next state)
        h_candidate = self.gru_cell(x_t, h_t)

        # Apply blockwise routing
        h_next = self.router.apply_routing(h_t, h_candidate, hard_mask)

        # Compute global scalars from new state
        g_t = self.global_broadcast(h_next)

        # Compute emergence metrics
        # CBR_t = c_t / E[c]
        cbr_t = c_t.squeeze(-1) / (self.c_running_mean + 1e-8)

        # Update running mean of c_t
        if training:
            with torch.no_grad():
                batch_mean = c_t.mean()
                self.c_running_count += batch_size
                alpha = min(0.01, batch_size / self.c_running_count)
                self.c_running_mean = (1 - alpha) * self.c_running_mean + alpha * batch_mean

        # BI_t (Broadcast Index) - participation ratio over unit activations
        # BI_t = (Σ|u_i|)² / (d * Σu_i² + ε)
        u_t = h_next  # Use hidden state as unit activations
        sum_abs = u_t.abs().sum(dim=-1)  # [batch]
        sum_sq = (u_t ** 2).sum(dim=-1)   # [batch]
        bi_t = (sum_abs ** 2) / (self.hidden_dim * sum_sq + 1e-8)

        return SubstrateOutput(
            h_next=h_next,
            g_t=g_t,
            c_t=c_t,
            k_r=k_r,
            n_t=n_t,
            routing_mask=hard_mask,
            cbr_t=cbr_t,
            bi_t=bi_t,
            compute_log_prob=compute_log_prob,
        )

    def get_value(self, h_t: torch.Tensor, g_t: torch.Tensor = None) -> torch.Tensor:
        """Get value estimate from [h_t || g_t] for K_eff gradient flow."""
        if g_t is None:
            g_t = torch.zeros(h_t.size(0), self.k_max, device=h_t.device)
        context = torch.cat([h_t, g_t], dim=-1)
        return self.value_head(context).squeeze(-1)

    def count_parameters(self) -> int:
        """Count total trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def count_flops_per_step(self) -> int:
        """
        Estimate FLOPs per forward step.

        Approximate: 2 * params * (1 + N_max) for worst case
        """
        params = self.count_parameters()
        # Conservative estimate: full forward + potential rollouts
        return 2 * params * (1 + self.n_max)


def create_substrate(obs_dim: int, **kwargs) -> RPJSubstrate:
    """Factory function to create substrate with defaults."""
    return RPJSubstrate(obs_dim=obs_dim, **kwargs)


if __name__ == "__main__":
    # Quick sanity check
    print("Testing RPJ Substrate...")

    obs_dim = 64
    batch_size = 4

    substrate = RPJSubstrate(obs_dim=obs_dim)

    # Initialize states
    h = substrate.init_hidden(batch_size, torch.device('cpu'))
    g = substrate.init_global_scalars(batch_size, torch.device('cpu'))

    # Dummy inputs
    phi_obs = torch.randn(batch_size, obs_dim)
    z_t = torch.randn(batch_size, LATENT_DIM)
    a_prev = torch.randint(0, 256, (batch_size, 1))

    # Forward pass
    output = substrate(phi_obs, z_t, a_prev, h, g, training=True)

    print(f"Parameters: {substrate.count_parameters():,}")
    print(f"Hidden shape: {output.h_next.shape}")
    print(f"Global scalars shape: {output.g_t.shape}")
    print(f"Compute allocation: {output.c_t.squeeze().tolist()}")
    print(f"Routed blocks: {output.k_r.tolist()}")
    print(f"CBR: {output.cbr_t.tolist()}")
    print(f"BI: {output.bi_t.tolist()}")
    print(f"Value: {substrate.get_value(output.h_next, output.g_t).tolist()}")

    print("\n✓ Substrate forward pass works!")
