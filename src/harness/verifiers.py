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
    scope: str = "full"    # e.g. "full", "syntax", "lint"


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
            [python_exe, "-m", "pytest", "-q", "--tb=short"],
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
            scope="full",
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


def run_pytest_fast(
    repo_path: str,
    *,
    timeout: int = 20,
    python_path: str | None = None,
    maxfail: int = 1,
) -> VerifierResult:
    """
    Run a cheap pytest pass that stops after the first failure.

    This is intended for denser feedback during training; use full `run_pytest`
    for final verification / SUBMIT.
    """
    import sys

    python_exe = python_path or sys.executable
    maxfail = max(1, int(maxfail))

    try:
        result = subprocess.run(
            [python_exe, "-m", "pytest", "-q", "--tb=short", f"--maxfail={maxfail}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = result.stdout + result.stderr

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

        passed = result.returncode == 0
        score = tests_passing / tests_total if tests_total > 0 else 0.0

        return VerifierResult(
            passed=passed,
            score=score,
            details=output[:500],
            tests_passing=tests_passing,
            tests_total=tests_total,
            scope="fast",
        )
    except subprocess.TimeoutExpired:
        return VerifierResult(
            passed=False,
            score=0.0,
            details="TIMEOUT: fast pytest took too long",
            scope="fast",
        )
    except Exception as e:
        return VerifierResult(
            passed=False,
            score=0.0,
            details=f"ERROR: {str(e)[:200]}",
            scope="fast",
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
    import sys
    python_exe = sys.executable

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
                scope="lint",
            )

        errors = []
        for py_file in py_files[:20]:  # Limit to first 20 files
            try:
                result = subprocess.run(
                    [python_exe, '-m', 'py_compile', py_file],
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
            scope="lint",
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
        scope="output",
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
        scope="diff",
    )


def run_py_compile_file(
    repo_path: str,
    rel_path: str,
    *,
    timeout: int = 5,
    python_path: str | None = None,
) -> VerifierResult:
    """
    Run a cheap syntax-only verifier (python -m py_compile) on a single file.

    This is intended as a dense, low-cost signal compared to full pytest.
    """
    file_path = os.path.join(repo_path, rel_path)

    if not rel_path:
        return VerifierResult(passed=False, score=0.0, details="No file specified", scope="syntax")
    if not os.path.exists(file_path):
        return VerifierResult(passed=False, score=0.0, details=f"File not found: {rel_path}", scope="syntax")

    import py_compile

    try:
        # Avoid spawning a subprocess (major training bottleneck). Compile in-process
        # and write bytecode to a temporary location so we don't mutate the repo.
        with tempfile.NamedTemporaryFile(suffix=".pyc") as tmp:
            py_compile.compile(file_path, cfile=tmp.name, doraise=True)
        passed = True
        details = ""
        return VerifierResult(
            passed=passed,
            score=1.0,
            details=details[:500],
            scope="syntax",
        )
    except py_compile.PyCompileError as e:
        return VerifierResult(
            passed=False,
            score=0.0,
            details=str(e).strip()[:500],
            scope="syntax",
        )
    except Exception as e:
        return VerifierResult(passed=False, score=0.0, details=f"ERROR: {str(e)[:200]}", scope="syntax")


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
    import sys
    python_exe = sys.executable

    try:
        result = subprocess.run(
            [python_exe, file_path] + args,
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
    diff_penalty: float = 0.0       # -0.0001 per changed line
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

    # Test reward: Give reward for ALL scopes now that syntax reward is disabled.
    # Fast tests get same reward as full - the delta signal in env.py is the main driver.
    if test_result.tests_total > 0:
        pass_rate = test_result.tests_passing / test_result.tests_total
        components.test_reward = 2.0 * pass_rate  # All scopes get reward
    else:
        components.test_reward = 0.0

    # Lint reward: +0.5 if lint passes
    if lint_result and lint_result.passed:
        components.lint_reward = 0.5

    # Diff penalty: keep small early so the agent learns to write at all.
    # MDL pressure is still present, but not so strong that "never write" dominates.
    components.diff_penalty = -0.0001 * diff_changed_lines

    # Action penalty: -0.01 per action (encourages efficiency)
    components.action_penalty = -0.01 * actions_taken

    # Success bonus: +10 if the FULL suite passes.
    if test_result.passed and test_result.tests_total > 0 and test_result.scope == "full":
        components.success_bonus = 10.0

    return components
