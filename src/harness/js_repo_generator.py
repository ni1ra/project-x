"""
JavaScript Repository Generator for JARVIS Harness

Phase 12: Extended Tool Diversity - Generates simple JS repos with injectable bugs
for training/evaluation of npm-based workflows.

Similar to repo_generator.py but for JavaScript projects with Jest tests.
"""

from __future__ import annotations

import os
import json
import tempfile
import shutil
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, List
import random


class JSBugType(Enum):
    """Types of bugs that can be injected into JS code."""
    WRONG_OPERATOR = "wrong_operator"       # > vs >=, === vs ==
    OFF_BY_ONE = "off_by_one"               # array[i] vs array[i-1]
    WRONG_LITERAL = "wrong_literal"         # null vs undefined, true vs false
    TYPO = "typo"                           # cosnt, fucntion


@dataclass
class JSBugInfo:
    """Information about an injected bug."""
    bug_type: JSBugType
    line: int
    column: int
    original: str
    buggy: str
    fix_token: str  # The token needed to fix the bug


@dataclass
class JSRepo:
    """A generated JS repository with test suite."""
    name: str
    root_path: str
    source_file: str      # Relative path, e.g., "src/utils.js"
    test_file: str        # Relative path, e.g., "test/utils.test.js"
    original_code: str
    buggy_code: str
    bug_info: JSBugInfo
    package_json: str
    tests_total: int
    tests_passing_with_bug: int


# ============================================================================
# JS Code Templates
# ============================================================================

# Template 1: Array utilities
ARRAY_UTILS_TEMPLATE = '''/**
 * Array utility functions
 */

/**
 * Check if array contains a value greater than threshold
 * @param {number[]} arr - Array of numbers
 * @param {number} threshold - Threshold value
 * @returns {boolean} True if any value exceeds threshold
 */
function hasValueAbove(arr, threshold) {
    for (let i = 0; i < arr.length; i++) {
        if (arr[i] {op} threshold) {
            return true;
        }
    }
    return false;
}

/**
 * Sum all values in array
 * @param {number[]} arr - Array of numbers
 * @returns {number} Sum of all values
 */
function sumArray(arr) {
    let sum = 0;
    for (let i = 0; i < arr.length; i++) {
        sum += arr[i];
    }
    return sum;
}

module.exports = { hasValueAbove, sumArray };
'''

ARRAY_UTILS_TEST = '''const { hasValueAbove, sumArray } = require('../src/utils');

describe('hasValueAbove', () => {
    test('returns true when value exceeds threshold', () => {
        expect(hasValueAbove([1, 2, 5], 4)).toBe(true);
    });

    test('returns false when no value exceeds threshold', () => {
        expect(hasValueAbove([1, 2, 3], 5)).toBe(false);
    });

    test('returns false for equal values (not strictly greater)', () => {
        expect(hasValueAbove([1, 2, 3], 3)).toBe(false);
    });

    test('handles empty array', () => {
        expect(hasValueAbove([], 0)).toBe(false);
    });
});

describe('sumArray', () => {
    test('sums positive numbers', () => {
        expect(sumArray([1, 2, 3])).toBe(6);
    });

    test('handles empty array', () => {
        expect(sumArray([])).toBe(0);
    });
});
'''

# Template 2: String utilities
STRING_UTILS_TEMPLATE = '''/**
 * String utility functions
 */

/**
 * Check if string length is within limit
 * @param {string} str - Input string
 * @param {number} limit - Maximum length
 * @returns {boolean} True if string length is at or below limit
 */
function isWithinLimit(str, limit) {
    return str.length {op} limit;
}

/**
 * Truncate string to specified length
 * @param {string} str - Input string
 * @param {number} maxLen - Maximum length
 * @returns {string} Truncated string
 */
function truncate(str, maxLen) {
    if (str.length <= maxLen) {
        return str;
    }
    return str.slice(0, maxLen);
}

module.exports = { isWithinLimit, truncate };
'''

STRING_UTILS_TEST = '''const { isWithinLimit, truncate } = require('../src/utils');

describe('isWithinLimit', () => {
    test('returns true when string is shorter than limit', () => {
        expect(isWithinLimit('hello', 10)).toBe(true);
    });

    test('returns true when string equals limit', () => {
        expect(isWithinLimit('hello', 5)).toBe(true);
    });

    test('returns false when string exceeds limit', () => {
        expect(isWithinLimit('hello world', 5)).toBe(false);
    });

    test('handles empty string', () => {
        expect(isWithinLimit('', 0)).toBe(true);
    });
});

describe('truncate', () => {
    test('truncates long strings', () => {
        expect(truncate('hello world', 5)).toBe('hello');
    });

    test('returns original if within limit', () => {
        expect(truncate('hi', 10)).toBe('hi');
    });
});
'''

# Package.json template
PACKAGE_JSON_TEMPLATE = '''{
  "name": "{name}",
  "version": "1.0.0",
  "description": "Generated JS repo for JARVIS training",
  "main": "src/utils.js",
  "scripts": {
    "test": "jest --json --outputFile=test-results.json"
  },
  "devDependencies": {
    "jest": "^29.0.0"
  }
}
'''

# Jest config (minimal)
JEST_CONFIG = '''module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/test/**/*.test.js'],
};
'''


# ============================================================================
# Bug Injection
# ============================================================================

def inject_wrong_operator_bug(code: str, template_type: str) -> Tuple[str, JSBugInfo]:
    """Inject a wrong operator bug."""
    if template_type == "array_utils":
        # Change > to >= (bug: returns true for equal values)
        buggy = code.replace("arr[i] > threshold", "arr[i] >= threshold")
        bug_info = JSBugInfo(
            bug_type=JSBugType.WRONG_OPERATOR,
            line=13,  # Approximate line number
            column=16,
            original=">",
            buggy=">=",
            fix_token=">",
        )
    else:  # string_utils
        # Change <= to < (bug: false when exactly at limit)
        buggy = code.replace("str.length <= limit", "str.length < limit")
        bug_info = JSBugInfo(
            bug_type=JSBugType.WRONG_OPERATOR,
            line=11,
            column=21,
            original="<=",
            buggy="<",
            fix_token="<=",
        )
    return buggy, bug_info


def inject_off_by_one_bug(code: str, template_type: str) -> Tuple[str, JSBugInfo]:
    """Inject an off-by-one bug."""
    if template_type == "array_utils":
        # Change i < arr.length to i <= arr.length (array bounds error)
        buggy = code.replace("i < arr.length", "i <= arr.length")
        bug_info = JSBugInfo(
            bug_type=JSBugType.OFF_BY_ONE,
            line=12,
            column=19,
            original="<",
            buggy="<=",
            fix_token="<",
        )
    else:
        # Change <= to < in truncate check
        buggy = code.replace("str.length <= maxLen", "str.length < maxLen")
        bug_info = JSBugInfo(
            bug_type=JSBugType.OFF_BY_ONE,
            line=21,
            column=17,
            original="<=",
            buggy="<",
            fix_token="<=",
        )
    return buggy, bug_info


# ============================================================================
# Repository Generation
# ============================================================================

def generate_js_repo(
    bug_type: JSBugType = JSBugType.WRONG_OPERATOR,
    template_type: str = "array_utils",
    seed: Optional[int] = None,
) -> JSRepo:
    """Generate a JS repository with an injected bug.

    Args:
        bug_type: Type of bug to inject
        template_type: "array_utils" or "string_utils"
        seed: Random seed for reproducibility

    Returns:
        JSRepo with buggy code ready for training/eval
    """
    if seed is not None:
        random.seed(seed)

    # Select template
    if template_type == "array_utils":
        original_code = ARRAY_UTILS_TEMPLATE.format(op=">")
        test_code = ARRAY_UTILS_TEST
        tests_total = 6
    else:
        original_code = STRING_UTILS_TEMPLATE.format(op="<=")
        test_code = STRING_UTILS_TEST
        tests_total = 6

    # Inject bug
    if bug_type == JSBugType.WRONG_OPERATOR:
        buggy_code, bug_info = inject_wrong_operator_bug(original_code, template_type)
        tests_passing = tests_total - 1  # One test should fail
    elif bug_type == JSBugType.OFF_BY_ONE:
        buggy_code, bug_info = inject_off_by_one_bug(original_code, template_type)
        tests_passing = tests_total - 1
    else:
        raise ValueError(f"Bug type {bug_type} not implemented for JS")

    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="js_repo_")
    repo_name = f"js_{template_type}_{bug_type.value}"

    # Create directory structure
    os.makedirs(os.path.join(temp_dir, "src"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "test"), exist_ok=True)

    # Write files
    source_path = os.path.join(temp_dir, "src", "utils.js")
    test_path = os.path.join(temp_dir, "test", "utils.test.js")
    package_path = os.path.join(temp_dir, "package.json")
    jest_config_path = os.path.join(temp_dir, "jest.config.js")

    with open(source_path, "w") as f:
        f.write(buggy_code)

    with open(test_path, "w") as f:
        f.write(test_code)

    package_json = PACKAGE_JSON_TEMPLATE.format(name=repo_name)
    with open(package_path, "w") as f:
        f.write(package_json)

    with open(jest_config_path, "w") as f:
        f.write(JEST_CONFIG)

    return JSRepo(
        name=repo_name,
        root_path=temp_dir,
        source_file="src/utils.js",
        test_file="test/utils.test.js",
        original_code=original_code,
        buggy_code=buggy_code,
        bug_info=bug_info,
        package_json=package_json,
        tests_total=tests_total,
        tests_passing_with_bug=tests_passing,
    )


def cleanup_js_repo(repo: JSRepo) -> None:
    """Clean up a generated JS repository."""
    if os.path.exists(repo.root_path):
        shutil.rmtree(repo.root_path)


# ============================================================================
# Batch Generation for BC Training
# ============================================================================

def generate_js_repo_batch(
    count: int,
    bug_types: Optional[List[JSBugType]] = None,
    template_types: Optional[List[str]] = None,
    seed: int = 42,
) -> List[JSRepo]:
    """Generate a batch of JS repos for BC training.

    Args:
        count: Number of repos to generate
        bug_types: List of bug types to sample from (default: all)
        template_types: List of templates to sample from (default: both)
        seed: Random seed

    Returns:
        List of JSRepo instances
    """
    if bug_types is None:
        bug_types = [JSBugType.WRONG_OPERATOR, JSBugType.OFF_BY_ONE]
    if template_types is None:
        template_types = ["array_utils", "string_utils"]

    random.seed(seed)
    repos = []

    for i in range(count):
        bug_type = random.choice(bug_types)
        template_type = random.choice(template_types)
        repo = generate_js_repo(
            bug_type=bug_type,
            template_type=template_type,
            seed=seed + i,
        )
        repos.append(repo)

    return repos


# ============================================================================
# JS Vocab for Bug Fixes
# ============================================================================

# Vocabulary tokens needed to fix JS bugs
JS_FIX_VOCAB = [
    ">", "<", ">=", "<=", "===", "==", "!==", "!=",  # comparison operators
    "null", "undefined", "true", "false",  # literals
    "const", "let", "var", "function",  # keywords
]


def get_fix_vocab_idx(fix_token: str) -> int:
    """Get the vocabulary index for a fix token."""
    if fix_token in JS_FIX_VOCAB:
        return JS_FIX_VOCAB.index(fix_token)
    return 0  # Default to first token


if __name__ == "__main__":
    # Demo: generate a repo and show info
    repo = generate_js_repo(
        bug_type=JSBugType.WRONG_OPERATOR,
        template_type="array_utils",
        seed=42,
    )
    print(f"Generated: {repo.name}")
    print(f"Path: {repo.root_path}")
    print(f"Bug: {repo.bug_info.bug_type.value}")
    print(f"Original: '{repo.bug_info.original}' -> Buggy: '{repo.bug_info.buggy}'")
    print(f"Fix token: '{repo.bug_info.fix_token}'")
    print(f"Tests: {repo.tests_passing_with_bug}/{repo.tests_total} passing")
    print(f"\nSource file:\n{repo.buggy_code[:500]}...")

    # Cleanup
    cleanup_js_repo(repo)
    print("\nCleaned up repo.")
