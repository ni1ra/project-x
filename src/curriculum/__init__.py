"""
Self-Paced Difficulty Control Module

Replaces external CurriculumScheduler with intrinsic Boredom/Stress signals
that let the agent self-regulate difficulty.

Philosophy: "We did not build these structures. We priced the resources,
and the structures emerged."
"""

from .signals import (
    BoredomConfig,
    StressConfig,
    SignalTracker,
    compute_boredom,
    compute_stress,
)
from .controller import (
    ControllerConfig,
    SelfPacedController,
)
from .difficulty_mapping import (
    DifficultyParams,
    map_difficulty_to_params,
)

__all__ = [
    # Signals
    "BoredomConfig",
    "StressConfig",
    "SignalTracker",
    "compute_boredom",
    "compute_stress",
    # Controller
    "ControllerConfig",
    "SelfPacedController",
    # Mapping
    "DifficultyParams",
    "map_difficulty_to_params",
]
