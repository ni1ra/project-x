"""
Local Synaptic Plasticity - The Learning Within Episodes

This implements BLUEPRINT Section 2.4:
- Next-observation predictor ψ(h_t)
- Local error signals: e^pred + e^delta
- Plasticity gate P_t from global scalars g_t
- Low-rank fast adapters (A_t, B_t) for recurrent + action head
- On-manifold Hebbian updates

Reference: BLUEPRINT.md Section 2.4
"""

from __future__ import annotations

from typing import Tuple, NamedTuple, Optional
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

# Constants from BLUEPRINT
HIDDEN_DIM = 512
# BLUEPRINT says rank=64, but we must satisfy P_fast <= min(0.5M, 0.05*P)
# With P~1.4M, budget is min(500K, 70K) = 70K
# Fast params = 2*(d*r + d*r) for rec (3d output) + 2*(256*r + d*r) for act
# With r=64: 2*(512*64 + 512*64) + 2*(256*64 + 512*64) ≈ 180K (too high)
# With r=16: 2*(512*16 + 512*16) + 2*(256*16 + 512*16) ≈ 45K (within budget)
ADAPTER_RANK = 16  # Reduced to fit within fast-param budget
K_MAX = 16


@dataclass
class PlasticityConfig:
    """Configuration for plasticity module."""
    hidden_dim: int = HIDDEN_DIM
    obs_dim: int = 64
    k_max: int = K_MAX
    adapter_rank: int = ADAPTER_RANK
    num_envs: int = 1  # BATCHED: Number of parallel environments

    # Learning rule parameters (slow, learned by RL)
    # JARVIS 410: Increased eta_init from 0.01 to 0.05 for stronger early-episode imprinting
    eta_init: float = 0.05      # Base learning rate for fast weights
    lambda_decay: float = 0.01  # Weight decay for fast weights

    # Bounds
    eta_min: float = 1e-4
    eta_max: float = 0.2  # JARVIS 410: Increased from 0.1 to allow stronger plasticity


class NextObsPredictor(nn.Module):
    """
    Predictive coding component: ψ(h_t) → φ(o_{t+1})

    Predicts normalized next observation from hidden state.
    """

    def __init__(self, hidden_dim: int, obs_dim: int):
        super().__init__()

        # 2-layer MLP predictor
        self.predictor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, obs_dim),
            nn.Tanh(),  # Output in [-1, 1] like phi(o)
        )

    def forward(self, h_t: torch.Tensor) -> torch.Tensor:
        """
        Predict normalized next observation.

        Args:
            h_t: Hidden state [batch, hidden_dim]

        Returns:
            phi_o_pred: Predicted φ(o_{t+1}) [batch, obs_dim]
        """
        return self.predictor(h_t)

    def prediction_loss(
        self,
        h_t: torch.Tensor,
        phi_o_next: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute prediction loss ℓ_pred = ||ψ(h_t) - φ(o_{t+1})||²

        Args:
            h_t: Hidden state [batch, hidden_dim]
            phi_o_next: True normalized next observation [batch, obs_dim]

        Returns:
            loss: Per-sample MSE [batch]
        """
        pred = self.forward(h_t)
        return ((pred - phi_o_next) ** 2).mean(dim=-1)


class PlasticityGate(nn.Module):
    """
    Plasticity gate: P_t = σ(w_P^T g_t + b_P)

    Maps global scalars to a single plasticity multiplier.
    """

    def __init__(self, k_max: int):
        super().__init__()

        self.w_P = nn.Parameter(torch.zeros(k_max))
        self.b_P = nn.Parameter(torch.tensor(0.0))

        # Initialize to produce P ≈ 0.5 initially
        nn.init.normal_(self.w_P, std=0.1)

    def forward(self, g_t: torch.Tensor) -> torch.Tensor:
        """
        Compute plasticity gate.

        Args:
            g_t: Global scalars [batch, k_max]

        Returns:
            P_t: Plasticity gate [batch]
        """
        # w_P^T g_t + b_P -> scalar per batch
        return torch.sigmoid((g_t * self.w_P).sum(dim=-1) + self.b_P)


class LowRankAdapter(nn.Module):
    """
    Low-rank fast weight adapter: W_eff = W_slow + A_t @ B_t^T

    A_t, B_t are fast weights updated within episodes.

    BATCHED VERSION (JARVIS 360→420 FIX):
    Now supports per-environment fast weights for vectorized training.
    Shape: [num_envs, out_dim, rank] and [num_envs, in_dim, rank]
    This enables proper per-episode learning and reset.
    """

    def __init__(self, in_dim: int, out_dim: int, rank: int = ADAPTER_RANK, num_envs: int = 1):
        super().__init__()

        self.in_dim = in_dim
        self.out_dim = out_dim
        self.rank = rank
        self.num_envs = num_envs

        # BATCHED: These are the FAST weights - [num_envs, dim, rank]
        # They're buffers that get reset each episode
        # DTYPE FIX: Explicitly use float32 to match model dtype
        if num_envs > 1:
            self.register_buffer('A', torch.zeros(num_envs, out_dim, rank, dtype=torch.float32))
            self.register_buffer('B', torch.zeros(num_envs, in_dim, rank, dtype=torch.float32))
        else:
            # Backward compatible non-batched mode
            self.register_buffer('A', torch.zeros(out_dim, rank, dtype=torch.float32))
            self.register_buffer('B', torch.zeros(in_dim, rank, dtype=torch.float32))

    def reset(self):
        """Reset ALL fast weights to zero."""
        self.A.zero_()
        self.B.zero_()

    def reset_envs(self, env_indices: torch.Tensor):
        """
        Reset fast weights for specific environments.

        Args:
            env_indices: Boolean or long tensor of environment indices to reset
        """
        if self.num_envs > 1:
            self.A[env_indices] = 0
            self.B[env_indices] = 0
        else:
            # Non-batched mode - reset all
            self.reset()

    def get_adaptation(self, env_idx: int = None) -> torch.Tensor:
        """
        Compute the fast weight delta: A @ B^T

        Args:
            env_idx: If batched, return adaptation for specific env. If None, return all.

        Returns:
            delta_W: Fast weight contribution
                     [out_dim, in_dim] if non-batched or env_idx specified
                     [num_envs, out_dim, in_dim] if batched and env_idx is None
        """
        if self.num_envs > 1:
            if env_idx is not None:
                return self.A[env_idx] @ self.B[env_idx].T
            else:
                # Batched matmul: [N, out, rank] @ [N, rank, in] -> [N, out, in]
                return torch.bmm(self.A, self.B.transpose(1, 2))
        else:
            return self.A @ self.B.T

    def update(
        self,
        e_t: torch.Tensor,
        x_t: torch.Tensor,
        P_t: torch.Tensor,
        eta: float,
        lambda_decay: float,
    ):
        """
        On-manifold plasticity update (BLUEPRINT Eq. 2.4):
        A_{t+1} = (1 - ηλ)A_t + ηP_t e_t (x_t^T B_t)
        B_{t+1} = (1 - ηλ)B_t + ηP_t x_t (e_t^T A_t)

        BATCHED VERSION: Applies per-environment updates instead of averaging.

        Args:
            e_t: Error signal [batch/num_envs, out_dim]
            x_t: Pre-activation [batch/num_envs, in_dim]
            P_t: Plasticity gate [batch/num_envs]
            eta: Learning rate (slow parameter)
            lambda_decay: Weight decay (slow parameter)
        """
        decay = 1.0 - eta * lambda_decay

        if self.num_envs > 1:
            # BATCHED UPDATE: Per-environment plasticity
            # e_t: [N, out_dim], x_t: [N, in_dim], P_t: [N]

            # Check for first update (per-env): where A[i] and B[i] are zero
            A_norms = self.A.norm(dim=(1, 2))  # [N]
            B_norms = self.B.norm(dim=(1, 2))  # [N]
            first_update_mask = (A_norms < 1e-8) & (B_norms < 1e-8)  # [N]

            # Bootstrap initialization for first-update envs
            if first_update_mask.any():
                e_norms = e_t[first_update_mask].norm(dim=1, keepdim=True) + 1e-8  # [M, 1]
                x_norms = x_t[first_update_mask].norm(dim=1, keepdim=True) + 1e-8  # [M, 1]
                P_vals = P_t[first_update_mask].unsqueeze(-1)  # [M, 1]
                scale = (eta * P_vals) ** 0.5  # [M, 1]

                # Initialize first column of A and B
                e_normalized = e_t[first_update_mask] / e_norms * scale  # [M, out_dim]
                x_normalized = x_t[first_update_mask] / x_norms * scale  # [M, in_dim]

                self.A.data[first_update_mask, :, 0] = e_normalized
                self.B.data[first_update_mask, :, 0] = x_normalized

            # Standard on-manifold update for non-first envs
            if (~first_update_mask).any():
                non_first = ~first_update_mask

                # Ensure dtype consistency
                B_f = self.B.float()
                A_f = self.A.float()

                # x^T B: [N, 1, in_dim] @ [N, in_dim, rank] -> [N, 1, rank] -> [N, rank]
                x_B = torch.bmm(x_t[non_first].unsqueeze(1), B_f[non_first]).squeeze(1)  # [M, rank]

                # e (x^T B): [M, out_dim, 1] @ [M, 1, rank] -> [M, out_dim, rank]
                P_vals = P_t[non_first].view(-1, 1, 1)  # [M, 1, 1]
                delta_A = eta * P_vals * torch.bmm(e_t[non_first].unsqueeze(2), x_B.unsqueeze(1))
                self.A.data[non_first] = decay * A_f[non_first] + delta_A

                # e^T A: [N, 1, out_dim] @ [N, out_dim, rank] -> [N, 1, rank] -> [N, rank]
                e_A = torch.bmm(e_t[non_first].unsqueeze(1), self.A[non_first].float()).squeeze(1)  # [M, rank]

                # x (e^T A): [M, in_dim, 1] @ [M, 1, rank] -> [M, in_dim, rank]
                delta_B = eta * P_vals * torch.bmm(x_t[non_first].unsqueeze(2), e_A.unsqueeze(1))
                self.B.data[non_first] = decay * B_f[non_first] + delta_B
        else:
            # LEGACY NON-BATCHED UPDATE (backward compatible)
            e_mean = e_t.mean(dim=0).float()  # [out_dim], ensure float32
            x_mean = x_t.mean(dim=0).float()  # [in_dim], ensure float32
            P_mean = P_t.mean().item() if P_t.dim() > 0 else P_t.item()

            # Ensure buffers are float32
            A_f = self.A.float()
            B_f = self.B.float()

            # Check if this is the first update (A=0, B=0)
            if A_f.norm() < 1e-8 and B_f.norm() < 1e-8:
                e_norm = e_mean.norm() + 1e-8
                x_norm = x_mean.norm() + 1e-8
                scale = (eta * P_mean) ** 0.5
                self.A.data[:, 0] = (scale * e_mean / e_norm).to(self.A.dtype)
                self.B.data[:, 0] = (scale * x_mean / x_norm).to(self.B.dtype)
            else:
                x_B = x_mean @ B_f  # [rank]
                delta_A = eta * P_mean * torch.outer(e_mean, x_B)  # [out_dim, rank]
                self.A.data = (decay * A_f + delta_A).to(self.A.dtype)

                e_A = e_mean @ self.A.float()  # [rank]
                delta_B = eta * P_mean * torch.outer(x_mean, e_A)  # [in_dim, rank]
                self.B.data = (decay * B_f + delta_B).to(self.B.dtype)


class LocalPlasticity(nn.Module):
    """
    Complete local plasticity system.

    Combines:
    - Next-obs predictor (for e^pred)
    - TD error projection (for e^delta)
    - Plasticity gate
    - Low-rank adapters for recurrent and action head
    """

    def __init__(self, config: PlasticityConfig):
        super().__init__()

        self.config = config

        # Next-observation predictor
        self.obs_predictor = NextObsPredictor(config.hidden_dim, config.obs_dim)

        # TD error projection to units: e^delta_j = w^delta_j * delta_t
        self.w_delta = nn.Parameter(torch.zeros(config.hidden_dim))
        nn.init.normal_(self.w_delta, std=0.01)

        # Plasticity gate
        self.plasticity_gate = PlasticityGate(config.k_max)

        # Low-rank adapters (BATCHED for per-env plasticity)
        # Recurrent adapter: modifies W_rec in GRU (d -> 3d for gates)
        self.recurrent_adapter = LowRankAdapter(
            in_dim=config.hidden_dim,
            out_dim=config.hidden_dim * 3,  # GRU has 3 gates
            rank=config.adapter_rank,
            num_envs=config.num_envs,
        )

        # Action head adapter: modifies final layer of action decoder
        # Typically hidden_dim -> 256 (byte logits)
        self.action_adapter = LowRankAdapter(
            in_dim=config.hidden_dim,
            out_dim=256,
            rank=config.adapter_rank,
            num_envs=config.num_envs,
        )

        # Learnable learning rate and decay (slow parameters)
        # Store as parameters so they're learned by RL
        self.log_eta = nn.Parameter(torch.tensor(float(config.eta_init)).log())
        self.log_lambda = nn.Parameter(torch.tensor(float(config.lambda_decay)).log())

    @property
    def eta(self) -> float:
        """Get clamped learning rate."""
        return torch.clamp(
            self.log_eta.exp(),
            self.config.eta_min,
            self.config.eta_max
        ).item()

    @property
    def lambda_decay(self) -> float:
        """Get decay coefficient."""
        return self.log_lambda.exp().item()

    def reset_fast_weights(self):
        """Reset all fast weights at episode start."""
        self.recurrent_adapter.reset()
        self.action_adapter.reset()

    def reset_envs(self, env_indices: torch.Tensor):
        """Reset fast weights for specific environments (BATCHED mode)."""
        self.recurrent_adapter.reset_envs(env_indices)
        self.action_adapter.reset_envs(env_indices)

    def compute_local_error(
        self,
        h_t: torch.Tensor,
        phi_o_next: torch.Tensor,
        td_error: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute total local error signal e_j(t).

        e_j(t) = e^pred_j(t) + e^delta_j(t)

        Where:
        - e^pred_j = ∂ℓ_pred/∂u_j (gradient of prediction loss w.r.t. activations)
        - e^delta_j = w^delta_j * delta_t (TD error broadcast)

        Args:
            h_t: Hidden state [batch, hidden_dim]
            phi_o_next: True normalized next obs [batch, obs_dim]
            td_error: Scalar TD error [batch]

        Returns:
            e_t: Total local error [batch, hidden_dim]
        """
        # Prediction error component via autograd
        # PLASTICITY FIX: Use torch.enable_grad() to compute gradients even in no_grad context
        h_t_grad = h_t.detach().clone().requires_grad_(True)
        with torch.enable_grad():
            pred_loss = self.obs_predictor.prediction_loss(h_t_grad, phi_o_next)
            # e^pred is gradient w.r.t. hidden activations
            # This is ∂ℓ_pred/∂h_t since h_t contains the unit activations
            e_pred = torch.autograd.grad(
                pred_loss.sum(),
                h_t_grad,
                create_graph=False,
            )[0]  # [batch, hidden_dim]

        # TD error broadcast component
        # e^delta_j = w^delta_j * delta_t
        e_delta = self.w_delta.unsqueeze(0) * td_error.unsqueeze(-1)  # [batch, hidden_dim]

        # Total local error
        e_t = e_pred + e_delta

        return e_t

    def update_fast_weights(
        self,
        e_t: torch.Tensor,
        x_rec: torch.Tensor,
        x_act: torch.Tensor,
        g_t: torch.Tensor,
    ):
        """
        Update fast weights using local plasticity rule.

        Args:
            e_t: Local error signal [batch, hidden_dim]
            x_rec: Pre-activations for recurrent adapter [batch, hidden_dim]
            x_act: Pre-activations for action adapter [batch, hidden_dim]
            g_t: Global scalars [batch, k_max]
        """
        # Get plasticity gate
        P_t = self.plasticity_gate(g_t)  # [batch]

        # Get learning parameters
        eta = self.eta
        lam = self.lambda_decay

        # Update recurrent adapter
        # For GRU, error is broadcast to all 3 gates
        e_rec = e_t.repeat(1, 3)  # [batch, hidden_dim * 3]
        self.recurrent_adapter.update(e_rec, x_rec, P_t, eta, lam)

        # Update action adapter
        # Project error to action output dimension via learned projection
        # For now, use mean projection (can be learned)
        e_act = e_t.mean(dim=-1, keepdim=True).expand(-1, 256)  # Simple broadcast
        self.action_adapter.update(e_act, x_act, P_t, eta, lam)

    def get_recurrent_adaptation(self) -> torch.Tensor:
        """Get delta to add to recurrent weights."""
        return self.recurrent_adapter.get_adaptation()

    def get_action_adaptation(self) -> torch.Tensor:
        """Get delta to add to action head weights."""
        return self.action_adapter.get_adaptation()

    def count_fast_parameters(self) -> int:
        """
        Count fast parameters.

        Must satisfy: P_fast <= min(0.5M, 0.05 * P_total)
        """
        rec_params = self.recurrent_adapter.A.numel() + self.recurrent_adapter.B.numel()
        act_params = self.action_adapter.A.numel() + self.action_adapter.B.numel()
        return rec_params + act_params

    def count_slow_parameters(self) -> int:
        """Count slow (learnable) parameters."""
        return sum(p.numel() for p in self.parameters())


class PlasticityOutput(NamedTuple):
    """Output from plasticity step."""
    P_t: torch.Tensor           # Plasticity gate [batch]
    e_t: torch.Tensor           # Local error [batch, hidden_dim]
    pred_loss: torch.Tensor     # Prediction loss [batch]
    rec_delta: torch.Tensor     # Recurrent weight delta [3d, d]
    act_delta: torch.Tensor     # Action weight delta [256, d]


def create_plasticity(obs_dim: int = 64, **kwargs) -> LocalPlasticity:
    """Factory function for local plasticity module."""
    config = PlasticityConfig(obs_dim=obs_dim, **kwargs)
    return LocalPlasticity(config)


if __name__ == "__main__":
    print("Testing Local Plasticity...")

    batch_size = 4
    hidden_dim = HIDDEN_DIM
    obs_dim = 64

    plasticity = create_plasticity(obs_dim=obs_dim)

    # Test inputs
    h_t = torch.randn(batch_size, hidden_dim)
    phi_o_next = torch.randn(batch_size, obs_dim)
    td_error = torch.randn(batch_size)
    g_t = torch.sigmoid(torch.randn(batch_size, K_MAX))
    x_rec = torch.randn(batch_size, hidden_dim)
    x_act = torch.randn(batch_size, hidden_dim)

    print("\n=== Testing Components ===")

    # Test prediction
    pred = plasticity.obs_predictor(h_t)
    print(f"Prediction shape: {pred.shape}")
    assert pred.shape == (batch_size, obs_dim)

    # Test prediction loss
    pred_loss = plasticity.obs_predictor.prediction_loss(h_t, phi_o_next)
    print(f"Prediction loss shape: {pred_loss.shape}")
    assert pred_loss.shape == (batch_size,)

    # Test plasticity gate
    P_t = plasticity.plasticity_gate(g_t)
    print(f"Plasticity gate shape: {P_t.shape}")
    print(f"Plasticity gate values: {P_t.tolist()}")
    assert P_t.shape == (batch_size,)
    assert (P_t >= 0).all() and (P_t <= 1).all()

    # Test local error computation
    e_t = plasticity.compute_local_error(h_t, phi_o_next, td_error)
    print(f"Local error shape: {e_t.shape}")
    assert e_t.shape == (batch_size, hidden_dim)

    # Test fast weight update
    plasticity.reset_fast_weights()
    print(f"\nFast weights before update:")
    print(f"  Rec A norm: {plasticity.recurrent_adapter.A.norm().item():.6f}")
    print(f"  Rec B norm: {plasticity.recurrent_adapter.B.norm().item():.6f}")

    plasticity.update_fast_weights(e_t, x_rec, x_act, g_t)
    print(f"\nFast weights after update:")
    print(f"  Rec A norm: {plasticity.recurrent_adapter.A.norm().item():.6f}")
    print(f"  Rec B norm: {plasticity.recurrent_adapter.B.norm().item():.6f}")

    # Test adaptations
    rec_delta = plasticity.get_recurrent_adaptation()
    act_delta = plasticity.get_action_adaptation()
    print(f"\nRecurrent adaptation shape: {rec_delta.shape}")
    print(f"Action adaptation shape: {act_delta.shape}")

    # Parameter counts
    print(f"\n=== Parameter Counts ===")
    fast_params = plasticity.count_fast_parameters()
    slow_params = plasticity.count_slow_parameters()
    print(f"Fast parameters: {fast_params:,}")
    print(f"Slow parameters: {slow_params:,}")

    # Verify fast param budget
    # P_fast <= min(0.5M, 0.05 * P_total)
    # With ~1.4M total params, budget is min(500K, 70K) = 70K
    # Our fast params: 2 * (512*64 + 512*64) for rec + 2 * (256*64 + 512*64) for act
    # = 2*(32768 + 32768) + 2*(16384 + 32768) = 131072 + 98304 = 229K
    # This is too high! Need to reduce rank.
    print(f"\nFast param budget check:")
    print(f"  Current: {fast_params:,}")
    print(f"  Budget: min(500K, 0.05*P_total)")

    # Test gradient flow
    loss = pred_loss.mean()
    loss.backward()
    print(f"\n✓ Backward pass OK")

    # Test learning rate access
    print(f"\nLearning parameters:")
    print(f"  eta: {plasticity.eta:.6f}")
    print(f"  lambda: {plasticity.lambda_decay:.6f}")

    print("\n✓ Local Plasticity works!")
