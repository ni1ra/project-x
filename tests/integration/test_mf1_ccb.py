"""
Integration test: MF-1 Baseline on CCB Environment.

JARVIS Validation Criteria:
- Train MF-1 on CCB for 2000 steps
- Ensure manifest.json energy caps trigger a kill-switch if exceeded
- Verify the pipeline works end-to-end
"""

import pytest
import torch
import numpy as np

from src.core.mf1_baseline import MF1Agent, MF1Config, MF1Trainer, RolloutBuffer
from src.benchmarks.ccb import CCBEnvironment, SCMParams, create_ccb_linear
from src.energy.proxy import EnergyConfig, EnergyBudgetExceeded


class TestMF1AgentBasic:
    """Test MF1Agent basic functionality."""

    def test_initialization(self):
        """Test agent initializes correctly."""
        agent = MF1Agent(obs_bytes=8, action_bytes=1)

        assert agent.obs_bytes == 8
        assert agent.action_bytes == 1

    def test_forward_pass(self):
        """Test forward pass produces valid outputs."""
        agent = MF1Agent(obs_bytes=8, action_bytes=1)

        # Create dummy observation
        obs = torch.randint(0, 256, (4, 8), dtype=torch.float32)

        action, log_prob, value, hidden = agent(obs)

        # Check shapes
        assert action.shape == (4, 1)
        assert log_prob.shape == (4, 1)
        assert value.shape == (4,)
        assert hidden.shape == (1, 4, agent.config.hidden_dim)

        # Actions should be valid bytes
        assert action.min() >= 0
        assert action.max() <= 255

        # Log probs should be negative
        assert (log_prob <= 0).all()

    def test_evaluate_actions(self):
        """Test action evaluation for PPO."""
        agent = MF1Agent(obs_bytes=8, action_bytes=1)

        obs = torch.randint(0, 256, (4, 8), dtype=torch.float32)
        actions = torch.randint(0, 256, (4, 1))

        log_probs, values, entropy = agent.evaluate_actions(obs, actions)

        assert log_probs.shape == (4, 1)
        assert values.shape == (4,)
        assert entropy.shape == (4,)
        assert (entropy >= 0).all()


class TestRolloutBuffer:
    """Test rollout buffer."""

    def test_add_and_retrieve(self):
        """Test adding transitions and computing returns."""
        buffer = RolloutBuffer(buffer_size=10, obs_dim=8, action_dim=1)

        # Add some transitions
        for i in range(10):
            buffer.add(
                obs=torch.randn(8),
                action=torch.randint(0, 256, (1,)),
                reward=float(i),
                value=float(i) * 0.5,
                log_prob=torch.randn(1),
                done=i == 9,
            )

        assert buffer.full or buffer.pos == 0

        # Compute returns
        buffer.compute_returns_and_advantages(last_value=0.0)

        # Advantages should be computed
        assert not torch.isnan(buffer.advantages).any()
        assert not torch.isnan(buffer.returns).any()


class TestMF1WithCCB:
    """Integration test: MF-1 on CCB environment."""

    def test_single_episode(self):
        """Test running a single episode of CCB with MF-1."""
        env = create_ccb_linear(seed=42, num_interventions=5)
        agent = MF1Agent(
            obs_bytes=env.observation_space_bytes,
            action_bytes=env.action_space_bytes,
        )

        obs, info = env.reset()
        obs = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
        hidden = None

        total_reward = 0
        done = False

        while not done:
            with torch.no_grad():
                action, log_prob, value, hidden = agent(obs)

            action_np = action.squeeze(0).cpu().numpy()
            next_obs, reward, terminated, truncated, info = env.step(action_np)
            done = terminated or truncated

            total_reward += reward
            obs = torch.tensor(next_obs, dtype=torch.float32).unsqueeze(0)

        # Episode should complete
        assert done

        # DoErr should be computable
        do_err = env.compute_do_error()
        assert do_err >= 0

    def test_short_training_run(self):
        """Test a short training run (256 steps)."""
        env = create_ccb_linear(seed=42, num_interventions=5)

        config = MF1Config(
            hidden_dim=64,  # Small for fast testing
            num_steps_per_update=64,
            num_epochs=2,
            minibatch_size=16,
        )

        agent = MF1Agent(
            obs_bytes=env.observation_space_bytes,
            action_bytes=env.action_space_bytes,
            config=config,
        )

        # Use relaxed energy config for testing
        energy_config = EnergyConfig(
            B_max_ep=1000.0,  # Very relaxed for testing
            B_max_day=100000.0,
        )

        trainer = MF1Trainer(agent, config=config, energy_config=energy_config)

        # Train for 256 steps (4 updates)
        stats = trainer.train(env, total_timesteps=256, log_interval=100)

        # Should have 4 updates
        assert len(stats) == 4

        # Stats should be reasonable
        for s in stats:
            assert "mean_reward" in s
            assert "policy_loss" in s
            assert "energy_J" in s
            assert s["energy_J"] >= 0

    @pytest.mark.slow
    def test_2000_step_training(self):
        """
        JARVIS Validation: Train MF-1 on CCB for 2000 steps.
        """
        env = create_ccb_linear(seed=42, num_interventions=5)

        config = MF1Config(
            hidden_dim=64,
            num_steps_per_update=128,
            num_epochs=2,
            minibatch_size=32,
        )

        agent = MF1Agent(
            obs_bytes=env.observation_space_bytes,
            action_bytes=env.action_space_bytes,
            config=config,
        )

        # Use manifest energy config
        energy_config = EnergyConfig()

        trainer = MF1Trainer(agent, config=config, energy_config=energy_config)

        # Train for 2048 steps (16 updates with 128 steps each)
        stats = trainer.train(env, total_timesteps=2048, log_interval=4)

        # Should complete without energy violation
        assert len(stats) == 16

        # Energy should be tracked
        final_energy = stats[-1]["energy_J"]
        assert final_energy > 0
        print(f"Total energy used: {final_energy:.4f} J")


class TestEnergyKillSwitch:
    """Test energy budget enforcement."""

    def test_kill_switch_triggers(self):
        """Test that exceeding energy budget raises exception."""
        env = create_ccb_linear(seed=42, num_interventions=5)

        config = MF1Config(
            hidden_dim=256,  # Larger to use more energy
            num_steps_per_update=32,
        )

        agent = MF1Agent(
            obs_bytes=env.observation_space_bytes,
            action_bytes=env.action_space_bytes,
            config=config,
        )

        # Impossibly small energy budget
        energy_config = EnergyConfig(
            B_max_ep=1e-10,  # Tiny budget - should trigger immediately
        )

        trainer = MF1Trainer(agent, config=config, energy_config=energy_config)

        # Should raise EnergyBudgetExceeded
        with pytest.raises(EnergyBudgetExceeded):
            trainer.collect_rollout(env, num_steps=32)


class TestPipelineIntegration:
    """Full pipeline integration tests."""

    def test_byte_interface_preserved(self):
        """Test that byte interface is used correctly throughout."""
        env = create_ccb_linear(seed=42, num_interventions=3)
        agent = MF1Agent(obs_bytes=env.observation_space_bytes, action_bytes=1)

        obs, _ = env.reset()

        # Observation should be bytes
        assert obs.dtype == np.uint8

        # Agent should handle float conversion internally
        obs_tensor = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
        action, _, _, _ = agent(obs_tensor)

        # Action should be valid byte indices
        action_np = action.squeeze(0).cpu().numpy()
        assert action_np.dtype in [np.int64, np.int32]
        assert 0 <= action_np[0] <= 255

        # Environment should accept byte action
        next_obs, reward, _, _, _ = env.step(action_np)
        assert next_obs.dtype == np.uint8
