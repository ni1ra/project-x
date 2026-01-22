"""
Phase 8: Structural Plasticity

This module enables the brain to develop heterogeneous structure (different regions
for different tasks). Key insight from paper.md Appendix K:

"What if we treat brain *structure* as a learnable parameter?"

Components:
1. RegionConfig - properties of each brain region
2. HeterogeneousSubstrate - multiple regions with different properties
3. StructuralPlasticity - gates, pruning, regrowth mechanisms
4. Optuna search helper - for structure space optimization

Reference: paper.md Appendix K "The Heterogeneous Brain Insight"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Callable
from enum import Enum

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class Timescale(Enum):
    """Timescale for region updates."""
    FAST = "fast"      # Every step
    MEDIUM = "medium"  # Every 4 steps
    SLOW = "slow"      # Every 10 steps


@dataclass
class RegionConfig:
    """
    Configuration for a single brain region.

    Inspired by biological brain regions:
    - Visual cortex: massive, hierarchical, mostly feedforward
    - Prefrontal cortex: smaller, deeply recurrent, integrative
    - Cerebellum: enormous neuron count, simple local circuits
    - Basal ganglia: sparse, acts as router/gate
    """
    name: str                        # e.g., "perception", "reasoning", "motor"
    width: int = 64                  # neurons in region (8-256)
    sparsity: float = 1.0            # fraction of active connections (0.1-1.0)
    fan_in_cap: int = 32             # max incoming connections per neuron
    fan_out_cap: int = 32            # max outgoing connections per neuron
    timescale: Timescale = Timescale.FAST  # update frequency
    fast_weight_rank: int = 0        # adapter rank for plasticity (0-64)
    activation_cost: float = 0.01   # energy penalty for using region

    def __post_init__(self):
        # Validate bounds
        assert 8 <= self.width <= 512, f"width must be in [8, 512], got {self.width}"
        assert 0.1 <= self.sparsity <= 1.0, f"sparsity must be in [0.1, 1.0], got {self.sparsity}"
        assert 4 <= self.fan_in_cap <= 256, f"fan_in_cap must be in [4, 256], got {self.fan_in_cap}"
        assert 4 <= self.fan_out_cap <= 256, f"fan_out_cap must be in [4, 256], got {self.fan_out_cap}"
        assert 0 <= self.fast_weight_rank <= 64, f"fast_weight_rank must be in [0, 64], got {self.fast_weight_rank}"
        assert 0.001 <= self.activation_cost <= 0.1, f"activation_cost must be in [0.001, 0.1], got {self.activation_cost}"


@dataclass
class StructuralPlasticityConfig:
    """Configuration for structural plasticity (pruning/regrowth)."""
    prune_fraction: float = 0.1     # fraction of connections to prune each sleep cycle
    regrowth_fraction: float = 0.1  # fraction to regrow
    prune_threshold: float = 0.01   # magnitude threshold for pruning
    regrowth_mode: str = "random"   # "random", "gradient", or "activity"
    sleep_interval: int = 10000     # steps between structural updates


class RegionGRU(nn.Module):
    """
    GRU for a single brain region with configurable properties.

    Supports:
    - Sparse connectivity (via fan_in/fan_out caps)
    - Different timescales (update frequencies)
    - Local fast weights (plasticity)
    """

    def __init__(self, config: RegionConfig, input_dim: int):
        super().__init__()
        self.config = config
        self.input_dim = input_dim
        self.hidden_dim = config.width

        # LayerNorm for stability
        self.ln_h = nn.LayerNorm(self.hidden_dim)
        self.ln_reset = nn.LayerNorm(self.hidden_dim)

        # Input projections (with potential sparsity)
        self.W_input = nn.Linear(input_dim, 3 * self.hidden_dim)

        # Recurrent projections
        self.U_hidden = nn.Linear(self.hidden_dim, 3 * self.hidden_dim, bias=False)

        # Apply sparsity mask if needed
        if config.sparsity < 1.0:
            self.register_buffer(
                'sparsity_mask',
                self._create_sparsity_mask(input_dim, self.hidden_dim, config.sparsity)
            )
        else:
            self.sparsity_mask = None

        # Fast weight adapters if rank > 0
        if config.fast_weight_rank > 0:
            rank = config.fast_weight_rank
            self.fast_A = nn.Parameter(torch.zeros(3 * self.hidden_dim, rank))
            self.fast_B = nn.Parameter(torch.zeros(self.hidden_dim, rank))
            nn.init.orthogonal_(self.fast_A)
            nn.init.orthogonal_(self.fast_B)
        else:
            self.fast_A = None
            self.fast_B = None

        # Step counter for timescale
        self.register_buffer('step_count', torch.tensor(0))

    def _create_sparsity_mask(
        self,
        input_dim: int,
        hidden_dim: int,
        sparsity: float
    ) -> torch.Tensor:
        """Create a random sparsity mask respecting fan_in/fan_out caps."""
        mask = torch.zeros(3 * hidden_dim, input_dim)

        num_connections = int(input_dim * hidden_dim * 3 * sparsity)
        num_connections = max(num_connections, hidden_dim * 3)  # At least 1 per output

        # Randomly select connections
        indices = torch.randperm(input_dim * hidden_dim * 3)[:num_connections]
        rows = indices // input_dim
        cols = indices % input_dim

        mask[rows, cols] = 1.0
        return mask

    def should_update(self, step: int) -> bool:
        """Check if this region should update at the current step."""
        if self.config.timescale == Timescale.FAST:
            return True
        elif self.config.timescale == Timescale.MEDIUM:
            return step % 4 == 0
        elif self.config.timescale == Timescale.SLOW:
            return step % 10 == 0
        return True

    def forward(
        self,
        x_t: torch.Tensor,
        h_t: torch.Tensor,
        global_step: int = 0,
    ) -> Tuple[torch.Tensor, bool]:
        """
        Forward pass for a single region.

        Args:
            x_t: Input [batch, input_dim]
            h_t: Hidden state [batch, hidden_dim]
            global_step: Current training step (for timescale gating)

        Returns:
            h_next: Next hidden state [batch, hidden_dim]
            updated: Whether the region was updated this step
        """
        batch_size = x_t.size(0)
        device = x_t.device

        # Check timescale
        if not self.should_update(global_step):
            return h_t, False

        # Apply sparsity mask to input weights
        if self.sparsity_mask is not None:
            W_masked = self.W_input.weight * self.sparsity_mask
        else:
            W_masked = self.W_input.weight

        # Pre-activation LayerNorm
        h_bar = self.ln_h(h_t)

        # Input projections with potential sparsity
        input_proj = F.linear(x_t, W_masked, self.W_input.bias)
        W_z, W_r, W_h = input_proj.chunk(3, dim=-1)

        # Hidden projections with optional fast weights
        hidden_proj = self.U_hidden(h_bar)
        if self.fast_A is not None and self.fast_B is not None:
            # Low-rank adapter: h_bar @ B @ A^T
            fast_delta = (h_bar @ self.fast_B) @ self.fast_A.t()
            hidden_proj = hidden_proj + fast_delta

        U_z, U_r, U_h = hidden_proj.chunk(3, dim=-1)

        # Gates
        z = torch.sigmoid(W_z + U_z)
        r = torch.sigmoid(W_r + U_r)

        # Candidate
        reset_h = self.ln_reset(r * h_bar)
        hidden_reset = self.U_hidden(reset_h)
        if self.fast_A is not None and self.fast_B is not None:
            fast_delta_reset = (reset_h @ self.fast_B) @ self.fast_A.t()
            hidden_reset = hidden_reset + fast_delta_reset
        U_h_reset = hidden_reset.chunk(3, dim=-1)[2]
        h_tilde = torch.tanh(W_h + U_h_reset)

        # Output
        h_next = (1 - z) * h_t + z * h_tilde

        self.step_count += 1
        return h_next, True


class InterRegionGate(nn.Module):
    """
    Learnable gate between brain regions.

    Implements gated information flow:
    output = gate * region_output + (1 - gate) * bypass

    The gate is learned and can become sparse through training,
    effectively "pruning" unused connections between regions.
    """

    def __init__(self, input_dim: int, output_dim: int):
        super().__init__()
        self.gate = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )
        self.projection = nn.Linear(input_dim, output_dim)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: Input from source region [batch, input_dim]

        Returns:
            output: Gated projection [batch, output_dim]
            gate_value: Gate activation [batch, 1] (for monitoring)
        """
        gate_value = self.gate(x)
        projected = self.projection(x)
        return gate_value * projected, gate_value


class HeterogeneousSubstrate(nn.Module):
    """
    Heterogeneous brain substrate with multiple specialized regions.

    Each region can have:
    - Different width (neuron count)
    - Different sparsity (connection density)
    - Different timescale (update frequency)
    - Different plasticity (fast weight rank)

    Regions are connected via learnable gates that can prune/regrow.
    """

    def __init__(
        self,
        regions: List[RegionConfig],
        obs_dim: int,
        latent_dim: int = 64,
        action_bytes: int = 1,
        k_max: int = 16,
    ):
        super().__init__()

        self.regions = regions
        self.num_regions = len(regions)
        self.obs_dim = obs_dim
        self.latent_dim = latent_dim
        self.k_max = k_max

        # Total hidden dimension is sum of all region widths
        self.total_hidden_dim = sum(r.width for r in regions)

        # Input dimension = phi(obs) + z_t + a_prev + g_prev
        self.input_dim = obs_dim + latent_dim + action_bytes + k_max

        # Create region GRUs
        # Each region GRU takes input of its own width (after projection)
        self.region_grus = nn.ModuleList()
        for config in regions:
            # Input to RegionGRU is region.width (projected from global input)
            self.region_grus.append(RegionGRU(config, config.width))

        # Inter-region gates (sparse connectivity pattern)
        # Each region can receive from all others (but gates can become sparse)
        self.inter_region_gates = nn.ModuleDict()
        for i, src_config in enumerate(regions):
            for j, dst_config in enumerate(regions):
                if i != j:  # No self-connections (handled by GRU)
                    key = f"gate_{i}_to_{j}"
                    self.inter_region_gates[key] = InterRegionGate(
                        src_config.width, dst_config.width
                    )

        # Input projection to each region's width
        # This transforms the global input to each region's native dimension
        self.input_projections = nn.ModuleList([
            nn.Linear(self.input_dim, r.width) for r in regions
        ])

        # Global broadcast (g_t) from combined regions
        self.global_broadcast = nn.Sequential(
            nn.Linear(self.total_hidden_dim, 128),
            nn.ReLU(),
            nn.Linear(128, k_max),
            nn.Sigmoid(),
        )

        # Compute allocation head
        self.compute_head = nn.Sequential(
            nn.Linear(self.total_hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

        # Value head
        self.value_head = nn.Sequential(
            nn.Linear(self.total_hidden_dim + k_max, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )

        # Register step counter
        self.register_buffer('global_step', torch.tensor(0))

    def init_hidden(self, batch_size: int, device: torch.device) -> torch.Tensor:
        """Initialize hidden states for all regions."""
        return torch.zeros(batch_size, self.total_hidden_dim, device=device)

    def init_global_scalars(self, batch_size: int, device: torch.device) -> torch.Tensor:
        """Initialize global scalars."""
        return torch.full((batch_size, self.k_max), 0.5, device=device)

    def _split_hidden(self, h: torch.Tensor) -> List[torch.Tensor]:
        """Split concatenated hidden state into per-region states."""
        regions = []
        offset = 0
        for config in self.regions:
            regions.append(h[:, offset:offset + config.width])
            offset += config.width
        return regions

    def _concat_hidden(self, region_states: List[torch.Tensor]) -> torch.Tensor:
        """Concatenate per-region states into single hidden state."""
        return torch.cat(region_states, dim=-1)

    def forward(
        self,
        phi_obs: torch.Tensor,
        z_t: torch.Tensor,
        a_prev: torch.Tensor,
        h_t: torch.Tensor,
        g_prev: torch.Tensor,
        training: bool = True,
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass through heterogeneous substrate.

        Args:
            phi_obs: Normalized observation [batch, obs_dim]
            z_t: Latent code [batch, latent_dim]
            a_prev: Previous action [batch, action_bytes]
            h_t: Hidden state [batch, total_hidden_dim]
            g_prev: Previous global scalars [batch, k_max]
            training: Training mode flag

        Returns:
            Dict with h_next, g_t, c_t, region_energies, gate_values
        """
        batch_size = phi_obs.size(0)
        device = phi_obs.device
        step = self.global_step.item()

        # Flatten a_prev if needed
        if a_prev.dim() == 2:
            a_prev_flat = a_prev.float().mean(dim=-1, keepdim=True)
        else:
            a_prev_flat = a_prev.float().unsqueeze(-1)

        # Construct input
        x_input = torch.cat([phi_obs, z_t, a_prev_flat.expand(-1, 1), g_prev], dim=-1)

        # Pad if input dimension doesn't match
        if x_input.size(-1) < self.input_dim:
            padding = torch.zeros(batch_size, self.input_dim - x_input.size(-1), device=device)
            x_input = torch.cat([x_input, padding], dim=-1)

        # Split hidden state into regions
        region_states = self._split_hidden(h_t)

        # Update each region
        new_region_states = []
        region_energies = []
        region_updated = []

        for i, (config, gru, h_region) in enumerate(zip(
            self.regions, self.region_grus, region_states
        )):
            # Project input to region dimension
            x_region = self.input_projections[i](x_input)

            # Add inter-region inputs (from other regions)
            for j, src_state in enumerate(region_states):
                if i != j:
                    gate_key = f"gate_{j}_to_{i}"
                    if gate_key in self.inter_region_gates:
                        gated_input, _ = self.inter_region_gates[gate_key](src_state)
                        x_region = x_region + gated_input

            # Update region
            h_new, updated = gru(x_region, h_region, step)
            new_region_states.append(h_new)
            region_updated.append(updated)

            # Compute energy for this region
            energy = config.activation_cost * (1.0 if updated else 0.0)
            region_energies.append(energy)

        # Concatenate new hidden states
        h_next = self._concat_hidden(new_region_states)

        # Compute global broadcast
        g_t = self.global_broadcast(h_next)

        # Compute allocation
        c_t = self.compute_head(h_next)

        # Collect gate values for monitoring
        gate_values = {}
        for key, gate in self.inter_region_gates.items():
            # Get gate activation from a representative sample
            src_idx = int(key.split('_')[1])
            _, gv = gate(region_states[src_idx])
            gate_values[key] = gv.mean().item()

        # Update global step
        if training:
            self.global_step += 1

        return {
            'h_next': h_next,
            'g_t': g_t,
            'c_t': c_t,
            'region_energies': torch.tensor(region_energies, device=device),
            'region_updated': region_updated,
            'gate_values': gate_values,
        }

    def get_value(self, h_t: torch.Tensor, g_t: torch.Tensor) -> torch.Tensor:
        """Get value estimate from hidden state."""
        combined = torch.cat([h_t, g_t], dim=-1)
        return self.value_head(combined).squeeze(-1)

    def compute_total_energy(self, output: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Compute total energy cost for a step."""
        return output['region_energies'].sum()


class StructuralPlasticity(nn.Module):
    """
    Structural plasticity mechanisms: pruning and regrowth.

    During "sleep" phases:
    1. Prune connections with low weight magnitude
    2. Regrow connections based on activity patterns

    This allows the brain structure to evolve during training.
    """

    def __init__(self, config: StructuralPlasticityConfig):
        super().__init__()
        self.config = config
        self.pruning_history: List[Dict[str, Any]] = []

    def prune_connections(
        self,
        substrate: HeterogeneousSubstrate,
        activity_stats: Optional[Dict[str, torch.Tensor]] = None,
    ) -> Dict[str, int]:
        """
        Prune low-magnitude connections from the substrate.

        Args:
            substrate: The heterogeneous substrate to prune
            activity_stats: Optional activity statistics for guided pruning

        Returns:
            Dict mapping region/gate names to number of pruned connections
        """
        pruned = {}

        # Prune inter-region gates (the main structural plasticity target)
        for name, gate in substrate.inter_region_gates.items():
            # Get projection weights
            W = gate.projection.weight.data

            # Compute magnitude
            magnitude = W.abs()

            # Find connections below threshold
            threshold = self.config.prune_threshold
            mask = magnitude < threshold

            # Respect prune_fraction limit
            num_to_prune = int(W.numel() * self.config.prune_fraction)
            if mask.sum() > num_to_prune:
                # Only prune the smallest
                flat_mag = magnitude.flatten()
                _, indices = flat_mag.sort()
                prune_indices = indices[:num_to_prune]
                mask = torch.zeros_like(W.flatten(), dtype=torch.bool)
                mask[prune_indices] = True
                mask = mask.view_as(W)

            # Zero out pruned connections
            W[mask] = 0.0
            pruned[name] = mask.sum().item()

        self.pruning_history.append({
            'step': len(self.pruning_history),
            'pruned': pruned.copy(),
        })

        return pruned

    def regrow_connections(
        self,
        substrate: HeterogeneousSubstrate,
        activity_stats: Optional[Dict[str, torch.Tensor]] = None,
    ) -> Dict[str, int]:
        """
        Regrow connections based on activity patterns or randomly.

        Args:
            substrate: The heterogeneous substrate to modify
            activity_stats: Optional activity statistics for guided regrowth

        Returns:
            Dict mapping region/gate names to number of regrown connections
        """
        regrown = {}

        for name, gate in substrate.inter_region_gates.items():
            W = gate.projection.weight.data

            # Find zero connections (candidates for regrowth)
            zero_mask = W.abs() < 1e-8
            num_zeros = zero_mask.sum().item()

            if num_zeros == 0:
                regrown[name] = 0
                continue

            # Number to regrow
            num_to_regrow = min(
                int(W.numel() * self.config.regrowth_fraction),
                num_zeros
            )

            if num_to_regrow == 0:
                regrown[name] = 0
                continue

            if self.config.regrowth_mode == "random":
                # Random regrowth
                zero_indices = zero_mask.flatten().nonzero(as_tuple=True)[0]
                perm = torch.randperm(len(zero_indices))[:num_to_regrow]
                regrow_indices = zero_indices[perm]

                # Initialize with small random values
                flat_W = W.flatten()
                flat_W[regrow_indices] = torch.randn(num_to_regrow, device=W.device) * 0.01
                W.copy_(flat_W.view_as(W))

            elif self.config.regrowth_mode == "gradient":
                # TODO: Gradient-based regrowth (requires gradient accumulation)
                pass

            elif self.config.regrowth_mode == "activity":
                # TODO: Activity-based regrowth (requires activity tracking)
                pass

            regrown[name] = num_to_regrow

        return regrown


def create_default_regions() -> List[RegionConfig]:
    """Create a default set of brain regions inspired by biology."""
    return [
        RegionConfig(
            name="perception",
            width=128,
            sparsity=0.8,
            fan_in_cap=64,
            fan_out_cap=64,
            timescale=Timescale.FAST,
            fast_weight_rank=8,
            activation_cost=0.005,
        ),
        RegionConfig(
            name="reasoning",
            width=256,
            sparsity=0.6,
            fan_in_cap=128,
            fan_out_cap=128,
            timescale=Timescale.MEDIUM,
            fast_weight_rank=16,
            activation_cost=0.02,
        ),
        RegionConfig(
            name="memory",
            width=128,
            sparsity=0.5,
            fan_in_cap=32,
            fan_out_cap=32,
            timescale=Timescale.SLOW,
            fast_weight_rank=32,
            activation_cost=0.01,
        ),
    ]


def create_optimal_regions() -> List[RegionConfig]:
    """
    Create optimal brain regions based on Optuna structure search.

    Search results (2026-01-22, 10 trials):
    - Best score: 82.8771 (vs baseline -83.70)
    - BC Accuracy: 83.3%

    Key insight: Mixed FAST/SLOW timescales perform best.
    The large SLOW region acts as persistent memory.
    """
    return [
        RegionConfig(
            name="fast_perception",
            width=96,
            sparsity=0.74,
            fan_in_cap=40,
            fan_out_cap=16,
            timescale=Timescale.FAST,
            fast_weight_rank=24,
            activation_cost=0.036,
        ),
        RegionConfig(
            name="slow_memory",
            width=224,
            sparsity=0.48,
            fan_in_cap=16,
            fan_out_cap=64,
            timescale=Timescale.SLOW,
            fast_weight_rank=0,  # No adapter - pure slow weights
            activation_cost=0.016,
        ),
        RegionConfig(
            name="fast_execution",
            width=64,
            sparsity=0.80,
            fan_in_cap=8,
            fan_out_cap=8,
            timescale=Timescale.FAST,
            fast_weight_rank=16,
            activation_cost=0.039,
        ),
    ]


# =============================================================================
# Optuna Search Helpers
# =============================================================================

def sample_region_config(trial, region_idx: int, prefix: str = "") -> RegionConfig:
    """
    Sample a region configuration using Optuna trial.

    Args:
        trial: Optuna trial object
        region_idx: Index of the region (for parameter naming)
        prefix: Optional prefix for parameter names

    Returns:
        Sampled RegionConfig
    """
    p = f"{prefix}region_{region_idx}_"

    return RegionConfig(
        name=f"region_{region_idx}",
        width=trial.suggest_int(f"{p}width", 32, 256, step=32),
        sparsity=trial.suggest_float(f"{p}sparsity", 0.3, 1.0),
        fan_in_cap=trial.suggest_int(f"{p}fan_in", 8, 64, step=8),
        fan_out_cap=trial.suggest_int(f"{p}fan_out", 8, 64, step=8),
        timescale=Timescale(
            trial.suggest_categorical(f"{p}timescale", ["fast", "medium", "slow"])
        ),
        fast_weight_rank=trial.suggest_int(f"{p}rank", 0, 32, step=8),
        activation_cost=trial.suggest_float(f"{p}cost", 0.005, 0.05),
    )


def create_optuna_objective(
    obs_dim: int,
    latent_dim: int,
    action_bytes: int,
    train_fn: Callable[[HeterogeneousSubstrate], Dict[str, float]],
    max_regions: int = 5,
) -> Callable:
    """
    Create an Optuna objective function for structure search.

    Args:
        obs_dim: Observation dimension
        latent_dim: Latent dimension
        action_bytes: Number of action bytes
        train_fn: Function that trains substrate and returns metrics dict
                  Should return {'reward': float, 'energy': float}
        max_regions: Maximum number of regions to search

    Returns:
        Optuna objective function
    """
    def objective(trial):
        # Sample number of regions
        num_regions = trial.suggest_int("num_regions", 2, max_regions)

        # Sample each region's config
        regions = []
        for i in range(num_regions):
            config = sample_region_config(trial, i)
            regions.append(config)

        # Create substrate
        substrate = HeterogeneousSubstrate(
            regions=regions,
            obs_dim=obs_dim,
            latent_dim=latent_dim,
            action_bytes=action_bytes,
        )

        # Train and evaluate
        metrics = train_fn(substrate)

        # Objective: reward - energy (RPJ principle)
        return metrics.get('reward', 0.0) - metrics.get('energy', 0.0)

    return objective


def run_structure_search(
    obs_dim: int,
    latent_dim: int,
    action_bytes: int,
    train_fn: Callable[[HeterogeneousSubstrate], Dict[str, float]],
    n_trials: int = 50,
    study_name: str = "jarvis_structure_search",
) -> Tuple[List[RegionConfig], Dict[str, Any]]:
    """
    Run Optuna structure search.

    Args:
        obs_dim: Observation dimension
        latent_dim: Latent dimension
        action_bytes: Number of action bytes
        train_fn: Training function
        n_trials: Number of Optuna trials
        study_name: Name for the study

    Returns:
        Tuple of (best_regions, best_params)
    """
    try:
        import optuna
    except ImportError:
        raise ImportError("Optuna not installed. Run: pip install optuna")

    objective = create_optuna_objective(
        obs_dim=obs_dim,
        latent_dim=latent_dim,
        action_bytes=action_bytes,
        train_fn=train_fn,
    )

    study = optuna.create_study(
        study_name=study_name,
        direction="maximize",
    )

    study.optimize(objective, n_trials=n_trials)

    # Reconstruct best regions
    best_params = study.best_params
    num_regions = best_params["num_regions"]

    best_regions = []
    for i in range(num_regions):
        p = f"region_{i}_"
        config = RegionConfig(
            name=f"region_{i}",
            width=best_params[f"{p}width"],
            sparsity=best_params[f"{p}sparsity"],
            fan_in_cap=best_params[f"{p}fan_in"],
            fan_out_cap=best_params[f"{p}fan_out"],
            timescale=Timescale(best_params[f"{p}timescale"]),
            fast_weight_rank=best_params[f"{p}rank"],
            activation_cost=best_params[f"{p}cost"],
        )
        best_regions.append(config)

    return best_regions, best_params


# =============================================================================
# Ablation Helper
# =============================================================================

def create_homogeneous_baseline(
    total_hidden: int = 512,
    num_regions: int = 4,
    obs_dim: int = 512,
    latent_dim: int = 64,
    action_bytes: int = 64,
) -> HeterogeneousSubstrate:
    """
    Create a homogeneous baseline (all regions identical) for ablation.

    Args:
        total_hidden: Total hidden dimension (divided equally)
        num_regions: Number of identical regions
        obs_dim: Observation dimension
        latent_dim: Latent dimension
        action_bytes: Number of action bytes

    Returns:
        HeterogeneousSubstrate with uniform regions
    """
    width_per_region = total_hidden // num_regions

    regions = [
        RegionConfig(
            name=f"region_{i}",
            width=width_per_region,
            sparsity=1.0,
            fan_in_cap=64,
            fan_out_cap=64,
            timescale=Timescale.FAST,
            fast_weight_rank=0,
            activation_cost=0.01,
        )
        for i in range(num_regions)
    ]

    return HeterogeneousSubstrate(
        regions=regions,
        obs_dim=obs_dim,
        latent_dim=latent_dim,
        action_bytes=action_bytes,
    )


if __name__ == "__main__":
    print("Testing Structural Plasticity Module...")

    # Create default regions
    regions = create_default_regions()
    print(f"\nDefault regions: {len(regions)}")
    for r in regions:
        print(f"  - {r.name}: width={r.width}, sparsity={r.sparsity}, timescale={r.timescale.value}")

    # Create substrate
    substrate = HeterogeneousSubstrate(
        regions=regions,
        obs_dim=512,
        latent_dim=64,
        action_bytes=64,
    )

    print(f"\nTotal hidden dim: {substrate.total_hidden_dim}")
    print(f"Num parameters: {sum(p.numel() for p in substrate.parameters()):,}")

    # Test forward pass
    batch_size = 4
    device = torch.device('cpu')

    h = substrate.init_hidden(batch_size, device)
    g = substrate.init_global_scalars(batch_size, device)

    phi_obs = torch.randn(batch_size, 512)
    z_t = torch.randn(batch_size, 64)
    a_prev = torch.randint(0, 256, (batch_size, 64))

    output = substrate(phi_obs, z_t, a_prev, h, g)

    print(f"\nForward pass:")
    print(f"  h_next shape: {output['h_next'].shape}")
    print(f"  g_t shape: {output['g_t'].shape}")
    print(f"  c_t shape: {output['c_t'].shape}")
    print(f"  Region energies: {output['region_energies'].tolist()}")
    print(f"  Regions updated: {output['region_updated']}")
    print(f"  Gate values: {output['gate_values']}")

    # Test value head
    value = substrate.get_value(output['h_next'], output['g_t'])
    print(f"  Value shape: {value.shape}")

    # Test structural plasticity
    sp_config = StructuralPlasticityConfig()
    sp = StructuralPlasticity(sp_config)

    pruned = sp.prune_connections(substrate)
    print(f"\nPruned connections: {pruned}")

    regrown = sp.regrow_connections(substrate)
    print(f"Regrown connections: {regrown}")

    # Test homogeneous baseline
    baseline = create_homogeneous_baseline()
    print(f"\nHomogeneous baseline hidden dim: {baseline.total_hidden_dim}")

    print("\n Phase 8: Structural Plasticity module works!")
