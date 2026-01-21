"""
Continuous Difficulty Mapping

Maps continuous difficulty d in [1, 100] to task generation parameters.
Uses smooth interpolation so adjacent difficulties are nearly imperceptible.

d=30 to d=31 is imperceptible.
d=10 to d=50 is substantial but gradual.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DifficultyParams:
    """Task parameters derived from continuous difficulty d."""
    # Code complexity
    min_lines: int
    max_lines: int
    min_files: int
    max_files: int

    # Bug characteristics
    bug_difficulty: int  # 1-5 mapping to BugDifficulty enum

    # Scaffolding (hints and assistance)
    provide_bug_line: bool       # Give the agent the bug location
    auto_focus_target: bool      # Automatically focus on target file
    force_write_focus_prob: float  # Probability to force WRITE_FOCUS action
    use_trivial_vocab: bool      # Restrict to simple action vocabulary


def map_difficulty_to_params(d: int) -> DifficultyParams:
    """
    Map continuous difficulty to task parameters with smooth interpolation.

    Anchor points:
    - d=1-10: Trivial (10-50 lines, 1 file, syntax bugs, full hints)
    - d=11-30: Easy (50-100 lines, 1-2 files, syntax/logic, partial hints)
    - d=31-50: Medium (100-200 lines, 2-5 files, logic/type, no hints)
    - d=51-70: Hard (200-500 lines, 5-10 files, state/import, no hints)
    - d=71-100: Expert (500+ lines, 10+ files, design flaws, no hints)

    Args:
        d: Difficulty in [1, 100]

    Returns:
        DifficultyParams with task generation settings
    """
    d = max(1, min(100, d))

    # Code complexity (linear interpolation between anchor points)
    if d <= 10:
        min_lines, max_lines = 10, 50
        min_files, max_files = 1, 1
    elif d <= 30:
        t = (d - 10) / 20
        min_lines = int(10 + t * 40)
        max_lines = int(50 + t * 50)
        min_files = 1
        max_files = 1 + int(t)  # 1-2 files
    elif d <= 50:
        t = (d - 30) / 20
        min_lines = int(50 + t * 50)
        max_lines = int(100 + t * 100)
        min_files = 1 + int(t)  # 1-2 files
        max_files = 2 + int(t * 3)  # 2-5 files
    elif d <= 70:
        t = (d - 50) / 20
        min_lines = int(100 + t * 100)
        max_lines = int(200 + t * 300)
        min_files = 2 + int(t * 3)  # 2-5 files
        max_files = 5 + int(t * 5)  # 5-10 files
    else:  # d > 70
        t = (d - 70) / 30
        min_lines = int(200 + t * 300)
        max_lines = int(500 + t * 500)
        min_files = 5 + int(t * 5)  # 5-10 files
        max_files = 10 + int(t * 10)  # 10-20 files

    # Bug difficulty mapping (1-5 enum values)
    if d <= 10:
        bug_difficulty = 1  # TRIVIAL
    elif d <= 30:
        bug_difficulty = 2  # EASY
    elif d <= 50:
        bug_difficulty = 3  # MEDIUM
    elif d <= 70:
        bug_difficulty = 4  # HARD
    else:
        bug_difficulty = 5  # EXPERT

    # Scaffolding (gradual removal)
    provide_bug_line = d <= 15      # Full hints only for very easy
    auto_focus_target = d <= 25     # Auto-focus for easy
    force_write_focus_prob = max(0.0, 1.0 - (d - 1) / 30)  # Fades to 0 by d=31
    use_trivial_vocab = d <= 10     # Simple vocab for trivial only

    return DifficultyParams(
        min_lines=min_lines,
        max_lines=max_lines,
        min_files=min_files,
        max_files=max_files,
        bug_difficulty=bug_difficulty,
        provide_bug_line=provide_bug_line,
        auto_focus_target=auto_focus_target,
        force_write_focus_prob=force_write_focus_prob,
        use_trivial_vocab=use_trivial_vocab,
    )


def get_bug_difficulty_enum(params: DifficultyParams):
    """
    Convert bug_difficulty int to BugDifficulty enum.

    Import here to avoid circular dependency at module load time.
    """
    from src.harness.bug_templates import BugDifficulty
    return BugDifficulty(params.bug_difficulty)


def describe_difficulty(d: int) -> str:
    """
    Return human-readable description of difficulty level.

    Args:
        d: Difficulty in [1, 100]

    Returns:
        Description string
    """
    if d <= 10:
        return f"d={d}: TRIVIAL - Single file, syntax bugs, full hints"
    elif d <= 30:
        return f"d={d}: EASY - 1-2 files, syntax/logic bugs, partial hints"
    elif d <= 50:
        return f"d={d}: MEDIUM - 2-5 files, logic/type bugs, no hints"
    elif d <= 70:
        return f"d={d}: HARD - 5-10 files, state/import bugs, no hints"
    else:
        return f"d={d}: EXPERT - 10+ files, design bugs, no hints"
