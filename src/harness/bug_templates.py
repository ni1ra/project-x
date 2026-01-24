"""
Jarvis Harness Bug Templates

Configurable bug templates for generating challenging debugging tasks.
Bugs range from trivial typos to multi-file dependency issues.

Categories:
1. Syntax bugs - typos, missing chars
2. Logic bugs - off-by-one, wrong operators
3. Type bugs - wrong types, missing conversions
4. Import bugs - circular deps, wrong paths
5. Multi-file bugs - interface mismatches, missing updates

Each template defines:
- The bug injection pattern
- The correct fix
- Difficulty rating
- Whether it spans multiple files
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable
import random
import re


class BugCategory(Enum):
    """Categories of bugs by type."""
    SYNTAX = "syntax"        # Typos, missing chars
    LOGIC = "logic"          # Wrong operators, off-by-one
    TYPE = "type"            # Type mismatches
    IMPORT = "import"        # Import/dependency issues
    INTERFACE = "interface"  # API mismatches between files
    STATE = "state"          # State management bugs
    CONCURRENCY = "concurrency"  # Race conditions (advanced)


class BugDifficulty(Enum):
    """Difficulty levels for bugs."""
    TRIVIAL = 1      # Single char fix, obvious location
    EASY = 2         # Single line fix, clear location
    MEDIUM = 3       # Multi-line or requires understanding context
    HARD = 4         # Requires understanding multiple files
    EXPERT = 5       # Requires deep system understanding


@dataclass
class BugTemplate:
    """Template for generating a specific type of bug."""
    name: str
    category: BugCategory
    difficulty: BugDifficulty
    description: str

    # Files affected (relative paths within generated repo)
    files_affected: List[str] = field(default_factory=list)

    # If True, this bug requires changes to multiple files to fix
    multi_file_fix: bool = False

    # Pattern to inject (regex or exact string)
    inject_pattern: str = ""

    # What to replace it with (buggy version)
    inject_replacement: str = ""

    # The fix (correct version)
    correct_pattern: str = ""

    # Optional: function to programmatically generate the bug
    generator: Optional[Callable] = None

    def __post_init__(self):
        if not self.files_affected:
            self.files_affected = []


@dataclass
class BugInstance:
    """An instantiated bug ready to inject into code."""
    template: BugTemplate
    file_path: str              # Where to inject
    original_code: str          # Code before injection
    buggy_code: str            # Code after injection
    fix_code: str              # How to fix it
    line_number: int           # Approximate line number
    hint: str = ""             # Optional hint for the agent (generic)
    fix_description: str = ""  # Specific fix description (e.g., "Change > to >=")

    # For multi-file bugs
    secondary_files: Dict[str, Tuple[str, str, str]] = field(default_factory=dict)
    # secondary_files: {path: (original, buggy, fixed)}


# =============================================================================
# Syntax Bug Templates
# =============================================================================

SYNTAX_MISSING_COLON = BugTemplate(
    name="missing_colon",
    category=BugCategory.SYNTAX,
    difficulty=BugDifficulty.TRIVIAL,
    description="Missing colon after function/class definition",
    inject_pattern=r"def (\w+)\([^)]*\):",
    inject_replacement=r"def \1(",  # Will need special handling
)

SYNTAX_WRONG_INDENTATION = BugTemplate(
    name="wrong_indentation",
    category=BugCategory.SYNTAX,
    difficulty=BugDifficulty.EASY,
    description="Wrong indentation level",
)

SYNTAX_UNCLOSED_BRACKET = BugTemplate(
    name="unclosed_bracket",
    category=BugCategory.SYNTAX,
    difficulty=BugDifficulty.EASY,
    description="Unclosed bracket/parenthesis",
)

SYNTAX_WRONG_QUOTE = BugTemplate(
    name="wrong_quote",
    category=BugCategory.SYNTAX,
    difficulty=BugDifficulty.TRIVIAL,
    description="Mismatched string quotes",
)


# =============================================================================
# Logic Bug Templates
# =============================================================================

LOGIC_OFF_BY_ONE = BugTemplate(
    name="off_by_one",
    category=BugCategory.LOGIC,
    difficulty=BugDifficulty.EASY,
    description="Off-by-one error in loop bounds",
)

LOGIC_WRONG_OPERATOR = BugTemplate(
    name="wrong_operator",
    category=BugCategory.LOGIC,
    difficulty=BugDifficulty.EASY,
    description="Wrong comparison/arithmetic operator",
)

LOGIC_WRONG_RETURN = BugTemplate(
    name="wrong_return",
    category=BugCategory.LOGIC,
    difficulty=BugDifficulty.MEDIUM,
    description="Function returns wrong value/variable",
)

LOGIC_MISSING_CONDITION = BugTemplate(
    name="missing_condition",
    category=BugCategory.LOGIC,
    difficulty=BugDifficulty.MEDIUM,
    description="Missing edge case condition",
)

LOGIC_WRONG_VARIABLE = BugTemplate(
    name="wrong_variable",
    category=BugCategory.LOGIC,
    difficulty=BugDifficulty.MEDIUM,
    description="Using wrong variable name (similar names)",
)


# =============================================================================
# Type Bug Templates
# =============================================================================

TYPE_WRONG_CAST = BugTemplate(
    name="wrong_cast",
    category=BugCategory.TYPE,
    difficulty=BugDifficulty.EASY,
    description="Missing or wrong type conversion",
)

TYPE_NONE_CHECK = BugTemplate(
    name="none_check",
    category=BugCategory.TYPE,
    difficulty=BugDifficulty.MEDIUM,
    description="Missing None check before operation",
)


# =============================================================================
# Import Bug Templates
# =============================================================================

IMPORT_WRONG_PATH = BugTemplate(
    name="wrong_import_path",
    category=BugCategory.IMPORT,
    difficulty=BugDifficulty.EASY,
    description="Import from wrong module path",
    multi_file_fix=False,
)

IMPORT_CIRCULAR = BugTemplate(
    name="circular_import",
    category=BugCategory.IMPORT,
    difficulty=BugDifficulty.HARD,
    description="Circular import dependency",
    multi_file_fix=True,
)


# =============================================================================
# Interface Bug Templates (Multi-file)
# =============================================================================

INTERFACE_SIGNATURE_MISMATCH = BugTemplate(
    name="signature_mismatch",
    category=BugCategory.INTERFACE,
    difficulty=BugDifficulty.HARD,
    description="Function signature doesn't match caller's expectations",
    multi_file_fix=True,
    files_affected=["module.py", "caller.py"],
)

INTERFACE_MISSING_FIELD = BugTemplate(
    name="missing_field",
    category=BugCategory.INTERFACE,
    difficulty=BugDifficulty.HARD,
    description="Class missing field that another file expects",
    multi_file_fix=True,
)

INTERFACE_WRONG_RETURN_TYPE = BugTemplate(
    name="wrong_return_type",
    category=BugCategory.INTERFACE,
    difficulty=BugDifficulty.MEDIUM,
    description="Function returns different type than caller expects",
    multi_file_fix=False,  # Can often be fixed in one place
)


# =============================================================================
# State Bug Templates
# =============================================================================

STATE_UNINITIALIZED = BugTemplate(
    name="uninitialized_state",
    category=BugCategory.STATE,
    difficulty=BugDifficulty.MEDIUM,
    description="Variable used before initialization",
)

STATE_WRONG_SCOPE = BugTemplate(
    name="wrong_scope",
    category=BugCategory.STATE,
    difficulty=BugDifficulty.MEDIUM,
    description="Variable in wrong scope (local vs instance)",
)

STATE_MUTATION_BUG = BugTemplate(
    name="mutation_bug",
    category=BugCategory.STATE,
    difficulty=BugDifficulty.HARD,
    description="Unexpected mutation of shared state",
    multi_file_fix=True,
)


# =============================================================================
# Bug Template Registry
# =============================================================================

ALL_TEMPLATES: List[BugTemplate] = [
    # Syntax
    SYNTAX_MISSING_COLON,
    SYNTAX_WRONG_INDENTATION,
    SYNTAX_UNCLOSED_BRACKET,
    SYNTAX_WRONG_QUOTE,
    # Logic
    LOGIC_OFF_BY_ONE,
    LOGIC_WRONG_OPERATOR,
    LOGIC_WRONG_RETURN,
    LOGIC_MISSING_CONDITION,
    LOGIC_WRONG_VARIABLE,
    # Type
    TYPE_WRONG_CAST,
    TYPE_NONE_CHECK,
    # Import
    IMPORT_WRONG_PATH,
    IMPORT_CIRCULAR,
    # Interface
    INTERFACE_SIGNATURE_MISMATCH,
    INTERFACE_MISSING_FIELD,
    INTERFACE_WRONG_RETURN_TYPE,
    # State
    STATE_UNINITIALIZED,
    STATE_WRONG_SCOPE,
    STATE_MUTATION_BUG,
]


def get_templates_by_difficulty(
    min_difficulty: BugDifficulty = BugDifficulty.TRIVIAL,
    max_difficulty: BugDifficulty = BugDifficulty.EXPERT,
) -> List[BugTemplate]:
    """Get templates within difficulty range."""
    return [
        t for t in ALL_TEMPLATES
        if min_difficulty.value <= t.difficulty.value <= max_difficulty.value
    ]


def get_templates_by_category(category: BugCategory) -> List[BugTemplate]:
    """Get templates for a specific category."""
    return [t for t in ALL_TEMPLATES if t.category == category]


def get_multi_file_templates() -> List[BugTemplate]:
    """Get only multi-file bug templates."""
    return [t for t in ALL_TEMPLATES if t.multi_file_fix]


def sample_template(
    difficulty: Optional[BugDifficulty] = None,
    category: Optional[BugCategory] = None,
    multi_file_only: bool = False,
    seed: Optional[int] = None,
) -> BugTemplate:
    """Sample a random template matching criteria."""
    if seed is not None:
        random.seed(seed)

    candidates = ALL_TEMPLATES

    if difficulty is not None:
        candidates = [t for t in candidates if t.difficulty == difficulty]

    if category is not None:
        candidates = [t for t in candidates if t.category == category]

    if multi_file_only:
        candidates = [t for t in candidates if t.multi_file_fix]

    if not candidates:
        raise ValueError("No templates match the given criteria")

    return random.choice(candidates)
