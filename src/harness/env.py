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
import os
import shutil
import tempfile
import subprocess
import time

import torch

from src.harness.actions import (
    ActionType, JarvisAction, decode_action, encode_action,
    validate_shell_command, action_to_string, ACTION_BYTES
)
from src.harness.observations import (
    JarvisObservation, encode_observation, decode_observation,
    scan_directory, OBS_TOTAL_BYTES
)
from src.harness.verifiers import (
    run_pytest, run_lint, compute_diff_size, compute_reward,
    RewardComponents, VerifierResult
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
    last_test_result: Optional[VerifierResult] = None
    last_reward: float = 0.0
    done: bool = False
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

        # Track original file contents for diff computation
        self._original_files: Dict[str, str] = {}

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

        # Clean up previous temp directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Copy repo to temp directory
        self.temp_dir = tempfile.mkdtemp(prefix="jarvis_harness_")
        if os.path.exists(self.task.repo_path):
            # Copy contents, not the directory itself
            for item in os.listdir(self.task.repo_path):
                s = os.path.join(self.task.repo_path, item)
                d = os.path.join(self.temp_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)

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

        # Reset state
        self.state = HarnessState(
            step=0,
            energy_used=0.0,
            time_start=time.time(),
            actions_taken=0,
            terminal_buffer=f"Task: {self.task.description}\nRepo ready at {self.temp_dir}\n",
            file_changes={},
            last_test_result=None,
            last_reward=0.0,
            done=False,
        )

        # Initial test run to establish baseline
        self.state.last_test_result = run_pytest(self.temp_dir)
        self.state.initial_tests_passing = self.state.last_test_result.tests_passing
        self.state.terminal_buffer += f"Initial tests: {self.state.last_test_result.tests_passing}/{self.state.last_test_result.tests_total} passing\n"

        return self._get_observation()

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

        # Decode action
        action = decode_action(action_bytes)

        # Track action history for exploration bonus
        action_type = int(action.action_type)
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
        result, output = self._execute_action(action)

        # Update terminal buffer
        self.state.terminal_buffer += f"\n[Step {self.state.step}] {action_to_string(action)}\n"
        self.state.terminal_buffer += output[:500] + "\n"

        # Keep only last N characters of terminal
        if len(self.state.terminal_buffer) > 2000:
            self.state.terminal_buffer = self.state.terminal_buffer[-2000:]

        # Update state
        self.state.step += 1
        self.state.actions_taken += 1

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

        # Explicit submit
        if action.action_type == ActionType.SUBMIT:
            done = True
            reason = "submitted"

        # Compute reward
        reward = self._compute_reward()
        self.state.last_reward = reward

        if done:
            self.state.done = True

        # Build info dict
        info = {
            "step": self.state.step,
            "action": action_to_string(action),
            "energy_used": self.state.energy_used,
            "time_elapsed": elapsed,
            "done_reason": reason if done else "",
            "tests_passing": self.state.last_test_result.tests_passing if self.state.last_test_result else 0,
            "tests_total": self.state.last_test_result.tests_total if self.state.last_test_result else 0,
        }

        return self._get_observation(), reward, done, info

    def _get_observation(self) -> torch.Tensor:
        """Build observation tensor from current state."""
        fs_snapshot = scan_directory(self.temp_dir, max_files=7) if self.temp_dir else {}

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
                chunk = content[action.offset:action.offset + action.length]
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

                # Write file
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, 'w') as f:
                    f.write(new_content)

                # Update tracked changes
                orig, _ = self.state.file_changes[rel_path]
                self.state.file_changes[rel_path] = (orig, new_content)

                return True, f"Wrote {len(action.content)} bytes to {target_path}"
            except Exception as e:
                return False, f"Write error: {e}"

        elif action.action_type == ActionType.RUN_TESTS:
            self.state.last_test_result = run_pytest(self.temp_dir)
            return True, self.state.last_test_result.details

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
            # Run final tests
            self.state.last_test_result = run_pytest(self.temp_dir)
            return True, f"Submitted. Final tests: {self.state.last_test_result.tests_passing}/{self.state.last_test_result.tests_total}"

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
            return self._navigate(action.target)

        elif action.action_type == ActionType.STACKTRACE:
            return self._parse_stacktrace()

        return False, f"Unknown action type: {action.action_type}"

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

    def _navigate(self, target: str) -> Tuple[bool, str]:
        """Navigate to (focus on) a different file."""
        if not target:
            return False, "No target file specified"

        fpath = os.path.join(self.temp_dir, target)
        if not os.path.exists(fpath):
            return False, f"File not found: {target}"

        # Read first part of file to show context
        try:
            with open(fpath, 'r') as f:
                content = f.read(500)
            return True, f"Navigated to {target}:\n{content}"
        except Exception as e:
            return False, f"Navigate error: {e}"

    def _parse_stacktrace(self) -> Tuple[bool, str]:
        """Parse last test output for stacktrace info."""
        if not self.state.last_test_result:
            return False, "No test result available"

        details = self.state.last_test_result.details
        # Extract file:line references from traceback
        import re
        pattern = r'File "([^"]+)", line (\d+)'
        matches = re.findall(pattern, details)

        if not matches:
            return True, "No stacktrace found in last output"

        # Format results
        results = []
        for fpath, line in matches[-5:]:  # Last 5 stack frames
            # Make path relative to temp_dir
            if self.temp_dir and fpath.startswith(self.temp_dir):
                fpath = os.path.relpath(fpath, self.temp_dir)
            results.append(f"{fpath}:{line}")

        return True, "Stacktrace:\n" + "\n".join(results)

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

        elif action.action_type == ActionType.WRITE_FILE:
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
        """Compute reward for current step with exploration bonuses."""
        # Get test result
        test_result = self.state.last_test_result or VerifierResult(passed=False, score=0)

        # Get lint result (optional, skip for now to save time)
        lint_result = None

        # Compute total diff lines
        total_diff_lines = 0
        for rel_path, (orig, current) in self.state.file_changes.items():
            changed, _ = compute_diff_size(orig, current)
            total_diff_lines += changed

        # Compute base reward components
        components = compute_reward(
            test_result=test_result,
            lint_result=lint_result,
            diff_changed_lines=total_diff_lines,
            actions_taken=self.state.actions_taken,
        )

        base_reward = components.total

        # === EXPLORATION BONUSES ===

        # 1. Repetition penalty: punish doing the same action repeatedly
        # -0.5 per consecutive repeat after the first
        repetition_penalty = 0.0
        if self.state.consecutive_same_action > 1:
            repetition_penalty = -0.5 * (self.state.consecutive_same_action - 1)

        # 2. Diversity bonus: reward for trying different actions
        # +0.2 for each unique action type in recent history
        unique_actions = len(set(self.state.action_history))
        diversity_bonus = 0.2 * unique_actions

        # 3. Progress bonus: extra reward for IMPROVING test count
        # +2.0 per test improved over baseline
        progress_bonus = 0.0
        current_passing = test_result.tests_passing
        if current_passing > self.state.initial_tests_passing:
            progress_bonus = 2.0 * (current_passing - self.state.initial_tests_passing)

        # Total reward
        total_reward = base_reward + repetition_penalty + diversity_bonus + progress_bonus

        return total_reward

    def close(self):
        """Clean up resources."""
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

    def __init__(self, num_envs: int, config: HarnessConfig = None):
        self.num_envs = num_envs
        self.config = config or HarnessConfig()
        self.envs = [JarvisHarnessEnv(self.config) for _ in range(num_envs)]

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
        obs_list = []
        reward_list = []
        done_list = []
        info_list = []

        for i, env in enumerate(self.envs):
            obs, reward, done, info = env.step(actions[i])
            obs_list.append(obs)
            reward_list.append(reward)
            done_list.append(done)
            info_list.append(info)

            # Auto-reset on done
            if done:
                obs_list[-1] = env.reset()

        return (
            torch.stack(obs_list),
            torch.tensor(reward_list, dtype=torch.float32),
            torch.tensor(done_list, dtype=torch.bool),
            info_list,
        )

    def close(self):
        """Close all environments."""
        for env in self.envs:
            env.close()
