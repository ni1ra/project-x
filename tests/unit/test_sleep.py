"""
Unit tests for Sleep/Offline Consolidation Module.

Tests verify:
1. Sleep trigger outputs valid probabilities
2. Latent dynamics model predicts next states
3. Replay buffer stores and samples correctly
4. Prioritized sampling works
5. Synaptic renormalization respects ρ
6. Multi-step imagination works

Reference: BLUEPRINT.md Section 2.5
"""

import pytest
import torch
import torch.nn as nn
import numpy as np

from src.core.sleep import (
    SleepModule,
    SleepTrigger,
    LatentDynamicsModel,
    PrioritizedReplayBuffer,
    Transition,
    SleepConfig,
    create_sleep_module,
    HIDDEN_DIM,
    LATENT_DIM,
    BUFFER_CAPACITY,
    PRIORITY_ALPHA,
    RHO,
    N_MAX,
)


class TestSleepTrigger:
    """Test the sleep trigger mechanism."""

    @pytest.fixture
    def trigger(self):
        return SleepTrigger(hidden_dim=HIDDEN_DIM)

    def test_output_shape(self, trigger):
        batch_size = 8
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        omega = trigger(h_t)
        assert omega.shape == (batch_size,)

    def test_output_range(self, trigger):
        """Omega should be in [0, 1] due to sigmoid."""
        h_t = torch.randn(100, HIDDEN_DIM) * 10
        omega = trigger(h_t)
        assert (omega >= 0).all() and (omega <= 1).all()

    def test_initial_low_probability(self, trigger):
        """Initially, sleep probability should be low (~0.1-0.2)."""
        h_t = torch.zeros(10, HIDDEN_DIM)
        omega = trigger(h_t)
        # Due to b_omega = -2, sigmoid(-2) ≈ 0.12
        assert (omega < 0.3).all()

    def test_gradient_flow(self, trigger):
        h_t = torch.randn(4, HIDDEN_DIM, requires_grad=True)
        omega = trigger(h_t)
        loss = omega.sum()
        loss.backward()
        assert h_t.grad is not None


class TestLatentDynamicsModel:
    """Test the latent dynamics prediction model."""

    @pytest.fixture
    def dynamics(self):
        return LatentDynamicsModel(latent_dim=LATENT_DIM, action_dim=1)

    def test_output_shape(self, dynamics):
        batch_size = 4
        z_t = torch.randn(batch_size, LATENT_DIM)
        a_t = torch.randint(0, 256, (batch_size, 1))
        z_next = dynamics(z_t, a_t)
        assert z_next.shape == (batch_size, LATENT_DIM)

    def test_different_actions_different_predictions(self, dynamics):
        z_t = torch.randn(1, LATENT_DIM)
        a1 = torch.tensor([[0]])
        a2 = torch.tensor([[255]])

        z1 = dynamics(z_t, a1)
        z2 = dynamics(z_t, a2)

        assert not torch.allclose(z1, z2)

    def test_different_states_different_predictions(self, dynamics):
        z1 = torch.randn(1, LATENT_DIM)
        z2 = torch.randn(1, LATENT_DIM) + 5
        a_t = torch.tensor([[128]])

        pred1 = dynamics(z1, a_t)
        pred2 = dynamics(z2, a_t)

        assert not torch.allclose(pred1, pred2)

    def test_multi_step_rollout_length(self, dynamics):
        batch_size = 4
        z_t = torch.randn(batch_size, LATENT_DIM)
        actions = torch.randint(0, 256, (batch_size, 5))

        z_preds = dynamics.multi_step_rollout(z_t, actions, n_steps=5)

        assert len(z_preds) == 5
        for z in z_preds:
            assert z.shape == (batch_size, LATENT_DIM)

    def test_multi_step_rollout_sequential(self, dynamics):
        """Each prediction should depend on previous."""
        batch_size = 2
        z_t = torch.randn(batch_size, LATENT_DIM)
        actions = torch.randint(0, 256, (batch_size, 3))

        z_preds = dynamics.multi_step_rollout(z_t, actions, n_steps=3)

        # Predictions should be different from each other
        assert not torch.allclose(z_preds[0], z_preds[1])
        assert not torch.allclose(z_preds[1], z_preds[2])

    def test_gradient_flow(self, dynamics):
        z_t = torch.randn(4, LATENT_DIM, requires_grad=True)
        a_t = torch.randint(0, 256, (4, 1))
        z_next = dynamics(z_t, a_t)
        loss = z_next.sum()
        loss.backward()
        assert z_t.grad is not None


class TestPrioritizedReplayBuffer:
    """Test the prioritized replay buffer."""

    @pytest.fixture
    def buffer(self):
        return PrioritizedReplayBuffer(capacity=100)

    def make_transition(self, obs_dim=64, latent_dim=64):
        return Transition(
            obs=torch.randint(0, 256, (obs_dim,)),
            action=torch.randint(0, 256, (1,)),
            reward=np.random.randn(),
            next_obs=torch.randint(0, 256, (obs_dim,)),
            done=False,
            energy=0.05,
            code_len=1.0,
            z_t=torch.randn(latent_dim),
            h_t=torch.randn(HIDDEN_DIM),
        )

    def test_add_and_size(self, buffer):
        for i in range(50):
            buffer.add(self.make_transition())
        assert len(buffer) == 50

    def test_capacity_limit(self, buffer):
        for i in range(150):
            buffer.add(self.make_transition())
        assert len(buffer) == 100  # Capacity is 100

    def test_sample_returns_correct_size(self, buffer):
        for i in range(50):
            buffer.add(self.make_transition())

        transitions, weights, indices = buffer.sample(batch_size=16)

        assert len(transitions) == 16
        assert weights.shape == (16,)
        assert len(indices) == 16

    def test_importance_weights_normalized(self, buffer):
        for i in range(50):
            buffer.add(self.make_transition(), td_error=float(i))

        _, weights, _ = buffer.sample(batch_size=16, beta=0.5)

        # Weights should be normalized to max = 1
        assert weights.max().item() == pytest.approx(1.0)
        assert (weights > 0).all()
        assert (weights <= 1).all()

    def test_priority_update(self, buffer):
        for i in range(20):
            buffer.add(self.make_transition())

        indices = np.array([0, 1, 2])
        td_errors = np.array([10.0, 5.0, 1.0])

        buffer.update_priorities(indices, td_errors)

        # Higher TD error should have higher priority
        assert buffer.priorities[0] > buffer.priorities[1]
        assert buffer.priorities[1] > buffer.priorities[2]

    def test_prioritized_sampling_bias(self, buffer):
        """High priority items should be sampled more often."""
        # Add 10 low priority, 10 high priority
        for i in range(10):
            buffer.add(self.make_transition(), td_error=0.1)
        for i in range(10):
            buffer.add(self.make_transition(), td_error=10.0)

        # Sample many times and count
        high_priority_count = 0
        for _ in range(100):
            _, _, indices = buffer.sample(batch_size=5)
            high_priority_count += sum(1 for i in indices if i >= 10)

        # High priority items should be sampled more than 50% of the time
        assert high_priority_count > 250  # 5 * 100 * 0.5


class TestSleepModule:
    """Integration tests for the complete sleep module."""

    @pytest.fixture
    def sleep(self):
        return create_sleep_module(obs_dim=64)

    def test_sleep_probability(self, sleep):
        batch_size = 4
        h_t = torch.randn(batch_size, HIDDEN_DIM)
        omega = sleep.get_sleep_probability(h_t)
        assert omega.shape == (batch_size,)

    def test_sleep_energy(self, sleep):
        omega = torch.tensor([0.0, 0.5, 1.0])
        energy = sleep.compute_sleep_energy(omega)

        assert energy[0].item() == pytest.approx(0.0)
        assert energy[1].item() == pytest.approx(0.05)  # 0.5 * 0.1
        assert energy[2].item() == pytest.approx(0.1)  # 1.0 * 0.1

    def test_is_sleeping(self, sleep):
        omega = torch.tensor([0.3, 0.5, 0.7, 0.9])
        sleeping = sleep.is_sleeping(omega)

        assert not sleeping[0]
        assert not sleeping[1]  # 0.5 is boundary, not sleeping
        assert sleeping[2]
        assert sleeping[3]

    def test_add_and_sample_experience(self, sleep):
        # Add experiences
        for i in range(50):
            sleep.add_experience(
                obs=torch.randint(0, 256, (64,)),
                action=torch.randint(0, 256, (1,)),
                reward=float(i),
                next_obs=torch.randint(0, 256, (64,)),
                done=False,
                energy=0.05,
                code_len=1.0,
                z_t=torch.randn(LATENT_DIM),
            )

        # Sample
        batch, weights, indices = sleep.sample_replay(batch_size=16)

        assert batch['obs'].shape == (16, 64)
        assert batch['rewards'].shape == (16,)
        assert batch['z_t'].shape == (16, LATENT_DIM)

    def test_dynamics_loss(self, sleep):
        batch_size = 4
        z_t = torch.randn(batch_size, LATENT_DIM)
        a_t = torch.randint(0, 256, (batch_size, 1))
        z_target = torch.randn(batch_size, LATENT_DIM)

        loss = sleep.compute_dynamics_loss(z_t, a_t, z_target)

        assert loss.shape == ()
        assert loss.item() >= 0

    def test_multistep_dynamics_loss(self, sleep):
        batch_size = 4
        z_t = torch.randn(batch_size, LATENT_DIM)
        actions = torch.randint(0, 256, (batch_size, 5))
        z_targets = [torch.randn(batch_size, LATENT_DIM) for _ in range(5)]

        loss = sleep.compute_multistep_dynamics_loss(z_t, actions, z_targets, n_steps=3)

        assert loss.shape == ()
        assert loss.item() >= 0

    def test_synaptic_renormalization(self, sleep):
        """Test that renormalization respects ρ."""
        # Create module with large weights
        module = nn.Linear(64, 32)
        module.weight.data *= 10

        # Some columns should exceed ρ=1.0
        col_norms_before = module.weight.norm(dim=1)
        assert (col_norms_before > RHO).any()

        # Apply renormalization
        sleep.synaptic_renormalization(module)

        # All column norms should be <= ρ
        col_norms_after = module.weight.norm(dim=1)
        assert (col_norms_after <= RHO + 1e-5).all()

    def test_renormalization_preserves_small_weights(self, sleep):
        """Weights already under ρ should not change."""
        module = nn.Linear(64, 32)
        module.weight.data *= 0.1  # Make weights small

        weights_before = module.weight.data.clone()
        sleep.synaptic_renormalization(module)
        weights_after = module.weight.data

        assert torch.allclose(weights_before, weights_after)

    def test_episode_reset(self, sleep):
        sleep.sleep_energy_used.fill_(50.0)
        sleep.reset_episode()
        assert sleep.sleep_energy_used.item() == 0.0

    def test_can_sleep_budget(self, sleep):
        assert sleep.can_sleep()

        sleep.sleep_energy_used.fill_(sleep.config.b_sleep + 1)
        assert not sleep.can_sleep()

    def test_beta_annealing(self, sleep):
        initial_beta = sleep.beta
        sleep.update_training_steps(500_000)
        mid_beta = sleep.beta
        sleep.update_training_steps(500_000)
        final_beta = sleep.beta

        assert initial_beta < mid_beta < final_beta
        assert final_beta <= sleep.config.beta_end


class TestSleepBudget:
    """Test sleep energy budget constraints."""

    def test_max_sleep_duration(self):
        """B_sleep / E_sleep_max = 100 / 0.1 = 1000 steps."""
        sleep = create_sleep_module()

        max_steps = sleep.config.b_sleep / sleep.config.e_sleep_max
        assert max_steps == 1000

    def test_e_sleep_max_value(self):
        """E_sleep_max should be 0.1 J/step."""
        sleep = create_sleep_module()
        assert sleep.config.e_sleep_max == 0.1

    def test_b_sleep_value(self):
        """B_sleep should be 100 J."""
        sleep = create_sleep_module()
        assert sleep.config.b_sleep == 100.0


class TestImagination:
    """Test imagination/latent rollout functionality."""

    @pytest.fixture
    def sleep(self):
        return create_sleep_module()

    def test_imagination_horizon(self, sleep):
        """Imagination should support up to N_max steps."""
        batch_size = 4
        z_t = torch.randn(batch_size, LATENT_DIM)
        actions = torch.randint(0, 256, (batch_size, N_MAX))

        z_preds = sleep.dynamics.multi_step_rollout(z_t, actions, n_steps=N_MAX)

        assert len(z_preds) == N_MAX

    def test_stop_gradient_in_loss(self, sleep):
        """Target should have stop-gradient applied."""
        batch_size = 4
        z_t = torch.randn(batch_size, LATENT_DIM, requires_grad=True)
        a_t = torch.randint(0, 256, (batch_size, 1))
        z_target = torch.randn(batch_size, LATENT_DIM, requires_grad=True)

        loss = sleep.compute_dynamics_loss(z_t, a_t, z_target)
        loss.backward()

        # z_t should have gradient (it's the input)
        assert z_t.grad is not None
        # z_target should NOT have gradient (stop-gradient)
        assert z_target.grad is None


class TestParameterCounts:
    """Test parameter counts are reasonable."""

    def test_dynamics_model_params(self):
        """Dynamics model should be small (2-layer MLP 64+1→128→64)."""
        dynamics = LatentDynamicsModel(latent_dim=64, action_dim=1)
        params = sum(p.numel() for p in dynamics.parameters())

        # Expected: (65*128 + 128) + (128*64 + 64) = 8448 + 8256 = 16704
        assert params < 20_000

    def test_sleep_module_total_params(self):
        """Total sleep module params should be small."""
        sleep = create_sleep_module()
        params = sum(p.numel() for p in sleep.parameters())

        # Should be relatively small compared to main brain
        assert params < 50_000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
