"""
Unit tests for Energy Proxy.

JARVIS Validation Criteria:
- Run a 512x512 matmul
- Assert E_t equals exactly (2*512^3 * k_F) + (3*512^2 * 4 * k_M)
"""

import pytest
from src.energy.proxy import (
    EnergyConfig,
    EnergyTracker,
    EnergyAccumulator,
    count_matmul_flops,
    count_matmul_bytes,
    count_linear_flops,
    count_gru_flops,
)


class TestMatmulCounting:
    """Test FLOP and byte counting for matrix multiplication."""

    def test_512x512_matmul_flops(self):
        """Test FLOP count for 512x512 matmul."""
        m, k, n = 512, 512, 512
        expected_flops = 2 * m * k * n  # 2 * 512^3
        assert count_matmul_flops(m, k, n) == expected_flops
        assert expected_flops == 2 * 512**3

    def test_512x512_matmul_bytes(self):
        """Test byte count for 512x512 matmul."""
        m, k, n = 512, 512, 512
        dtype_bytes = 4  # float32
        # Read A[512,512] + B[512,512], Write C[512,512]
        expected_bytes = (m * k + k * n + m * n) * dtype_bytes
        assert count_matmul_bytes(m, k, n, dtype_bytes) == expected_bytes
        assert expected_bytes == 3 * 512**2 * 4


class TestEnergyCalculation:
    """Test energy calculation with kappa constants."""

    def test_512x512_matmul_energy(self):
        """
        JARVIS Validation Test:
        E_t = (2*512^3 * k_F) + (3*512^2 * 4 * k_M)
        """
        config = EnergyConfig(
            kappa_F=1e-9,  # J/FLOP
            kappa_M=5e-11,  # J/Byte
        )

        tracker = EnergyTracker(config)
        tracker.record_matmul(512, 512, 512)

        # Calculate expected energy
        expected_flops = 2 * 512**3
        expected_bytes = 3 * 512**2 * 4
        expected_energy = (expected_flops * config.kappa_F +
                          expected_bytes * config.kappa_M)

        assert tracker.step_energy == pytest.approx(expected_energy)

        # Verify the formula matches JARVIS specification
        jarvis_formula_energy = (2 * 512**3 * 1e-9) + (3 * 512**2 * 4 * 5e-11)
        assert tracker.step_energy == pytest.approx(jarvis_formula_energy)

    def test_energy_accumulation(self):
        """Test that energy accumulates correctly across operations."""
        config = EnergyConfig()
        tracker = EnergyTracker(config)

        # Two matmuls
        tracker.record_matmul(256, 256, 256)
        energy_1 = tracker.step_energy

        tracker.record_matmul(128, 128, 128)
        energy_2 = tracker.step_energy

        # Energy should be sum of both
        assert energy_2 > energy_1


class TestBudgetEnforcement:
    """Test energy budget enforcement (kill-switch)."""

    def test_episode_budget_exceeded(self):
        """Test that exceeding episode budget returns False."""
        config = EnergyConfig(
            kappa_F=1e-9,
            kappa_M=5e-11,
            B_max_ep=0.001,  # Very small budget
        )

        tracker = EnergyTracker(config)

        # Large operation should exceed budget
        tracker.record_matmul(1024, 1024, 1024)

        # Commit should return False (budget exceeded)
        assert tracker.commit_step() is False

    def test_episode_budget_ok(self):
        """Test that staying within budget returns True."""
        config = EnergyConfig(
            kappa_F=1e-9,
            kappa_M=5e-11,
            B_max_ep=200.0,  # Default budget
        )

        tracker = EnergyTracker(config)

        # Small operation should be within budget
        tracker.record_matmul(64, 64, 64)

        # Commit should return True (within budget)
        assert tracker.commit_step() is True

    def test_episode_reset(self):
        """Test that episode reset clears episode energy."""
        config = EnergyConfig()
        tracker = EnergyTracker(config)

        tracker.record_matmul(512, 512, 512)
        tracker.commit_step()
        initial_episode_energy = tracker.episode_energy

        tracker.reset_episode()

        assert tracker.episode_energy == 0.0
        assert tracker.total_energy > 0.0  # Total should persist


class TestLinearLayerCounting:
    """Test FLOP counting for linear layers."""

    def test_linear_flops(self):
        """Test FLOP count for linear layer."""
        in_features, out_features, batch_size = 512, 256, 32

        expected_flops = 2 * in_features * out_features * batch_size
        assert count_linear_flops(in_features, out_features, batch_size) == expected_flops


class TestGRUCounting:
    """Test FLOP counting for GRU cells."""

    def test_gru_flops_positive(self):
        """Test that GRU FLOP count is positive and reasonable."""
        input_size, hidden_size, batch_size = 128, 512, 32

        flops = count_gru_flops(input_size, hidden_size, batch_size)

        # GRU should have substantial FLOPs
        assert flops > 0

        # Should be roughly 6 linear layers worth (3 gates × 2 projections)
        linear_flops = count_linear_flops(input_size, hidden_size, batch_size)
        assert flops > 5 * linear_flops  # At least 5 linear layers worth


class TestEnergyConfig:
    """Test energy configuration loading."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EnergyConfig()

        assert config.kappa_F == 1e-9
        assert config.kappa_M == 5e-11
        assert config.B_max_ep == 200.0
        assert config.B_max_day == 72000.0
        assert config.calibrated is False


class TestEnergyStats:
    """Test energy statistics reporting."""

    def test_get_stats(self):
        """Test that stats are reported correctly."""
        config = EnergyConfig()
        tracker = EnergyTracker(config)

        tracker.record_matmul(512, 512, 512)

        stats = tracker.get_stats()

        assert "step_energy_J" in stats
        assert "episode_energy_J" in stats
        assert "total_flops" in stats
        assert "total_bytes" in stats
        assert "calibrated" in stats
        assert stats["calibrated"] is False
