"""
Jarvis Harness Environment

A gymnasium-style environment where the RPJ brain learns to operate tools
in a repo-as-world setting. The agent must:
1. Read/write files
2. Run shell commands
3. Execute tests
4. Submit solutions

All under energy, time, and action budget constraints.

This is Sprint 1's "Jarvis Harness v0" - converting cool emergence metrics
into a useful operator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import os
import shutil
import tempfile
import subprocess
import time
import hashlib

import torch

from src.harness.actions import (
    ACTION_BYTES,
    ACTION_BYTES_V2,
    ActionType,
    JarvisAction,
    action_to_string,
    decode_action,
    decode_action_v2,
    encode_action,
    validate_shell_command,
)
from src.harness.observations import (
    JarvisObservation, encode_observation, decode_observation,
    scan_directory, hash_file_content, OBS_TOTAL_BYTES
)
from src.harness.verifiers import (
    run_pytest, run_lint, compute_diff_size, compute_reward,
    RewardComponents, VerifierResult, run_py_compile_file, run_pytest_fast
)
from src.energy.proxy import EnergyTracker, EnergyConfig


@dataclass
class HarnessConfig:
    """Configuration for Jarvis Harness environment."""
    # Budget constraints
    max_steps: int = 100              # Maximum actions per episode
    max_energy_joules: float = 10.0   # Energy budget (proxy)
    max_time_seconds: float = 60.0    # Wall-clock time limit

    # Observation config
    obs_bytes: int = OBS_TOTAL_BYTES  # 512 bytes
    action_bytes: int = ACTION_BYTES  # 32 bytes

    # Reward shaping
    test_reward_scale: float = 1.0    # Per-test reward
    lint_reward: float = 0.5          # Bonus for passing lint
    diff_penalty: float = -0.01       # Per changed line
    action_penalty: float = -0.01     # Per action
    success_bonus: float = 10.0       # All tests pass
    run_tests_on_reset: bool = True   # If False, skip pytest in reset() (faster training)
    run_fast_tests: bool = False      # If True, RUN_TESTS uses run_pytest_fast
    async_tests: bool = False         # If True, RUN_TESTS/SUBMIT run asynchronously (training)
    auto_tests_on_write: bool = False # If True, start fast tests after successful writes (async only)
    auto_full_tests_on_fast_pass: bool = False  # If True, run full tests when fast tests pass (async only)
    test_timeout_seconds: int = 30
    fast_test_timeout_seconds: int = 20

    # Task config
    task_type: str = "fix_bug"        # fix_bug, add_feature, refactor
    task_difficulty: str = "easy"     # easy, medium, hard

    # Energy proxy coefficients (from BLUEPRINT)
    kappa_F: float = 1e-9             # J/FLOP
    kappa_M: float = 5e-11            # J/Byte


@dataclass
class Task:
    """A single task for the agent to complete."""
    name: str
    description: str                  # Goal for the agent
    repo_path: str                    # Path to repo (will be copied to temp)
    target_file: str                  # Primary file to fix/modify
    expected_tests_passing: int = 1   # Minimum tests that should pass


@dataclass
class HarnessState:
    """Mutable state during episode."""
    step: int = 0
    energy_used: float = 0.0
    time_start: float = 0.0
    actions_taken: int = 0
    terminal_buffer: str = ""
    file_changes: Dict[str, Tuple[str, str]] = field(default_factory=dict)  # file -> (original, current)
    per_file_diff_lines: Dict[str, int] = field(default_factory=dict)  # file -> changed_lines vs original
    total_diff_lines: int = 0
    last_test_result: Optional[VerifierResult] = None
    last_test_step: int = -1
    test_process: Optional[subprocess.Popen] = None
    test_process_start: float = 0.0
    test_process_timeout_s: float = 0.0
    test_process_scope: str = ""
    pending_submit: bool = False
    prev_tests_passing: int = 0
    prev_tests_total: int = 0
    has_test_baseline: bool = False
    last_tests_delta_passing: int = 0
    last_tests_delta_total: int = 0
    last_reward: float = 0.0
    episode_return: float = 0.0  # Cumulative reward for the episode
    done: bool = False
    last_action_success: bool = True
    last_edit_changed: bool = False
    # Step-local bookkeeping for reward shaping / metrics
    last_action_type: int = -1
    prev_diff_lines: int = 0
    write_file_actions: int = 0
    write_focus_actions: int = 0
    effective_edits: int = 0
    run_tests_actions: int = 0
    # Focus buffer (for learnable, relative edits)
    focus_file: str = ""
    focus_offset: int = 0
    focus_text: str = ""
    last_syntax_result: Optional[VerifierResult] = None
    last_syntax_step: int = -1
    # Exploration tracking
    action_history: List[int] = field(default_factory=list)  # Recent action types
    initial_tests_passing: int = 0  # Baseline for progress reward
    consecutive_same_action: int = 0  # Count of repeated same action


class JarvisHarnessEnv:
    """
    Gymnasium-style environment for tool-using agent.

    Implements the "repo-as-world" paradigm where the agent:
    1. Observes: terminal output, filesystem state, goal, budgets
    2. Acts: shell commands, file operations, run tests
    3. Gets reward: based on test pass/fail, diff minimality

    Energy budget from BLUEPRINT is enforced via EnergyTracker.
    """

    def __init__(self, config: HarnessConfig = None):
        self.config = config or HarnessConfig()
        energy_config = EnergyConfig(
            kappa_F=self.config.kappa_F,
            kappa_M=self.config.kappa_M,
        )
        self.energy_tracker = EnergyTracker(energy_config)

        self.task: Optional[Task] = None
        self.temp_dir: Optional[str] = None
        self.state: Optional[HarnessState] = None
        self._source_repo_path: Optional[str] = None

        # Track original file contents for diff computation
        self._original_files: Dict[str, str] = {}
        # Cached filesystem snapshot (avoid per-step disk hashing).
        self._fs_snapshot_cache: Dict[str, str] = {}

    @property
    def observation_space_dim(self) -> int:
        """Observation byte dimension."""
        return self.config.obs_bytes

    @property
    def action_space_dim(self) -> int:
        """Action byte dimension."""
        return self.config.action_bytes

    def set_task(self, task: Task):
        """Set the current task."""
        self.task = task

    def reset(self, task: Optional[Task] = None) -> torch.Tensor:
        """
        Reset environment for new episode.

        Args:
            task: Optional new task. If None, uses current task.

        Returns:
            Initial observation bytes [obs_bytes]
        """
        if task is not None:
            self.task = task

        if self.task is None:
            raise ValueError("No task set. Call set_task() first.")

        # Ensure no verifier subprocess is still running from a previous episode.
        if self.state is not None and self.state.test_process is not None:
            try:
                self.state.test_process.kill()
                self.state.test_process.communicate(timeout=1)
            except Exception:
                pass

        # Prefer a fast reset (git reset/clean) when reusing the same repo source.
        reuse_workspace = (
            self.temp_dir
            and os.path.exists(self.temp_dir)
            and self._source_repo_path == self.task.repo_path
        )

        if reuse_workspace and self._git_hard_reset():
            pass
        else:
            # Clean up previous temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)

            # Copy repo to temp directory
            self.temp_dir = tempfile.mkdtemp(prefix="jarvis_harness_")
            if os.path.exists(self.task.repo_path):
                # Copy contents, not the directory itself
                for item in os.listdir(self.task.repo_path):
                    if item == ".git":
                        continue
                    s = os.path.join(self.task.repo_path, item)
                    d = os.path.join(self.temp_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)

            # Initialize a fresh git repo in the temp workspace so git actions work
            self._init_git_repo()
            self._source_repo_path = self.task.repo_path

        # Store original file contents
        self._original_files = {}
        for root, _, files in os.walk(self.temp_dir):
            for f in files:
                if f.endswith('.py'):
                    fpath = os.path.join(root, f)
                    rel_path = os.path.relpath(fpath, self.temp_dir)
                    try:
                        with open(fpath, 'r') as fp:
                            self._original_files[rel_path] = fp.read()
                    except Exception:
                        pass
        # Refresh fs snapshot cache once per reset (cheap for small repos).
        self._fs_snapshot_cache = scan_directory(self.temp_dir, max_files=50) if self.temp_dir else {}

        # Reset state
        self.state = HarnessState(
            step=0,
            energy_used=0.0,
            time_start=time.time(),
            actions_taken=0,
            terminal_buffer=f"Task: {self.task.description}\nRepo ready at {self.temp_dir}\n",
            file_changes={},
            last_test_result=None,
            last_test_step=-1,
            prev_tests_passing=0,
            prev_tests_total=0,
            last_tests_delta_passing=0,
            last_tests_delta_total=0,
            last_reward=0.0,
            done=False,
            last_action_type=-1,
            prev_diff_lines=0,
            write_file_actions=0,
            write_focus_actions=0,
            run_tests_actions=0,
            focus_file="",
            focus_offset=0,
            focus_text="",
            last_syntax_result=None,
            last_syntax_step=-1,
        )

        # Initialize focus to the task's target file so WRITE_FOCUS is immediately usable.
        try:
            target = self.task.target_file if self.task else ""
            if target and self.temp_dir:
                fpath = os.path.join(self.temp_dir, target)
                if os.path.exists(fpath):
                    with open(fpath, "r") as f:
                        content = f.read()
                    self.state.focus_file = target
                    self.state.focus_offset = 0
                    self.state.focus_text = content[:256]
        except Exception:
            pass

        # Optional initial test run to establish baseline.
        #
        # In async mode, start a non-blocking fast pytest so the agent gets early failure localization
        # without stalling vectorized env stepping.
        if self.config.run_tests_on_reset:
            if self.config.async_tests:
                self.state.initial_tests_passing = 0
                self.state.has_test_baseline = False
                self.state.last_test_result = None
                self.state.last_test_step = -1
                ok, msg = self._start_pytest_process(fast=bool(self.config.run_fast_tests))
                self.state.terminal_buffer += f"Initial tests: {msg if ok else 'failed to start'}\n"
            else:
                if self.config.run_fast_tests:
                    self.state.last_test_result = run_pytest_fast(
                        self.temp_dir,
                        timeout=self.config.fast_test_timeout_seconds,
                        maxfail=1,
                    )
                else:
                    self.state.last_test_result = run_pytest(self.temp_dir, timeout=self.config.test_timeout_seconds)

                self.state.last_test_step = 0
                self.state.initial_tests_passing = self.state.last_test_result.tests_passing
                self.state.prev_tests_passing = self.state.last_test_result.tests_passing
                self.state.prev_tests_total = self.state.last_test_result.tests_total
                self.state.has_test_baseline = True
                self.state.terminal_buffer += (
                    f"Initial tests: {self.state.last_test_result.tests_passing}/"
                    f"{self.state.last_test_result.tests_total} passing\n"
                )
        else:
            self.state.initial_tests_passing = 0
            self.state.has_test_baseline = False
            self.state.terminal_buffer += "Initial tests: (skipped)\n"

        return self._get_observation()

    def _init_git_repo(self) -> None:
        """Initialize a git repo in the temp workspace for v2 git actions."""
        if not self.temp_dir:
            return

        try:
            # Init
            subprocess.run(
                ["git", "init"],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            # Local identity (avoid relying on global git config)
            subprocess.run(
                ["git", "config", "user.email", "jarvis-harness@local"],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            subprocess.run(
                ["git", "config", "user.name", "Jarvis Harness"],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            # Commit initial snapshot so git diff/status/reset/checkout are meaningful.
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            subprocess.run(
                ["git", "commit", "-m", "init", "--no-gpg-sign"],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except FileNotFoundError:
            if self.state is not None:
                self.state.terminal_buffer += "git not found; git actions disabled\n"
        except Exception as e:
            if self.state is not None:
                self.state.terminal_buffer += f"git init failed: {e}\n"

    def _git_hard_reset(self) -> bool:
        """Hard reset the temp workspace to its initial git commit (fast reset path)."""
        if not self.temp_dir:
            return False
        if not os.path.isdir(os.path.join(self.temp_dir, ".git")):
            return False

        try:
            reset = subprocess.run(
                ["git", "reset", "--hard", "HEAD"],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            clean = subprocess.run(
                ["git", "clean", "-fd"],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return reset.returncode == 0 and clean.returncode == 0
        except Exception:
            return False

    def step(self, action_bytes: torch.Tensor) -> Tuple[torch.Tensor, float, bool, Dict[str, Any]]:
        """
        Execute action and return (obs, reward, done, info).

        Args:
            action_bytes: Action tensor [action_bytes]

        Returns:
            observation: Next observation [obs_bytes]
            reward: Scalar reward
            done: Episode termination flag
            info: Additional information dict
        """
        if self.state is None:
            raise RuntimeError("Environment not reset. Call reset() first.")

        if self.state.done:
            return self._get_observation(), 0.0, True, {"reason": "already_done"}

        # Decode action (v1=32 bytes, v2=64 bytes)
        action = self._decode_action_bytes(action_bytes)

        # Track action history for exploration bonus
        action_type = int(action.action_type)
        self.state.last_action_type = action_type

        if action.action_type == ActionType.WRITE_FILE:
            self.state.write_file_actions += 1
        elif action.action_type == ActionType.WRITE_FOCUS:
            self.state.write_focus_actions += 1
        elif action.action_type == ActionType.RUN_TESTS:
            self.state.run_tests_actions += 1

        if self.state.action_history and self.state.action_history[-1] == action_type:
            self.state.consecutive_same_action += 1
        else:
            self.state.consecutive_same_action = 1
        self.state.action_history.append(action_type)
        if len(self.state.action_history) > 10:
            self.state.action_history.pop(0)

        # Track energy (simplified - actual FLOP counting would need model forward pass)
        action_energy = self._estimate_action_energy(action)
        self.state.energy_used += action_energy

        # Execute action
        self.state.last_action_success = True
        self.state.last_edit_changed = False
        result, output = self._execute_action(action)
        self.state.last_action_success = bool(result)

        # Update terminal buffer
        self.state.terminal_buffer += f"\n[Step {self.state.step}] {action_to_string(action)}\n"
        self.state.terminal_buffer += output[:500] + "\n"

        # Keep only last N characters of terminal
        if len(self.state.terminal_buffer) > 2000:
            self.state.terminal_buffer = self.state.terminal_buffer[-2000:]

        # Update state
        self.state.step += 1
        self.state.actions_taken += 1

        # Poll any in-flight verifier subprocess (non-blocking).
        self._poll_test_process()

        # Check termination conditions
        done = False
        reason = ""

        # Time limit
        elapsed = time.time() - self.state.time_start
        if elapsed > self.config.max_time_seconds:
            done = True
            reason = "time_limit"

        # Energy limit
        if self.state.energy_used > self.config.max_energy_joules:
            done = True
            reason = "energy_limit"

        # Action limit
        if self.state.step >= self.config.max_steps:
            done = True
            reason = "action_limit"

        if not self.config.async_tests and action.action_type == ActionType.SUBMIT:
            done = True
            reason = "submitted"
        elif self.config.async_tests:
            # Submit only ends the episode once the full suite passes.
            tests_fresh = (
                self.state.last_test_result is not None
                and self.state.last_test_step == int(self.state.step) - 1
            )
            if tests_fresh and bool(self.state.pending_submit) and self.state.last_test_result.scope == "full":
                if self.state.last_test_result.passed:
                    done = True
                    reason = "submitted"
                else:
                    # Failed submit: keep episode running and let the agent continue editing.
                    self.state.pending_submit = False

        # Compute reward
        reward = self._compute_reward()
        self.state.last_reward = reward
        self.state.episode_return += reward

        if done:
            self.state.done = True
            # Best-effort: terminate any still-running test process.
            if self.state.test_process is not None:
                try:
                    self.state.test_process.kill()
                    self.state.test_process.communicate(timeout=1)
                except Exception:
                    pass
                self.state.test_process = None

        # Build info dict
        diff_lines = int(self.state.total_diff_lines) if self.state is not None else 0

        info = {
            "step": self.state.step,
            "action": action_to_string(action),
            "energy_used": self.state.energy_used,
            "time_elapsed": elapsed,
            "done_reason": reason if done else "",
            "tests_passing": self.state.last_test_result.tests_passing if self.state.last_test_result else 0,
            "tests_total": self.state.last_test_result.tests_total if self.state.last_test_result else 0,
            "diff_lines": diff_lines,
            "write_file_actions": self.state.write_file_actions,
            "write_focus_actions": self.state.write_focus_actions,
            "run_tests_actions": self.state.run_tests_actions,
            "episode_return": self.state.episode_return,  # Cumulative reward for curriculum success metric
        }

        return self._get_observation(), reward, done, info

    def _decode_action_bytes(self, action_bytes: torch.Tensor) -> JarvisAction:
        """Decode action bytes according to configured action size."""
        # Ensure we can handle numpy arrays or non-tensors.
        if not isinstance(action_bytes, torch.Tensor):
            action_bytes = torch.tensor(action_bytes, dtype=torch.uint8)

        # Prefer config setting, but fall back to shape heuristics if mismatched.
        expected = int(self.config.action_bytes)
        actual = int(action_bytes.shape[-1]) if action_bytes.dim() >= 1 else expected

        if expected == ACTION_BYTES_V2 or actual >= ACTION_BYTES_V2:
            return decode_action_v2(action_bytes)
        return decode_action(action_bytes)

    def _get_observation(self) -> torch.Tensor:
        """Build observation tensor from current state."""
        # Avoid per-step directory scans (CPU/disk bound). Snapshot is refreshed on reset
        # and updated on edits.
        fs_snapshot = self._fs_snapshot_cache or {}

        # Compute resource remaining
        elapsed = time.time() - self.state.time_start if self.state.time_start else 0
        time_remaining = max(0, 1 - elapsed / self.config.max_time_seconds)
        energy_remaining = max(0, 1 - self.state.energy_used / self.config.max_energy_joules)
        actions_remaining = max(0, self.config.max_steps - self.state.step)

        obs = JarvisObservation(
            terminal_output=self.state.terminal_buffer if self.state else "",
            fs_snapshot=fs_snapshot,
            goal=self.task.description if self.task else "",
            energy_remaining=energy_remaining,
            time_remaining=time_remaining,
            actions_remaining=actions_remaining,
            step=self.state.step if self.state else 0,
            last_reward=self.state.last_reward if self.state else 0,
            tests_passing=self.state.last_test_result.tests_passing if self.state and self.state.last_test_result else 0,
            tests_total=self.state.last_test_result.tests_total if self.state and self.state.last_test_result else 0,
            focus_offset=self.state.focus_offset if self.state else 0,
            focus_length=len(self.state.focus_text) if self.state else 0,
            focus_file_hash=(
                hashlib.md5(self.state.focus_file.encode("utf-8", errors="replace")).digest()[:16]
                if self.state and self.state.focus_file
                else b""
            ),
            focus_text=(self.state.focus_text if self.state and self.state.focus_text else ""),
            focus_preview=(self.state.focus_text[:32] if self.state and self.state.focus_text else ""),
        )

        return encode_observation(obs, self.config.obs_bytes)

    def _execute_action(self, action: JarvisAction) -> Tuple[bool, str]:
        """
        Execute an action and return (success, output).
        """
        if action.action_type == ActionType.NO_OP:
            return True, "No operation"

        elif action.action_type == ActionType.SHELL_CMD:
            valid, msg = validate_shell_command(action.content)
            if not valid:
                return False, f"Invalid command: {msg}"

            try:
                result = subprocess.run(
                    action.content,
                    shell=True,
                    cwd=self.temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return True, result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                return False, "Command timed out"
            except Exception as e:
                return False, f"Error: {e}"

        elif action.action_type == ActionType.READ_FILE:
            target_path = action.target or (self.task.target_file if self.task else "")
            if not target_path:
                return False, "No target file specified"
            fpath = os.path.join(self.temp_dir, target_path)
            if not os.path.exists(fpath):
                return False, f"File not found: {target_path}"

            try:
                with open(fpath, 'r') as f:
                    content = f.read()
                offset = max(0, min(int(action.offset), len(content)))
                length = max(0, min(int(action.length), max(0, len(content) - offset)))
                chunk = content[offset:offset + length]
                # Update focus buffer for learnable relative edits.
                self.state.focus_file = target_path
                self.state.focus_offset = offset
                self.state.focus_text = chunk
                return True, chunk
            except Exception as e:
                return False, f"Read error: {e}"

        elif action.action_type == ActionType.WRITE_FILE:
            target_path = action.target or (self.task.target_file if self.task else "")
            if not target_path:
                return False, "No target file specified"
            fpath = os.path.join(self.temp_dir, target_path)

            try:
                # Read existing content
                existing = ""
                if os.path.exists(fpath):
                    with open(fpath, 'r') as f:
                        existing = f.read()

                # Store original if first edit
                rel_path = os.path.relpath(fpath, self.temp_dir)
                if rel_path not in self.state.file_changes:
                    self.state.file_changes[rel_path] = (existing, existing)

                # Apply edit: replace [offset:offset+length] with payload.
                # This matches the byte-level offset/length scheme in BLUEPRINT.md 2.8.2.
                offset = max(0, min(action.offset, len(existing)))
                length = max(0, min(action.length, len(existing) - offset))
                new_content = existing[:offset] + action.content + existing[offset + length:]

                changed = new_content != existing
                self.state.last_edit_changed = bool(changed)
                if changed:
                    self.state.effective_edits += 1
                if not changed:
                    return True, f"No-op write (no changes) to {target_path}"

                # Write file
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, 'w') as f:
                    f.write(new_content)

                # Update tracked changes
                orig, _ = self.state.file_changes[rel_path]
                self.state.file_changes[rel_path] = (orig, new_content)
                # Update MDL proxy incrementally (avoid per-step difflib diffs).
                old_changed = int(self.state.per_file_diff_lines.get(rel_path, 0))
                new_changed, _ = compute_diff_size(orig, new_content)
                self.state.per_file_diff_lines[rel_path] = int(new_changed)
                self.state.total_diff_lines = int(self.state.total_diff_lines) + int(new_changed) - old_changed
                # Update fs snapshot cache for observation.
                self._fs_snapshot_cache[rel_path] = hash_file_content(new_content).hex()

                # Update focus to the edited file/region.
                self.state.focus_file = target_path
                self.state.focus_offset = offset
                self.state.focus_text = new_content[offset:offset + min(512, len(new_content) - offset)]

                syntax_msg = ""
                if target_path.endswith(".py"):
                    self.state.last_syntax_result = run_py_compile_file(self.temp_dir, rel_path, timeout=5)
                    self.state.last_syntax_step = int(self.state.step)
                    if self.state.last_syntax_result.passed:
                        syntax_msg = "\nSyntax OK"
                    else:
                        syntax_msg = f"\nSyntax ERROR:\n{self.state.last_syntax_result.details}"

                # Training helper: after a real, syntax-valid edit, start a cheap async test run.
                if self.config.auto_tests_on_write and self.config.async_tests:
                    diff_changed = int(new_changed) != int(old_changed)
                    syntax_ok = (not target_path.endswith(".py")) or (
                        self.state.last_syntax_result is not None and self.state.last_syntax_result.passed
                    )
                    if diff_changed and syntax_ok:
                        self.state.pending_submit = False
                        self._start_pytest_process(fast=True)

                return True, f"Wrote {len(action.content)} bytes to {target_path}{syntax_msg}"
            except Exception as e:
                return False, f"Write error: {e}"

        elif action.action_type == ActionType.WRITE_FOCUS:
            if not self.state.focus_file:
                return False, "No focus set (use READ_FILE/NAVIGATE first)"

            target_path = self.state.focus_file
            fpath = os.path.join(self.temp_dir, target_path)
            if not os.path.exists(fpath):
                return False, f"Focused file not found: {target_path}"

            try:
                with open(fpath, "r") as f:
                    existing = f.read()

                rel_path = os.path.relpath(fpath, self.temp_dir)
                if rel_path not in self.state.file_changes:
                    self.state.file_changes[rel_path] = (existing, existing)

                focus_base = max(0, min(int(self.state.focus_offset), len(existing)))
                offset_in_focus = max(0, int(action.offset))
                global_offset = max(0, min(focus_base + offset_in_focus, len(existing)))

                replace_len = max(0, min(int(action.length), max(0, len(existing) - global_offset)))
                new_content = existing[:global_offset] + action.content + existing[global_offset + replace_len:]

                changed = new_content != existing
                self.state.last_edit_changed = bool(changed)
                if changed:
                    self.state.effective_edits += 1
                if not changed:
                    return True, f"No-op write (no changes) to focus {target_path}"

                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, "w") as f:
                    f.write(new_content)

                orig, _ = self.state.file_changes[rel_path]
                self.state.file_changes[rel_path] = (orig, new_content)
                old_changed = int(self.state.per_file_diff_lines.get(rel_path, 0))
                new_changed, _ = compute_diff_size(orig, new_content)
                self.state.per_file_diff_lines[rel_path] = int(new_changed)
                self.state.total_diff_lines = int(self.state.total_diff_lines) + int(new_changed) - old_changed
                self._fs_snapshot_cache[rel_path] = hash_file_content(new_content).hex()

                # Refresh focus window in the edited file.
                window_len = len(self.state.focus_text) if self.state.focus_text else 256
                self.state.focus_offset = max(0, min(focus_base, len(new_content)))
                self.state.focus_text = new_content[self.state.focus_offset:self.state.focus_offset + window_len]

                syntax_msg = ""
                if target_path.endswith(".py"):
                    self.state.last_syntax_result = run_py_compile_file(self.temp_dir, rel_path, timeout=5)
                    self.state.last_syntax_step = int(self.state.step)
                    if self.state.last_syntax_result.passed:
                        syntax_msg = "\nSyntax OK"
                    else:
                        syntax_msg = f"\nSyntax ERROR:\n{self.state.last_syntax_result.details}"

                if self.config.auto_tests_on_write and self.config.async_tests:
                    diff_changed = int(new_changed) != int(old_changed)
                    syntax_ok = (not target_path.endswith(".py")) or (
                        self.state.last_syntax_result is not None and self.state.last_syntax_result.passed
                    )
                    if diff_changed and syntax_ok:
                        self.state.pending_submit = False
                        self._start_pytest_process(fast=True)

                return True, f"Wrote {len(action.content)} bytes to focus {target_path}{syntax_msg}"
            except Exception as e:
                return False, f"Write focus error: {e}"

        elif action.action_type == ActionType.REPLACE_FOCUS:
            if not self.state.focus_file:
                return False, "No focus set (use READ_FILE/NAVIGATE first)"

            find_s = (action.target or "").strip()
            repl_s = action.content or ""
            if not find_s:
                return False, "No find string provided"

            target_path = self.state.focus_file
            fpath = os.path.join(self.temp_dir, target_path)
            if not os.path.exists(fpath):
                return False, f"Focused file not found: {target_path}"

            try:
                with open(fpath, "r") as f:
                    existing = f.read()

                rel_path = os.path.relpath(fpath, self.temp_dir)
                if rel_path not in self.state.file_changes:
                    self.state.file_changes[rel_path] = (existing, existing)

                # Prefer replacing within the current focus window.
                focus_text = self.state.focus_text or ""
                idx = focus_text.find(find_s)
                if idx < 0:
                    return False, "Find string not found in focus window"

                focus_base = max(0, min(int(self.state.focus_offset), len(existing)))
                global_offset = max(0, min(focus_base + idx, len(existing)))
                end = max(0, min(global_offset + len(find_s), len(existing)))

                new_content = existing[:global_offset] + repl_s + existing[end:]

                changed = new_content != existing
                self.state.last_edit_changed = bool(changed)
                if changed:
                    self.state.effective_edits += 1
                if not changed:
                    return True, f"No-op replace (no changes) in focus {target_path}"

                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, "w") as f:
                    f.write(new_content)

                orig, _ = self.state.file_changes[rel_path]
                self.state.file_changes[rel_path] = (orig, new_content)

                old_changed = int(self.state.per_file_diff_lines.get(rel_path, 0))
                new_changed, _ = compute_diff_size(orig, new_content)
                self.state.per_file_diff_lines[rel_path] = int(new_changed)
                self.state.total_diff_lines = int(self.state.total_diff_lines) + int(new_changed) - old_changed
                self._fs_snapshot_cache[rel_path] = hash_file_content(new_content).hex()

                # Refresh focus window in the edited file.
                window_len = len(self.state.focus_text) if self.state.focus_text else 256
                self.state.focus_offset = max(0, min(focus_base, len(new_content)))
                self.state.focus_text = new_content[self.state.focus_offset:self.state.focus_offset + window_len]

                syntax_msg = ""
                if target_path.endswith(".py"):
                    self.state.last_syntax_result = run_py_compile_file(self.temp_dir, rel_path, timeout=5)
                    self.state.last_syntax_step = int(self.state.step)
                    if self.state.last_syntax_result.passed:
                        syntax_msg = "\nSyntax OK"
                    else:
                        syntax_msg = f"\nSyntax ERROR:\n{self.state.last_syntax_result.details}"

                if self.config.auto_tests_on_write and self.config.async_tests:
                    diff_changed = int(new_changed) != int(old_changed)
                    syntax_ok = (not target_path.endswith(".py")) or (
                        self.state.last_syntax_result is not None and self.state.last_syntax_result.passed
                    )
                    if diff_changed and syntax_ok:
                        self.state.pending_submit = False
                        self._start_pytest_process(fast=True)

                return True, f"Replaced '{find_s}' -> '{repl_s}' in focus {target_path}{syntax_msg}"
            except Exception as e:
                return False, f"Replace focus error: {e}"

        elif action.action_type == ActionType.RUN_TESTS:
            if not self.config.async_tests:
                if self.config.run_fast_tests:
                    result = run_pytest_fast(
                        self.temp_dir,
                        timeout=self.config.fast_test_timeout_seconds,
                        maxfail=1,
                    )
                else:
                    result = run_pytest(self.temp_dir, timeout=self.config.test_timeout_seconds)

                self.state.last_test_result = result
                self.state.last_test_step = int(self.state.step)

                if not bool(self.state.has_test_baseline):
                    self.state.has_test_baseline = True
                    self.state.initial_tests_passing = int(result.tests_passing)
                    self.state.prev_tests_passing = int(result.tests_passing)
                    self.state.prev_tests_total = int(result.tests_total)
                    self.state.last_tests_delta_passing = 0
                    self.state.last_tests_delta_total = 0
                else:
                    prev_passing = int(self.state.prev_tests_passing)
                    prev_total = int(self.state.prev_tests_total)
                    self.state.last_tests_delta_passing = int(result.tests_passing) - prev_passing
                    self.state.last_tests_delta_total = int(result.tests_total) - prev_total
                    self.state.prev_tests_passing = int(result.tests_passing)
                    self.state.prev_tests_total = int(result.tests_total)

                self._maybe_update_focus_from_test_details(result.details)
                return True, result.details

            # Async mode: avoid CPU subprocess stalls that starve the GPU.
            self.state.pending_submit = False
            ok, msg = self._start_pytest_process(fast=bool(self.config.run_fast_tests))
            return ok, msg

        elif action.action_type == ActionType.SEARCH:
            # Simple grep-like search
            query = action.target
            results = []
            for root, _, files in os.walk(self.temp_dir):
                for f in files:
                    if not f.endswith('.py'):
                        continue
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, 'r') as fp:
                            for i, line in enumerate(fp):
                                if query in line:
                                    rel_path = os.path.relpath(fpath, self.temp_dir)
                                    results.append(f"{rel_path}:{i+1}: {line.strip()}")
                    except Exception:
                        pass
            return True, "\n".join(results[:20]) if results else "No matches found"

        elif action.action_type == ActionType.SUBMIT:
            if not self.config.async_tests:
                # Run final tests
                result = run_pytest(self.temp_dir, timeout=self.config.test_timeout_seconds)
                self.state.last_test_result = result
                self.state.last_test_step = int(self.state.step)

                if not bool(self.state.has_test_baseline):
                    self.state.has_test_baseline = True
                    self.state.initial_tests_passing = int(result.tests_passing)
                    self.state.prev_tests_passing = int(result.tests_passing)
                    self.state.prev_tests_total = int(result.tests_total)
                    self.state.last_tests_delta_passing = 0
                    self.state.last_tests_delta_total = 0
                else:
                    prev_passing = int(self.state.prev_tests_passing)
                    prev_total = int(self.state.prev_tests_total)
                    self.state.last_tests_delta_passing = int(result.tests_passing) - prev_passing
                    self.state.last_tests_delta_total = int(result.tests_total) - prev_total
                    self.state.prev_tests_passing = int(result.tests_passing)
                    self.state.prev_tests_total = int(result.tests_total)

                self._maybe_update_focus_from_test_details(result.details)
                return True, (
                    "Submitted. Final tests: "
                    f"{result.tests_passing}/{result.tests_total}"
                )

            # Async submit: run the FULL suite and end the episode only if it passes.
            self.state.pending_submit = True
            ok, msg = self._start_pytest_process(fast=False)
            return ok, msg

        # =================================================================
        # Git operations (v2)
        # =================================================================
        elif action.action_type == ActionType.GIT_STATUS:
            return self._git_status()

        elif action.action_type == ActionType.GIT_DIFF:
            return self._git_diff(action.target)

        elif action.action_type == ActionType.GIT_ADD:
            return self._git_add(action.target)

        elif action.action_type == ActionType.GIT_RESET:
            return self._git_reset(action.target)

        elif action.action_type == ActionType.GIT_CHECKOUT:
            return self._git_checkout(action.target)

        elif action.action_type == ActionType.GIT_LOG:
            return self._git_log()

        # =================================================================
        # Multi-file operations (v2)
        # =================================================================
        elif action.action_type == ActionType.LIST_FILES:
            return self._list_files(action.target)

        elif action.action_type == ActionType.NAVIGATE:
            return self._navigate(action.target, action.offset, action.length)

        elif action.action_type == ActionType.STACKTRACE:
            return self._parse_stacktrace()

        return False, f"Unknown action type: {action.action_type}"

    def _start_pytest_process(self, *, fast: bool) -> Tuple[bool, str]:
        if self.state is None or self.temp_dir is None:
            return False, "No workspace"

        # Only allow one in-flight test process per env to avoid runaway subprocess churn.
        if self.state.test_process is not None:
            try:
                if self.state.test_process.poll() is None:
                    return True, "Tests already running"
            except Exception:
                pass

        import sys

        python_exe = sys.executable
        cmd = [python_exe, "-m", "pytest", "-q", "--tb=short"]
        scope = "full"
        timeout_s: float = float(self.config.test_timeout_seconds)
        if fast:
            cmd.append("--maxfail=1")
            scope = "fast"
            timeout_s = float(self.config.fast_test_timeout_seconds)

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=self.temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as e:
            return False, f"Failed to start tests: {e}"

        self.state.test_process = proc
        self.state.test_process_start = time.time()
        self.state.test_process_timeout_s = max(0.0, timeout_s)
        self.state.test_process_scope = scope
        return True, f"Started tests ({scope})"

    def _poll_test_process(self) -> None:
        if self.state is None or self.state.test_process is None:
            return

        proc = self.state.test_process
        scope = self.state.test_process_scope or "fast"
        now = time.time()

        def _finalize(output: str, *, returncode: int, timed_out: bool) -> None:
            output = output or ""
            tests_passing = 0
            tests_total = 0
            if "passed" in output:
                import re

                passed_match = re.search(r"(\d+) passed", output)
                if passed_match:
                    tests_passing = int(passed_match.group(1))
                    tests_total = tests_passing

                failed_match = re.search(r"(\d+) failed", output)
                if failed_match:
                    tests_total += int(failed_match.group(1))

            passed = (returncode == 0) and (not timed_out)
            score = tests_passing / tests_total if tests_total > 0 else 0.0
            details = ("TIMEOUT: tests\n" + output) if timed_out else output
            details_trunc = details[:500]

            # Clear the completed process handle first so we can optionally launch follow-on tests.
            self.state.test_process = None
            self.state.test_process_start = 0.0
            self.state.test_process_timeout_s = 0.0
            self.state.test_process_scope = ""

            self.state.last_test_result = VerifierResult(
                passed=passed,
                score=score,
                details=details_trunc,
                tests_passing=tests_passing,
                tests_total=tests_total,
                scope=scope,
            )
            # Mark "fresh" on the step where results become available.
            self.state.last_test_step = int(self.state.step) - 1

            if not bool(self.state.has_test_baseline):
                self.state.has_test_baseline = True
                self.state.initial_tests_passing = int(tests_passing)
                self.state.prev_tests_passing = int(tests_passing)
                self.state.prev_tests_total = int(tests_total)
                self.state.last_tests_delta_passing = 0
                self.state.last_tests_delta_total = 0
            else:
                prev_passing = int(self.state.prev_tests_passing)
                prev_total = int(self.state.prev_tests_total)
                self.state.last_tests_delta_passing = int(tests_passing) - prev_passing
                self.state.last_tests_delta_total = int(tests_total) - prev_total
                self.state.prev_tests_passing = int(tests_passing)
                self.state.prev_tests_total = int(tests_total)

            # Surface results to the agent.
            self.state.terminal_buffer += (
                f"\n[Tests completed: {scope}] {tests_passing}/{tests_total} passing\n"
                + details_trunc
                + "\n"
            )
            if len(self.state.terminal_buffer) > 2000:
                self.state.terminal_buffer = self.state.terminal_buffer[-2000:]

            # Update focus from traceback hints (makes focused edits learnable).
            self._maybe_update_focus_from_test_details(details_trunc)

            # Training helper: if fast tests pass, opportunistically run the full suite so the
            # success bonus is reachable even if the agent hasn't learned SUBMIT yet.
            if (
                scope == "fast"
                and bool(passed)
                and bool(self.config.async_tests)
                and bool(self.config.auto_full_tests_on_fast_pass)
                and self.state is not None
                and (not bool(self.state.pending_submit))
            ):
                self.state.pending_submit = True
                ok, msg = self._start_pytest_process(fast=False)
                if not ok:
                    self.state.pending_submit = False
                self.state.terminal_buffer += f"\n[Auto full tests] {msg}\n"
                if len(self.state.terminal_buffer) > 2000:
                    self.state.terminal_buffer = self.state.terminal_buffer[-2000:]

        try:
            returncode = proc.poll()
        except Exception:
            returncode = None

        if returncode is None:
            # Enforce timeout without blocking.
            timeout_s = float(self.state.test_process_timeout_s or 0.0)
            if timeout_s > 0 and (now - float(self.state.test_process_start or 0.0)) > timeout_s:
                try:
                    proc.kill()
                except Exception:
                    pass
                try:
                    out, err = proc.communicate(timeout=1)
                except Exception:
                    out, err = "", ""
                _finalize((out or "") + (err or ""), returncode=-1, timed_out=True)
            return

        try:
            out, err = proc.communicate(timeout=1)
        except Exception:
            out, err = "", ""
        _finalize((out or "") + (err or ""), returncode=int(returncode), timed_out=False)

    def _extract_trace_locations(self, details: str) -> List[Tuple[str, int]]:
        """Best-effort parse of file:line locations from pytest/traceback text."""
        if not details:
            return []

        import re

        locs: List[Tuple[str, int]] = []

        # Python traceback format.
        for fpath, line_s in re.findall(r'File "([^"]+)", line (\d+)', details):
            try:
                locs.append((fpath, int(line_s)))
            except Exception:
                continue

        # Pytest short/summary format (also catches many error lines).
        for fpath, line_s in re.findall(r"([A-Za-z0-9_./\\\\-]+\\.py):(\\d+)", details):
            try:
                locs.append((fpath, int(line_s)))
            except Exception:
                continue

        return locs

    def _normalize_trace_path(self, fpath: str) -> Optional[str]:
        """Return repo-relative path if fpath points inside the temp workspace."""
        if not self.temp_dir:
            return None
        fpath = (fpath or "").strip()
        if not fpath or not fpath.endswith(".py"):
            return None

        try:
            if os.path.isabs(fpath):
                if not fpath.startswith(self.temp_dir):
                    return None
                rel = os.path.relpath(fpath, self.temp_dir)
            else:
                candidate = os.path.join(self.temp_dir, fpath)
                if not os.path.exists(candidate):
                    return None
                rel = fpath
        except Exception:
            return None

        rel = rel.replace("\\", "/")
        if rel.startswith("../"):
            return None
        return rel

    def _set_focus_from_location(self, rel_path: str, *, line: int) -> bool:
        """Set focus window around a (file, line) location and surface a small snippet."""
        if self.state is None or self.temp_dir is None:
            return False

        rel_path = (rel_path or "").replace("\\", "/")
        if not rel_path:
            return False

        fpath = os.path.join(self.temp_dir, rel_path)
        if not os.path.exists(fpath):
            return False

        try:
            with open(fpath, "r") as f:
                content = f.read()
        except Exception:
            return False

        lines = content.splitlines(True)
        if not lines:
            return False

        try:
            line_idx = int(line) - 1
        except Exception:
            line_idx = 0
        line_idx = max(0, min(line_idx, len(lines) - 1))

        offset = 0
        for i in range(line_idx):
            offset += len(lines[i])

        self.state.focus_file = rel_path
        self.state.focus_offset = int(offset)
        self.state.focus_text = content[offset:offset + 512]

        # Surface a small snippet for debugging/edit guidance.
        start = max(0, line_idx - 3)
        end = min(len(lines), line_idx + 4)
        snippet = "".join(f"{i+1:04d} {lines[i]}" for i in range(start, end))
        self.state.terminal_buffer += f"\n[Focus] {rel_path}:{line_idx + 1}\n{snippet}\n"
        if len(self.state.terminal_buffer) > 2000:
            self.state.terminal_buffer = self.state.terminal_buffer[-2000:]

        return True

    def _maybe_update_focus_from_test_details(self, details: str) -> None:
        """Opportunistically set focus to a relevant traceback location (learnability helper)."""
        if self.state is None or self.temp_dir is None:
            return

        candidates: List[Tuple[str, int]] = []
        seen: set[Tuple[str, int]] = set()
        for fpath, line in self._extract_trace_locations(details):
            rel = self._normalize_trace_path(fpath)
            if rel is None:
                continue
            key = (rel, int(line))
            if key in seen:
                continue
            seen.add(key)
            candidates.append(key)

        if not candidates:
            return

        chosen: Optional[Tuple[str, int]] = None
        for rel, line in reversed(candidates):
            if not rel.replace("\\", "/").startswith("tests/"):
                chosen = (rel, line)
                break
        if chosen is None:
            chosen = candidates[-1]

        self._set_focus_from_location(chosen[0], line=int(chosen[1]))

    # =================================================================
    # Git operation implementations
    # =================================================================

    def _git_status(self) -> Tuple[bool, str]:
        """Show git status of working directory."""
        try:
            result = subprocess.run(
                ['git', 'status', '--short'],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = result.stdout.strip() or "No changes"
            return True, output
        except Exception as e:
            return False, f"Git status error: {e}"

    def _git_diff(self, target: str = "") -> Tuple[bool, str]:
        """Show git diff for file or all changes."""
        try:
            cmd = ['git', 'diff']
            if target:
                cmd.append(target)
            result = subprocess.run(
                cmd,
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout[:1000]  # Truncate
            return True, output or "No diff"
        except Exception as e:
            return False, f"Git diff error: {e}"

    def _git_add(self, target: str) -> Tuple[bool, str]:
        """Stage a file."""
        if not target:
            return False, "No file specified for git add"
        try:
            result = subprocess.run(
                ['git', 'add', target],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True, f"Staged: {target}"
            return False, result.stderr
        except Exception as e:
            return False, f"Git add error: {e}"

    def _git_reset(self, target: str) -> Tuple[bool, str]:
        """Unstage a file."""
        if not target:
            return False, "No file specified for git reset"
        try:
            result = subprocess.run(
                ['git', 'reset', 'HEAD', target],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return True, f"Unstaged: {target}"
        except Exception as e:
            return False, f"Git reset error: {e}"

    def _git_checkout(self, target: str) -> Tuple[bool, str]:
        """Discard changes to a file."""
        if not target:
            return False, "No file specified for git checkout"
        try:
            result = subprocess.run(
                ['git', 'checkout', '--', target],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True, f"Discarded changes: {target}"
            return False, result.stderr
        except Exception as e:
            return False, f"Git checkout error: {e}"

    def _git_log(self) -> Tuple[bool, str]:
        """Show recent git log."""
        try:
            result = subprocess.run(
                ['git', 'log', '--oneline', '-5'],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return True, result.stdout.strip() or "No commits"
        except Exception as e:
            return False, f"Git log error: {e}"

    # =================================================================
    # Multi-file operation implementations
    # =================================================================

    def _list_files(self, target: str = "") -> Tuple[bool, str]:
        """List files in directory."""
        try:
            dir_path = os.path.join(self.temp_dir, target) if target else self.temp_dir
            if not os.path.isdir(dir_path):
                return False, f"Not a directory: {target}"

            files = []
            for item in sorted(os.listdir(dir_path)):
                full = os.path.join(dir_path, item)
                if os.path.isdir(full):
                    files.append(f"{item}/")
                else:
                    size = os.path.getsize(full)
                    files.append(f"{item} ({size}b)")

            return True, "\n".join(files[:30])
        except Exception as e:
            return False, f"List error: {e}"

    def _navigate(self, target: str, offset: int = 0, length: int = 256) -> Tuple[bool, str]:
        """Navigate to (focus on) a different file."""
        if not target:
            return False, "No target file specified"

        fpath = os.path.join(self.temp_dir, target)
        if not os.path.exists(fpath):
            return False, f"File not found: {target}"

        # Read a chunk of the file to show context and set the focus buffer.
        try:
            with open(fpath, "r") as f:
                content = f.read()

            file_offset = max(0, min(int(offset), len(content)))
            window = max(0, min(int(length), max(0, len(content) - file_offset)))
            chunk = content[file_offset:file_offset + window]

            if self.state is not None:
                self.state.focus_file = target
                self.state.focus_offset = file_offset
                self.state.focus_text = chunk

            return True, f"Navigated to {target} @ {file_offset}:\n{chunk}"
        except Exception as e:
            return False, f"Navigate error: {e}"

    def _parse_stacktrace(self) -> Tuple[bool, str]:
        """Parse last test output for stacktrace info."""
        if not self.state.last_test_result:
            return False, "No test result available"

        details = self.state.last_test_result.details
        locs = self._extract_trace_locations(details)
        if not locs:
            return True, "No stacktrace found in last output"

        results: List[str] = []
        seen: set[str] = set()
        for fpath, line in locs[-10:]:
            rel = self._normalize_trace_path(fpath)
            label = f"{rel}:{line}" if rel is not None else f"{fpath}:{line}"
            if label in seen:
                continue
            seen.add(label)
            results.append(label)

        return True, "Stacktrace:\n" + "\n".join(results[-5:])

    def _estimate_action_energy(self, action: JarvisAction) -> float:
        """Estimate energy cost of an action."""
        # Simple heuristics - real implementation would track actual compute
        base_cost = 0.001  # Base cost per action

        if action.action_type == ActionType.NO_OP:
            return base_cost * 0.1

        elif action.action_type == ActionType.SHELL_CMD:
            return base_cost * 10  # Shell commands are expensive

        elif action.action_type == ActionType.READ_FILE:
            return base_cost * (1 + action.length / 1000)

        elif action.action_type in (ActionType.WRITE_FILE, ActionType.WRITE_FOCUS, ActionType.REPLACE_FOCUS):
            return base_cost * (2 + len(action.content) / 1000)

        elif action.action_type == ActionType.RUN_TESTS:
            return base_cost * 50  # Tests are expensive

        elif action.action_type == ActionType.SEARCH:
            return base_cost * 5

        elif action.action_type == ActionType.SUBMIT:
            return base_cost * 50  # Triggers final tests

        # Git operations (v2) - moderate cost
        elif action.action_type in [
            ActionType.GIT_STATUS,
            ActionType.GIT_LOG,
            ActionType.GIT_DIFF,
        ]:
            return base_cost * 3

        elif action.action_type in [
            ActionType.GIT_ADD,
            ActionType.GIT_RESET,
            ActionType.GIT_CHECKOUT,
        ]:
            return base_cost * 5

        # Multi-file operations (v2) - cheap info gathering
        elif action.action_type in [
            ActionType.LIST_FILES,
            ActionType.NAVIGATE,
            ActionType.STACKTRACE,
        ]:
            return base_cost * 2

        return base_cost

    def _compute_reward(self) -> float:
        """
        Compute reward for current step (verifier-grounded).

        Key principles:
        - No constant reward from stale verifier state.
        - Dense, cheap signal from syntax-only checks on edits.
        - Test rewards only when tests are actually run (RUN_TESTS / SUBMIT).
        """
        # Total diff lines (MDL proxy), tracked incrementally on edits.
        total_diff_lines = int(self.state.total_diff_lines)

        # Penalize only NEW diff introduced this step (discourages thrashing).
        delta_diff_lines = max(0, int(total_diff_lines) - int(self.state.prev_diff_lines))
        self.state.prev_diff_lines = int(total_diff_lines)

        # Only treat pytest results as "fresh" on the step they were executed.
        tests_fresh = self.state.last_test_result is not None and self.state.last_test_step == int(self.state.step) - 1
        test_result = self.state.last_test_result if tests_fresh else VerifierResult(passed=False, score=0.0, scope="none")

        # Base reward: uses per-step penalties (actions=1) + optional pytest reward.
        components = compute_reward(
            test_result=test_result,
            lint_result=None,
            diff_changed_lines=delta_diff_lines,
            actions_taken=1,
        )
        reward = float(components.total)

        # Dense edit feedback (py_compile): encourage edits that keep syntax valid.
        syntax_fresh = (
            self.state.last_syntax_result is not None
            and self.state.last_syntax_step == int(self.state.step) - 1
        )
        if syntax_fresh:
            if self.state.last_syntax_result.passed:
                # Positive for making a real, compiling edit (avoid rewarding no-ops).
                if bool(self.state.last_edit_changed):
                    reward += 1.0 if int(self.state.effective_edits) == 1 else 0.2
            else:
                reward -= 0.5

        # Reward improvement in tests when tests are run (dense delta signal).
        if tests_fresh:
            reward += 2.0 * float(self.state.last_tests_delta_passing)

        # Penalize ineffective write actions (no-op edits).
        try:
            at = ActionType(int(self.state.last_action_type))
        except Exception:
            at = None
        if (
            at in (ActionType.WRITE_FILE, ActionType.WRITE_FOCUS, ActionType.REPLACE_FOCUS)
            and bool(self.state.last_action_success)
            and (not bool(self.state.last_edit_changed))
        ):
            reward -= 0.05

        return reward

    def close(self):
        """Clean up resources."""
        if self.state is not None and self.state.test_process is not None:
            try:
                self.state.test_process.kill()
                self.state.test_process.communicate(timeout=1)
            except Exception:
                pass
            self.state.test_process = None
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None

    def __del__(self):
        self.close()


# =============================================================================
# Vectorized Environment for Parallel Training
# =============================================================================

class VectorizedJarvisEnv:
    """
    Vectorized version of JarvisHarnessEnv for parallel training.

    Maintains multiple environment instances and provides batched interface.
    """

    def __init__(
        self,
        num_envs: int,
        config: HarnessConfig = None,
        *,
        parallel: bool = True,
        max_workers: Optional[int] = None,
    ):
        self.num_envs = num_envs
        self.config = config or HarnessConfig()
        self.envs = [JarvisHarnessEnv(self.config) for _ in range(num_envs)]
        self._executor: Optional[ThreadPoolExecutor] = None
        if parallel and num_envs > 1:
            cpu_workers = max(1, int(os.cpu_count() or 1))
            workers = int(max_workers) if max_workers is not None else min(cpu_workers, num_envs)
            self._executor = ThreadPoolExecutor(max_workers=workers)

    @property
    def observation_space_dim(self) -> int:
        return self.config.obs_bytes

    @property
    def action_space_dim(self) -> int:
        return self.config.action_bytes

    def set_tasks(self, tasks: List[Task]):
        """Set tasks for each environment."""
        for i, env in enumerate(self.envs):
            env.set_task(tasks[i % len(tasks)])

    def reset(self, tasks: Optional[List[Task]] = None) -> torch.Tensor:
        """
        Reset all environments.

        Returns:
            observations: [num_envs, obs_bytes]
        """
        if tasks:
            self.set_tasks(tasks)

        if self._executor is not None:
            futures = [self._executor.submit(env.reset) for env in self.envs]
            obs_list = [f.result() for f in futures]
        else:
            obs_list = [env.reset() for env in self.envs]
        return torch.stack(obs_list)

    def step(self, actions: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, List[Dict]]:
        """
        Step all environments.

        Args:
            actions: [num_envs, action_bytes]

        Returns:
            observations: [num_envs, obs_bytes]
            rewards: [num_envs]
            dones: [num_envs] (bool)
            infos: List of info dicts
        """
        # Environment stepping is CPU-bound; ensure action bytes are on CPU to avoid per-env GPU sync.
        if isinstance(actions, torch.Tensor):
            actions_cpu = actions.detach().to(torch.uint8).cpu()
        else:
            actions_cpu = torch.tensor(actions, dtype=torch.uint8)

        obs_list: List[torch.Tensor] = [torch.zeros(self.config.obs_bytes, dtype=torch.uint8)] * self.num_envs
        reward_list: List[float] = [0.0] * self.num_envs
        done_list: List[bool] = [False] * self.num_envs
        info_list: List[Dict[str, Any]] = [{}] * self.num_envs

        if self._executor is not None:
            futures = [
                self._executor.submit(env.step, actions_cpu[i])
                for i, env in enumerate(self.envs)
            ]
            results = [f.result() for f in futures]
            for i, (obs, reward, done, info) in enumerate(results):
                obs_list[i] = obs
                reward_list[i] = float(reward)
                done_list[i] = bool(done)
                info_list[i] = info
        else:
            for i, env in enumerate(self.envs):
                obs, reward, done, info = env.step(actions_cpu[i])
                obs_list[i] = obs
                reward_list[i] = float(reward)
                done_list[i] = bool(done)
                info_list[i] = info

        # Auto-reset on done (reset is expensive; keep it out of the parallel critical path)
        for i, done in enumerate(done_list):
            if done:
                obs_list[i] = self.envs[i].reset()

        return (
            torch.stack(obs_list),
            torch.tensor(reward_list, dtype=torch.float32),
            torch.tensor(done_list, dtype=torch.bool),
            info_list,
        )

    def close(self):
        """Close all environments."""
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=False)
            self._executor = None
        for env in self.envs:
            env.close()
