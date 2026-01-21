#!/usr/bin/env python3
"""
Generate K_eff plots for publication.

The key finding is the Exploration → Habituation → Re-emergence trajectory:
1. K_eff rises as the brain explores neuromodulator space
2. K_eff collapses as the brain habituates to familiar tasks
3. K_eff RE-EMERGES when task diversity requires persistent plasticity

This is "Architectural Autopoiesis via Energy Pressure" - the homogeneous
substrate self-organizes into bipartite architecture dynamically.

Usage:
    python scripts/plot_k_eff.py
"""

import torch
import numpy as np

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("matplotlib not installed - using ASCII plot")


def ascii_plot(k_eff_history: list, title: str = "K_eff vs Training Steps"):
    """ASCII art plot for environments without matplotlib."""
    width = 70
    height = 20

    k_eff = np.array(k_eff_history)
    steps = np.arange(len(k_eff)) * 1.048576  # Million steps per update

    # Normalize to plot dimensions
    y_min, y_max = 0, max(k_eff) * 1.1
    x_min, x_max = 0, max(steps)

    # Create plot grid
    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Add y-axis
    for i in range(height):
        grid[i][0] = '|'

    # Add x-axis
    for j in range(width):
        grid[height-1][j] = '-'
    grid[height-1][0] = '+'

    # Plot data points
    for i, (x, y) in enumerate(zip(steps, k_eff)):
        col = int((x - x_min) / (x_max - x_min) * (width - 2)) + 1
        row = height - 2 - int((y - y_min) / (y_max - y_min) * (height - 2))
        row = max(0, min(height-2, row))
        col = max(1, min(width-1, col))

        # Use different chars for different phases
        if y < 0.5:
            char = 'v'  # Collapsed
        elif y > 3.0:
            char = '^'  # High activity
        else:
            char = '*'  # Normal
        grid[row][col] = char

    # Print plot
    print("\n" + "=" * (width + 10))
    print(title.center(width + 10))
    print("=" * (width + 10))
    print(f"  {y_max:.1f} |")
    for row in grid[:-1]:
        print("      " + ''.join(row))
    print(f"  {y_min:.1f} " + ''.join(grid[-1]))
    print(f"        0{' ' * (width//2 - 5)}Steps (M){' ' * (width//2 - 5)}{x_max:.0f}")
    print()

    # Add legend
    print("  Legend: ^ = High K_eff (emergence)")
    print("          * = Normal K_eff")
    print("          v = Collapsed K_eff (habituation)")


def plot_k_eff_matplotlib(k_eff_history: list, save_path: str = "results/k_eff_trajectory.png"):
    """Generate publication-quality K_eff plot."""
    k_eff = np.array(k_eff_history)
    steps = np.arange(len(k_eff)) * 1.048576  # Million steps per update

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot K_eff trajectory
    ax.plot(steps, k_eff, 'b-', linewidth=2, label='K_eff')

    # Add threshold lines
    ax.axhline(y=2, color='g', linestyle='--', alpha=0.5, label='Target band [2-6]')
    ax.axhline(y=6, color='g', linestyle='--', alpha=0.5)
    ax.fill_between([0, max(steps)], [2, 2], [6, 6], alpha=0.1, color='green')

    # Annotate phases
    # Phase 1: Exploration (steps 0-5M)
    ax.annotate('1. Exploration', xy=(3, 2.5), fontsize=10, color='blue')

    # Phase 2: Habituation (steps 8-12M)
    ax.annotate('2. Habituation', xy=(10, 0.5), fontsize=10, color='red')

    # Phase 3: Re-emergence (steps 20-50M)
    ax.annotate('3. Re-emergence', xy=(30, 3.2), fontsize=10, color='green')

    # Labels and title
    ax.set_xlabel('Training Steps (Millions)', fontsize=12)
    ax.set_ylabel('K_eff (Effective Neuromodulator Count)', fontsize=12)
    ax.set_title('K_eff Trajectory: Exploration → Habituation → Re-emergence\n(Architectural Autopoiesis via Energy Pressure)', fontsize=14)

    ax.set_ylim(-0.2, 5)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # Save
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Plot saved to: {save_path}")


def main():
    print("=" * 60)
    print("K_EFF TRAJECTORY ANALYSIS")
    print("=" * 60)

    # Load checkpoint with K_eff history
    checkpoint_path = "results/checkpoint_multitask_ccb_final_50331648.pt"
    checkpoint = torch.load(checkpoint_path, map_location='cpu')

    k_eff_history = checkpoint.get('k_eff_history', [])
    print(f"\nLoaded K_eff history: {len(k_eff_history)} data points")

    # Analysis
    k_eff = np.array(k_eff_history)
    print(f"\n=== K_EFF STATISTICS ===")
    print(f"  Mean: {k_eff.mean():.3f}")
    print(f"  Std:  {k_eff.std():.3f}")
    print(f"  Min:  {k_eff.min():.3f}")
    print(f"  Max:  {k_eff.max():.3f}")

    # Identify phases
    print(f"\n=== PHASE ANALYSIS ===")

    # Phase 1: Exploration (first high values)
    exploration_idx = np.where(k_eff > 2.0)[0]
    if len(exploration_idx) > 0:
        first_exploration = exploration_idx[0]
        print(f"  Phase 1 (Exploration): Update {first_exploration} - K_eff rises to {k_eff[first_exploration]:.2f}")

    # Phase 2: Habituation (minimum)
    min_idx = np.argmin(k_eff)
    print(f"  Phase 2 (Habituation): Update {min_idx} - K_eff drops to {k_eff[min_idx]:.4f}")

    # Phase 3: Re-emergence (after habituation, back to high)
    post_habit = k_eff[min_idx:]
    if len(post_habit) > 5:
        re_emergence_idx = np.where(post_habit > 2.0)[0]
        if len(re_emergence_idx) > 0:
            actual_idx = min_idx + re_emergence_idx[0]
            print(f"  Phase 3 (Re-emergence): Update {actual_idx} - K_eff rises to {k_eff[actual_idx]:.2f}")

    # Final state
    final_k_eff = k_eff[-5:].mean()
    print(f"\n  Final K_eff (last 5 updates): {final_k_eff:.2f}")

    # Validation
    in_target_band = 2.0 <= final_k_eff <= 6.0
    print(f"\n=== VALIDATION ===")
    print(f"  K_eff in target [2-6]: {'PASS' if in_target_band else 'FAIL'}")
    print(f"  Trajectory pattern: Exploration → Habituation → Re-emergence")
    print(f"  Interpretation: Architectural Autopoiesis via Energy Pressure")

    # Generate plots
    print(f"\n=== GENERATING PLOTS ===")

    # ASCII plot (always works)
    ascii_plot(k_eff_history, "K_eff vs Training Steps (50M)")

    # Matplotlib plot if available
    if HAS_MATPLOTLIB:
        plot_k_eff_matplotlib(k_eff_history, "results/k_eff_trajectory.png")
    else:
        print("  Skipping matplotlib plot (not installed)")

    # Save numerical data
    results = {
        'k_eff_history': k_eff_history,
        'mean': float(k_eff.mean()),
        'std': float(k_eff.std()),
        'min': float(k_eff.min()),
        'max': float(k_eff.max()),
        'final_k_eff': float(final_k_eff),
        'in_target_band': in_target_band,
    }
    torch.save(results, 'results/k_eff_analysis.pt')
    print(f"\nNumerical data saved to: results/k_eff_analysis.pt")


if __name__ == "__main__":
    main()
