"""
VAE / Bits-Back Module - THE SOUL

This implements the stochastic latent bottleneck z_t that enables:
1. Compression pressure via bits-back codelength objective
2. Information gain intrinsic reward
3. Representation learning that survives energy constraints

CRITICAL: The encoder MUST be q(z|h,o) NOT q(z|h).
Without conditioning on o_t, it's a prior, not a posterior.
Bits-back coding requires the posterior to encode information about o_t.

Reference: BLUEPRINT.md Section 2.6
"""

from __future__ import annotations

import math
from typing import Tuple, NamedTuple, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


# =============================================================================
# Architectural Constants (BLUEPRINT.md Section 2.6)
# =============================================================================

LATENT_DIM = 64          # dim(z_t)
HIDDEN_DIM = 512         # Substrate hidden dim
DECODER_MLP_DIM = 128    # Decoder MLP intermediate dim
PE_DIM = 64              # Positional encoding dimension


class VAEOutput(NamedTuple):
    """Output from VAE forward pass."""
    z_t: torch.Tensor            # Sampled latent [batch, latent_dim]
    mu: torch.Tensor             # Posterior mean [batch, latent_dim]
    sigma: torch.Tensor          # Posterior std [batch, latent_dim]
    code_len: torch.Tensor       # Codelength [batch]
    log_p_o_given_z: torch.Tensor  # Reconstruction log-prob [batch]


class SinusoidalPositionalEncoding(nn.Module):
    """
    Fixed sinusoidal positional encoding for byte positions.

    Same style as Transformer PE but for 1D byte sequences.
    """

    def __init__(self, dim: int = PE_DIM, max_len: int = 4096):
        super().__init__()

        # Create PE matrix
        pe = torch.zeros(max_len, dim)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, dim, 2).float() * (-math.log(10000.0) / dim)
        )

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)

        # Register as buffer (not a parameter)
        self.register_buffer('pe', pe)

    def forward(self, positions: torch.Tensor) -> torch.Tensor:
        """
        Get positional encodings for given positions.

        Args:
            positions: Position indices [batch, seq] or [seq]

        Returns:
            Positional encodings [batch, seq, dim] or [seq, dim]
        """
        return self.pe[positions]


class VAEEncoder(nn.Module):
    """
    Posterior Encoder: q(z_t | h_t, φ(o_t))

    CRITICAL: This MUST condition on BOTH h_t AND φ(o_t).

    From BLUEPRINT.md Section 2.6:
        q(z_t | h_t, φ(o_t)) = N(μ_z, σ_z)
        μ_z = W_μ [h_t || φ(o_t)] + b_μ
        σ_z = softplus(W_σ [h_t || φ(o_t)] + b_σ)

    Why o_t is required:
    - Encoder must be a POSTERIOR q(z|h,o), not a prior q(z|h)
    - Bits-back coding computes -log p(o|z) + log q(z|o,h) - log p_0(z)
    - If q ignores o_t, it cannot encode information ABOUT o_t into z_t
    - This makes the negative ELBO meaningless as a codelength
    """

    def __init__(
        self,
        obs_dim: int,
        hidden_dim: int = HIDDEN_DIM,
        latent_dim: int = LATENT_DIM,
        min_sigma: float = 1e-4,
    ):
        super().__init__()

        self.obs_dim = obs_dim
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.min_sigma = min_sigma

        # Input: [h_t || φ(o_t)]
        input_dim = hidden_dim + obs_dim

        # Mean projection
        self.W_mu = nn.Linear(input_dim, latent_dim)

        # Std projection (softplus for positivity)
        self.W_sigma = nn.Linear(input_dim, latent_dim)

    def forward(
        self,
        h_t: torch.Tensor,
        phi_obs: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Encode observation to latent posterior.

        Args:
            h_t: Substrate hidden state [batch, hidden_dim]
            phi_obs: Normalized observation [batch, obs_dim]

        Returns:
            z_t: Sampled latent [batch, latent_dim]
            mu: Posterior mean [batch, latent_dim]
            sigma: Posterior std [batch, latent_dim]
        """
        # Concatenate h_t and φ(o_t) - THIS IS CRITICAL
        concat = torch.cat([h_t, phi_obs], dim=-1)

        # Compute mean and std
        mu = self.W_mu(concat)
        sigma = F.softplus(self.W_sigma(concat)) + self.min_sigma

        # Reparameterization trick: z = μ + σ * ε
        eps = torch.randn_like(mu)
        z_t = mu + sigma * eps

        return z_t, mu, sigma


class VAEDecoder(nn.Module):
    """
    Likelihood Decoder: p(o_t | z_t)

    From BLUEPRINT.md Section 2.6:
        p(o_t | z_t) = Π_i Cat(o_{t,i}; softmax(W_dec f_pos(i, z_t) + b_dec))

    Where:
        f_pos(i, z_t) = MLP([PE(i) || z_t])
        W_dec, b_dec are SHARED across bytes

    This parameter-efficient design keeps decoder params O(1) in obs_dim.
    """

    def __init__(
        self,
        obs_dim: int,
        latent_dim: int = LATENT_DIM,
        pe_dim: int = PE_DIM,
        mlp_dim: int = DECODER_MLP_DIM,
    ):
        super().__init__()

        self.obs_dim = obs_dim
        self.latent_dim = latent_dim

        # Positional encoding
        self.pe = SinusoidalPositionalEncoding(dim=pe_dim)

        # Position-wise MLP: [PE(i) || z_t] -> hidden
        # Input: pe_dim + latent_dim
        # Output: mlp_dim
        self.f_pos = nn.Sequential(
            nn.Linear(pe_dim + latent_dim, mlp_dim),
            nn.ReLU(),
            nn.Linear(mlp_dim, mlp_dim),
            nn.ReLU(),
        )

        # Shared output projection: mlp_dim -> 256 (byte values)
        self.W_dec = nn.Linear(mlp_dim, 256)

    def forward(self, z_t: torch.Tensor, obs_dim: Optional[int] = None) -> torch.Tensor:
        """
        Decode latent to byte logits.

        Args:
            z_t: Latent [batch, latent_dim]
            obs_dim: Number of bytes to decode (default: self.obs_dim)

        Returns:
            logits: Byte logits [batch, obs_dim, 256]
        """
        batch_size = z_t.size(0)
        obs_dim = obs_dim or self.obs_dim

        # Get positional encodings for all byte positions
        positions = torch.arange(obs_dim, device=z_t.device)
        pe = self.pe(positions)  # [obs_dim, pe_dim]

        # Expand z_t to match positions
        # z_t: [batch, latent_dim] -> [batch, obs_dim, latent_dim]
        z_expanded = z_t.unsqueeze(1).expand(-1, obs_dim, -1)

        # Expand PE to match batch
        # pe: [obs_dim, pe_dim] -> [batch, obs_dim, pe_dim]
        pe_expanded = pe.unsqueeze(0).expand(batch_size, -1, -1)

        # Concatenate: [batch, obs_dim, pe_dim + latent_dim]
        concat = torch.cat([pe_expanded, z_expanded], dim=-1)

        # Apply position-wise MLP: [batch, obs_dim, mlp_dim]
        hidden = self.f_pos(concat)

        # Apply shared output projection: [batch, obs_dim, 256]
        logits = self.W_dec(hidden)

        return logits

    def log_prob(
        self,
        z_t: torch.Tensor,
        obs_bytes: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute log p(o_t | z_t).

        Args:
            z_t: Latent [batch, latent_dim]
            obs_bytes: Original observation bytes [batch, obs_dim]

        Returns:
            log_prob: Log probability [batch]
        """
        # Get logits
        logits = self.forward(z_t, obs_bytes.size(-1))  # [batch, obs_dim, 256]

        # Convert observations to long for indexing
        obs_long = obs_bytes.long()

        # Log softmax over byte values
        log_probs = F.log_softmax(logits, dim=-1)  # [batch, obs_dim, 256]

        # Gather log probs for actual bytes
        # obs_long: [batch, obs_dim] -> [batch, obs_dim, 1]
        obs_idx = obs_long.unsqueeze(-1)
        selected_log_probs = log_probs.gather(-1, obs_idx).squeeze(-1)  # [batch, obs_dim]

        # Sum over bytes (log of product)
        total_log_prob = selected_log_probs.sum(dim=-1)  # [batch]

        return total_log_prob


class BitsBackVAE(nn.Module):
    """
    Complete VAE for Bits-Back Codelength Computation.

    From BLUEPRINT.md Section 2.6:
        CodeLen_t = -log p(o_t | z_t) - log p_0(z_t) + log q(z_t | h_t, φ(o_t))

    This is the negative ELBO, used as a codelength estimate for MDL pressure.

    Features:
    - Online encoder: updated by SGD on L_VAE
    - Target encoder: used for actual z_t, updated by Polyak averaging
    - This prevents representation drift after sleep/replay
    """

    def __init__(
        self,
        obs_dim: int,
        hidden_dim: int = HIDDEN_DIM,
        latent_dim: int = LATENT_DIM,
        polyak_tau: float = 1e-3,
    ):
        super().__init__()

        self.obs_dim = obs_dim
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.polyak_tau = polyak_tau

        # Online encoder (trained by SGD)
        self.encoder_online = VAEEncoder(obs_dim, hidden_dim, latent_dim)

        # Target encoder (Polyak averaged, used for inference)
        self.encoder_target = VAEEncoder(obs_dim, hidden_dim, latent_dim)

        # Initialize target = online
        self._copy_params(self.encoder_online, self.encoder_target)

        # Make target non-trainable
        for param in self.encoder_target.parameters():
            param.requires_grad = False

        # Shared decoder
        self.decoder = VAEDecoder(obs_dim, latent_dim)

        # Prior: p_0(z) = N(0, I) - no learnable params

    def _copy_params(self, source: nn.Module, target: nn.Module):
        """Copy parameters from source to target."""
        for s_param, t_param in zip(source.parameters(), target.parameters()):
            t_param.data.copy_(s_param.data)

    def update_target(self):
        """Update target encoder via Polyak averaging."""
        tau = self.polyak_tau
        for s_param, t_param in zip(
            self.encoder_online.parameters(),
            self.encoder_target.parameters()
        ):
            t_param.data.copy_((1 - tau) * t_param.data + tau * s_param.data)

    def encode(
        self,
        h_t: torch.Tensor,
        phi_obs: torch.Tensor,
        use_target: bool = True
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Encode observation to latent.

        Args:
            h_t: Substrate hidden state [batch, hidden_dim]
            phi_obs: Normalized observation [batch, obs_dim]
            use_target: Whether to use target encoder (True for inference)

        Returns:
            z_t, mu, sigma
        """
        encoder = self.encoder_target if use_target else self.encoder_online
        return encoder(h_t, phi_obs)

    def decode_logits(self, z_t: torch.Tensor) -> torch.Tensor:
        """Get decoder logits for visualization/analysis."""
        return self.decoder(z_t)

    def forward(
        self,
        h_t: torch.Tensor,
        phi_obs: torch.Tensor,
        obs_bytes: torch.Tensor,
        use_target_for_z: bool = True,
    ) -> VAEOutput:
        """
        Full VAE forward pass with codelength computation.

        Args:
            h_t: Substrate hidden state [batch, hidden_dim]
            phi_obs: Normalized observation [batch, obs_dim]
            obs_bytes: Original bytes [batch, obs_dim] (for reconstruction)
            use_target_for_z: Use target encoder for z_t sampling

        Returns:
            VAEOutput with z_t, mu, sigma, code_len, log_p_o_given_z
        """
        # Encode using target (for actual z_t used by substrate)
        z_t, mu_target, sigma_target = self.encode(h_t, phi_obs, use_target=use_target_for_z)

        # Also get online encoder stats (for training)
        _, mu_online, sigma_online = self.encode(h_t, phi_obs, use_target=False)

        # Use online stats for codelength (training objective)
        mu = mu_online
        sigma = sigma_online

        # Reconstruction: log p(o_t | z_t)
        log_p_o_given_z = self.decoder.log_prob(z_t, obs_bytes)

        # Prior: log p_0(z_t) = log N(z_t; 0, I)
        # = -0.5 * (d * log(2π) + ||z||²)
        log_p0_z = -0.5 * (
            self.latent_dim * math.log(2 * math.pi) +
            (z_t ** 2).sum(dim=-1)
        )

        # Posterior: log q(z_t | h, o)
        # = log N(z_t; μ, σ) = -0.5 * (d * log(2π) + Σ log σ² + Σ ((z-μ)/σ)²)
        log_q_z = -0.5 * (
            self.latent_dim * math.log(2 * math.pi) +
            2 * sigma.log().sum(dim=-1) +
            (((z_t - mu) / sigma) ** 2).sum(dim=-1)
        )

        # Codelength: -log p(o|z) - log p_0(z) + log q(z|h,o)
        # = negative ELBO
        code_len = -log_p_o_given_z - log_p0_z + log_q_z

        return VAEOutput(
            z_t=z_t,
            mu=mu,
            sigma=sigma,
            code_len=code_len,
            log_p_o_given_z=log_p_o_given_z
        )

    def compute_kl_intrinsic(
        self,
        mu_curr: torch.Tensor,
        sigma_curr: torch.Tensor,
        mu_prev: torch.Tensor,
        sigma_prev: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute KL divergence intrinsic reward.

        r^int_t = KL(q(z_t | h_t, o_t) || q(z_{t-1} | h_{t-1}, o_{t-1}))

        This measures information gain - how much the new observation
        shifted the latent distribution.

        Args:
            mu_curr, sigma_curr: Current posterior [batch, latent_dim]
            mu_prev, sigma_prev: Previous posterior [batch, latent_dim]

        Returns:
            kl: KL divergence [batch]
        """
        # KL between two diagonal Gaussians:
        # KL(N(μ1, σ1²) || N(μ2, σ2²)) =
        #   log(σ2/σ1) + (σ1² + (μ1-μ2)²) / (2σ2²) - 1/2

        var_curr = sigma_curr ** 2
        var_prev = sigma_prev ** 2

        kl = (
            sigma_prev.log() - sigma_curr.log() +
            (var_curr + (mu_curr - mu_prev) ** 2) / (2 * var_prev) -
            0.5
        ).sum(dim=-1)

        return kl

    def get_vae_loss(
        self,
        h_t: torch.Tensor,
        phi_obs: torch.Tensor,
        obs_bytes: torch.Tensor
    ) -> torch.Tensor:
        """
        Get VAE training loss (negative ELBO).

        This is trained by direct SGD, not through RL rewards.
        """
        output = self.forward(h_t, phi_obs, obs_bytes, use_target_for_z=False)
        return output.code_len.mean()


def create_vae(obs_dim: int, **kwargs) -> BitsBackVAE:
    """Factory function to create VAE with defaults."""
    return BitsBackVAE(obs_dim=obs_dim, **kwargs)


if __name__ == "__main__":
    # Quick sanity check
    print("Testing Bits-Back VAE...")

    obs_dim = 64
    batch_size = 4

    vae = BitsBackVAE(obs_dim=obs_dim)

    # Dummy inputs
    h_t = torch.randn(batch_size, HIDDEN_DIM)
    phi_obs = torch.randn(batch_size, obs_dim)  # Already normalized
    obs_bytes = torch.randint(0, 256, (batch_size, obs_dim))

    # Forward pass
    output = vae(h_t, phi_obs, obs_bytes)

    print(f"z_t shape: {output.z_t.shape}")
    print(f"mu shape: {output.mu.shape}")
    print(f"sigma range: [{output.sigma.min():.4f}, {output.sigma.max():.4f}]")
    print(f"codelength: {output.code_len.tolist()}")
    print(f"log p(o|z): {output.log_p_o_given_z.tolist()}")

    # Test KL intrinsic
    _, mu_prev, sigma_prev = vae.encode(h_t, phi_obs)
    h_t_new = h_t + 0.1 * torch.randn_like(h_t)
    phi_obs_new = phi_obs + 0.1 * torch.randn_like(phi_obs)
    _, mu_curr, sigma_curr = vae.encode(h_t_new, phi_obs_new)

    kl = vae.compute_kl_intrinsic(mu_curr, sigma_curr, mu_prev, sigma_prev)
    print(f"KL intrinsic: {kl.tolist()}")

    # Test Polyak update
    old_params = [p.clone() for p in vae.encoder_target.parameters()]
    vae.update_target()
    new_params = list(vae.encoder_target.parameters())
    print(f"Target encoder updated: {not all(torch.equal(o, n) for o, n in zip(old_params, new_params))}")

    # Test loss
    loss = vae.get_vae_loss(h_t, phi_obs, obs_bytes)
    print(f"VAE loss: {loss.item():.4f}")

    # Backward
    loss.backward()
    print("Backward pass OK")

    # Parameter count
    params = sum(p.numel() for p in vae.parameters() if p.requires_grad)
    print(f"Trainable parameters: {params:,}")

    print("\n✓ VAE forward pass works!")
