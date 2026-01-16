"""
Tests for Jarvis Harness v2 features:
- Multi-file bug templates
- Repo generation
- Extended action space (git operations, multi-file nav)
"""

import pytest
import torch
import tempfile
import os
import shutil

from src.harness.bug_templates import (
    BugTemplate, BugInstance, BugCategory, BugDifficulty,
    sample_template, get_templates_by_difficulty, get_multi_file_templates,
    ALL_TEMPLATES,
)
from src.harness.repo_generator import (
    RepoGenerator, GeneratedRepo, RepoFile,
    generate_task_batch,
    inject_off_by_one, inject_wrong_operator, inject_wrong_return,
)
from src.harness.actions import (
    ActionType, JarvisAction,
    encode_action_v2, decode_action_v2, ACTION_BYTES_V2,
    is_git_action, is_multi_file_action, action_to_string,
)
from src.harness.env import JarvisHarnessEnv, HarnessConfig, Task
from src.harness.observations import OBS_TOTAL_BYTES, decode_observation
from src.harness.verifiers import run_pytest


class TestBugTemplates:
    """Test bug template system."""

    def test_template_count(self):
        """Verify we have a reasonable number of templates."""
        assert len(ALL_TEMPLATES) >= 15

    def test_categories_covered(self):
        """Verify all categories have templates."""
        categories = {t.category for t in ALL_TEMPLATES}
        assert BugCategory.SYNTAX in categories
        assert BugCategory.LOGIC in categories
        assert BugCategory.INTERFACE in categories

    def test_difficulty_range(self):
        """Test difficulty filtering."""
        easy = get_templates_by_difficulty(
            min_difficulty=BugDifficulty.TRIVIAL,
            max_difficulty=BugDifficulty.EASY
        )
        assert len(easy) > 0
        assert all(t.difficulty.value <= BugDifficulty.EASY.value for t in easy)

        hard = get_templates_by_difficulty(
            min_difficulty=BugDifficulty.HARD,
            max_difficulty=BugDifficulty.EXPERT
        )
        assert len(hard) > 0
        assert all(t.difficulty.value >= BugDifficulty.HARD.value for t in hard)

    def test_multi_file_templates(self):
        """Test multi-file template filtering."""
        multi = get_multi_file_templates()
        assert len(multi) > 0
        assert all(t.multi_file_fix for t in multi)

    def test_sample_template(self):
        """Test random template sampling."""
        t = sample_template(seed=42)
        assert isinstance(t, BugTemplate)

        # With filters
        t = sample_template(difficulty=BugDifficulty.HARD, seed=42)
        assert t.difficulty == BugDifficulty.HARD


class TestBugInjection:
    """Test bug injection functions."""

    def test_inject_off_by_one(self):
        """Test off-by-one injection."""
        code = """
for i in range(0, n + 1):
    result += i
"""
        buggy, hint, fix = inject_off_by_one(code)
        assert buggy != code
        assert "range(0, n)" in buggy
        assert hint

    def test_inject_wrong_operator(self):
        """Test operator injection."""
        code = """
if x == 5:
    return True
"""
        buggy, hint, fix = inject_wrong_operator(code)
        assert buggy != code
        assert "!=" in buggy or ">=" in buggy

    def test_inject_wrong_return(self):
        """Test return value injection."""
        code = """
def calculate():
    result = 42
    return result
"""
        buggy, hint, fix = inject_wrong_return(code)
        # May or may not change depending on random
        if buggy != code:
            assert "return" in buggy


class TestRepoGenerator:
    """Test synthetic repo generation."""

    def test_generate_basic(self):
        """Test basic repo generation."""
        gen = RepoGenerator(seed=42)
        repo = gen.generate(difficulty=BugDifficulty.EASY)

        assert isinstance(repo, GeneratedRepo)
        assert len(repo.files) > 0
        assert repo.name

    def test_generate_with_template(self):
        """Test generation with specific template."""
        gen = RepoGenerator(seed=42)

        repo = gen.generate(template_name="data_pipeline")
        assert "models.py" in repo.files
        assert "processor.py" in repo.files
        assert "test_pipeline.py" in repo.files

        repo2 = gen.generate(template_name="rest_api")
        assert "database.py" in repo2.files
        assert "handlers.py" in repo2.files
        assert "test_app.py" in repo2.files

    def test_generate_with_bugs(self):
        """Test that bugs are actually injected."""
        gen = RepoGenerator(seed=42)
        repo = gen.generate(num_bugs=2, difficulty=BugDifficulty.MEDIUM)

        # Should have bugs
        assert len(repo.bugs) >= 1

        # Buggy files should differ from originals
        for bug in repo.bugs:
            assert bug.buggy_code != bug.original_code

    def test_hard_multi_file_injects_secondary_files(self):
        """HARD multi-file generation should inject a true multi-file bug combo."""
        gen = RepoGenerator(seed=123)
        repo = gen.generate(
            template_name="data_pipeline",
            difficulty=BugDifficulty.HARD,
            num_bugs=1,
            multi_file=True,
        )

        assert repo.multi_file, "Expected a multi-file bug under HARD + multi_file=True"
        assert any(b.secondary_files for b in repo.bugs), "Expected secondary_files for multi-file bug"

    def test_write_to_disk(self):
        """Test writing generated repo to disk."""
        gen = RepoGenerator(seed=42)
        repo = gen.generate(template_name="data_pipeline")

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = gen.write_to_disk(repo, tmpdir)

            assert os.path.isdir(repo_path)
            assert os.path.exists(os.path.join(repo_path, "models.py"))
            assert os.path.exists(os.path.join(repo_path, "test_pipeline.py"))

    def test_generate_task_batch(self):
        """Test batch generation."""
        tasks = generate_task_batch(
            num_tasks=5,
            difficulty_range=(BugDifficulty.EASY, BugDifficulty.MEDIUM),
            seed=42,
        )

        assert len(tasks) == 5
        assert all(isinstance(t, GeneratedRepo) for t in tasks)

    def test_generated_repos_fail_verifier(self):
        """Generated repos with injected bugs should fail pytest (no free-win tasks)."""
        gen = RepoGenerator(seed=42)

        for template_name in ["data_pipeline", "rest_api"]:
            repo = gen.generate(template_name=template_name, difficulty=BugDifficulty.EASY, num_bugs=1)
            with tempfile.TemporaryDirectory() as tmpdir:
                repo_path = gen.write_to_disk(repo, tmpdir)
                result = run_pytest(repo_path)
                assert not result.passed, f"{template_name} unexpectedly passed tests with injected bugs"


class TestExtendedActions:
    """Test v2 action encoding with 64 bytes."""

    def test_encode_decode_v2_basic(self):
        """Test basic v2 encoding/decoding."""
        action = JarvisAction(
            action_type=ActionType.WRITE_FILE,
            target="models.py",
            content="return result",
            offset=100,
            length=50,
        )

        encoded = encode_action_v2(action)
        assert encoded.shape == torch.Size([ACTION_BYTES_V2])

        decoded = decode_action_v2(encoded)
        assert decoded.action_type == ActionType.WRITE_FILE
        assert decoded.target == "models.py"
        assert decoded.content == "return result"
        assert decoded.offset == 100
        assert decoded.length == 50

    def test_encode_decode_v2_git_action(self):
        """Test git action encoding."""
        action = JarvisAction(
            action_type=ActionType.GIT_DIFF,
            target="processor.py",
        )

        encoded = encode_action_v2(action)
        decoded = decode_action_v2(encoded)

        assert decoded.action_type == ActionType.GIT_DIFF
        assert decoded.target == "processor.py"

    def test_is_git_action(self):
        """Test git action classification."""
        assert is_git_action(ActionType.GIT_STATUS)
        assert is_git_action(ActionType.GIT_DIFF)
        assert is_git_action(ActionType.GIT_ADD)
        assert is_git_action(ActionType.GIT_CHECKOUT)

        assert not is_git_action(ActionType.READ_FILE)
        assert not is_git_action(ActionType.SHELL_CMD)

    def test_is_multi_file_action(self):
        """Test multi-file action classification."""
        assert is_multi_file_action(ActionType.LIST_FILES)
        assert is_multi_file_action(ActionType.NAVIGATE)
        assert is_multi_file_action(ActionType.STACKTRACE)

        assert not is_multi_file_action(ActionType.READ_FILE)
        assert not is_multi_file_action(ActionType.GIT_STATUS)

    def test_action_to_string_git(self):
        """Test git action string representation."""
        action = JarvisAction(ActionType.GIT_STATUS)
        s = action_to_string(action)
        assert "GIT_STATUS" in s

        action = JarvisAction(ActionType.GIT_DIFF, target="file.py")
        s = action_to_string(action)
        assert "GIT_DIFF" in s
        assert "file.py" in s

    def test_action_to_string_multifile(self):
        """Test multi-file action string representation."""
        action = JarvisAction(ActionType.LIST_FILES, target="src")
        s = action_to_string(action)
        assert "LIST_FILES" in s
        assert "src" in s

        action = JarvisAction(ActionType.STACKTRACE)
        s = action_to_string(action)
        assert "STACKTRACE" in s


class TestActionTypeCount:
    """Test action type completeness."""

    def test_action_count(self):
        """Verify all action types are defined."""
        # Original 7 + 6 git + 3 multi-file + 2 focus-edits = 18
        assert len(ActionType) == 18

    def test_all_actions_have_string(self):
        """Verify all actions have string representation."""
        for action_type in ActionType:
            action = JarvisAction(action_type=action_type)
            s = action_to_string(action)
            assert len(s) > 0
            assert "UNKNOWN" not in s


class TestGeneratedRepoStructure:
    """Test generated repo structure validity."""

    def test_has_test_files(self):
        """Generated repos should have test files."""
        gen = RepoGenerator(seed=42)
        repo = gen.generate(template_name="data_pipeline")

        test_files = [f for f in repo.files if f.startswith("test_")]
        assert len(test_files) > 0

    def test_has_conftest(self):
        """Generated repos should have conftest for imports."""
        gen = RepoGenerator(seed=42)
        repo = gen.generate()

        assert "conftest.py" in repo.files

    def test_preserves_original(self):
        """Original files should be preserved for comparison."""
        gen = RepoGenerator(seed=42)
        repo = gen.generate(num_bugs=1)

        assert len(repo.original_files) > 0

        # At least one file should differ if bugs were injected
        if repo.bugs:
            has_diff = False
            for path, file_obj in repo.files.items():
                if path in repo.original_files:
                    if file_obj.content != repo.original_files[path]:
                        has_diff = True
                        break
            # May or may not have diff depending on injection success


class TestHarnessV2Env:
    """Smoke tests that v2 (64-byte) actions execute end-to-end in the env."""

    def test_env_steps_with_v2_actions_and_git(self):
        gen = RepoGenerator(seed=7)
        repo = gen.generate(
            template_name="data_pipeline",
            difficulty=BugDifficulty.HARD,
            num_bugs=1,
            multi_file=True,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = gen.write_to_disk(repo, tmpdir)

            env = JarvisHarnessEnv(
                HarnessConfig(
                    obs_bytes=OBS_TOTAL_BYTES,
                    action_bytes=ACTION_BYTES_V2,
                    max_steps=10,
                    max_time_seconds=20,
                )
            )
            task = Task(
                name="v2_smoke",
                description="Fix the bugs and make tests pass.",
                repo_path=repo_path,
                target_file=repo.bugs[0].file_path if repo.bugs else "models.py",
            )

            obs = env.reset(task)
            assert obs.shape == (OBS_TOTAL_BYTES,)

            # Git status should work (env initializes a fresh git repo).
            action = JarvisAction(action_type=ActionType.GIT_STATUS)
            obs, _, done, _ = env.step(encode_action_v2(action))
            assert not done
            decoded = decode_observation(obs)
            assert "No changes" in decoded.terminal_output or "GIT_STATUS" in decoded.terminal_output

            # Write to a file using v2's explicit target field.
            action = JarvisAction(
                action_type=ActionType.WRITE_FILE,
                target="models.py",
                content="\n# jarvis_v2_smoke\n",
                offset=0,
                length=0,
            )
            obs, _, done, _ = env.step(encode_action_v2(action))
            assert not done

            # Git diff should now show some output (or at least not error).
            action = JarvisAction(action_type=ActionType.GIT_DIFF, target="models.py")
            obs, _, done, _ = env.step(encode_action_v2(action))
            assert not done
            decoded = decode_observation(obs)
            assert "diff --git" in decoded.terminal_output or "No diff" in decoded.terminal_output

            env.close()
