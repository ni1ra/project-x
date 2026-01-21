"""
Tests for Temporal Hierarchy module.
"""

import pytest
import torch

from src.core.temporal_hierarchy import (
    HierarchicalSubstrate, HierarchyConfig, create_hierarchical_substrate
)


class TestHierarchicalSubstrate:
    """Test hierarchical substrate functionality."""

    @pytest.fixture
    def substrate(self):
        config = HierarchyConfig()
        return HierarchicalSubstrate(config, obs_dim=64, latent_dim=64)

    @pytest.fixture
    def batch_inputs(self, substrate):
        batch_size = 4
        obs_dim = 64
        latent_dim = 64

        h_fast, h_slow, g = substrate.init_state(batch_size, torch.device('cpu'))
        phi_obs = torch.randn(batch_size, obs_dim)
        z_t = torch.randn(batch_size, latent_dim)
        a_prev = torch.randint(0, 256, (batch_size,))
        k_r = torch.randint(1, 5, (batch_size,))

        return {
            "h_fast": h_fast,
            "h_slow": h_slow,
            "g": g,
            "phi_obs": phi_obs,
            "z_t": z_t,
            "a_prev": a_prev,
            "k_r": k_r,
        }

    def test_init_state(self, substrate):
        batch_size = 8
        h_fast, h_slow, g = substrate.init_state(batch_size, torch.device('cpu'))

        assert h_fast.shape == (batch_size, substrate.config.hidden_dim)
        assert h_slow.shape == (batch_size, substrate.config.slow_hidden_dim)
        assert g.shape == (batch_size, substrate.config.k_max)

        # All zeros at init
        assert torch.all(h_fast == 0)
        assert torch.all(h_slow == 0)
        assert torch.all(g == 0)

    def test_forward_shapes(self, substrate, batch_inputs):
        output = substrate(
            phi_obs=batch_inputs["phi_obs"],
            z_t=batch_inputs["z_t"],
            a_prev=batch_inputs["a_prev"],
            h_fast=batch_inputs["h_fast"],
            h_slow=batch_inputs["h_slow"],
            g_prev=batch_inputs["g"],
            k_r=batch_inputs["k_r"],
            training=True,
        )

        batch_size = batch_inputs["h_fast"].size(0)

        assert output.h_combined.shape == (batch_size, substrate.config.hidden_dim)
        assert output.h_fast.shape == (batch_size, substrate.config.hidden_dim)
        assert output.h_slow.shape == (batch_size, substrate.config.slow_hidden_dim)
        assert output.g_t.shape == (batch_size, substrate.config.k_max)
        assert output.gate_t.shape == (batch_size,)
        assert output.slow_updated.shape == (batch_size,)
        assert output.surprise_t.shape == (batch_size,)

    def test_force_slow_update(self, substrate, batch_inputs):
        # Without force
        output1 = substrate(
            phi_obs=batch_inputs["phi_obs"],
            z_t=batch_inputs["z_t"],
            a_prev=batch_inputs["a_prev"],
            h_fast=batch_inputs["h_fast"],
            h_slow=batch_inputs["h_slow"],
            g_prev=batch_inputs["g"],
            k_r=batch_inputs["k_r"],
            training=False,
            force_slow_update=False,
        )

        # With force
        output2 = substrate(
            phi_obs=batch_inputs["phi_obs"],
            z_t=batch_inputs["z_t"],
            a_prev=batch_inputs["a_prev"],
            h_fast=batch_inputs["h_fast"],
            h_slow=batch_inputs["h_slow"],
            g_prev=batch_inputs["g"],
            k_r=batch_inputs["k_r"],
            training=False,
            force_slow_update=True,
        )

        # Forced should all be 1.0
        assert torch.all(output2.slow_updated == 1.0)

    def test_gate_range(self, substrate, batch_inputs):
        """Gate should be in [0, 1] (sigmoid output)."""
        output = substrate(
            phi_obs=batch_inputs["phi_obs"],
            z_t=batch_inputs["z_t"],
            a_prev=batch_inputs["a_prev"],
            h_fast=batch_inputs["h_fast"],
            h_slow=batch_inputs["h_slow"],
            g_prev=batch_inputs["g"],
            k_r=batch_inputs["k_r"],
            training=True,
        )

        assert torch.all(output.gate_t >= 0)
        assert torch.all(output.gate_t <= 1)

    def test_g_t_range(self, substrate, batch_inputs):
        """Global scalars should be in [0, 1] (sigmoid output)."""
        output = substrate(
            phi_obs=batch_inputs["phi_obs"],
            z_t=batch_inputs["z_t"],
            a_prev=batch_inputs["a_prev"],
            h_fast=batch_inputs["h_fast"],
            h_slow=batch_inputs["h_slow"],
            g_prev=batch_inputs["g"],
            k_r=batch_inputs["k_r"],
            training=True,
        )

        assert torch.all(output.g_t >= 0)
        assert torch.all(output.g_t <= 1)

    def test_gradient_flow(self, substrate, batch_inputs):
        """Verify gradients flow through all components."""
        output = substrate(
            phi_obs=batch_inputs["phi_obs"],
            z_t=batch_inputs["z_t"],
            a_prev=batch_inputs["a_prev"],
            h_fast=batch_inputs["h_fast"],
            h_slow=batch_inputs["h_slow"],
            g_prev=batch_inputs["g"],
            k_r=batch_inputs["k_r"],
            training=True,
        )

        # Create loss from multiple outputs
        loss = (
            output.h_combined.sum() +
            output.g_t.sum() +
            output.gate_t.sum()
        )
        loss.backward()

        # Check gradient flow to key components
        assert substrate.fast_gru.W_input.weight.grad is not None
        assert substrate.slow_gru.W_input.weight.grad is not None
        assert substrate.gate_net[0].weight.grad is not None
        assert substrate.W_g.weight.grad is not None

    def test_k_eff_computation(self, substrate, batch_inputs):
        """Test K_eff computation."""
        output = substrate(
            phi_obs=batch_inputs["phi_obs"],
            z_t=batch_inputs["z_t"],
            a_prev=batch_inputs["a_prev"],
            h_fast=batch_inputs["h_fast"],
            h_slow=batch_inputs["h_slow"],
            g_prev=batch_inputs["g"],
            k_r=batch_inputs["k_r"],
            training=True,
        )

        k_eff = substrate.compute_k_eff(output.g_t)

        # K_eff should be positive and <= k_max
        assert k_eff > 0
        assert k_eff <= substrate.config.k_max

    def test_energy_cost_computation(self, substrate, batch_inputs):
        """Test energy cost with slow update penalty."""
        output = substrate(
            phi_obs=batch_inputs["phi_obs"],
            z_t=batch_inputs["z_t"],
            a_prev=batch_inputs["a_prev"],
            h_fast=batch_inputs["h_fast"],
            h_slow=batch_inputs["h_slow"],
            g_prev=batch_inputs["g"],
            k_r=batch_inputs["k_r"],
            training=True,
            force_slow_update=True,
        )

        energy = substrate.get_energy_cost(output.slow_updated)

        # With slow update, energy should be > base
        assert torch.all(energy > 0.01)  # base_energy

    def test_multiple_steps(self, substrate, batch_inputs):
        """Test running multiple sequential steps."""
        h_fast = batch_inputs["h_fast"]
        h_slow = batch_inputs["h_slow"]
        g = batch_inputs["g"]

        for step in range(10):
            output = substrate(
                phi_obs=batch_inputs["phi_obs"],
                z_t=batch_inputs["z_t"],
                a_prev=batch_inputs["a_prev"],
                h_fast=h_fast,
                h_slow=h_slow,
                g_prev=g,
                k_r=batch_inputs["k_r"],
                training=True,
            )

            # Update states for next step
            h_fast = output.h_fast
            h_slow = output.h_slow
            g = output.g_t

        # States should have evolved
        assert not torch.allclose(h_fast, batch_inputs["h_fast"])

    def test_factory_function(self):
        """Test create_hierarchical_substrate factory."""
        substrate = create_hierarchical_substrate(
            obs_dim=64,
            latent_dim=32,
            k_slow=16,
        )

        assert substrate.config.k_slow == 16
        assert substrate.latent_dim == 32

    def test_step_counter_increments(self, substrate, batch_inputs):
        """Verify step counter increments during training."""
        initial_count = substrate.step_counter.item()

        for _ in range(5):
            substrate(
                phi_obs=batch_inputs["phi_obs"],
                z_t=batch_inputs["z_t"],
                a_prev=batch_inputs["a_prev"],
                h_fast=batch_inputs["h_fast"],
                h_slow=batch_inputs["h_slow"],
                g_prev=batch_inputs["g"],
                k_r=batch_inputs["k_r"],
                training=True,
            )

        assert substrate.step_counter.item() == initial_count + 5

    def test_inference_mode_counter_increments(self, substrate, batch_inputs):
        """Step counter should increment during inference (clock trigger depends on it)."""
        initial_count = substrate.step_counter.item()

        for _ in range(5):
            substrate(
                phi_obs=batch_inputs["phi_obs"],
                z_t=batch_inputs["z_t"],
                a_prev=batch_inputs["a_prev"],
                h_fast=batch_inputs["h_fast"],
                h_slow=batch_inputs["h_slow"],
                g_prev=batch_inputs["g"],
                k_r=batch_inputs["k_r"],
                training=False,
            )

        assert substrate.step_counter.item() == initial_count + 5

    def test_surprise_stop_gradient(self, substrate, batch_inputs):
        """Surprise signal should be stop-gradient (no autograd path)."""
        output = substrate(
            phi_obs=batch_inputs["phi_obs"],
            z_t=batch_inputs["z_t"],
            a_prev=batch_inputs["a_prev"],
            h_fast=batch_inputs["h_fast"],
            h_slow=batch_inputs["h_slow"],
            g_prev=batch_inputs["g"],
            k_r=batch_inputs["k_r"],
            training=True,
        )

        assert output.surprise_t.requires_grad is False
