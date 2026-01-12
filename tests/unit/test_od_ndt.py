"""
Tests for OD-NDT (One-Demonstration No-Data Transfer) harness.

These tests verify the OD-NDT protocol implementation per BLUEPRINT.md Section 4.3.
"""

import pytest
import torch
import torch.nn as nn
from typing import Tuple, Dict, Any, Optional

from src.benchmarks.od_ndt import (
    ODNDTConfig,
    ODNDTHarness,
    ODNDTResult,
    create_od_ndt_harness,
    MAX_DEMO_STEPS,
    B_SLEEP_1,
    NUM_TEST_TASKS,
    SR_NOVEL_THRESHOLD,
    TRANSFER_THRESHOLD,
)


# =============================================================================
# Mock Environment
# =============================================================================

class MockTaskEnvironment:
    """Mock task environment for testing OD-NDT harness."""

    def __init__(self, success_rate: float = 0.7, obs_dim: int = 8):
        self.success_rate = success_rate
        self.obs_dim = obs_dim
        self._current_task = 0
        self._step_count = 0
        self._success = False
        self._max_steps = 50

    def reset(self, task_id: Optional[int] = None) -> Tuple[torch.Tensor, Dict[str, Any]]:
        self._current_task = task_id if task_id is not None else 0
        self._step_count = 0
        # Deterministic success based on task_id
        self._success = (task_id or 0) % 10 < int(self.success_rate * 10)
        obs = torch.randn(self.obs_dim)
        return obs, {'task_id': self._current_task}

    def step(self, action: torch.Tensor) -> Tuple[torch.Tensor, float, bool, bool, Dict[str, Any]]:
        self._step_count += 1
        obs = torch.randn(self.obs_dim)
        reward = 1.0 if self._success else -1.0
        terminated = self._step_count >= self._max_steps
        truncated = False
        return obs, reward, terminated, truncated, {}

    def get_oracle_action(self, obs: torch.Tensor) -> torch.Tensor:
        """Oracle action (mock)."""
        return torch.tensor([128])  # Middle value

    def get_task_success(self) -> bool:
        """Success determined by task_id."""
        return self._success


# =============================================================================
# Mock Brain
# =============================================================================

class MockSubstrate(nn.Module):
    """Mock substrate for testing."""

    def __init__(self, hidden_dim: int = 512):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.fc = nn.Linear(hidden_dim, hidden_dim)


class MockAdapter(nn.Module):
    """Mock adapter for fast weights."""

    def __init__(self, dim: int = 512, rank: int = 16):
        super().__init__()
        self.A = nn.Parameter(torch.zeros(dim, rank))
        self.B = nn.Parameter(torch.zeros(rank, dim))

    def reset(self):
        self.A.zero_()
        self.B.zero_()


class MockPlasticity(nn.Module):
    """Mock plasticity module."""

    def __init__(self, dim: int = 512):
        super().__init__()
        self.recurrent_adapter = MockAdapter(dim)
        self.action_adapter = MockAdapter(dim)

    def reset_fast_weights(self):
        self.recurrent_adapter.reset()
        self.action_adapter.reset()


class MockSleep(nn.Module):
    """Mock sleep module."""

    def __init__(self):
        super().__init__()
        self.experiences = []

    def add_experience(self, **kwargs):
        self.experiences.append(kwargs)

    @property
    def replay_buffer(self):
        return self

    @property
    def size(self):
        return len(self.experiences)

    def sample(self, batch_size):
        # Return mock batch
        return {
            'obs': torch.randn(batch_size, 8),
            'action': torch.randint(0, 256, (batch_size,)),
            'z_t': torch.randn(batch_size, 64),
        }, list(range(batch_size)), torch.ones(batch_size)

    def synaptic_renormalization(self, plasticity):
        pass


class MockByteInterface:
    """Mock byte interface."""

    @staticmethod
    def encode_observation(obs):
        return (obs / 127.5) - 1.0


class MockVAE(nn.Module):
    """Mock VAE."""

    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(512, 64)

    def forward(self, h, phi_obs):
        from collections import namedtuple
        Output = namedtuple('Output', ['z_t', 'mu', 'sigma'])
        return Output(
            z_t=torch.randn(1, 64),
            mu=torch.zeros(1, 64),
            sigma=torch.ones(1, 64),
        )


class MockBrainOutput:
    """Mock brain output."""

    def __init__(self, action, h_next, g_t=None):
        self.action = action
        self.h_next = h_next
        self.g_t = g_t


class MockBrain(nn.Module):
    """Mock brain for testing OD-NDT."""

    def __init__(self, obs_dim: int = 8, hidden_dim: int = 512):
        super().__init__()
        self.substrate = MockSubstrate(hidden_dim)
        self.plasticity = MockPlasticity(hidden_dim)
        self.sleep = MockSleep()
        self.byte_interface = MockByteInterface()
        self.vae = MockVAE()

        self.fc = nn.Linear(obs_dim, 1)

    def forward(self, obs, h, training=False):
        action = torch.randint(0, 256, (1, 1))
        h_next = h.clone()
        return MockBrainOutput(action, h_next, torch.rand(1, 16))


# =============================================================================
# Tests: Constants
# =============================================================================

class TestConstants:
    """Test that constants match BLUEPRINT.md Section 4.3."""

    def test_max_demo_steps(self):
        assert MAX_DEMO_STEPS == 200, "Max demo steps should be 200"

    def test_sleep_budget(self):
        assert B_SLEEP_1 == 100.0, "Sleep budget should be 100J"

    def test_num_test_tasks(self):
        assert NUM_TEST_TASKS == 100, "Should test on 100 held-out tasks"

    def test_sr_novel_threshold(self):
        assert SR_NOVEL_THRESHOLD == 0.60, "SR_novel threshold should be 0.60"

    def test_transfer_threshold(self):
        assert TRANSFER_THRESHOLD == 0.80, "Transfer T threshold should be 0.80"


# =============================================================================
# Tests: Config
# =============================================================================

class TestODNDTConfig:
    """Test OD-NDT configuration."""

    def test_default_values(self):
        config = ODNDTConfig()
        assert config.max_demo_steps == 200
        assert config.sleep_budget == 100.0
        assert config.num_test_tasks == 100
        assert config.sr_novel_threshold == 0.60
        assert config.transfer_threshold == 0.80

    def test_custom_values(self):
        config = ODNDTConfig(
            max_demo_steps=100,
            sleep_budget=50.0,
            num_test_tasks=50,
        )
        assert config.max_demo_steps == 100
        assert config.sleep_budget == 50.0
        assert config.num_test_tasks == 50


# =============================================================================
# Tests: Harness Creation
# =============================================================================

class TestHarnessCreation:
    """Test OD-NDT harness creation."""

    def test_create_harness(self):
        brain = MockBrain()
        harness = ODNDTHarness(brain)
        assert harness.brain is brain
        assert harness.config is not None

    def test_factory_function(self):
        brain = MockBrain()
        harness = create_od_ndt_harness(brain, device="cpu")
        assert harness.brain is brain
        assert harness.config.device == "cpu"


# =============================================================================
# Tests: Demo Collection
# =============================================================================

class TestDemoCollection:
    """Test expert demonstration collection."""

    def test_collect_demo_returns_data(self):
        brain = MockBrain()
        env = MockTaskEnvironment(success_rate=1.0)
        harness = ODNDTHarness(brain)

        demo_data, success = harness.collect_demo(env, demo_task_id=0)

        assert len(demo_data) > 0
        assert 'obs' in demo_data[0]
        assert 'action' in demo_data[0]
        assert 'hidden' in demo_data[0]

    def test_demo_length_bounded(self):
        brain = MockBrain()
        env = MockTaskEnvironment(success_rate=1.0)
        env._max_steps = 300  # Longer than max demo
        harness = ODNDTHarness(brain)

        demo_data, _ = harness.collect_demo(env, demo_task_id=0)

        assert len(demo_data) <= MAX_DEMO_STEPS


# =============================================================================
# Tests: Sleep Consolidation
# =============================================================================

class TestSleepConsolidation:
    """Test sleep consolidation phase."""

    def test_sleep_returns_energy(self):
        brain = MockBrain()
        harness = ODNDTHarness(brain)

        demo_data = [
            {'obs': torch.randn(8), 'action': torch.tensor([128]), 'hidden': torch.randn(1, 512)}
            for _ in range(10)
        ]

        energy = harness.sleep_consolidation(demo_data)

        assert isinstance(energy, float)
        assert energy >= 0

    def test_sleep_within_budget(self):
        brain = MockBrain()
        harness = ODNDTHarness(brain)

        demo_data = [
            {'obs': torch.randn(8), 'action': torch.tensor([128]), 'hidden': torch.randn(1, 512)}
            for _ in range(50)
        ]

        energy = harness.sleep_consolidation(demo_data)

        assert energy <= harness.config.sleep_budget


# =============================================================================
# Tests: Fast Weight Management
# =============================================================================

class TestFastWeightManagement:
    """Test fast weight saving/restoring between test episodes."""

    def test_save_fast_weights(self):
        brain = MockBrain()
        harness = ODNDTHarness(brain)

        # Set some non-zero fast weights
        with torch.no_grad():
            brain.plasticity.recurrent_adapter.A.fill_(1.0)

        harness._save_fast_weights()

        assert harness._post_sleep_fast_weights is not None
        assert torch.allclose(
            harness._post_sleep_fast_weights['recurrent_A'],
            torch.ones_like(harness._post_sleep_fast_weights['recurrent_A'])
        )

    def test_restore_fast_weights(self):
        brain = MockBrain()
        harness = ODNDTHarness(brain)

        # Save initial state
        with torch.no_grad():
            brain.plasticity.recurrent_adapter.A.fill_(1.0)
        harness._save_fast_weights()

        # Modify weights
        with torch.no_grad():
            brain.plasticity.recurrent_adapter.A.fill_(2.0)

        # Restore
        harness._restore_fast_weights()

        assert torch.allclose(
            brain.plasticity.recurrent_adapter.A,
            torch.ones_like(brain.plasticity.recurrent_adapter.A)
        )


# =============================================================================
# Tests: Test Evaluation
# =============================================================================

class TestTaskEvaluation:
    """Test evaluation on test tasks."""

    def test_evaluate_returns_bool(self):
        brain = MockBrain()
        env = MockTaskEnvironment(success_rate=1.0)
        harness = ODNDTHarness(brain)

        # Need to save fast weights first
        harness._save_fast_weights()

        success = harness.evaluate_test_task(env, task_id=0)

        assert isinstance(success, bool)

    def test_fast_weights_reset_between_episodes(self):
        brain = MockBrain()
        env = MockTaskEnvironment(success_rate=1.0)
        harness = ODNDTHarness(brain)

        # Save initial state
        with torch.no_grad():
            brain.plasticity.recurrent_adapter.A.fill_(1.0)
        harness._save_fast_weights()

        # Modify weights
        with torch.no_grad():
            brain.plasticity.recurrent_adapter.A.fill_(2.0)

        # Evaluate task (should restore weights)
        harness.evaluate_test_task(env, task_id=0)

        # Weights should be back to saved state
        assert torch.allclose(
            brain.plasticity.recurrent_adapter.A,
            torch.ones_like(brain.plasticity.recurrent_adapter.A)
        )


# =============================================================================
# Tests: Full Evaluation
# =============================================================================

class TestFullEvaluation:
    """Test complete OD-NDT evaluation."""

    def test_run_evaluation_returns_result(self):
        brain = MockBrain()
        env = MockTaskEnvironment(success_rate=0.7)

        config = ODNDTConfig(num_test_tasks=10)  # Small for testing
        harness = ODNDTHarness(brain, config)

        test_task_ids = list(range(10))
        result = harness.run_evaluation(
            env,
            demo_task_id=0,
            test_task_ids=test_task_ids,
            sr_train=1.0,
        )

        assert isinstance(result, ODNDTResult)
        assert hasattr(result, 'sr_novel')
        assert hasattr(result, 'transfer_ratio')
        assert hasattr(result, 'passed')

    def test_high_success_rate_passes(self):
        brain = MockBrain()
        env = MockTaskEnvironment(success_rate=0.8)

        config = ODNDTConfig(num_test_tasks=10)
        harness = ODNDTHarness(brain, config)

        test_task_ids = list(range(10))
        result = harness.run_evaluation(
            env,
            demo_task_id=0,
            test_task_ids=test_task_ids,
            sr_train=1.0,
        )

        # With 80% success rate, SR_novel should be ~0.8
        # Transfer T = 0.8/1.0 = 0.8 which meets threshold
        assert result.sr_novel >= 0.5  # Deterministic from mock

    def test_low_success_rate_fails(self):
        brain = MockBrain()
        env = MockTaskEnvironment(success_rate=0.3)

        config = ODNDTConfig(num_test_tasks=10)
        harness = ODNDTHarness(brain, config)

        test_task_ids = list(range(10))
        result = harness.run_evaluation(
            env,
            demo_task_id=0,
            test_task_ids=test_task_ids,
            sr_train=1.0,
        )

        # With 30% success rate, SR_novel should be ~0.3 < 0.60 threshold
        assert result.sr_novel < 0.60 or not result.passed


# =============================================================================
# Tests: Result Object
# =============================================================================

class TestODNDTResult:
    """Test OD-NDT result object."""

    def test_result_repr(self):
        result = ODNDTResult(
            sr_train=1.0,
            sr_novel=0.7,
            transfer_ratio=0.7,
            passed=True,
            demo_energy=1.0,
            sleep_energy=50.0,
            test_successes=[True, False, True],
            fail_reasons=[],
        )

        repr_str = repr(result)
        assert "PASS" in repr_str
        assert "0.7" in repr_str

    def test_result_fail_reasons(self):
        result = ODNDTResult(
            sr_train=1.0,
            sr_novel=0.5,
            transfer_ratio=0.5,
            passed=False,
            demo_energy=1.0,
            sleep_energy=50.0,
            test_successes=[],
            fail_reasons=["SR_novel 0.500 < 0.60"],
        )

        assert not result.passed
        assert len(result.fail_reasons) > 0
        assert "SR_novel" in result.fail_reasons[0]
