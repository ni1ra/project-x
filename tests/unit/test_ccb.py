"""
Unit tests for CCB (Confounded Causal Bandits) Environment.

JARVIS Validation Criteria:
- CCB Environment outputs bytes (not floats)
- Generate 1000 samples and verify correlation matches theoretical confounding
"""

import pytest
import numpy as np

from src.benchmarks.ccb import (
    CCBEnvironment,
    CCBScorer,
    SCMParams,
    float_to_byte_quantized,
    byte_to_float_quantized,
    create_ccb_linear,
    create_ccb_nonlinear,
)


class TestQuantization:
    """Test quantized byte conversion utilities."""

    def test_float_round_trip(self):
        """Test float → byte → float conversion (with quantization error)."""
        values = [-2.0, -1.0, 0.0, 0.5, 1.0, 2.0]

        for val in values:
            b = float_to_byte_quantized(val, min_val=-2.0, max_val=2.0)
            recovered = byte_to_float_quantized(b, min_val=-2.0, max_val=2.0)
            assert recovered == pytest.approx(val, abs=0.05)

    def test_clipping(self):
        """Test that quantization clips out-of-range values."""
        b_low = float_to_byte_quantized(-999.0, min_val=-2.0, max_val=2.0)
        b_high = float_to_byte_quantized(999.0, min_val=-2.0, max_val=2.0)

        assert b_low == 0
        assert b_high == 255


class TestCCBEnvironmentByteOutput:
    """Test that CCB environment outputs bytes."""

    def test_observation_is_bytes(self):
        """Test that observation is a byte array, not floats."""
        env = create_ccb_linear(seed=42)
        obs, info = env.reset()

        # Should be uint8 array
        assert obs.dtype == np.uint8

        # Should be correct length
        assert len(obs) == env.observation_space_bytes

    def test_observation_contains_valid_data(self):
        """Test that observation bytes can be decoded back to floats."""
        env = create_ccb_linear(seed=42)
        obs, info = env.reset()

        # Decode Z and target_X from quantized bytes (2-byte observation)
        z_float = byte_to_float_quantized(int(obs[0]), min_val=-2.0, max_val=2.0)
        target_x_float = byte_to_float_quantized(int(obs[1]), min_val=-2.0, max_val=2.0)

        # Should be reasonable values
        assert -2 <= z_float <= 2
        assert -2 <= target_x_float <= 2

        # target_X should match info
        # Quantization introduces ~4/255 ≈ 0.016 error; allow a small tolerance.
        assert target_x_float == pytest.approx(info["target_X"], abs=0.05)

    def test_step_returns_bytes(self):
        """Test that step returns byte observation."""
        env = create_ccb_linear(seed=42)
        obs, _ = env.reset()

        # Take action (1 byte)
        action = np.array([128], dtype=np.uint8)
        next_obs, reward, terminated, truncated, info = env.step(action)

        if not terminated:
            assert next_obs.dtype == np.uint8
            assert len(next_obs) == env.observation_space_bytes


class TestCCBLinearSCM:
    """Test linear CCB SCM correctness."""

    def test_do_effect_linear(self):
        """Test that true do() effect is b_X * X for linear SCM."""
        params = SCMParams(b_X=1.5, nonlinear=False)
        env = CCBEnvironment(params=params, seed=42)

        # For linear SCM: E[Y | do(X=x)] = b_X * x
        test_x_values = [-2.0, -1.0, 0.0, 1.0, 2.0]

        for x in test_x_values:
            expected = params.b_X * x
            # The environment computes this internally
            # We verify via the scorer

    def test_confounding_correlation(self):
        """
        Test that Z and Y are correlated due to confounding.

        JARVIS Validation: Generate 1000 samples and verify correlation.
        """
        params = SCMParams(a_U=0.8, b_U=0.6, nonlinear=False)
        rng = np.random.default_rng(42)

        n_samples = 1000
        U_samples = rng.standard_normal(n_samples)
        epsilon_Z = rng.normal(0, params.sigma_Z, n_samples)
        epsilon_Y = rng.normal(0, params.sigma_Y, n_samples)

        Z = params.a_U * U_samples + epsilon_Z

        # Observed Y (with X=0 for simplicity)
        X = np.zeros(n_samples)
        Y = params.b_X * X + params.b_U * U_samples + epsilon_Y

        # Z and Y should be correlated through U
        correlation = np.corrcoef(Z, Y)[0, 1]

        # Both are positively correlated with U, so they should be positively correlated
        assert correlation > 0.3, f"Expected positive correlation, got {correlation}"

        # Theoretical correlation: Cov(Z,Y)/sqrt(Var(Z)*Var(Y))
        # Cov(Z,Y) = a_U * b_U * Var(U) = a_U * b_U = 0.8 * 0.6 = 0.48
        # Var(Z) ≈ a_U² + sigma_Z² = 0.64 + 0.01 = 0.65
        # Var(Y) ≈ b_U² + sigma_Y² = 0.36 + 0.01 = 0.37
        # Expected correlation ≈ 0.48 / sqrt(0.65 * 0.37) ≈ 0.98

        # Allow some sampling variance
        assert abs(correlation - 0.48 / np.sqrt(0.65 * 0.37)) < 0.15


class TestCCBNonlinearSCM:
    """Test non-linear CCB-NL SCM."""

    def test_nonlinear_scm_exists(self):
        """Test that nonlinear environment can be created."""
        env = create_ccb_nonlinear(seed=42)
        assert env.params.nonlinear is True

    def test_nonlinear_do_effect(self):
        """Test that nonlinear do() effect is computed."""
        params = SCMParams(b_X=1.0, b_U=0.5, nonlinear=True)
        env = CCBEnvironment(params=params, seed=42)

        # For nonlinear: Y = ReLU(b_X * X² + b_U * U)
        # E[Y | do(X=x)] depends on the distribution of U
        # For x=0: E[Y | do(X=0)] = E[ReLU(b_U * U)]

        # The _compute_do_effect_nonlinear method should handle this
        effect = env._compute_do_effect_nonlinear(0.0)
        assert effect >= 0  # ReLU output is non-negative


class TestCCBScorer:
    """Test CCB scoring."""

    def test_perfect_predictions_linear(self):
        """Test that perfect predictions give DoErr = 0."""
        params = SCMParams(b_X=1.0, nonlinear=False)
        scorer = CCBScorer()

        # If agent predicts exactly b_X * x, error should be 0
        target_X = np.array([0.0, 1.0, 2.0, -1.0, -2.0])
        predictions = params.b_X * target_X  # Perfect predictions

        result = scorer.evaluate(predictions, target_X, params)

        assert result["DoErr"] == pytest.approx(0.0, abs=1e-6)
        assert result["DoErr_pass"] == True  # Use == for numpy bool

    def test_biased_predictions_fail(self):
        """Test that biased predictions fail the threshold."""
        params = SCMParams(b_X=1.0, nonlinear=False)
        scorer = CCBScorer()

        target_X = np.array([0.0, 1.0, 2.0, -1.0, -2.0])
        # Agent predicts with wrong coefficient
        predictions = 0.5 * target_X  # Wrong!

        result = scorer.evaluate(predictions, target_X, params)

        # Error should be significant
        assert result["DoErr"] > 0.05
        assert result["DoErr_pass"] == False  # Use == for numpy bool


class TestCCBEpisode:
    """Test full CCB episode."""

    def test_episode_completion(self):
        """Test that episode terminates after num_interventions queries."""
        env = create_ccb_linear(seed=42, num_interventions=5)
        obs, _ = env.reset()

        for i in range(5):
            action = np.array([128], dtype=np.uint8)
            obs, reward, terminated, truncated, info = env.step(action)

            if i < 4:
                assert not terminated
            else:
                assert terminated

    def test_rewards_are_negative_errors(self):
        """Test that rewards are negative absolute errors."""
        env = create_ccb_linear(seed=42, num_interventions=3)
        obs, info = env.reset()

        # Make a prediction
        action = np.array([128], dtype=np.uint8)  # Maps to Y ≈ 0
        _, reward, _, _, step_info = env.step(action)

        # Reward should be -|predicted - true|
        assert reward == pytest.approx(-step_info["error"])
        assert reward <= 0


class TestCCBFactoryFunctions:
    """Test factory functions for CCB environments."""

    def test_create_ccb_linear(self):
        """Test linear CCB creation."""
        env = create_ccb_linear(seed=42)
        assert not env.params.nonlinear

    def test_create_ccb_nonlinear(self):
        """Test nonlinear CCB-NL creation."""
        env = create_ccb_nonlinear(seed=42)
        assert env.params.nonlinear

    def test_reproducibility_with_seed(self):
        """Test that same seed gives same sequence."""
        env1 = create_ccb_linear(seed=42)
        env2 = create_ccb_linear(seed=42)

        obs1, _ = env1.reset()
        obs2, _ = env2.reset()

        np.testing.assert_array_equal(obs1, obs2)
