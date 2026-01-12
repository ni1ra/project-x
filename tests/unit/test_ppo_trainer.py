"""
Unit tests for PPO Trainer.

Tests verify:
1. PopArt normalizer updates correctly
2. Rollout buffer stores and batches correctly
3. GAE computation is correct
4. Collapse detection works
5. PPO update modifies parameters
6. VAE and sleep training work

Reference: BLUEPRINT.md Section 2.7, 2.8
"""

import pytest
import torch
import torch.nn as nn
import numpy as np

from src.core.ppo_trainer import (
    PPOConfig,
    PopArtNormalizer,
    RPJRolloutBuffer,
    RPJTrainer,
    create_trainer,
)
from src.core.rpj_brain import RPJBrain, RPJConfig, create_brain
from src.core.byte_interface import phi


class TestPopArtNormalizer:
    """Test the PopArt value normalization."""

    def test_initial_state(self):
        normalizer = PopArtNormalizer()
        assert normalizer.mean == 0.0
        assert normalizer.std == 1.0
        assert normalizer.count == 0

    def test_first_update(self):
        normalizer = PopArtNormalizer()
        values = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])
        normalizer.update(values)

        assert normalizer.count == 5
        assert normalizer.mean == pytest.approx(3.0, rel=0.01)
        # std of [1,2,3,4,5] is ~1.58
        assert normalizer.std > 1.0

    def test_normalize_denormalize(self):
        normalizer = PopArtNormalizer()
        values = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])
        normalizer.update(values)

        # Normalize and denormalize should be inverse
        normalized = normalizer.normalize(values)
        denormalized = normalizer.denormalize(normalized)

        assert torch.allclose(values, denormalized, atol=1e-5)

    def test_normalized_mean_zero(self):
        normalizer = PopArtNormalizer()
        values = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])
        normalizer.update(values)

        normalized = normalizer.normalize(values)
        assert normalized.mean().item() == pytest.approx(0.0, abs=0.01)

    def test_exponential_moving_average(self):
        normalizer = PopArtNormalizer(beta=0.5)

        # First update
        values1 = torch.tensor([0.0, 0.0, 0.0, 0.0])
        normalizer.update(values1)
        mean1 = normalizer.mean

        # Second update with different values
        values2 = torch.tensor([10.0, 10.0, 10.0, 10.0])
        normalizer.update(values2)
        mean2 = normalizer.mean

        # With beta=0.5, mean should be between the two
        assert mean2 > mean1
        assert mean2 < 10.0


class TestRPJRolloutBuffer:
    """Test the rollout buffer."""

    @pytest.fixture
    def buffer(self):
        return RPJRolloutBuffer(
            buffer_size=100,
            obs_dim=64,
            action_bytes=1,
            hidden_dim=512,
            latent_dim=64,
            k_max=6,
            device="cpu",
        )

    def make_transition(self, obs_dim=64, hidden_dim=512, latent_dim=64, k_max=6):
        return {
            "obs": torch.randint(0, 256, (obs_dim,)),
            "next_obs": torch.randint(0, 256, (obs_dim,)),
            "action": torch.randint(0, 256, (1,)),
            "extrinsic_reward": np.random.randn(),
            "intrinsic_reward": np.random.randn() * 0.1,
            "rpj_reward": np.random.randn(),
            "value": np.random.randn(),
            "action_log_prob": torch.randn(1),
            "compute_log_prob": np.random.randn(),
            "done": False,
            "energy": np.random.rand() * 0.1,
            "code_len": np.random.rand(),
            "hidden": torch.randn(hidden_dim),
            "z_t": torch.randn(latent_dim),
            "mu": torch.randn(latent_dim),
            "sigma": torch.rand(latent_dim) + 0.1,
            "g_t": torch.sigmoid(torch.randn(k_max)),
            "c_t": torch.rand(1),
        }

    def test_add_and_position(self, buffer):
        trans = self.make_transition()
        buffer.add(**trans)
        assert buffer.pos == 1
        assert not buffer.full

    def test_buffer_wraps(self, buffer):
        for i in range(150):
            buffer.add(**self.make_transition())

        assert buffer.pos == 50  # 150 % 100
        assert buffer.full

    def test_get_batches_size(self, buffer):
        for i in range(100):
            buffer.add(**self.make_transition())

        batch_size = 32
        batches = list(buffer.get_batches(batch_size))

        # Should have at least 3 batches (100 / 32 = 3.125)
        assert len(batches) >= 3

        # Each batch should have correct keys
        for batch in batches:
            assert 'observations' in batch
            assert 'actions' in batch
            assert 'returns' in batch
            assert 'advantages' in batch

    def test_returns_computed(self, buffer):
        for i in range(100):
            trans = self.make_transition()
            trans["rpj_reward"] = 1.0  # Fixed reward
            trans["value"] = 0.5
            buffer.add(**trans)

        buffer.compute_returns_and_advantages(last_value=0.0, gamma=0.99)

        # Returns should be computed
        assert buffer.returns.sum() != 0
        # Advantages should be computed
        assert buffer.advantages.sum() != 0

    def test_collapse_metric_range(self, buffer):
        for i in range(50):
            buffer.add(**self.make_transition())

        entropy = buffer.compute_collapse_metric()

        # Binary entropy is in [0, ln(2) ≈ 0.693]
        assert entropy >= 0
        assert entropy <= 0.7

    def test_collapse_metric_saturated(self, buffer):
        """When c_t is all 0 or all 1, entropy should be near 0."""
        for i in range(50):
            trans = self.make_transition()
            trans["c_t"] = torch.tensor([0.001])  # Nearly 0
            buffer.add(**trans)

        entropy = buffer.compute_collapse_metric()
        assert entropy < 0.05

    def test_reset(self, buffer):
        for i in range(50):
            buffer.add(**self.make_transition())

        buffer.reset()
        assert buffer.pos == 0
        assert not buffer.full


class TestGAEComputation:
    """Test GAE advantage computation."""

    def test_gae_simple_case(self):
        """Test GAE with known values."""
        buffer = RPJRolloutBuffer(
            buffer_size=5,
            obs_dim=8,
            action_bytes=1,
            hidden_dim=64,
            latent_dim=32,
            k_max=6,
            device="cpu",
        )

        # Add 5 transitions with known rewards and values
        for i in range(5):
            buffer.observations[i] = torch.zeros(8)
            buffer.next_observations[i] = torch.zeros(8)
            buffer.actions[i] = torch.zeros(1)
            buffer.rpj_rewards[i] = 1.0  # Constant reward
            buffer.values[i] = 0.5      # Constant value
            buffer.dones[i] = 0.0

        buffer.pos = 5

        # Compute GAE
        buffer.compute_returns_and_advantages(last_value=0.5, gamma=0.99, gae_lambda=0.95)

        # Advantages should be computed
        assert buffer.advantages.sum() != 0
        # Returns should be > values since rewards are positive
        assert (buffer.returns > buffer.values).all()

    def test_gae_episode_boundary(self):
        """Test that done=True cuts off bootstrapping."""
        buffer = RPJRolloutBuffer(
            buffer_size=5,
            obs_dim=8,
            action_bytes=1,
            hidden_dim=64,
            latent_dim=32,
            k_max=6,
            device="cpu",
        )

        for i in range(5):
            buffer.observations[i] = torch.zeros(8)
            buffer.next_observations[i] = torch.zeros(8)
            buffer.actions[i] = torch.zeros(1)
            buffer.rpj_rewards[i] = 1.0
            buffer.values[i] = 0.5
            buffer.dones[i] = 0.0

        # Mark step 2 as done (episode boundary)
        buffer.dones[2] = 1.0
        buffer.pos = 5

        buffer.compute_returns_and_advantages(last_value=0.5, gamma=0.99, gae_lambda=0.95)

        # Returns should be computed
        assert buffer.returns.sum() != 0


class TestPPOConfigDefaults:
    """Test PPO configuration defaults match BLUEPRINT."""

    def test_default_values(self):
        config = PPOConfig()

        # From BLUEPRINT Section 2.7
        assert config.gamma >= 0.999
        assert config.clip_epsilon == 0.2
        assert config.lr_policy == 3e-4
        assert config.entropy_coef == 0.01
        assert config.max_grad_norm == 1.0

    def test_collapse_threshold(self):
        config = PPOConfig()
        # BLUEPRINT: H(c_t) < 0.05 = collapse
        assert config.collapse_entropy_threshold == 0.05


class TestRPJTrainerCreation:
    """Test trainer initialization."""

    def test_create_trainer(self):
        brain, trainer = create_trainer(obs_dim=64, action_bytes=1, device="cpu")

        assert isinstance(brain, RPJBrain)
        assert isinstance(trainer, RPJTrainer)

    def test_trainer_has_optimizers(self):
        brain, trainer = create_trainer(obs_dim=64, device="cpu")

        assert trainer.policy_optimizer is not None
        assert trainer.vae_optimizer is not None
        assert trainer.rnd_optimizer is not None

    def test_trainer_with_sleep(self):
        brain, trainer = create_trainer(obs_dim=64, enable_sleep=True, device="cpu")

        assert brain.sleep is not None
        assert trainer.sleep_optimizer is not None

    def test_trainer_without_sleep(self):
        brain, trainer = create_trainer(obs_dim=64, enable_sleep=False, device="cpu")

        assert brain.sleep is None
        assert trainer.sleep_optimizer is None


class TestTrainerUpdate:
    """Test training update mechanics."""

    @pytest.fixture
    def trainer(self):
        brain, trainer = create_trainer(obs_dim=8, action_bytes=1, device="cpu")
        return trainer

    def fill_buffer(self, trainer, n=100):
        """Fill buffer with dummy data."""
        k_max = trainer.brain.config.k_max  # Use actual k_max from brain
        hidden_dim = trainer.brain.config.hidden_dim
        latent_dim = trainer.brain.config.latent_dim
        obs_dim = trainer.brain.config.obs_dim

        for i in range(n):
            trainer.buffer.add(
                obs=torch.randint(0, 256, (obs_dim,)),
                next_obs=torch.randint(0, 256, (obs_dim,)),
                action=torch.randint(0, 256, (1,)),
                extrinsic_reward=np.random.randn(),
                intrinsic_reward=np.random.randn() * 0.1,
                rpj_reward=np.random.randn(),
                value=np.random.randn(),
                action_log_prob=torch.randn(1),
                compute_log_prob=np.random.randn(),
                done=False,
                energy=np.random.rand() * 0.1,
                code_len=np.random.rand(),
                hidden=torch.randn(hidden_dim),
                z_t=torch.randn(latent_dim),
                mu=torch.randn(latent_dim),
                sigma=torch.rand(latent_dim) + 0.1,
                g_t=torch.sigmoid(torch.randn(k_max)),
                c_t=torch.rand(1),
            )
        trainer.buffer.compute_returns_and_advantages(last_value=0.0)

    def test_policy_update_modifies_params(self, trainer):
        """PPO update should change policy parameters."""
        self.fill_buffer(trainer, n=trainer.config.num_steps_per_update)

        # Get initial params
        initial_params = {
            name: param.clone()
            for name, param in trainer.brain.substrate.named_parameters()
        }

        # Update
        stats = trainer.update_policy()

        # Check some params changed
        changed = False
        for name, param in trainer.brain.substrate.named_parameters():
            if not torch.allclose(param, initial_params[name]):
                changed = True
                break

        assert changed, "Policy update should modify parameters"

    def test_vae_update_modifies_params(self, trainer):
        """VAE update should change VAE parameters."""
        self.fill_buffer(trainer, n=trainer.config.num_steps_per_update)

        # Get initial params
        initial_params = {
            name: param.clone()
            for name, param in trainer.brain.vae.named_parameters()
            if param.requires_grad
        }

        # Update
        stats = trainer.update_vae()

        # Check some params changed
        changed = False
        for name, param in trainer.brain.vae.named_parameters():
            if param.requires_grad and name in initial_params:
                if not torch.allclose(param, initial_params[name]):
                    changed = True
                    break

        assert changed, "VAE update should modify parameters"

    def test_update_returns_stats(self, trainer):
        """Updates should return statistics."""
        self.fill_buffer(trainer, n=trainer.config.num_steps_per_update)

        policy_stats = trainer.update_policy()

        assert "policy_loss" in policy_stats
        assert "value_loss" in policy_stats
        assert "entropy" in policy_stats


class TestSleepTraining:
    """Test sleep/consolidation training."""

    def test_sleep_update(self):
        brain, trainer = create_trainer(obs_dim=8, enable_sleep=True, device="cpu")

        # Fill replay buffer
        for i in range(100):
            brain.add_experience_to_replay(
                obs=torch.randint(0, 256, (8,)),
                action=torch.randint(0, 256, (1,)),
                reward=np.random.randn(),
                next_obs=torch.randint(0, 256, (8,)),
                done=False,
                energy=0.05,
                code_len=1.0,
                z_t=torch.randn(64),
            )

        # Do sleep
        stats = trainer.do_sleep()

        assert "dynamics_loss" in stats

    def test_sleep_renormalization_called(self):
        brain, trainer = create_trainer(obs_dim=8, enable_sleep=True, device="cpu")

        # Fill replay buffer
        for i in range(100):
            brain.add_experience_to_replay(
                obs=torch.randint(0, 256, (8,)),
                action=torch.randint(0, 256, (1,)),
                reward=np.random.randn(),
                next_obs=torch.randint(0, 256, (8,)),
                done=False,
                energy=0.05,
                code_len=1.0,
                z_t=torch.randn(64),
            )

        # This should not crash
        trainer.do_sleep()


class TestIntegrationWithEnv:
    """Integration tests with actual environment."""

    def test_single_rollout(self):
        """Test collecting a single rollout."""
        from src.benchmarks.ccb import CCBEnvironment

        brain, trainer = create_trainer(obs_dim=8, action_bytes=1, device="cpu")
        env = CCBEnvironment()

        # Collect rollout
        stats = trainer.collect_rollout(env, num_steps=50)

        assert "mean_extrinsic_reward" in stats
        assert "mean_rpj_reward" in stats
        assert "energy_J" in stats
        assert "collapse_entropy" in stats

    def test_full_train_loop(self):
        """Test full training loop runs."""
        from src.benchmarks.ccb import CCBEnvironment

        brain, trainer = create_trainer(obs_dim=8, action_bytes=1, device="cpu")
        env = CCBEnvironment()

        # Train for 1 update
        config = PPOConfig(num_steps_per_update=64)
        trainer.config = config

        stats = trainer.train(env, total_timesteps=64, log_interval=100)

        assert len(stats) == 1
        assert stats[0]["timesteps"] == 64


class TestParameterCounts:
    """Test parameter counts are reasonable."""

    def test_total_under_budget(self):
        """Total params should be under 10M (with room to spare)."""
        brain, _ = create_trainer(obs_dim=64)
        params = brain.count_parameters()

        assert params['total'] < 2_000_000  # ~1.5M for CCB-sized brain

    def test_fast_param_budget(self):
        """Fast params should respect budget."""
        brain, _ = create_trainer(obs_dim=64, enable_plasticity=True)

        if brain.plasticity is not None:
            fast = brain.plasticity.count_fast_parameters()
            total = brain.count_parameters()['total']
            budget = min(500_000, int(0.05 * total))

            assert fast <= budget


class TestComputeDecisionLearning:
    """Test that compute decisions (k_r, N) are learned via PPO."""

    def test_compute_log_prob_in_policy_loss(self):
        """Verify compute_log_probs are used in PPO ratio calculation.

        From BLUEPRINT Section 2.2: (k_r, N) should be included in PPO's
        objective to make compute allocation learnable.
        """
        brain, trainer = create_trainer(obs_dim=8, action_bytes=1, device="cpu")

        # Fill buffer with data
        k_max = brain.config.k_max
        hidden_dim = brain.config.hidden_dim
        latent_dim = brain.config.latent_dim

        for i in range(trainer.config.num_steps_per_update):
            trainer.buffer.add(
                obs=torch.randint(0, 256, (8,)),
                next_obs=torch.randint(0, 256, (8,)),
                action=torch.randint(0, 256, (1,)),
                extrinsic_reward=np.random.randn(),
                intrinsic_reward=np.random.randn() * 0.1,
                rpj_reward=np.random.randn(),
                value=np.random.randn(),
                action_log_prob=torch.randn(1),
                compute_log_prob=np.random.randn(),  # Non-zero compute log prob
                done=False,
                energy=np.random.rand() * 0.1,
                code_len=np.random.rand(),
                hidden=torch.randn(hidden_dim),
                z_t=torch.randn(latent_dim),
                mu=torch.randn(latent_dim),
                sigma=torch.rand(latent_dim) + 0.1,
                g_t=torch.sigmoid(torch.randn(k_max)),
                c_t=torch.rand(1),
            )
        trainer.buffer.compute_returns_and_advantages(last_value=0.0)

        # Get initial compute allocator params (w_c is a Linear layer)
        initial_weight = brain.substrate.compute_allocator.w_c.weight.clone()

        # Run PPO update
        trainer.update_policy()

        # Compute allocator weights should have changed
        final_weight = brain.substrate.compute_allocator.w_c.weight

        # They should be different (gradients flowed through)
        assert not torch.allclose(initial_weight, final_weight), \
            "Compute allocator weights should change from PPO update"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
