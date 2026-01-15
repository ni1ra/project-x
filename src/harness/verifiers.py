"""
Jarvis Harness Verifiers

Hard verifiers for the tool-using agent:
- Tests pass/fail
- Lint pass/fail
- Program output matches spec
- Diffs are minimal (MDL-friendly)

Verifiers return GROUND TRUTH - no model-based scoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Optional, List
import subprocess
import tempfile
import os
import difflib


@dataclass
class VerifierResult:
    """Result from a verifier check."""
    passed: bool
    score: float           # [0, 1] - 1.0 = perfect
    details: str = ""      # Human-readable details
    tests_passing: int = 0
    tests_total: int = 0


def run_pytest(repo_path: str, timeout: int = 30, python_path: str = None) -> VerifierResult:
    """
    Run pytest in the repo and return results.

    Args:
        repo_path: Path to repository root
        timeout: Maximum seconds to wait
        python_path: Path to python executable (defaults to sys.executable)

    Returns:
        VerifierResult with test pass/fail status
    """
    import sys
    python_exe = python_path or sys.executable

    try:
        # Note: removed -x flag to get full test count
        result = subprocess.run(
            [python_exe, '-m', 'pytest', '-q', '--tb=no'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = result.stdout + result.stderr

        # Parse pytest output for pass/fail counts
        # Format: "X passed, Y failed" or "X passed"
        tests_passing = 0
        tests_total = 0

        if 'passed' in output:
            import re
            passed_match = re.search(r'(\d+) passed', output)
            if passed_match:
                tests_passing = int(passed_match.group(1))
                tests_total = tests_passing

            failed_match = re.search(r'(\d+) failed', output)
            if failed_match:
                tests_total += int(failed_match.group(1))

        passed = result.returncode == 0
        score = tests_passing / tests_total if tests_total > 0 else 0.0

        return VerifierResult(
            passed=passed,
            score=score,
            details=output[:500],  # Truncate for obs
            tests_passing=tests_passing,
            tests_total=tests_total,
        )

    except subprocess.TimeoutExpired:
        return VerifierResult(
            passed=False,
            score=0.0,
            details="TIMEOUT: Tests took too long",
        )
    except Exception as e:
        return VerifierResult(
            passed=False,
            score=0.0,
            details=f"ERROR: {str(e)[:200]}",
        )


def run_lint(repo_path: str, timeout: int = 15) -> VerifierResult:
    """
    Run basic Python lint check.

    Args:
        repo_path: Path to repository root
        timeout: Maximum seconds to wait

    Returns:
        VerifierResult with lint pass/fail status
    """
    try:
        # Use python -m py_compile for basic syntax check
        # Find all Python files
        py_files = []
        for root, _, files in os.walk(repo_path):
            for f in files:
                if f.endswith('.py'):
                    py_files.append(os.path.join(root, f))

        if not py_files:
            return VerifierResult(
                passed=True,
                score=1.0,
                details="No Python files to lint",
            )

        errors = []
        for py_file in py_files[:20]:  # Limit to first 20 files
            try:
                result = subprocess.run(
                    ['python', '-m', 'py_compile', py_file],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    errors.append(f"{py_file}: {result.stderr[:100]}")
            except Exception:
                pass

        passed = len(errors) == 0
        score = 1.0 - (len(errors) / len(py_files)) if py_files else 1.0

        return VerifierResult(
            passed=passed,
            score=score,
            details="\n".join(errors[:5]) if errors else "All files pass syntax check",
        )

    except Exception as e:
        return VerifierResult(
            passed=False,
            score=0.0,
            details=f"ERROR: {str(e)[:200]}",
        )


def verify_output_matches(
    actual: str,
    expected: str,
    exact: bool = False
) -> VerifierResult:
    """
    Verify program output matches expected.

    Args:
        actual: Actual program output
        expected: Expected output
        exact: If True, require exact match. Otherwise allow fuzzy.

    Returns:
        VerifierResult
    """
    actual = actual.strip()
    expected = expected.strip()

    if exact:
        passed = actual == expected
        score = 1.0 if passed else 0.0
    else:
        # Use sequence matcher for fuzzy comparison
        ratio = difflib.SequenceMatcher(None, actual, expected).ratio()
        passed = ratio > 0.9
        score = ratio

    return VerifierResult(
        passed=passed,
        score=score,
        details=f"Match ratio: {score:.2f}",
    )


def compute_diff_size(original: str, modified: str) -> Tuple[int, float]:
    """
    Compute diff size for MDL penalty.

    Returns:
        (num_changed_lines, compression_ratio)

    Where compression_ratio = 1 - (changed_lines / total_lines)
    """
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff = list(difflib.unified_diff(original_lines, modified_lines))
    changed_lines = sum(1 for line in diff if line.startswith('+') or line.startswith('-'))
    changed_lines = max(0, changed_lines - 2)  # Subtract header lines

    total_lines = max(len(original_lines), len(modified_lines), 1)
    compression_ratio = 1.0 - (changed_lines / total_lines)

    return changed_lines, compression_ratio


def verify_minimal_diff(
    original: str,
    modified: str,
    max_changed_lines: int = 10
) -> VerifierResult:
    """
    Verify the diff is minimal (MDL-friendly).

    Args:
        original: Original file content
        modified: Modified file content
        max_changed_lines: Maximum allowed changed lines

    Returns:
        VerifierResult
    """
    changed_lines, compression_ratio = compute_diff_size(original, modified)

    passed = changed_lines <= max_changed_lines
    score = compression_ratio

    return VerifierResult(
        passed=passed,
        score=score,
        details=f"Changed {changed_lines} lines (max {max_changed_lines}), compression: {compression_ratio:.2f}",
    )


def run_python_file(
    file_path: str,
    args: List[str] = None,
    timeout: int = 10
) -> Tuple[str, int]:
    """
    Run a Python file and return output.

    Returns:
        (output, return_code)
    """
    args = args or []

    try:
        result = subprocess.run(
            ['python', file_path] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout + result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", -1
    except Exception as e:
        return f"ERROR: {e}", -1


@dataclass
class RewardComponents:
    """Breakdown of reward for transparency."""
    test_reward: float = 0.0        # +1 per test that passes
    lint_reward: float = 0.0        # +0.5 if lint passes
    diff_penalty: float = 0.0       # -0.01 per changed line
    action_penalty: float = 0.0     # -0.01 per action
    success_bonus: float = 0.0      # +10 if all tests pass

    @property
    def total(self) -> float:
        return (
            self.test_reward +
            self.lint_reward +
            self.diff_penalty +
            self.action_penalty +
            self.success_bonus
        )


def compute_reward(
    test_result: VerifierResult,
    lint_result: Optional[VerifierResult],
    diff_changed_lines: int,
    actions_taken: int,
) -> RewardComponents:
    """
    Compute reward from verifier results.

    Args:
        test_result: Result from run_pytest
        lint_result: Result from run_lint (optional)
        diff_changed_lines: Number of lines changed
        actions_taken: Number of actions taken this episode

    Returns:
        RewardComponents with breakdown
    """
    components = RewardComponents()

    # Test reward: +1 per passing test
    components.test_reward = test_result.tests_passing

    # Lint reward: +0.5 if lint passes
    if lint_result and lint_result.passed:
        components.lint_reward = 0.5

    # Diff penalty: -0.01 per changed line (encourages minimal edits)
    components.diff_penalty = -0.01 * diff_changed_lines

    # Action penalty: -0.01 per action (encourages efficiency)
    components.action_penalty = -0.01 * actions_taken

    # Success bonus: +10 if all tests pass
    if test_result.passed and test_result.tests_total > 0:
        components.success_bonus = 10.0

    return components
