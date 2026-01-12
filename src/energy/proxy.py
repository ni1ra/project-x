"""
Energy Proxy Implementation

Measures energy consumption as:
    E = κ_F · FLOPs + κ_M · BytesMoved

This is the "Meter" - the physics engine of the project.
All energy accounting flows through this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn


@dataclass
class EnergyConfig:
    """Energy proxy configuration from manifest."""

    kappa_F: float = 1e-9  # J/FLOP
    kappa_M: float = 5e-11  # J/Byte
    B_max_ep: float = 200.0  # J per episode
    B_max_day: float = 72000.0  # J per day
    B_sleep: float = 100.0  # J sleep budget
    calibrated: bool = False

    @classmethod
    def from_manifest(cls, manifest_path: Path) -> "EnergyConfig":
        """Load config from manifest.json."""
        with open(manifest_path) as f:
            manifest = json.load(f)

        energy = manifest["energy_constants"]
        budgets = manifest["budgets"]

        return cls(
            kappa_F=energy["kappa_F"],
            kappa_M=energy["kappa_M"],
            B_max_ep=budgets["B_max_ep"],
            B_max_day=budgets["B_max_day"],
            B_sleep=budgets["B_sleep"],
            calibrated=energy["calibration_status"] == "CALIBRATED",
        )


@dataclass
class EnergyAccumulator:
    """Accumulates energy consumption across operations."""

    total_flops: int = 0
    total_bytes_moved: int = 0
    config: EnergyConfig = field(default_factory=EnergyConfig)

    # Budget tracking
    episode_energy: float = 0.0
    day_energy: float = 0.0
    sleep_energy: float = 0.0

    # Step tracking
    step_flops: int = 0
    step_bytes: int = 0

    def reset_step(self) -> None:
        """Reset per-step counters."""
        self.step_flops = 0
        self.step_bytes = 0

    def reset_episode(self) -> None:
        """Reset episode counters."""
        self.episode_energy = 0.0
        self.reset_step()

    def reset_day(self) -> None:
        """Reset daily counters."""
        self.day_energy = 0.0
        self.reset_episode()

    def add_flops(self, flops: int) -> None:
        """Add FLOPs to accumulator."""
        self.total_flops += flops
        self.step_flops += flops

    def add_bytes(self, bytes_moved: int) -> None:
        """Add bytes moved to accumulator."""
        self.total_bytes_moved += bytes_moved
        self.step_bytes += bytes_moved

    def compute_energy(self, flops: int, bytes_moved: int) -> float:
        """Compute energy for given FLOPs and bytes."""
        return self.config.kappa_F * flops + self.config.kappa_M * bytes_moved

    @property
    def step_energy(self) -> float:
        """Energy consumed this step."""
        return self.compute_energy(self.step_flops, self.step_bytes)

    @property
    def total_energy(self) -> float:
        """Total energy consumed."""
        return self.compute_energy(self.total_flops, self.total_bytes_moved)

    def commit_step(self, is_sleep: bool = False) -> bool:
        """
        Commit step energy to episode/day totals.
        Returns True if within budget, False if exceeded (kill-switch).
        """
        energy = self.step_energy
        self.episode_energy += energy
        self.day_energy += energy

        if is_sleep:
            self.sleep_energy += energy

        self.reset_step()

        # Check budgets (kill-switch conditions)
        if self.episode_energy > self.config.B_max_ep:
            return False
        if self.day_energy > self.config.B_max_day:
            return False
        if is_sleep and self.sleep_energy > self.config.B_sleep:
            return False

        return True


def count_linear_flops(in_features: int, out_features: int, batch_size: int = 1) -> int:
    """
    Count FLOPs for a linear layer.

    FLOPs = 2 * in_features * out_features * batch_size
    (multiply-add counts as 2 operations)
    """
    return 2 * in_features * out_features * batch_size


def count_linear_bytes(
    in_features: int,
    out_features: int,
    batch_size: int = 1,
    dtype_bytes: int = 4  # float32
) -> int:
    """
    Count bytes moved for a linear layer.

    Reads: weight matrix + input
    Writes: output
    """
    weight_bytes = in_features * out_features * dtype_bytes
    input_bytes = batch_size * in_features * dtype_bytes
    output_bytes = batch_size * out_features * dtype_bytes
    return weight_bytes + input_bytes + output_bytes


def count_matmul_flops(m: int, k: int, n: int) -> int:
    """
    Count FLOPs for matrix multiplication [m, k] @ [k, n].

    FLOPs = 2 * m * k * n
    """
    return 2 * m * k * n


def count_matmul_bytes(m: int, k: int, n: int, dtype_bytes: int = 4) -> int:
    """
    Count bytes moved for matrix multiplication.

    Reads: A[m,k] + B[k,n]
    Writes: C[m,n]
    """
    return (m * k + k * n + m * n) * dtype_bytes


def count_gru_flops(input_size: int, hidden_size: int, batch_size: int = 1) -> int:
    """
    Count FLOPs for one GRU step.

    GRU has 3 gates (reset, update, new), each with input and hidden projections.
    Plus element-wise operations.
    """
    # Linear projections: 3 gates × (input projection + hidden projection)
    gate_flops = 3 * (
        count_linear_flops(input_size, hidden_size, batch_size) +
        count_linear_flops(hidden_size, hidden_size, batch_size)
    )

    # Element-wise: sigmoid (×2 for r,z), tanh (×1), multiplications, additions
    # Approximate as 10 ops per hidden unit per gate
    elementwise_flops = 10 * hidden_size * batch_size

    return gate_flops + elementwise_flops


def count_gru_bytes(
    input_size: int,
    hidden_size: int,
    batch_size: int = 1,
    dtype_bytes: int = 4
) -> int:
    """
    Count bytes moved for one GRU step.
    """
    # Weight matrices: W_ir, W_iz, W_in, W_hr, W_hz, W_hn + biases
    weight_bytes = 3 * (input_size * hidden_size + hidden_size * hidden_size) * dtype_bytes
    bias_bytes = 6 * hidden_size * dtype_bytes

    # Input/hidden state reads
    input_bytes = batch_size * input_size * dtype_bytes
    hidden_bytes = batch_size * hidden_size * dtype_bytes

    # Output write
    output_bytes = batch_size * hidden_size * dtype_bytes

    return weight_bytes + bias_bytes + input_bytes + hidden_bytes + output_bytes


class EnergyTracker:
    """
    High-level energy tracking for neural network operations.

    Usage:
        tracker = EnergyTracker(config)

        # Manual tracking
        tracker.record_linear(in_features=512, out_features=256, batch_size=32)
        tracker.record_gru_step(input_size=128, hidden_size=512, batch_size=32)

        # Check budget
        if not tracker.commit_step():
            raise EnergyBudgetExceeded()
    """

    def __init__(self, config: Optional[EnergyConfig] = None):
        self.config = config or EnergyConfig()
        self.accumulator = EnergyAccumulator(config=self.config)

    def record_linear(
        self,
        in_features: int,
        out_features: int,
        batch_size: int = 1
    ) -> None:
        """Record energy for a linear layer forward pass."""
        flops = count_linear_flops(in_features, out_features, batch_size)
        bytes_moved = count_linear_bytes(in_features, out_features, batch_size)
        self.accumulator.add_flops(flops)
        self.accumulator.add_bytes(bytes_moved)

    def record_gru_step(
        self,
        input_size: int,
        hidden_size: int,
        batch_size: int = 1
    ) -> None:
        """Record energy for one GRU step."""
        flops = count_gru_flops(input_size, hidden_size, batch_size)
        bytes_moved = count_gru_bytes(input_size, hidden_size, batch_size)
        self.accumulator.add_flops(flops)
        self.accumulator.add_bytes(bytes_moved)

    def record_matmul(self, m: int, k: int, n: int) -> None:
        """Record energy for matrix multiplication."""
        flops = count_matmul_flops(m, k, n)
        bytes_moved = count_matmul_bytes(m, k, n)
        self.accumulator.add_flops(flops)
        self.accumulator.add_bytes(bytes_moved)

    def record_layernorm(self, normalized_shape: int, batch_size: int = 1) -> None:
        """Record energy for LayerNorm."""
        # Mean: sum + divide = 2 ops per element
        # Var: subtract + square + sum + divide = 4 ops per element
        # Normalize: subtract + divide = 2 ops per element
        # Scale/shift: multiply + add = 2 ops per element
        flops = 10 * normalized_shape * batch_size

        # Read input, gamma, beta; write output
        bytes_moved = (3 * normalized_shape + normalized_shape * batch_size * 2) * 4

        self.accumulator.add_flops(flops)
        self.accumulator.add_bytes(bytes_moved)

    def commit_step(self, is_sleep: bool = False) -> bool:
        """Commit current step. Returns False if budget exceeded."""
        return self.accumulator.commit_step(is_sleep)

    def reset_episode(self) -> None:
        """Reset for new episode."""
        self.accumulator.reset_episode()

    @property
    def step_energy(self) -> float:
        """Energy consumed this step (Joules)."""
        return self.accumulator.step_energy

    @property
    def episode_energy(self) -> float:
        """Energy consumed this episode (Joules)."""
        return self.accumulator.episode_energy

    @property
    def total_energy(self) -> float:
        """Total energy consumed (Joules)."""
        return self.accumulator.total_energy

    def get_stats(self) -> dict:
        """Get energy statistics."""
        return {
            "step_energy_J": self.step_energy,
            "episode_energy_J": self.episode_energy,
            "total_energy_J": self.total_energy,
            "total_flops": self.accumulator.total_flops,
            "total_bytes": self.accumulator.total_bytes_moved,
            "budget_remaining_ep_J": self.config.B_max_ep - self.accumulator.episode_energy,
            "calibrated": self.config.calibrated,
        }


class EnergyBudgetExceeded(Exception):
    """Raised when energy budget is exceeded (kill-switch)."""
    pass
