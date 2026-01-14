"""
Unit tests for the LN-GRU Substrate.

Tests verify:
1. Architectural correctness per BLUEPRINT.md Section 2.2
2. Forward pass shapes and ranges
3. Sparse routing behavior
4. Compute allocation (Binomial sampling in train, deterministic in eval)
5. Global scalars emission
6. Emergence metrics (CBR, BI, K_eff)
"""

import pytest
import torch
import torch.nn as nn

from src.core.substrate import (
    RPJSubstrate,
    LNGRUCell,
    SparseRouter,
    ComputeAllocator,
    GlobalScalarBroadcast,
    SubstrateOutput,
    HIDDEN_DIM,
    K_MAX,
    LATENT_DIM,
    K_R_MAX,
    N_MAX,
    NUM_BLOCKS,
)


class TestArchitecturalConstants:
    """Verify architectural constants match BLUEPRINT.md Section 2.2."""

    def test_hidden_dim(self):
        assert HIDDEN_DIM == 512, "d (hidden dim) must be 512"

    def test_k_max(self):
        assert K_MAX == 16, "K_max (global scalars) must be 16"

    def test_latent_dim(self):
        assert LATENT_DIM == 64, "dim(z_t) must be 64"

    def test_k_r_max(self):
        assert K_R_MAX == 4, "k_r_max (max routed blocks) must be 4"

    def test_n_max(self):
        assert N_MAX == 5, "N_max (max rollout steps) must be 5"

    def test_num_blocks(self):
        assert NUM_BLOCKS == 64, "B (routing blocks) must be 64"

    def test_hidden_divisible_by_blocks(self):
        assert HIDDEN_DIM % NUM_BLOCKS == 0, \
            "hidden_dim must be divisible by num_blocks"


class TestLNGRUCell:
    """Test the LayerNorm GRU cell."""

    @pytest.fixture
    def cell(self):
        return LNGRUCell(input_dim=100, hidden_dim=HIDDEN_DIM)

    def test_output_shape(self, cell):
        batch_size = 8
        x = torch.randn(batch_size, 100)
        h = torch.randn(batch_size, HIDDEN_DIM)

        h_next = cell(x, h)

        assert h_next.shape == (batch_size, HIDDEN_DIM)

    def test_contains_layer_norm(self, cell):
        """Verify LayerNorm is present (BLUEPRINT requirement)."""
        assert hasattr(cell, 'ln_h'), "Must have pre-activation LayerNorm"
        assert hasattr(cell, 'ln_reset'), "Must have reset gate LayerNorm"
        assert isinstance(cell.ln_h, nn.LayerNorm)
        assert isinstance(cell.ln_reset, nn.LayerNorm)

    def test_hidden_state_bounded(self, cell):
        """Hidden state should be bounded (tanh output)."""
        batch_size = 8
        x = torch.randn(batch_size, 100) * 10  # Large input
        h = torch.randn(batch_size, HIDDEN_DIM)

        h_next = cell(x, h)

        # tanh outputs are in [-1, 1], but GRU mixing can expand this
        # Still should be roughly bounded
        assert h_next.abs().max() < 10, "Hidden state should be bounded"


class TestSparseRouter:
    """Test blockwise sparse routing."""

    @pytest.fixture
    def router(self):
        return SparseRouter(
            hidden_dim=HIDDEN_DIM,
            num_blocks=NUM_BLOCKS,
            k_r_max=K_R_MAX
        )

    def test_routing_mask_shape(self, router):
        batch_size = 8
        h = torch.randn(batch_size, HIDDEN_DIM)
        k_r = torch.tensor([2, 3, 4, 2, 3, 4, 2, 3])

        soft, hard = router(h, k_r, training=True)

        assert soft.shape == (batch_size, NUM_BLOCKS)
        assert hard.shape == (batch_size, NUM_BLOCKS)

    def test_hard_mask_sparsity(self, router):
        """Hard mask should have exactly k_r ones per sample."""
        batch_size = 4
        h = torch.randn(batch_size, HIDDEN_DIM)
        k_r = torch.tensor([2, 3, 4, 1])

        _, hard = router(h, k_r, training=False)

        for i in range(batch_size):
            num_ones = hard[i].sum().item()
            assert num_ones == k_r[i].item(), \
                f"Sample {i}: expected {k_r[i].item()} active blocks, got {num_ones}"

    def test_invalid_mask_does_not_corrupt_block0(self, router):
        """
        Regression test for CRITICAL bug:
        invalid TopK positions must not zero out block 0 when k_r < k_max_batch.
        """
        batch_size = 2
        h = torch.zeros(batch_size, HIDDEN_DIM)
        k_r = torch.tensor([1, K_R_MAX])  # k_max_batch=4, sample 0 has invalid positions

        # Force deterministic TopK indices [0, 1, 2, 3, ...] via router bias.
        with torch.no_grad():
            router.router.weight.zero_()
            router.router.bias.copy_(torch.arange(NUM_BLOCKS, 0, -1, dtype=torch.float32))

        _, hard = router(h, k_r, training=False)

        # Sample 0 should keep block 0 active (not corrupted) and have exactly 1 routed block.
        assert hard[0, 0].item() == 1.0
        assert hard[0].sum().item() == 1.0

        # Sample 1 should have exactly K_R_MAX routed blocks.
        assert hard[1].sum().item() == float(K_R_MAX)

    def test_soft_weights_sum_to_one(self, router):
        """Soft weights should sum to 1 (softmax/Gumbel-softmax)."""
        batch_size = 4
        h = torch.randn(batch_size, HIDDEN_DIM)
        k_r = torch.tensor([2, 3, 4, 2])

        soft, _ = router(h, k_r, training=False)

        sums = soft.sum(dim=-1)
        assert torch.allclose(sums, torch.ones(batch_size), atol=1e-5)

    def test_apply_routing_preserves_shape(self, router):
        batch_size = 4
        h_current = torch.randn(batch_size, HIDDEN_DIM)
        h_next = torch.randn(batch_size, HIDDEN_DIM)
        mask = torch.zeros(batch_size, NUM_BLOCKS)
        mask[:, :2] = 1  # Route first 2 blocks

        h_routed = router.apply_routing(h_current, h_next, mask)

        assert h_routed.shape == (batch_size, HIDDEN_DIM)

    def test_routing_actually_routes(self, router):
        """Verify routing actually selects blocks."""
        batch_size = 1
        h_current = torch.zeros(batch_size, HIDDEN_DIM)
        h_next = torch.ones(batch_size, HIDDEN_DIM)

        # Route only first block
        mask = torch.zeros(batch_size, NUM_BLOCKS)
        mask[0, 0] = 1

        h_routed = router.apply_routing(h_current, h_next, mask)

        block_size = HIDDEN_DIM // NUM_BLOCKS
        # First block should be from h_next (ones)
        assert h_routed[0, :block_size].sum().item() == block_size
        # Rest should be from h_current (zeros)
        assert h_routed[0, block_size:].sum().item() == 0


class TestComputeAllocator:
    """Test compute allocation with Binomial sampling."""

    @pytest.fixture
    def allocator(self):
        return ComputeAllocator(
            hidden_dim=HIDDEN_DIM,
            k_r_max=K_R_MAX,
            n_max=N_MAX
        )

    def test_output_shapes(self, allocator):
        batch_size = 8
        h = torch.randn(batch_size, HIDDEN_DIM)

        c_t, k_r, n_t, log_prob = allocator(h, training=True)

        assert c_t.shape == (batch_size, 1)
        assert k_r.shape == (batch_size,)
        assert n_t.shape == (batch_size,)
        assert log_prob.shape == (batch_size,)

    def test_c_t_in_range(self, allocator):
        """c_t should be in [0, 1] (sigmoid output)."""
        batch_size = 8
        h = torch.randn(batch_size, HIDDEN_DIM) * 10

        c_t, _, _, _ = allocator(h, training=True)

        assert (c_t >= 0).all() and (c_t <= 1).all()

    def test_k_r_in_range_train(self, allocator):
        """k_r should be in [1, k_r_max] during training."""
        batch_size = 100  # Large batch for statistical coverage
        h = torch.randn(batch_size, HIDDEN_DIM)

        _, k_r, _, _ = allocator(h, training=True)

        assert (k_r >= 1).all(), "k_r must be at least 1"
        assert (k_r <= K_R_MAX).all(), f"k_r must be at most {K_R_MAX}"

    def test_n_t_in_range_train(self, allocator):
        """n_t should be in [0, n_max] during training."""
        batch_size = 100
        h = torch.randn(batch_size, HIDDEN_DIM)

        _, _, n_t, _ = allocator(h, training=True)

        assert (n_t >= 0).all(), "n_t must be at least 0"
        assert (n_t <= N_MAX).all(), f"n_t must be at most {N_MAX}"

    def test_deterministic_eval(self, allocator):
        """Eval mode should give deterministic results."""
        batch_size = 4
        h = torch.randn(batch_size, HIDDEN_DIM)

        c1, k1, n1, _ = allocator(h, training=False)
        c2, k2, n2, _ = allocator(h, training=False)

        assert torch.allclose(c1, c2)
        assert torch.equal(k1, k2)
        assert torch.equal(n1, n2)

    def test_log_prob_finite(self, allocator):
        """Log probabilities should be finite."""
        batch_size = 8
        h = torch.randn(batch_size, HIDDEN_DIM)

        _, _, _, log_prob = allocator(h, training=True)

        assert torch.isfinite(log_prob).all()


class TestGlobalScalarBroadcast:
    """Test global scalar emission."""

    @pytest.fixture
    def broadcast(self):
        return GlobalScalarBroadcast(hidden_dim=HIDDEN_DIM, k_max=K_MAX)

    def test_output_shape(self, broadcast):
        batch_size = 8
        h = torch.randn(batch_size, HIDDEN_DIM)

        g_t = broadcast(h)

        assert g_t.shape == (batch_size, K_MAX)

    def test_output_range(self, broadcast):
        """g_t should be in [0, 1] (sigmoid)."""
        batch_size = 8
        h = torch.randn(batch_size, HIDDEN_DIM) * 10

        g_t = broadcast(h)

        assert (g_t >= 0).all() and (g_t <= 1).all()

    def test_k_eff_computation(self, broadcast):
        """Test K_eff (participation ratio) computation."""
        # Create g_t with known variance pattern
        # If all scalars have equal variance, K_eff = K_max
        # If one scalar dominates, K_eff -> 1

        # Equal variance case
        g_equal = torch.rand(100, K_MAX)
        k_eff_equal = GlobalScalarBroadcast.compute_k_eff(g_equal)
        # Should be close to K_MAX
        assert k_eff_equal > K_MAX * 0.5

        # One dominant scalar case
        g_dominant = torch.zeros(100, K_MAX)
        g_dominant[:, 0] = torch.rand(100)  # Only first scalar varies
        k_eff_dominant = GlobalScalarBroadcast.compute_k_eff(g_dominant)
        # Should be close to 1
        assert k_eff_dominant < 2


class TestRPJSubstrate:
    """Integration tests for the full substrate."""

    @pytest.fixture
    def substrate(self):
        return RPJSubstrate(obs_dim=64)

    def test_parameter_count_reasonable(self, substrate):
        """Parameter count should fit under energy budget."""
        params = substrate.count_parameters()
        # BLUEPRINT: P ≤ 10M with N_max=5
        assert params < 10_000_000, f"Too many parameters: {params:,}"
        # Should have a reasonable minimum for the architecture
        assert params > 100_000, f"Too few parameters: {params:,}"

    def test_forward_pass_shapes(self, substrate):
        batch_size = 4
        obs_dim = 64

        h = substrate.init_hidden(batch_size, torch.device('cpu'))
        g = substrate.init_global_scalars(batch_size, torch.device('cpu'))

        phi_obs = torch.randn(batch_size, obs_dim)
        z_t = torch.randn(batch_size, LATENT_DIM)
        a_prev = torch.randint(0, 256, (batch_size, 1))

        output = substrate(phi_obs, z_t, a_prev, h, g, training=True)

        assert output.h_next.shape == (batch_size, HIDDEN_DIM)
        assert output.g_t.shape == (batch_size, K_MAX)
        assert output.c_t.shape == (batch_size, 1)
        assert output.k_r.shape == (batch_size,)
        assert output.routing_mask.shape == (batch_size, NUM_BLOCKS)
        assert output.cbr_t.shape == (batch_size,)
        assert output.bi_t.shape == (batch_size,)

    def test_output_type(self, substrate):
        batch_size = 2
        h = substrate.init_hidden(batch_size, torch.device('cpu'))
        g = substrate.init_global_scalars(batch_size, torch.device('cpu'))

        phi_obs = torch.randn(batch_size, 64)
        z_t = torch.randn(batch_size, LATENT_DIM)
        a_prev = torch.randint(0, 256, (batch_size,))

        output = substrate(phi_obs, z_t, a_prev, h, g, training=True)

        assert isinstance(output, SubstrateOutput)

    def test_value_head(self, substrate):
        batch_size = 4
        h = torch.randn(batch_size, HIDDEN_DIM)

        value = substrate.get_value(h)

        assert value.shape == (batch_size,)

    def test_recurrent_state_update(self, substrate):
        """Hidden state should change after forward pass."""
        batch_size = 2
        h0 = substrate.init_hidden(batch_size, torch.device('cpu'))
        g0 = substrate.init_global_scalars(batch_size, torch.device('cpu'))

        phi_obs = torch.randn(batch_size, 64)
        z_t = torch.randn(batch_size, LATENT_DIM)
        a_prev = torch.randint(0, 256, (batch_size, 1))

        output = substrate(phi_obs, z_t, a_prev, h0, g0, training=True)

        # h_next should be different from h0 (unless very unlucky)
        assert not torch.allclose(output.h_next, h0)

    def test_gradient_flow(self, substrate):
        """Gradients should flow through the substrate."""
        batch_size = 2
        h = substrate.init_hidden(batch_size, torch.device('cpu'))
        g = substrate.init_global_scalars(batch_size, torch.device('cpu'))
        h.requires_grad_(True)

        phi_obs = torch.randn(batch_size, 64, requires_grad=True)
        z_t = torch.randn(batch_size, LATENT_DIM, requires_grad=True)
        a_prev = torch.randint(0, 256, (batch_size, 1))

        output = substrate(phi_obs, z_t, a_prev, h, g, training=True)

        # Compute loss and backprop
        loss = output.h_next.sum() + output.g_t.sum()
        loss.backward()

        # Check gradients exist
        assert phi_obs.grad is not None
        assert z_t.grad is not None

    def test_multi_step_rollout(self, substrate):
        """Test multiple sequential steps."""
        batch_size = 2
        num_steps = 10

        h = substrate.init_hidden(batch_size, torch.device('cpu'))
        g = substrate.init_global_scalars(batch_size, torch.device('cpu'))

        for _ in range(num_steps):
            phi_obs = torch.randn(batch_size, 64)
            z_t = torch.randn(batch_size, LATENT_DIM)
            a_prev = torch.randint(0, 256, (batch_size, 1))

            output = substrate(phi_obs, z_t, a_prev, h, g, training=True)
            h = output.h_next
            g = output.g_t

        # Should complete without error
        assert h.shape == (batch_size, HIDDEN_DIM)


class TestEmergenceMetrics:
    """Test emergence metrics computation."""

    @pytest.fixture
    def substrate(self):
        return RPJSubstrate(obs_dim=64)

    def test_cbr_positive(self, substrate):
        """CBR should be positive."""
        batch_size = 4
        h = substrate.init_hidden(batch_size, torch.device('cpu'))
        g = substrate.init_global_scalars(batch_size, torch.device('cpu'))

        phi_obs = torch.randn(batch_size, 64)
        z_t = torch.randn(batch_size, LATENT_DIM)
        a_prev = torch.randint(0, 256, (batch_size, 1))

        output = substrate(phi_obs, z_t, a_prev, h, g, training=True)

        assert (output.cbr_t > 0).all()

    def test_bi_in_range(self, substrate):
        """BI (broadcast index) should be in [0, 1]."""
        batch_size = 4
        h = substrate.init_hidden(batch_size, torch.device('cpu'))
        g = substrate.init_global_scalars(batch_size, torch.device('cpu'))

        phi_obs = torch.randn(batch_size, 64)
        z_t = torch.randn(batch_size, LATENT_DIM)
        a_prev = torch.randint(0, 256, (batch_size, 1))

        output = substrate(phi_obs, z_t, a_prev, h, g, training=True)

        assert (output.bi_t >= 0).all()
        assert (output.bi_t <= 1).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
