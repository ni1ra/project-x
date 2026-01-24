"""
Real Codebase Source for JARVIS Training (Phase 9)

Loads actual GitHub repositories for training, replacing synthetic templates.
This is the bridge from toy bugs to real-world debugging capability.

Design:
1. Curated Repo Index - list of compatible repos (pytest, small, pure Python)
2. Clone/Cache Manager - handles fetching and caching repos
3. Task Generator - applies bug injection to real code

The key insight: we use the SAME bug injectors as synthetic, just on real code.
This maintains curriculum continuity while expanding to real codebases.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import shutil
import hashlib
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random

from src.harness.bug_templates import BugDifficulty, BugCategory, BugTemplate, BugInstance
from src.harness.repo_generator import (
    RepoFile, GeneratedRepo,
    inject_wrong_operator, inject_off_by_one, inject_wrong_return,
    inject_case_transform, inject_missing_colon, inject_missing_paren,
    inject_wrong_quote, inject_typo_keyword,
    _compute_bug_line,
)


# =============================================================================
# Curated Repo Index
# =============================================================================

@dataclass
class RepoEntry:
    """Entry in the curated repo index."""
    name: str                  # e.g., "psf/requests" or local name
    url: str                   # Git clone URL or local path
    commit: str                # Specific commit hash (all tests pass here)
    test_cmd: str = "pytest"   # Command to run tests
    test_files: List[str] = field(default_factory=list)  # Specific test files (optional)
    source_dirs: List[str] = field(default_factory=lambda: ["src", "."])  # Where to find source
    exclude_patterns: List[str] = field(default_factory=list)  # Files to exclude
    max_file_size: int = 5000  # Max lines per file (larger = harder)
    difficulty_tier: str = "easy"  # easy, medium, hard
    tags: List[str] = field(default_factory=list)  # e.g., ["web", "cli", "data"]

    def __hash__(self):
        return hash((self.name, self.commit))


# Initial curated repos - small, well-tested Python projects
# Requirements:
# 1. pytest test suite
# 2. All tests pass at specified commit
# 3. <1000 LOC source (for focus window)
# 4. Pure Python (no native extensions)
# 5. Clear, readable code

CURATED_REPOS: List[RepoEntry] = [
    # Tier 1: Tiny libs (< 200 LOC, simple logic)
    RepoEntry(
        name="mini-calc",
        url="local:fixtures/real_repos/mini_calc",  # We'll create these
        commit="HEAD",
        test_cmd="pytest",
        source_dirs=["."],
        difficulty_tier="easy",
        tags=["math", "utility"],
    ),
    RepoEntry(
        name="string-utils",
        url="local:fixtures/real_repos/string_utils",
        commit="HEAD",
        test_cmd="pytest",
        source_dirs=["."],
        difficulty_tier="easy",
        tags=["string", "utility"],
    ),
    RepoEntry(
        name="data-validator",
        url="local:fixtures/real_repos/data_validator",
        commit="HEAD",
        test_cmd="pytest",
        source_dirs=["."],
        difficulty_tier="easy",
        tags=["validation", "data"],
    ),

    # Tier 2: Small projects (200-500 LOC, multi-file)
    RepoEntry(
        name="task-queue",
        url="local:fixtures/real_repos/task_queue",
        commit="HEAD",
        test_cmd="pytest",
        source_dirs=["."],
        difficulty_tier="medium",
        tags=["async", "queue"],
    ),
    RepoEntry(
        name="config-manager",
        url="local:fixtures/real_repos/config_manager",
        commit="HEAD",
        test_cmd="pytest",
        source_dirs=["."],
        difficulty_tier="medium",
        tags=["config", "utility"],
    ),

    # Tier 3: Medium projects (500-1000 LOC, complex logic)
    RepoEntry(
        name="http-client",
        url="local:fixtures/real_repos/http_client",
        commit="HEAD",
        test_cmd="pytest",
        source_dirs=["."],
        difficulty_tier="hard",
        tags=["http", "network"],
    ),
]


def get_repos_by_difficulty(difficulty: BugDifficulty) -> List[RepoEntry]:
    """Get repos appropriate for a difficulty level."""
    tier_map = {
        BugDifficulty.TRIVIAL: ["easy"],
        BugDifficulty.EASY: ["easy", "medium"],
        BugDifficulty.MEDIUM: ["easy", "medium"],
        BugDifficulty.HARD: ["easy", "medium", "hard"],
    }
    tiers = tier_map.get(difficulty, ["easy"])
    return [r for r in CURATED_REPOS if r.difficulty_tier in tiers]


# =============================================================================
# Repo Clone/Cache Manager
# =============================================================================

@dataclass
class CachedRepo:
    """A cloned and cached repository."""
    entry: RepoEntry
    local_path: Path
    files: Dict[str, str]  # path -> content
    test_results: Optional[Tuple[bool, str]] = None  # (passed, output)


class RepoCache:
    """Manages cloning and caching of repositories."""

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "fixtures", "real_repos_cache"
            )
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._loaded: Dict[str, CachedRepo] = {}

    def get_cache_path(self, entry: RepoEntry) -> Path:
        """Get the local cache path for a repo."""
        # Hash the URL + commit for unique cache key
        key = hashlib.md5(f"{entry.url}:{entry.commit}".encode()).hexdigest()[:12]
        return self.cache_dir / f"{entry.name}_{key}"

    def load_repo(self, entry: RepoEntry) -> Optional[CachedRepo]:
        """Load a repo, cloning if necessary."""
        cache_key = f"{entry.name}:{entry.commit}"
        if cache_key in self._loaded:
            return self._loaded[cache_key]

        # Check for local: prefix (fixtures we create)
        if entry.url.startswith("local:"):
            local_path = Path(os.path.dirname(__file__)) / ".." / ".." / entry.url[6:]
            if not local_path.exists():
                return None
            return self._load_local_repo(entry, local_path)

        # TODO: Implement git cloning for remote repos
        # For now, we only support local fixtures
        return None

    def _load_local_repo(self, entry: RepoEntry, local_path: Path) -> CachedRepo:
        """Load a local repository."""
        files = {}

        for source_dir in entry.source_dirs:
            dir_path = local_path / source_dir if source_dir != "." else local_path
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                # Skip excluded patterns
                rel_path = py_file.relative_to(local_path)
                if any(pattern in str(rel_path) for pattern in entry.exclude_patterns):
                    continue

                # Skip __pycache__ and similar
                if "__pycache__" in str(rel_path) or ".pyc" in str(rel_path):
                    continue

                try:
                    content = py_file.read_text(encoding='utf-8')
                    # Skip files that are too large
                    if content.count('\n') > entry.max_file_size:
                        continue
                    files[str(rel_path)] = content
                except Exception:
                    continue

        cached = CachedRepo(
            entry=entry,
            local_path=local_path,
            files=files,
        )
        self._loaded[f"{entry.name}:{entry.commit}"] = cached
        return cached

    def verify_tests(self, cached: CachedRepo) -> Tuple[bool, str]:
        """Run tests to verify the repo is in a clean state."""
        if cached.test_results is not None:
            return cached.test_results

        try:
            result = subprocess.run(
                cached.entry.test_cmd.split(),
                cwd=cached.local_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            passed = result.returncode == 0
            output = result.stdout + result.stderr
            cached.test_results = (passed, output)
            return (passed, output)
        except Exception as e:
            cached.test_results = (False, str(e))
            return (False, str(e))


# =============================================================================
# Real Repo Task Generator
# =============================================================================

def inject_bug_into_real_code(
    files: Dict[str, str],
    difficulty: BugDifficulty,
    seed: int = None,
) -> Optional[Tuple[Dict[str, str], BugInstance]]:
    """
    Inject a bug into real code using our standard injectors.

    Args:
        files: Dict of path -> content for all source files
        difficulty: Target difficulty level
        seed: Random seed

    Returns:
        (buggy_files, bug_instance) or None if injection failed
    """
    if seed is not None:
        random.seed(seed)

    # Select non-test files
    candidates = [
        (p, c) for p, c in files.items()
        if not p.startswith("test_") and "conftest" not in p
        and not p.startswith("tests/")
    ]

    if not candidates:
        return None

    # Select injectors based on difficulty
    # NOTE: For real repos, we EXCLUDE typo bugs (inject_typo_keyword) because:
    # - Typos like 'retrun' cause Python syntax errors at import time
    # - Pytest can't collect tests when imports fail
    # - This breaks the "test-failure-based" training feedback loop
    # - Typo bugs require error-message-based fixing (different training approach)
    if difficulty == BugDifficulty.TRIVIAL:
        injectors = [inject_missing_colon, inject_missing_paren, inject_wrong_quote]
    elif difficulty == BugDifficulty.EASY:
        # Real repos: only logic bugs that don't break imports
        injectors = [inject_wrong_operator, inject_off_by_one]
    elif difficulty == BugDifficulty.MEDIUM:
        injectors = [inject_wrong_operator, inject_off_by_one, inject_wrong_return]
    else:  # HARD
        injectors = [inject_wrong_return, inject_case_transform, inject_off_by_one]

    random.shuffle(candidates)
    random.shuffle(injectors)

    # Try to inject a bug
    for path, content in candidates:
        for injector in injectors:
            buggy, hint, fix_desc = injector(content)
            if buggy != content:
                # Success! Create bug instance
                buggy_files = dict(files)
                buggy_files[path] = buggy

                template = BugTemplate(
                    name=f"real:{injector.__name__}",
                    category=BugCategory.LOGIC if difficulty != BugDifficulty.TRIVIAL else BugCategory.SYNTAX,
                    difficulty=difficulty,
                    description=hint,
                    files_affected=[path],
                )

                bug_line = _compute_bug_line(content, buggy)

                bug_instance = BugInstance(
                    template=template,
                    file_path=path,
                    original_code=content,
                    buggy_code=buggy,
                    fix_code=content,
                    line_number=bug_line,
                    hint=hint,
                )

                return buggy_files, bug_instance

    return None


def generate_real_repo_task(
    repo_cache: RepoCache,
    difficulty: BugDifficulty = BugDifficulty.EASY,
    seed: int = None,
) -> Optional[GeneratedRepo]:
    """
    Generate a task from a real repository.

    This creates a GeneratedRepo compatible with the existing training pipeline,
    but sourced from real code instead of templates.

    Args:
        repo_cache: Repo cache instance
        difficulty: Target difficulty
        seed: Random seed

    Returns:
        GeneratedRepo instance or None if generation failed
    """
    if seed is not None:
        random.seed(seed)

    # Get appropriate repos for difficulty
    eligible = get_repos_by_difficulty(difficulty)
    if not eligible:
        return None

    random.shuffle(eligible)

    # Try repos until we find one that works
    for entry in eligible:
        cached = repo_cache.load_repo(entry)
        if cached is None or not cached.files:
            continue

        # Try to inject a bug
        result = inject_bug_into_real_code(cached.files, difficulty, seed)
        if result is None:
            continue

        buggy_files, bug_instance = result

        # Build file objects
        file_objs = {}
        for path, content in buggy_files.items():
            file_objs[path] = RepoFile(
                path=path,
                content=content,
                is_test=path.startswith("test_") or "conftest" in path,
            )

        return GeneratedRepo(
            name=f"real_{entry.name}_{random.randint(1000, 9999)}",
            files=file_objs,
            bugs=[bug_instance],
            difficulty=difficulty,
            multi_file=len([f for f in file_objs if not file_objs[f].is_test]) > 1,
            original_files=cached.files,
            fix_description=bug_instance.hint or "",
        )

    return None


def generate_real_task_batch(
    num_tasks: int,
    difficulty_range: Tuple[BugDifficulty, BugDifficulty] = (
        BugDifficulty.EASY, BugDifficulty.HARD
    ),
    seed: int = None,
    repo_cache: RepoCache = None,
) -> List[GeneratedRepo]:
    """
    Generate a batch of tasks from real repositories.

    Args:
        num_tasks: Number of tasks to generate
        difficulty_range: Range of difficulties to sample
        seed: Random seed
        repo_cache: Optional repo cache (creates new if None)

    Returns:
        List of GeneratedRepo tasks
    """
    if seed is not None:
        random.seed(seed)

    if repo_cache is None:
        repo_cache = RepoCache()

    difficulties = list(BugDifficulty)
    valid_difficulties = [
        d for d in difficulties
        if difficulty_range[0].value <= d.value <= difficulty_range[1].value
    ]

    tasks = []
    attempts = 0
    max_attempts = num_tasks * 5  # Allow some failures

    while len(tasks) < num_tasks and attempts < max_attempts:
        attempts += 1
        difficulty = random.choice(valid_difficulties)
        task_seed = seed + attempts if seed is not None else None

        task = generate_real_repo_task(repo_cache, difficulty, task_seed)
        if task is not None:
            tasks.append(task)

    return tasks


# =============================================================================
# Mixed Dataset Generator (Synthetic + Real)
# =============================================================================

def generate_mixed_task_batch(
    num_tasks: int,
    real_ratio: float = 0.3,
    difficulty_range: Tuple[BugDifficulty, BugDifficulty] = (
        BugDifficulty.EASY, BugDifficulty.HARD
    ),
    seed: int = None,
) -> List[GeneratedRepo]:
    """
    Generate a mixed batch of synthetic and real tasks.

    This is the main entry point for Phase 9 training data.
    Curriculum: Start with mostly synthetic, gradually increase real ratio.

    Args:
        num_tasks: Total number of tasks
        real_ratio: Fraction of real tasks (0.0 to 1.0)
        difficulty_range: Range of difficulties
        seed: Random seed

    Returns:
        List of GeneratedRepo tasks (mixed)
    """
    from src.harness.repo_generator import generate_task_batch as generate_synthetic

    if seed is not None:
        random.seed(seed)

    num_real = int(num_tasks * real_ratio)
    num_synthetic = num_tasks - num_real

    # Generate synthetic tasks
    synthetic_tasks = generate_synthetic(
        num_tasks=num_synthetic,
        difficulty_range=difficulty_range,
        seed=seed,
    )

    # Generate real tasks
    real_tasks = generate_real_task_batch(
        num_tasks=num_real,
        difficulty_range=difficulty_range,
        seed=seed + 10000 if seed else None,
    )

    # Combine and shuffle
    all_tasks = synthetic_tasks + real_tasks
    random.shuffle(all_tasks)

    return all_tasks


# =============================================================================
# Real Repo Fixture Creator
# =============================================================================

def create_mini_calc_fixture(base_path: Path) -> None:
    """Create the mini-calc fixture repo."""
    repo_path = base_path / "mini_calc"
    repo_path.mkdir(parents=True, exist_ok=True)

    # Main source
    (repo_path / "calculator.py").write_text('''"""Simple calculator module."""


def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def divide(a: float, b: float) -> float:
    """Divide a by b. Raises ValueError if b is zero."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def power(base: float, exponent: int) -> float:
    """Raise base to exponent power."""
    if exponent < 0:
        return 1 / power(base, -exponent)
    result = 1.0
    for _ in range(exponent):
        result *= base
    return result


def factorial(n: int) -> int:
    """Calculate n factorial. Raises ValueError for negative n."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def is_even(n: int) -> bool:
    """Check if n is even."""
    return n % 2 == 0


def is_prime(n: int) -> bool:
    """Check if n is prime."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0:
            return False
    return True
''')

    # Tests
    (repo_path / "test_calculator.py").write_text('''"""Tests for calculator module."""
import pytest
from calculator import (
    add, subtract, multiply, divide, power,
    factorial, is_even, is_prime
)


class TestBasicOperations:
    def test_add(self):
        assert add(2, 3) == 5
        assert add(-1, 1) == 0
        assert add(0.5, 0.5) == 1.0

    def test_subtract(self):
        assert subtract(5, 3) == 2
        assert subtract(3, 5) == -2

    def test_multiply(self):
        assert multiply(3, 4) == 12
        assert multiply(-2, 3) == -6

    def test_divide(self):
        assert divide(10, 2) == 5
        assert divide(7, 2) == 3.5

    def test_divide_by_zero(self):
        with pytest.raises(ValueError):
            divide(1, 0)


class TestPower:
    def test_positive_exponent(self):
        assert power(2, 3) == 8
        assert power(5, 0) == 1

    def test_negative_exponent(self):
        assert power(2, -1) == 0.5


class TestFactorial:
    def test_factorial(self):
        assert factorial(0) == 1
        assert factorial(1) == 1
        assert factorial(5) == 120

    def test_factorial_negative(self):
        with pytest.raises(ValueError):
            factorial(-1)


class TestPredicates:
    def test_is_even(self):
        assert is_even(0) == True
        assert is_even(2) == True
        assert is_even(3) == False

    def test_is_prime(self):
        assert is_prime(2) == True
        assert is_prime(3) == True
        assert is_prime(4) == False
        assert is_prime(17) == True
        assert is_prime(1) == False
''')

    # conftest
    (repo_path / "conftest.py").write_text('''"""Pytest configuration."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
''')


def create_string_utils_fixture(base_path: Path) -> None:
    """Create the string-utils fixture repo."""
    repo_path = base_path / "string_utils"
    repo_path.mkdir(parents=True, exist_ok=True)

    (repo_path / "strings.py").write_text('''"""String utility functions."""


def reverse(s: str) -> str:
    """Reverse a string."""
    return s[::-1]


def is_palindrome(s: str) -> bool:
    """Check if string is a palindrome (case-insensitive)."""
    cleaned = s.lower().replace(" ", "")
    return cleaned == cleaned[::-1]


def capitalize_words(s: str) -> str:
    """Capitalize first letter of each word."""
    return " ".join(word.capitalize() for word in s.split())


def count_vowels(s: str) -> int:
    """Count vowels in a string."""
    vowels = "aeiouAEIOU"
    return sum(1 for char in s if char in vowels)


def truncate(s: str, max_len: int, suffix: str = "...") -> str:
    """Truncate string to max_len, adding suffix if truncated."""
    if len(s) <= max_len:
        return s
    return s[:max_len - len(suffix)] + suffix


def snake_to_camel(s: str) -> str:
    """Convert snake_case to camelCase."""
    parts = s.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def camel_to_snake(s: str) -> str:
    """Convert camelCase to snake_case."""
    result = []
    for i, char in enumerate(s):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def remove_duplicates(s: str) -> str:
    """Remove duplicate characters, keeping first occurrence."""
    seen = set()
    result = []
    for char in s:
        if char not in seen:
            seen.add(char)
            result.append(char)
    return "".join(result)
''')

    (repo_path / "test_strings.py").write_text('''"""Tests for string utilities."""
import pytest
from strings import (
    reverse, is_palindrome, capitalize_words, count_vowels,
    truncate, snake_to_camel, camel_to_snake, remove_duplicates
)


def test_reverse():
    assert reverse("hello") == "olleh"
    assert reverse("") == ""
    assert reverse("a") == "a"


def test_is_palindrome():
    assert is_palindrome("radar") == True
    assert is_palindrome("hello") == False
    assert is_palindrome("A man a plan a canal Panama") == True


def test_capitalize_words():
    assert capitalize_words("hello world") == "Hello World"
    assert capitalize_words("HELLO") == "Hello"


def test_count_vowels():
    assert count_vowels("hello") == 2
    assert count_vowels("xyz") == 0
    assert count_vowels("AEIOU") == 5


def test_truncate():
    assert truncate("hello world", 8) == "hello..."
    assert truncate("hi", 10) == "hi"
    assert truncate("testing", 7) == "testing"


def test_snake_to_camel():
    assert snake_to_camel("hello_world") == "helloWorld"
    assert snake_to_camel("my_var_name") == "myVarName"
    assert snake_to_camel("single") == "single"


def test_camel_to_snake():
    assert camel_to_snake("helloWorld") == "hello_world"
    assert camel_to_snake("myVarName") == "my_var_name"


def test_remove_duplicates():
    assert remove_duplicates("hello") == "helo"
    assert remove_duplicates("aabbcc") == "abc"
''')

    (repo_path / "conftest.py").write_text('''"""Pytest configuration."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
''')


def create_data_validator_fixture(base_path: Path) -> None:
    """Create the data-validator fixture repo."""
    repo_path = base_path / "data_validator"
    repo_path.mkdir(parents=True, exist_ok=True)

    (repo_path / "validator.py").write_text(r'''"""Data validation utilities."""
import re
from typing import Any, Optional


def is_email(value: str) -> bool:
    """Check if value is a valid email address."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, value))


def is_phone(value: str) -> bool:
    """Check if value is a valid US phone number."""
    cleaned = re.sub(r"[^0-9]", "", value)
    return len(cleaned) == 10


def is_positive_int(value: Any) -> bool:
    """Check if value is a positive integer."""
    if not isinstance(value, int):
        return False
    return value > 0


def is_in_range(value: float, min_val: float, max_val: float) -> bool:
    """Check if value is within inclusive range."""
    return min_val <= value <= max_val


def is_non_empty_string(value: Any) -> bool:
    """Check if value is a non-empty string."""
    return isinstance(value, str) and len(value.strip()) > 0


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    Returns (is_valid, error_message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain lowercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain a digit"
    return True, ""


def sanitize_string(value: str, max_len: int = 255) -> str:
    """Sanitize string by stripping and truncating."""
    cleaned = value.strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    return cleaned


def parse_int(value: str, default: int = 0) -> int:
    """Parse string to int with default fallback."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
''')

    (repo_path / "test_validator.py").write_text('''"""Tests for validator module."""
import pytest
from validator import (
    is_email, is_phone, is_positive_int, is_in_range,
    is_non_empty_string, validate_password, sanitize_string, parse_int
)


class TestEmailValidation:
    def test_valid_emails(self):
        assert is_email("test@example.com") == True
        assert is_email("user.name@domain.org") == True

    def test_invalid_emails(self):
        assert is_email("not-an-email") == False
        assert is_email("missing@domain") == False
        assert is_email("@nodomain.com") == False


class TestPhoneValidation:
    def test_valid_phones(self):
        assert is_phone("1234567890") == True
        assert is_phone("123-456-7890") == True
        assert is_phone("(123) 456-7890") == True

    def test_invalid_phones(self):
        assert is_phone("123") == False
        assert is_phone("12345678901") == False


class TestNumericValidation:
    def test_positive_int(self):
        assert is_positive_int(1) == True
        assert is_positive_int(0) == False
        assert is_positive_int(-1) == False
        assert is_positive_int(1.5) == False

    def test_in_range(self):
        assert is_in_range(5, 1, 10) == True
        assert is_in_range(1, 1, 10) == True
        assert is_in_range(10, 1, 10) == True
        assert is_in_range(0, 1, 10) == False


class TestStringValidation:
    def test_non_empty_string(self):
        assert is_non_empty_string("hello") == True
        assert is_non_empty_string("  ") == False
        assert is_non_empty_string("") == False
        assert is_non_empty_string(123) == False


class TestPasswordValidation:
    def test_valid_password(self):
        valid, msg = validate_password("SecurePass1")
        assert valid == True
        assert msg == ""

    def test_short_password(self):
        valid, msg = validate_password("Short1")
        assert valid == False
        assert "8 characters" in msg

    def test_no_uppercase(self):
        valid, msg = validate_password("lowercase1")
        assert valid == False
        assert "uppercase" in msg


class TestUtilities:
    def test_sanitize_string(self):
        assert sanitize_string("  hello  ") == "hello"
        assert len(sanitize_string("x" * 300, max_len=100)) == 100

    def test_parse_int(self):
        assert parse_int("42") == 42
        assert parse_int("not-a-number") == 0
        assert parse_int("invalid", default=-1) == -1
''')

    (repo_path / "conftest.py").write_text('''"""Pytest configuration."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
''')


def setup_real_repo_fixtures(force: bool = False) -> Path:
    """
    Set up all real repo fixtures.

    Args:
        force: If True, recreate even if they exist

    Returns:
        Path to fixtures directory
    """
    base_path = Path(os.path.dirname(__file__)) / ".." / ".." / "fixtures" / "real_repos"

    if base_path.exists() and not force:
        # Check if all fixtures exist
        expected = ["mini_calc", "string_utils", "data_validator"]
        if all((base_path / name).exists() for name in expected):
            return base_path

    base_path.mkdir(parents=True, exist_ok=True)

    # Create fixtures
    create_mini_calc_fixture(base_path)
    create_string_utils_fixture(base_path)
    create_data_validator_fixture(base_path)

    return base_path


if __name__ == "__main__":
    # Test the real repo pipeline
    print("Setting up real repo fixtures...")
    fixtures_path = setup_real_repo_fixtures(force=True)
    print(f"Fixtures created at: {fixtures_path}")

    print("\nTesting repo cache...")
    cache = RepoCache()

    for entry in CURATED_REPOS[:3]:
        print(f"\nLoading {entry.name}...")
        cached = cache.load_repo(entry)
        if cached:
            print(f"  Files loaded: {len(cached.files)}")
            for path in list(cached.files.keys())[:3]:
                lines = cached.files[path].count('\n')
                print(f"    - {path}: {lines} lines")

    print("\nTesting bug injection...")
    for difficulty in [BugDifficulty.TRIVIAL, BugDifficulty.EASY, BugDifficulty.MEDIUM]:
        task = generate_real_repo_task(cache, difficulty, seed=42)
        if task:
            print(f"  {difficulty.name}: Generated {task.name} with {len(task.bugs)} bug(s)")
            if task.bugs:
                print(f"    Bug: {task.bugs[0].hint}")
        else:
            print(f"  {difficulty.name}: No task generated")

    print("\nTesting mixed batch generation...")
    mixed = generate_mixed_task_batch(
        num_tasks=10,
        real_ratio=0.5,
        seed=42,
    )
    real_count = sum(1 for t in mixed if t.name.startswith("real_"))
    print(f"  Generated {len(mixed)} tasks: {real_count} real, {len(mixed) - real_count} synthetic")
