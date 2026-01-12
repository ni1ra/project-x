"""
Unit tests for the Bits-Back VAE.

Tests verify:
1. Encoder properly conditions on BOTH h_t AND φ(o_t)
2. Decoder produces valid byte distributions
3. Codelength computation matches BLUEPRINT Section 2.6
4. Online/target encoder split works correctly
5. KL intrinsic reward computation
"""

import pytest
import torch
import torch.nn as nn
import math

from src.core.vae import (
    BitsBackVAE,
    VAEEncoder,
    VAEDecoder,
    SinusoidalPositionalEncoding,
    VAEOutput,
    LATENT_DIM,
    HIDDEN_DIM,
)


class TestSinusoidalPE:
    """Test positional encoding."""

    @pytest.fixture
    def pe(self):
        return SinusoidalPositionalEncoding(dim=64)

    def test_output_shape(self, pe):
        positions = torch.arange(100)
        output = pe(positions)
        assert output.shape == (100, 64)

    def test_different_positions_different_encodings(self, pe):
        positions = torch.arange(10)
        output = pe(positions)
        # Check first and last are different
        assert not torch.allclose(output[0], output[-1])

    def test_deterministic(self, pe):
        positions = torch.arange(10)
        out1 = pe(positions)
        out2 = pe(positions)
        assert torch.allclose(out1, out2)


class TestVAEEncoder:
    """Test the VAE encoder q(z|h,o)."""

    @pytest.fixture
    def encoder(self):
        return VAEEncoder(obs_dim=64, hidden_dim=HIDDEN_DIM, latent_dim=LATENT_DIM)

    def test_output_shapes(self, encoder):
        batch_size = 8
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        phi_obs = torch.randn(batch_size, 64)

        z, mu, sigma = encoder(h_t, phi_obs)

        assert z.shape == (batch_size, LATENT_DIM)
        assert mu.shape == (batch_size, LATENT_DIM)
        assert sigma.shape == (batch_size, LATENT_DIM)

    def test_sigma_positive(self, encoder):
        """Sigma must be positive (softplus output)."""
        batch_size = 8
        h_t = torch.randn(batch_size, HIDDEN_DIM) * 10  # Large values
        phi_obs = torch.randn(batch_size, 64)

        _, _, sigma = encoder(h_t, phi_obs)

        assert (sigma > 0).all()

    def test_reparameterization_gradient(self, encoder):
        """Gradients should flow through z via reparameterization."""
        batch_size = 4
        h_t = torch.randn(batch_size, HIDDEN_DIM, requires_grad=True)
        phi_obs = torch.randn(batch_size, 64, requires_grad=True)

        z, _, _ = encoder(h_t, phi_obs)
        loss = z.sum()
        loss.backward()

        assert h_t.grad is not None
        assert phi_obs.grad is not None

    def test_different_obs_different_z(self, encoder):
        """Different observations should produce different z distributions."""
        h_t = torch.randn(1, HIDDEN_DIM)
        obs1 = torch.randn(1, 64)
        obs2 = torch.randn(1, 64) + 5  # Different observation

        _, mu1, _ = encoder(h_t, obs1)
        _, mu2, _ = encoder(h_t, obs2)

        # Should produce different means
        assert not torch.allclose(mu1, mu2)

    def test_encoder_uses_observation(self, encoder):
        """
        CRITICAL TEST: Encoder must USE the observation.
        If ignoring o, mu would be same for different observations.
        """
        batch_size = 2
        h_t = torch.randn(batch_size, HIDDEN_DIM)

        # Two very different observations
        obs_a = torch.zeros(batch_size, 64)
        obs_b = torch.ones(batch_size, 64)

        _, mu_a, _ = encoder(h_t, obs_a)
        _, mu_b, _ = encoder(h_t, obs_b)

        # Must produce different outputs
        assert not torch.allclose(mu_a, mu_b), \
            "CRITICAL: Encoder ignoring observation! This violates bits-back requirement."


class TestVAEDecoder:
    """Test the VAE decoder p(o|z)."""

    @pytest.fixture
    def decoder(self):
        return VAEDecoder(obs_dim=64, latent_dim=LATENT_DIM)

    def test_logits_shape(self, decoder):
        batch_size = 4
        z_t = torch.randn(batch_size, LATENT_DIM)

        logits = decoder(z_t)

        assert logits.shape == (batch_size, 64, 256)

    def test_log_prob_shape(self, decoder):
        batch_size = 4
        z_t = torch.randn(batch_size, LATENT_DIM)
        obs = torch.randint(0, 256, (batch_size, 64))

        log_prob = decoder.log_prob(z_t, obs)

        assert log_prob.shape == (batch_size,)

    def test_log_prob_negative(self, decoder):
        """Log probabilities should be negative (or zero for perfect reconstruction)."""
        batch_size = 4
        z_t = torch.randn(batch_size, LATENT_DIM)
        obs = torch.randint(0, 256, (batch_size, 64))

        log_prob = decoder.log_prob(z_t, obs)

        # Random prediction on random obs should have negative log prob
        assert (log_prob < 0).all()

    def test_log_prob_finite(self, decoder):
        batch_size = 4
        z_t = torch.randn(batch_size, LATENT_DIM)
        obs = torch.randint(0, 256, (batch_size, 64))

        log_prob = decoder.log_prob(z_t, obs)

        assert torch.isfinite(log_prob).all()

    def test_different_z_different_logits(self, decoder):
        """Different latents should produce different predictions."""
        z1 = torch.randn(1, LATENT_DIM)
        z2 = torch.randn(1, LATENT_DIM) + 5

        logits1 = decoder(z1)
        logits2 = decoder(z2)

        assert not torch.allclose(logits1, logits2)


class TestBitsBackVAE:
    """Integration tests for the complete VAE."""

    @pytest.fixture
    def vae(self):
        return BitsBackVAE(obs_dim=64)

    def test_output_type(self, vae):
        batch_size = 2
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        phi_obs = torch.randn(batch_size, 64)
        obs_bytes = torch.randint(0, 256, (batch_size, 64))

        output = vae(h_t, phi_obs, obs_bytes)

        assert isinstance(output, VAEOutput)

    def test_codelength_formula(self, vae):
        """
        Verify codelength matches BLUEPRINT Section 2.6:
        CodeLen_t = -log p(o|z) - log p_0(z) + log q(z|h,o)
        """
        batch_size = 2
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        phi_obs = torch.randn(batch_size, 64)
        obs_bytes = torch.randint(0, 256, (batch_size, 64))

        output = vae(h_t, phi_obs, obs_bytes)

        # Manually compute codelength
        z_t, mu, sigma = output.z_t, output.mu, output.sigma

        # log p(o|z)
        log_p_o_z = output.log_p_o_given_z

        # log p_0(z) = log N(z; 0, I)
        log_p0_z = -0.5 * (
            LATENT_DIM * math.log(2 * math.pi) +
            (z_t ** 2).sum(dim=-1)
        )

        # log q(z|h,o) = log N(z; μ, σ)
        log_q_z = -0.5 * (
            LATENT_DIM * math.log(2 * math.pi) +
            2 * sigma.log().sum(dim=-1) +
            (((z_t - mu) / sigma) ** 2).sum(dim=-1)
        )

        expected_codelen = -log_p_o_z - log_p0_z + log_q_z

        assert torch.allclose(output.code_len, expected_codelen, atol=1e-4)

    def test_online_target_split(self, vae):
        """Test that online and target encoders are separate."""
        batch_size = 2
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        phi_obs = torch.randn(batch_size, 64)

        # Initially they should produce same output
        z_online, mu_online, _ = vae.encode(h_t, phi_obs, use_target=False)
        z_target, mu_target, _ = vae.encode(h_t, phi_obs, use_target=True)

        assert torch.allclose(mu_online, mu_target)

        # After training online encoder only
        loss = mu_online.sum()
        loss.backward()

        # Target gradients should be None
        for param in vae.encoder_target.parameters():
            assert param.grad is None

    def test_polyak_update(self, vae):
        """Test Polyak averaging updates target."""
        # Get initial target params
        old_target = [p.clone() for p in vae.encoder_target.parameters()]

        # Modify online encoder (simulate training step)
        for param in vae.encoder_online.parameters():
            param.data += 0.1 * torch.randn_like(param)

        # Update target
        vae.update_target()

        # Target should have changed slightly
        new_target = list(vae.encoder_target.parameters())
        changed = not all(torch.equal(o, n) for o, n in zip(old_target, new_target))
        assert changed, "Target encoder should update via Polyak averaging"

    def test_kl_intrinsic_symmetric(self, vae):
        """KL divergence should be non-negative."""
        batch_size = 4
        mu1 = torch.randn(batch_size, LATENT_DIM)
        sigma1 = torch.abs(torch.randn(batch_size, LATENT_DIM)) + 0.1
        mu2 = torch.randn(batch_size, LATENT_DIM)
        sigma2 = torch.abs(torch.randn(batch_size, LATENT_DIM)) + 0.1

        kl = vae.compute_kl_intrinsic(mu1, sigma1, mu2, sigma2)

        assert (kl >= 0).all(), "KL divergence must be non-negative"

    def test_kl_zero_for_same_distribution(self, vae):
        """KL(P||P) = 0."""
        batch_size = 4
        mu = torch.randn(batch_size, LATENT_DIM)
        sigma = torch.abs(torch.randn(batch_size, LATENT_DIM)) + 0.1

        kl = vae.compute_kl_intrinsic(mu, sigma, mu, sigma)

        assert torch.allclose(kl, torch.zeros_like(kl), atol=1e-5)

    def test_vae_loss_positive(self, vae):
        """VAE loss (negative ELBO) should typically be positive for random init."""
        batch_size = 4
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        phi_obs = torch.randn(batch_size, 64)
        obs_bytes = torch.randint(0, 256, (batch_size, 64))

        loss = vae.get_vae_loss(h_t, phi_obs, obs_bytes)

        # For untrained model on random data, loss is typically large positive
        assert loss > 0

    def test_gradient_flow(self, vae):
        """Gradients should flow through the VAE."""
        batch_size = 2
        h_t = torch.randn(batch_size, HIDDEN_DIM, requires_grad=True)
        phi_obs = torch.randn(batch_size, 64, requires_grad=True)
        obs_bytes = torch.randint(0, 256, (batch_size, 64))

        output = vae(h_t, phi_obs, obs_bytes, use_target_for_z=False)
        loss = output.code_len.mean()
        loss.backward()

        assert h_t.grad is not None
        assert phi_obs.grad is not None

    def test_parameter_count_reasonable(self, vae):
        """Parameter count should be reasonable."""
        params = sum(p.numel() for p in vae.parameters() if p.requires_grad)

        # Should be less than substrate (auxiliary module)
        assert params < 500_000, f"VAE has too many parameters: {params:,}"
        assert params > 10_000, f"VAE has too few parameters: {params:,}"


class TestCodelengthBounds:
    """Test that codelength behaves as expected."""

    @pytest.fixture
    def vae(self):
        return BitsBackVAE(obs_dim=32)

    def test_codelen_finite(self, vae):
        """Codelength should always be finite."""
        batch_size = 8
        h_t = torch.randn(batch_size, HIDDEN_DIM) * 10
        phi_obs = torch.randn(batch_size, 32)
        obs_bytes = torch.randint(0, 256, (batch_size, 32))

        output = vae(h_t, phi_obs, obs_bytes)

        assert torch.isfinite(output.code_len).all()

    def test_codelen_depends_on_observation(self, vae):
        """Different observations should have different codelengths."""
        batch_size = 1
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        phi_obs = torch.randn(batch_size, 32)

        obs1 = torch.zeros(batch_size, 32, dtype=torch.long)
        obs2 = torch.full((batch_size, 32), 255, dtype=torch.long)

        codelen1 = vae(h_t, phi_obs, obs1).code_len
        codelen2 = vae(h_t, phi_obs, obs2).code_len

        # Different observations should have different codelengths
        assert not torch.equal(codelen1, codelen2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
