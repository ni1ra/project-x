"""
Continuous Difficulty Mapping

Maps continuous difficulty d in [1, 100] to task generation parameters.
Uses smooth interpolation so adjacent difficulties are nearly imperceptible.

d=30 to d=31 is imperceptible.
d=10 to d=50 is substantial but gradual.

All discrete parameters use PROBABILISTIC scaffolding:
- Boolean flags → probabilities, sampled per episode
- Integer counts → stochastic rounding for smooth transitions
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DifficultyParams:
    """Task parameters derived from continuous difficulty d."""
    # Code complexity (use stochastic_round for actual values)
    min_lines: int
    max_lines: int
    min_files_expected: float  # Expected value, use stochastic_round()
    max_files_expected: float  # Expected value, use stochastic_round()

    # Bug characteristics
    bug_difficulty: int  # 1-5 mapping to BugDifficulty enum

    # Scaffolding PROBABILITIES (sample per episode)
    provide_bug_line_prob: float    # Probability to give bug location
    auto_focus_target_prob: float   # Probability to auto-focus on target
    force_write_focus_prob: float   # Probability to force WRITE_FOCUS action
    use_trivial_vocab_prob: float   # Probability to use simple vocab


def stochastic_round(x: float) -> int:
    """
    Stochastic rounding: floor(x) + Bernoulli(frac(x)).

    This makes integer parameters smooth in expectation.
    E.g., x=1.7 returns 1 with prob 0.3, 2 with prob 0.7.
    """
    floor_x = int(np.floor(x))
    frac = x - floor_x
    if np.random.random() < frac:
        return floor_x + 1
    return floor_x


def map_difficulty_to_params(d: int) -> DifficultyParams:
    """
    Map continuous difficulty to task parameters with smooth interpolation.

    All parameters are now SMOOTH:
    - Integer counts use expected values (apply stochastic_round when sampling)
    - Boolean flags are now probabilities (sample per episode)

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

    # Code complexity (linear interpolation - SMOOTH expected values)
    if d <= 10:
        min_lines, max_lines = 10, 50
        min_files_exp, max_files_exp = 1.0, 1.0
    elif d <= 30:
        t = (d - 10) / 20
        min_lines = int(10 + t * 40)
        max_lines = int(50 + t * 50)
        min_files_exp = 1.0
        max_files_exp = 1.0 + t  # Smooth 1.0 → 2.0
    elif d <= 50:
        t = (d - 30) / 20
        min_lines = int(50 + t * 50)
        max_lines = int(100 + t * 100)
        min_files_exp = 1.0 + t  # Smooth 1.0 → 2.0
        max_files_exp = 2.0 + t * 3  # Smooth 2.0 → 5.0
    elif d <= 70:
        t = (d - 50) / 20
        min_lines = int(100 + t * 100)
        max_lines = int(200 + t * 300)
        min_files_exp = 2.0 + t * 3  # Smooth 2.0 → 5.0
        max_files_exp = 5.0 + t * 5  # Smooth 5.0 → 10.0
    else:  # d > 70
        t = (d - 70) / 30
        min_lines = int(200 + t * 300)
        max_lines = int(500 + t * 500)
        min_files_exp = 5.0 + t * 5  # Smooth 5.0 → 10.0
        max_files_exp = 10.0 + t * 10  # Smooth 10.0 → 20.0

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

    # Scaffolding PROBABILITIES (smooth linear decay)
    # provide_bug_line: 100% at d=1, 0% at d=20
    provide_bug_line_prob = max(0.0, min(1.0, 1.0 - (d - 1) / 19))

    # auto_focus_target: 100% at d=1, 0% at d=30
    auto_focus_target_prob = max(0.0, min(1.0, 1.0 - (d - 1) / 29))

    # force_write_focus: 100% at d=1, 0% at d=35
    force_write_focus_prob = max(0.0, min(1.0, 1.0 - (d - 1) / 34))

    # use_trivial_vocab: 100% at d=1, 0% at d=15
    use_trivial_vocab_prob = max(0.0, min(1.0, 1.0 - (d - 1) / 14))

    return DifficultyParams(
        min_lines=min_lines,
        max_lines=max_lines,
        min_files_expected=min_files_exp,
        max_files_expected=max_files_exp,
        bug_difficulty=bug_difficulty,
        provide_bug_line_prob=provide_bug_line_prob,
        auto_focus_target_prob=auto_focus_target_prob,
        force_write_focus_prob=force_write_focus_prob,
        use_trivial_vocab_prob=use_trivial_vocab_prob,
    )


@dataclass
class SampledEpisodeParams:
    """Concrete parameters sampled for a single episode."""
    min_lines: int
    max_lines: int
    min_files: int
    max_files: int
    bug_difficulty: int
    provide_bug_line: bool
    auto_focus_target: bool
    force_write_focus: bool
    use_trivial_vocab: bool


def sample_episode_params(params: DifficultyParams) -> SampledEpisodeParams:
    """
    Sample concrete episode parameters from probabilistic DifficultyParams.

    Use this to get actual values for a single episode:
    - Expected file counts → stochastic rounded integers
    - Probabilities → sampled booleans

    Args:
        params: DifficultyParams with expected values and probabilities

    Returns:
        SampledEpisodeParams with concrete values for this episode
    """
    return SampledEpisodeParams(
        min_lines=params.min_lines,
        max_lines=params.max_lines,
        min_files=max(1, stochastic_round(params.min_files_expected)),
        max_files=max(1, stochastic_round(params.max_files_expected)),
        bug_difficulty=params.bug_difficulty,
        provide_bug_line=np.random.random() < params.provide_bug_line_prob,
        auto_focus_target=np.random.random() < params.auto_focus_target_prob,
        force_write_focus=np.random.random() < params.force_write_focus_prob,
        use_trivial_vocab=np.random.random() < params.use_trivial_vocab_prob,
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
        Description string with probabilistic scaffolding info
    """
    params = map_difficulty_to_params(d)

    if d <= 10:
        tier = "TRIVIAL"
    elif d <= 30:
        tier = "EASY"
    elif d <= 50:
        tier = "MEDIUM"
    elif d <= 70:
        tier = "HARD"
    else:
        tier = "EXPERT"

    return (
        f"d={d}: {tier} - "
        f"files={params.min_files_expected:.1f}-{params.max_files_expected:.1f}, "
        f"bug_line={params.provide_bug_line_prob:.0%}, "
        f"focus={params.auto_focus_target_prob:.0%}"
    )
