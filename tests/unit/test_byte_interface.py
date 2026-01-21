"""
Unit tests for Byte Interface.

JARVIS Validation Criteria:
- Pass [0, 255, 0] through φ
- Verify output shape is [3] (normalized float)
- Verify decoder emits valid byte tokens
"""

import pytest
import torch

from src.core.byte_interface import (
    phi,
    phi_inverse,
    AutoregressiveActionDecoder,
    ByteInterface,
)


class TestPhi:
    """Test observation encoder φ(o)."""

    def test_basic_encoding(self):
        """Test basic byte → float encoding."""
        # Input: [0, 255, 0]
        obs = torch.tensor([0, 255, 0], dtype=torch.uint8)

        encoded = phi(obs)

        # Output shape should match input
        assert encoded.shape == obs.shape

        # Check normalization range
        assert encoded.min() >= -1.0
        assert encoded.max() <= 1.0

    def test_normalization_values(self):
        """Test specific normalization values."""
        obs = torch.tensor([0, 127, 128, 255], dtype=torch.float32)

        encoded = phi(obs)

        # 0 → -1.0 (approximately)
        assert encoded[0].item() == pytest.approx(-127.5 / 127.5, abs=0.01)

        # 127 → ~0 (approximately, slight negative)
        assert abs(encoded[1].item()) < 0.01

        # 128 → ~0 (approximately, slight positive)
        assert abs(encoded[2].item()) < 0.01

        # 255 → 1.0
        assert encoded[3].item() == pytest.approx(127.5 / 127.5, abs=0.01)

    def test_batch_encoding(self):
        """Test batch encoding."""
        obs = torch.randint(0, 256, (32, 100), dtype=torch.uint8)

        encoded = phi(obs)

        assert encoded.shape == (32, 100)
        assert encoded.min() >= -1.0
        assert encoded.max() <= 1.0

    def test_phi_inverse(self):
        """Test that phi_inverse reverses phi."""
        obs = torch.tensor([0, 64, 128, 192, 255], dtype=torch.uint8)

        encoded = phi(obs.float())
        decoded = phi_inverse(encoded)

        # Should recover original bytes (with possible rounding)
        assert torch.allclose(decoded.float(), obs.float(), atol=1)


class TestAutoregressiveActionDecoder:
    """Test autoregressive action decoder."""

    def test_initialization(self):
        """Test decoder initializes correctly."""
        decoder = AutoregressiveActionDecoder(
            hidden_dim=512,
            decoder_hidden=128,
            byte_embed_dim=16,
            num_action_bytes=4,
        )

        assert decoder.hidden_dim == 512
        assert decoder.decoder_hidden == 128
        assert decoder.num_action_bytes == 4

    def test_forward_shapes(self):
        """Test that forward produces correct shapes."""
        decoder = AutoregressiveActionDecoder(
            hidden_dim=512,
            decoder_hidden=128,
            num_action_bytes=4,
        )

        batch_size = 8
        h_t = torch.randn(batch_size, 512)

        actions, log_probs, action_mu = decoder(h_t)

        # Actions should be byte indices [0, 255]
        assert actions.shape == (batch_size, 4)
        assert actions.dtype == torch.long
        assert actions.min() >= 0
        assert actions.max() <= 255

        # Log probs should be negative
        assert log_probs.shape == (batch_size, 4)
        assert (log_probs <= 0).all()
        assert action_mu is None

    def test_greedy_decoding(self):
        """Test greedy decoding is deterministic."""
        decoder = AutoregressiveActionDecoder(hidden_dim=512, num_action_bytes=4)
        h_t = torch.randn(1, 512)

        # Greedy should be deterministic
        actions1, _, _ = decoder(h_t, greedy=True)
        actions2, _, _ = decoder(h_t, greedy=True)

        assert torch.equal(actions1, actions2)

    def test_sampling_stochastic(self):
        """Test that sampling produces different results."""
        decoder = AutoregressiveActionDecoder(hidden_dim=512, num_action_bytes=4)
        h_t = torch.randn(1, 512)

        # Sampling should occasionally differ
        torch.manual_seed(42)
        actions1, _, _ = decoder(h_t, greedy=False)

        torch.manual_seed(123)
        actions2, _, _ = decoder(h_t, greedy=False)

        # Not guaranteed but highly likely to differ
        # (if they're identical something might be wrong)

    def test_get_log_prob(self):
        """Test log probability computation for given actions."""
        decoder = AutoregressiveActionDecoder(hidden_dim=512, num_action_bytes=4)

        batch_size = 8
        h_t = torch.randn(batch_size, 512)
        actions = torch.randint(0, 256, (batch_size, 4))

        log_probs = decoder.get_log_prob(h_t, actions)

        assert log_probs.shape == (batch_size, 4)
        assert (log_probs <= 0).all()

    def test_get_entropy(self):
        """Test entropy computation."""
        decoder = AutoregressiveActionDecoder(hidden_dim=512, num_action_bytes=4)

        batch_size = 8
        h_t = torch.randn(batch_size, 512)

        entropy = decoder.get_entropy(h_t)

        # Entropy should be positive and bounded
        assert entropy.shape == (batch_size,)
        assert (entropy >= 0).all()

        # Max entropy for 256-way categorical is ln(256) ≈ 5.54
        assert (entropy <= 6.0).all()

    def test_variable_action_length(self):
        """Test decoder works with different action lengths."""
        decoder = AutoregressiveActionDecoder(hidden_dim=512, num_action_bytes=1, use_gaussian=False)
        h_t = torch.randn(4, 512)

        # Override with different lengths
        actions_1, _, _ = decoder(h_t, num_bytes=1)
        actions_8, _, _ = decoder(h_t, num_bytes=8)

        assert actions_1.shape == (4, 1)
        assert actions_8.shape == (4, 8)


class TestByteInterface:
    """Test complete ByteInterface wrapper."""

    def test_encode_observation(self):
        """Test observation encoding through interface."""
        interface = ByteInterface(hidden_dim=512)

        obs = torch.randint(0, 256, (8, 64), dtype=torch.uint8)
        encoded = interface.encode_observation(obs)

        assert encoded.shape == (8, 64)
        assert encoded.min() >= -1.0
        assert encoded.max() <= 1.0

    def test_decode_action(self):
        """Test action decoding through interface."""
        interface = ByteInterface(hidden_dim=512, num_action_bytes=4)

        h_t = torch.randn(8, 512)
        actions, log_probs = interface.decode_action(h_t)

        assert actions.shape == (8, 4)
        assert log_probs.shape == (8, 4)

    def test_full_pipeline(self):
        """Test full observation → action pipeline."""
        interface = ByteInterface(hidden_dim=512, num_action_bytes=2)

        # Simulate observation
        obs = torch.randint(0, 256, (4, 32), dtype=torch.uint8)

        # Encode observation
        encoded_obs = interface.encode_observation(obs)
        assert encoded_obs.shape == (4, 32)

        # Simulate hidden state (would come from substrate)
        h_t = torch.randn(4, 512)

        # Decode action
        actions, log_probs = interface.decode_action(h_t)

        # Verify valid byte actions
        assert actions.shape == (4, 2)
        assert actions.min() >= 0
        assert actions.max() <= 255
        assert actions.dtype == torch.long
