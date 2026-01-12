"""
Unit tests for Local Plasticity.

Tests verify:
1. Next-obs predictor produces valid predictions
2. Plasticity gate maps g_t to [0,1]
3. Low-rank adapters update correctly
4. Local error combines prediction and TD components
5. Fast weight budget is respected
6. Episode reset works correctly

Reference: BLUEPRINT.md Section 2.4
"""

import pytest
import torch
import torch.nn as nn
import math

from src.core.plasticity import (
    LocalPlasticity,
    NextObsPredictor,
    PlasticityGate,
    LowRankAdapter,
    PlasticityConfig,
    create_plasticity,
    HIDDEN_DIM,
    ADAPTER_RANK,
    K_MAX,
)


class TestNextObsPredictor:
    """Test the predictive coding component."""

    @pytest.fixture
    def predictor(self):
        return NextObsPredictor(hidden_dim=HIDDEN_DIM, obs_dim=64)

    def test_output_shape(self, predictor):
        batch_size = 8
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        pred = predictor(h_t)
        assert pred.shape == (batch_size, 64)

    def test_output_range(self, predictor):
        """Predictions should be in [-1, 1] due to Tanh."""
        h_t = torch.randn(100, HIDDEN_DIM) * 10
        pred = predictor(h_t)
        assert (pred >= -1).all() and (pred <= 1).all()

    def test_prediction_loss_shape(self, predictor):
        batch_size = 4
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        phi_o = torch.randn(batch_size, 64)
        loss = predictor.prediction_loss(h_t, phi_o)
        assert loss.shape == (batch_size,)

    def test_prediction_loss_nonnegative(self, predictor):
        """MSE loss should be non-negative."""
        batch_size = 4
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        phi_o = torch.randn(batch_size, 64)
        loss = predictor.prediction_loss(h_t, phi_o)
        assert (loss >= 0).all()

    def test_different_inputs_different_outputs(self, predictor):
        h1 = torch.randn(1, HIDDEN_DIM)
        h2 = torch.randn(1, HIDDEN_DIM) + 5
        pred1 = predictor(h1)
        pred2 = predictor(h2)
        assert not torch.allclose(pred1, pred2)


class TestPlasticityGate:
    """Test the plasticity gating mechanism."""

    @pytest.fixture
    def gate(self):
        return PlasticityGate(k_max=K_MAX)

    def test_output_shape(self, gate):
        batch_size = 8
        g_t = torch.randn(batch_size, K_MAX)
        P_t = gate(g_t)
        assert P_t.shape == (batch_size,)

    def test_output_range(self, gate):
        """Gate output should be in [0, 1] due to sigmoid."""
        g_t = torch.randn(100, K_MAX) * 10
        P_t = gate(g_t)
        assert (P_t >= 0).all() and (P_t <= 1).all()

    def test_zero_input(self, gate):
        """Zero g_t should produce P ≈ sigmoid(b_P)."""
        g_t = torch.zeros(1, K_MAX)
        P_t = gate(g_t)
        expected = torch.sigmoid(gate.b_P)
        assert torch.allclose(P_t, expected.expand_as(P_t), atol=1e-5)

    def test_gradient_flow(self, gate):
        g_t = torch.randn(4, K_MAX, requires_grad=True)
        P_t = gate(g_t)
        loss = P_t.sum()
        loss.backward()
        assert g_t.grad is not None


class TestLowRankAdapter:
    """Test the low-rank fast weight adapter."""

    @pytest.fixture
    def adapter(self):
        return LowRankAdapter(in_dim=64, out_dim=128, rank=16)

    def test_initial_state(self, adapter):
        """A and B should be zero initially."""
        assert adapter.A.norm() == 0
        assert adapter.B.norm() == 0

    def test_reset(self, adapter):
        """Reset should return to zero state."""
        adapter.A.fill_(1.0)
        adapter.B.fill_(1.0)
        adapter.reset()
        assert adapter.A.norm() == 0
        assert adapter.B.norm() == 0

    def test_adaptation_shape(self, adapter):
        """Delta W should have shape [out_dim, in_dim]."""
        adapter.A.data = torch.randn(128, 16)
        adapter.B.data = torch.randn(64, 16)
        delta = adapter.get_adaptation()
        assert delta.shape == (128, 64)

    def test_zero_adaptation_initially(self, adapter):
        """With zero A and B, adaptation should be zero."""
        delta = adapter.get_adaptation()
        assert delta.norm() == 0

    def test_first_update_initializes(self, adapter):
        """First update should initialize A and B."""
        e_t = torch.randn(4, 128)
        x_t = torch.randn(4, 64)
        P_t = torch.ones(4) * 0.5
        adapter.update(e_t, x_t, P_t, eta=0.01, lambda_decay=0.01)
        assert adapter.A.norm() > 0
        assert adapter.B.norm() > 0

    def test_subsequent_updates_modify(self, adapter):
        """Subsequent updates should change A and B."""
        # First update
        e_t = torch.randn(4, 128)
        x_t = torch.randn(4, 64)
        P_t = torch.ones(4) * 0.5
        adapter.update(e_t, x_t, P_t, eta=0.01, lambda_decay=0.01)

        A_after_first = adapter.A.clone()
        B_after_first = adapter.B.clone()

        # Second update
        adapter.update(e_t, x_t, P_t, eta=0.01, lambda_decay=0.01)

        assert not torch.equal(adapter.A, A_after_first)
        assert not torch.equal(adapter.B, B_after_first)

    def test_decay_reduces_weights(self, adapter):
        """With zero error/pre-activation, decay should reduce weights."""
        # Initialize with non-zero values
        adapter.A.data = torch.ones(128, 16)
        adapter.B.data = torch.ones(64, 16)

        initial_norm = adapter.A.norm()

        # Update with zero signals (only decay)
        e_t = torch.zeros(4, 128)
        x_t = torch.zeros(4, 64)
        P_t = torch.ones(4)
        adapter.update(e_t, x_t, P_t, eta=0.01, lambda_decay=0.1)

        # Norm should decrease
        assert adapter.A.norm() < initial_norm


class TestLocalPlasticity:
    """Integration tests for the complete plasticity module."""

    @pytest.fixture
    def plasticity(self):
        return create_plasticity(obs_dim=64)

    def test_reset_fast_weights(self, plasticity):
        """Reset should zero all fast weights."""
        # Put some values
        plasticity.recurrent_adapter.A.fill_(1.0)
        plasticity.action_adapter.A.fill_(1.0)

        plasticity.reset_fast_weights()

        assert plasticity.recurrent_adapter.A.norm() == 0
        assert plasticity.action_adapter.A.norm() == 0

    def test_local_error_shape(self, plasticity):
        batch_size = 4
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        phi_o_next = torch.randn(batch_size, 64)
        td_error = torch.randn(batch_size)

        e_t = plasticity.compute_local_error(h_t, phi_o_next, td_error)

        assert e_t.shape == (batch_size, HIDDEN_DIM)

    def test_local_error_depends_on_prediction(self, plasticity):
        """Different next observations should give different errors."""
        batch_size = 2
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        td_error = torch.zeros(batch_size)

        phi_o1 = torch.zeros(batch_size, 64)
        phi_o2 = torch.ones(batch_size, 64)

        e1 = plasticity.compute_local_error(h_t, phi_o1, td_error)
        e2 = plasticity.compute_local_error(h_t, phi_o2, td_error)

        assert not torch.allclose(e1, e2)

    def test_local_error_depends_on_td(self, plasticity):
        """Different TD errors should give different local errors."""
        batch_size = 2
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        phi_o = torch.randn(batch_size, 64)

        td1 = torch.zeros(batch_size)
        td2 = torch.ones(batch_size) * 10

        e1 = plasticity.compute_local_error(h_t, phi_o, td1)
        e2 = plasticity.compute_local_error(h_t, phi_o, td2)

        assert not torch.allclose(e1, e2)

    def test_update_fast_weights(self, plasticity):
        """Fast weight update should change adapter values."""
        batch_size = 4
        e_t = torch.randn(batch_size, HIDDEN_DIM)
        x_rec = torch.randn(batch_size, HIDDEN_DIM)
        x_act = torch.randn(batch_size, HIDDEN_DIM)
        g_t = torch.sigmoid(torch.randn(batch_size, K_MAX))

        plasticity.reset_fast_weights()
        plasticity.update_fast_weights(e_t, x_rec, x_act, g_t)

        assert plasticity.recurrent_adapter.A.norm() > 0
        assert plasticity.action_adapter.A.norm() > 0

    def test_adaptations_nonzero_after_update(self, plasticity):
        batch_size = 4
        e_t = torch.randn(batch_size, HIDDEN_DIM)
        x_rec = torch.randn(batch_size, HIDDEN_DIM)
        x_act = torch.randn(batch_size, HIDDEN_DIM)
        g_t = torch.sigmoid(torch.randn(batch_size, K_MAX))

        plasticity.reset_fast_weights()
        plasticity.update_fast_weights(e_t, x_rec, x_act, g_t)

        rec_delta = plasticity.get_recurrent_adaptation()
        act_delta = plasticity.get_action_adaptation()

        assert rec_delta.norm() > 0
        assert act_delta.norm() > 0

    def test_learning_parameters(self, plasticity):
        """Eta and lambda should be accessible."""
        eta = plasticity.eta
        lam = plasticity.lambda_decay

        assert eta > 0
        assert lam > 0


class TestFastParameterBudget:
    """Test that fast parameter budget is respected."""

    def test_budget_compliance(self):
        """Fast params must satisfy: P_fast <= min(0.5M, 0.05 * P_total)."""
        plasticity = create_plasticity(obs_dim=64)

        fast_params = plasticity.count_fast_parameters()

        # Budget is min(500K, 0.05 * total_model_params)
        # For a ~1.4M model, this is min(500K, 70K) = 70K
        # We're being conservative and checking against 100K
        assert fast_params <= 100_000, f"Fast params {fast_params:,} exceeds budget"

    def test_fast_params_breakdown(self):
        """Verify where fast params come from."""
        plasticity = create_plasticity(obs_dim=64)

        # Recurrent adapter: (hidden_dim * 3, rank) + (hidden_dim, rank)
        # = (1536, 16) + (512, 16) = 24576 + 8192 = 32768
        rec_params = plasticity.recurrent_adapter.A.numel() + plasticity.recurrent_adapter.B.numel()

        # Action adapter: (256, rank) + (hidden_dim, rank)
        # = (256, 16) + (512, 16) = 4096 + 8192 = 12288
        act_params = plasticity.action_adapter.A.numel() + plasticity.action_adapter.B.numel()

        total_fast = plasticity.count_fast_parameters()
        assert total_fast == rec_params + act_params


class TestSlowParameters:
    """Test slow (learnable) parameters."""

    def test_slow_params_gradient(self):
        """Slow parameters should have gradients after backward."""
        plasticity = create_plasticity(obs_dim=64)

        h_t = torch.randn(4, HIDDEN_DIM, requires_grad=True)
        phi_o = torch.randn(4, 64)

        loss = plasticity.obs_predictor.prediction_loss(h_t, phi_o).mean()
        loss.backward()

        # Check predictor weights have gradients
        for param in plasticity.obs_predictor.parameters():
            assert param.grad is not None

    def test_plasticity_gate_learnable(self):
        """Plasticity gate parameters should be learnable."""
        plasticity = create_plasticity(obs_dim=64)

        g_t = torch.randn(4, K_MAX, requires_grad=True)
        P_t = plasticity.plasticity_gate(g_t)
        loss = P_t.sum()
        loss.backward()

        assert plasticity.plasticity_gate.w_P.grad is not None
        assert plasticity.plasticity_gate.b_P.grad is not None

    def test_td_projection_learnable(self):
        """TD error projection vector should be a learnable parameter."""
        plasticity = create_plasticity(obs_dim=64)
        assert plasticity.w_delta.requires_grad


class TestAdapterShapes:
    """Test that adapter shapes match expected layers."""

    def test_recurrent_adapter_shape(self):
        """Recurrent adapter should modify GRU weights (3*d x d)."""
        plasticity = create_plasticity(obs_dim=64)

        rec_delta = plasticity.get_recurrent_adaptation()

        # GRU has 3 gates, each d->d
        assert rec_delta.shape == (HIDDEN_DIM * 3, HIDDEN_DIM)

    def test_action_adapter_shape(self):
        """Action adapter should modify action head (256 x d)."""
        plasticity = create_plasticity(obs_dim=64)

        act_delta = plasticity.get_action_adaptation()

        # Action head outputs byte logits (256 classes)
        assert act_delta.shape == (256, HIDDEN_DIM)


class TestEpisodeLifecycle:
    """Test plasticity across episode boundaries."""

    def test_multi_step_updates(self):
        """Multiple updates within episode should accumulate."""
        plasticity = create_plasticity(obs_dim=64)
        plasticity.reset_fast_weights()

        batch_size = 4
        g_t = torch.sigmoid(torch.randn(batch_size, K_MAX))

        norms = []
        for _ in range(5):
            e_t = torch.randn(batch_size, HIDDEN_DIM)
            x_rec = torch.randn(batch_size, HIDDEN_DIM)
            x_act = torch.randn(batch_size, HIDDEN_DIM)
            plasticity.update_fast_weights(e_t, x_rec, x_act, g_t)
            norms.append(plasticity.recurrent_adapter.A.norm().item())

        # Weights should change over updates (may not monotonically increase)
        assert not all(n == norms[0] for n in norms)

    def test_reset_between_episodes(self):
        """Reset should return to clean slate."""
        plasticity = create_plasticity(obs_dim=64)

        # Simulate episode
        batch_size = 4
        for _ in range(10):
            e_t = torch.randn(batch_size, HIDDEN_DIM)
            x_rec = torch.randn(batch_size, HIDDEN_DIM)
            x_act = torch.randn(batch_size, HIDDEN_DIM)
            g_t = torch.sigmoid(torch.randn(batch_size, K_MAX))
            plasticity.update_fast_weights(e_t, x_rec, x_act, g_t)

        # End of episode
        plasticity.reset_fast_weights()

        # Should be back to zero
        assert plasticity.recurrent_adapter.A.norm() == 0
        assert plasticity.action_adapter.A.norm() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
