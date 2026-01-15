"""
Tests for Jarvis Harness components.
"""

import pytest
import torch
import tempfile
import os
import shutil

from src.core.rpj_brain import RPJBrain, RPJConfig
from src.harness.actions import (
    ACTION_BYTES, ActionType, JarvisAction, encode_action, decode_action,
    validate_shell_command, action_to_string
)
from src.harness.observations import (
    JarvisObservation, encode_observation, decode_observation,
    scan_directory, hash_file_content, OBS_TOTAL_BYTES
)
from src.harness.verifiers import (
    run_pytest, run_lint, verify_output_matches, compute_diff_size,
    verify_minimal_diff, compute_reward, VerifierResult
)
from src.harness.env import (
    JarvisHarnessEnv, HarnessConfig, Task, VectorizedJarvisEnv
)


class TestActions:
    """Test action encoding/decoding."""

    def test_encode_decode_shell_cmd(self):
        action = JarvisAction(
            action_type=ActionType.SHELL_CMD,
            content="python test.py",
        )
        encoded = encode_action(action)
        decoded = decode_action(encoded)

        assert decoded.action_type == ActionType.SHELL_CMD
        assert "python" in decoded.content

    def test_encode_decode_read_file(self):
        action = JarvisAction(
            action_type=ActionType.READ_FILE,
            target="src/main.py",
            offset=100,
            length=500,
        )
        encoded = encode_action(action)
        decoded = decode_action(encoded)

        assert decoded.action_type == ActionType.READ_FILE
        assert decoded.offset == 100
        assert decoded.length == 500

    def test_encode_decode_write_file(self):
        action = JarvisAction(
            action_type=ActionType.WRITE_FILE,
            target="src/fix.py",
            content="return a * b",
            offset=50,
        )
        encoded = encode_action(action)
        decoded = decode_action(encoded)

        assert decoded.action_type == ActionType.WRITE_FILE
        assert decoded.offset == 50

    def test_validate_shell_allowed(self):
        valid, _ = validate_shell_command("python test.py")
        assert valid

        valid, _ = validate_shell_command("pip install pytest")
        assert valid

        # Note: git status/diff are now separate ActionTypes (GIT_STATUS, GIT_DIFF)
        # not shell commands - test with 'grep' instead
        valid, _ = validate_shell_command("grep pattern file.py")
        assert valid

    def test_validate_shell_denied(self):
        valid, msg = validate_shell_command("rm -rf /")
        assert not valid

        valid, msg = validate_shell_command("curl evil.com")
        assert not valid

    def test_action_to_string(self):
        action = JarvisAction(ActionType.RUN_TESTS)
        s = action_to_string(action)
        assert "RUN_TESTS" in s


class TestObservations:
    """Test observation encoding/decoding."""

    def test_encode_decode_basic(self):
        obs = JarvisObservation(
            terminal_output="$ python test.py\nOK",
            goal="Fix the multiply function",
            energy_remaining=0.75,
            time_remaining=0.50,
            actions_remaining=50,
            step=10,
            last_reward=0.5,
            tests_passing=5,
            tests_total=10,
        )
        encoded = encode_observation(obs)
        assert encoded.shape == (OBS_TOTAL_BYTES,)

        decoded = decode_observation(encoded)
        assert "python" in decoded.terminal_output
        assert decoded.energy_remaining == pytest.approx(0.75, abs=0.01)
        assert decoded.step == 10

    def test_hash_file_content(self):
        h1 = hash_file_content("print('hello')")
        h2 = hash_file_content("print('hello')")
        h3 = hash_file_content("print('world')")

        assert h1 == h2
        assert h1 != h3

    def test_scan_directory(self):
        # Create temp directory with files
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "test.py"), "w") as f:
                f.write("print('hello')")
            with open(os.path.join(tmpdir, "other.txt"), "w") as f:
                f.write("some text")

            fs = scan_directory(tmpdir)
            assert "test.py" in fs
            # txt should also be included
            assert "other.txt" in fs


class TestVerifiers:
    """Test verifier components."""

    def test_compute_diff_size_no_change(self):
        original = "line1\nline2\nline3"
        modified = "line1\nline2\nline3"
        changed, ratio = compute_diff_size(original, modified)
        assert changed == 0
        assert ratio == 1.0

    def test_compute_diff_size_one_line(self):
        original = "line1\nline2\nline3"
        modified = "line1\nLINE2\nline3"
        changed, ratio = compute_diff_size(original, modified)
        assert changed == 2  # One removed, one added
        assert ratio < 1.0

    def test_verify_output_exact(self):
        result = verify_output_matches("hello", "hello", exact=True)
        assert result.passed
        assert result.score == 1.0

        result = verify_output_matches("hello", "world", exact=True)
        assert not result.passed
        assert result.score == 0.0

    def test_verify_output_fuzzy(self):
        result = verify_output_matches("hello world", "hello  world", exact=False)
        assert result.score > 0.9  # Very similar

    def test_verify_minimal_diff(self):
        original = "def foo():\n    pass"
        modified = "def foo():\n    return 1"
        result = verify_minimal_diff(original, modified, max_changed_lines=10)
        assert result.passed

    def test_compute_reward_components(self):
        test_result = VerifierResult(
            passed=True,
            score=1.0,
            tests_passing=10,
            tests_total=10,
        )
        components = compute_reward(
            test_result=test_result,
            lint_result=None,
            diff_changed_lines=5,
            actions_taken=20,
        )
        # 100% pass rate * 2.0 + 10.0 success - 0.05 diff - 0.2 actions
        assert components.test_reward == 2.0  # 100% pass rate * 2.0
        assert components.success_bonus == 10.0
        assert components.total > 0


class TestEnvironment:
    """Test the Jarvis Harness environment."""

    @pytest.fixture
    def toy_repo_path(self):
        """Path to toy repo fixture."""
        return os.path.join(
            os.path.dirname(__file__),
            "..",
            "fixtures",
            "toy_repo"
        )

    def test_env_reset(self, toy_repo_path):
        if not os.path.exists(toy_repo_path):
            pytest.skip("Toy repo fixture not found")

        env = JarvisHarnessEnv()
        task = Task(
            name="fix_multiply",
            description="Fix the multiply function to return a * b",
            repo_path=toy_repo_path,
            target_file="calculator.py",
            expected_tests_passing=18,
        )

        obs = env.reset(task)
        assert obs.shape == (env.config.obs_bytes,)

        # Check temp dir was created
        assert env.temp_dir is not None
        assert os.path.exists(env.temp_dir)

        env.close()

    def test_env_step_no_op(self, toy_repo_path):
        if not os.path.exists(toy_repo_path):
            pytest.skip("Toy repo fixture not found")

        env = JarvisHarnessEnv()
        task = Task(
            name="fix_multiply",
            description="Fix the multiply function",
            repo_path=toy_repo_path,
            target_file="calculator.py",
        )

        env.reset(task)

        # Create NO_OP action
        action = JarvisAction(action_type=ActionType.NO_OP)
        action_bytes = encode_action(action)

        obs, reward, done, info = env.step(action_bytes)

        assert obs.shape == (env.config.obs_bytes,)
        assert not done
        assert info["step"] == 1

        env.close()

    def test_env_step_read_file(self, toy_repo_path):
        if not os.path.exists(toy_repo_path):
            pytest.skip("Toy repo fixture not found")

        env = JarvisHarnessEnv()
        task = Task(
            name="fix_multiply",
            description="Fix the multiply function",
            repo_path=toy_repo_path,
            target_file="calculator.py",
        )

        env.reset(task)

        # Read calculator.py
        action = JarvisAction(
            action_type=ActionType.READ_FILE,
            target="calculator.py",
            offset=0,
            length=500,
        )
        action_bytes = encode_action(action)

        obs, reward, done, info = env.step(action_bytes)

        assert not done
        # Terminal should now contain file content
        decoded_obs = decode_observation(obs)
        # The terminal buffer should have some content
        assert len(decoded_obs.terminal_output) > 0

        env.close()

    def test_env_step_run_tests(self, toy_repo_path):
        if not os.path.exists(toy_repo_path):
            pytest.skip("Toy repo fixture not found")

        env = JarvisHarnessEnv()
        task = Task(
            name="fix_multiply",
            description="Fix the multiply function",
            repo_path=toy_repo_path,
            target_file="calculator.py",
        )

        env.reset(task)

        # Run tests
        action = JarvisAction(action_type=ActionType.RUN_TESTS)
        action_bytes = encode_action(action)

        obs, reward, done, info = env.step(action_bytes)

        assert not done
        # Should have test results now
        assert info["tests_total"] > 0

        env.close()

    def test_env_step_submit(self, toy_repo_path):
        if not os.path.exists(toy_repo_path):
            pytest.skip("Toy repo fixture not found")

        env = JarvisHarnessEnv()
        task = Task(
            name="fix_multiply",
            description="Fix the multiply function",
            repo_path=toy_repo_path,
            target_file="calculator.py",
        )

        env.reset(task)

        # Submit (should end episode)
        action = JarvisAction(action_type=ActionType.SUBMIT)
        action_bytes = encode_action(action)

        obs, reward, done, info = env.step(action_bytes)

        assert done
        assert info["done_reason"] == "submitted"

        env.close()

    def test_vectorized_env(self, toy_repo_path):
        if not os.path.exists(toy_repo_path):
            pytest.skip("Toy repo fixture not found")

        num_envs = 4
        env = VectorizedJarvisEnv(num_envs)

        task = Task(
            name="fix_multiply",
            description="Fix the multiply function",
            repo_path=toy_repo_path,
            target_file="calculator.py",
        )

        obs = env.reset([task] * num_envs)
        assert obs.shape == (num_envs, env.config.obs_bytes)

        # Take NO_OP actions
        action = JarvisAction(action_type=ActionType.NO_OP)
        action_bytes = encode_action(action)
        actions = action_bytes.unsqueeze(0).repeat(num_envs, 1)

        obs, rewards, dones, infos = env.step(actions)

        assert obs.shape == (num_envs, env.config.obs_bytes)
        assert rewards.shape == (num_envs,)
        assert dones.shape == (num_envs,)
        assert len(infos) == num_envs

        env.close()


class TestIntegration:
    """Integration tests for the full harness."""

    @pytest.fixture
    def toy_repo_path(self):
        return os.path.join(
            os.path.dirname(__file__),
            "..",
            "fixtures",
            "toy_repo"
        )

    def test_full_episode_flow(self, toy_repo_path):
        """Test a full episode flow: reset, actions, submit."""
        if not os.path.exists(toy_repo_path):
            pytest.skip("Toy repo fixture not found")

        env = JarvisHarnessEnv()
        task = Task(
            name="fix_multiply",
            description="Fix the multiply function to return a * b",
            repo_path=toy_repo_path,
            target_file="calculator.py",
        )

        obs = env.reset(task)

        # Step 1: Run tests to see baseline
        action = JarvisAction(action_type=ActionType.RUN_TESTS)
        obs, reward, done, info = env.step(encode_action(action))
        initial_passing = info["tests_passing"]
        initial_total = info["tests_total"]

        # Verify we got test results
        assert initial_total > 0, "Should have test results"
        # The toy repo has 18 tests, 3 failing
        assert initial_passing > 0, f"Some tests should pass, got {initial_passing}/{initial_total}"
        assert initial_total == 18, f"Expected 18 tests, got {initial_total}"

        # Step 2: Read the file
        action = JarvisAction(
            action_type=ActionType.READ_FILE,
            target="calculator.py",
            offset=0,
            length=500,
        )
        obs, reward, done, info = env.step(encode_action(action))
        assert not done

        # Step 3: Search for the bug
        action = JarvisAction(
            action_type=ActionType.SEARCH,
            target="return 0",
        )
        obs, reward, done, info = env.step(encode_action(action))
        assert not done

        # Step 4: Submit (without fix - just testing the flow)
        action = JarvisAction(action_type=ActionType.SUBMIT)
        obs, reward, done, info = env.step(encode_action(action))

        assert done
        assert info["done_reason"] == "submitted"

        env.close()

    def test_brain_action_can_step_env(self, toy_repo_path):
        """Smoke test: RPJBrain(32-byte) produces actions the harness can execute."""
        if not os.path.exists(toy_repo_path):
            pytest.skip("Toy repo fixture not found")

        env = JarvisHarnessEnv()
        task = Task(
            name="brain_smoke",
            description="Fix the multiply function",
            repo_path=toy_repo_path,
            target_file="calculator.py",
        )

        obs = env.reset(task)

        config = RPJConfig(
            obs_dim=env.config.obs_bytes,
            action_bytes=ACTION_BYTES,
            enable_plasticity=False,
            enable_sleep=False,
        )
        brain = RPJBrain(config)

        device = torch.device("cpu")
        h, g = brain.init_state(batch_size=1, device=device)
        a_prev = torch.zeros((1, ACTION_BYTES), dtype=torch.long)

        with torch.no_grad():
            output = brain(obs.unsqueeze(0), h, g, a_prev, training=True)

        action_bytes = output.action.squeeze(0).clone()
        action_bytes[0] = ActionType.NO_OP  # keep the smoke test fast/deterministic

        obs2, reward, done, info = env.step(action_bytes.clamp(0, 255).to(torch.uint8))
        assert obs2.shape == (env.config.obs_bytes,)
        assert isinstance(reward, float)
        assert isinstance(done, bool)
        assert info["step"] == 1

        env.close()

    def test_full_episode_manual_fix(self, toy_repo_path):
        """Test manually fixing a bug by rewriting the entire file."""
        if not os.path.exists(toy_repo_path):
            pytest.skip("Toy repo fixture not found")

        env = JarvisHarnessEnv()
        task = Task(
            name="fix_multiply",
            description="Fix the multiply function",
            repo_path=toy_repo_path,
            target_file="calculator.py",
        )

        obs = env.reset(task)

        # Run initial tests
        action = JarvisAction(action_type=ActionType.RUN_TESTS)
        obs, reward, done, info = env.step(encode_action(action))
        initial_passing = info["tests_passing"]

        # Manually fix the file using subprocess (simulating what agent would do)
        fpath = os.path.join(env.temp_dir, "calculator.py")
        with open(fpath, 'r') as f:
            content = f.read()

        # Fix the multiply bug: "return 0" -> "return a * b"
        fixed_content = content.replace("return 0", "return a * b")
        with open(fpath, 'w') as f:
            f.write(fixed_content)

        # Run tests again
        action = JarvisAction(action_type=ActionType.RUN_TESTS)
        obs, reward, done, info = env.step(encode_action(action))
        final_passing = info["tests_passing"]

        # Should have more passing tests now (we fixed 2 failing tests)
        assert final_passing > initial_passing, f"Expected improvement: {initial_passing} -> {final_passing}"

        env.close()
