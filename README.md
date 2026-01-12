# WIRED-BRAIN: RPJ Brain v5

A 20W-equivalent neural agent demonstrating **emergent brain-like architecture** from reward-per-joule optimization.

## Overview

This project implements the RPJ (Reward Per Joule) Brain - proving that brain-like structures (conscious/unconscious modes, neuromodulators, sleep consolidation) can **emerge** from energy constraints and compression pressure, rather than being hand-coded.

**Key constraints:**
- Zero LLM dependencies
- Zero transformer embeddings
- No pretrained models
- Content-free interface (bytes only)

## Architecture

| Component | Description | Params |
|-----------|-------------|--------|
| LN-GRU Substrate | Sparse recurrent core (B=64 blocks, k_r routing) | ~1.05M |
| Bits-Back VAE | Encoder q(z\|h,o) + decoder + codelength | ~140K |
| Local Plasticity | Low-rank adapters for fast weights | ~45K fast |
| Sleep Module | Offline consolidation (replay + dynamics) | ~17K |
| **Total** | | **~1.45M** |

## Installation

```bash
# Clone repository
git clone https://github.com/ni1ra/WIRED-BRAIN.git
cd WIRED-BRAIN

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install torch numpy pytest
```

## Quick Start

### Run Tests
```bash
python -m pytest tests/ -v
```

### Train on CCB (Confounded Causal Bandits)
```bash
# Short validation run
PYTHONPATH=. python scripts/train_ccb.py --timesteps 2048 --log-interval 2

# Full training
PYTHONPATH=. python scripts/train_ccb.py --timesteps 100000 --save-stats

# With GPU
PYTHONPATH=. python scripts/train_ccb.py --timesteps 100000 --device cuda
```

## Project Structure

```
src/
  core/
    substrate.py      # LN-GRU brain core with sparse routing
    vae.py            # Bits-back VAE for compression
    plasticity.py     # Local fast weights (low-rank adapters)
    sleep.py          # Offline consolidation module
    rpj_brain.py      # Integrated RPJ Brain system
    ppo_trainer.py    # PPO training with PopArt normalization
    byte_interface.py # Content-free I/O normalization
    mf1_baseline.py   # PPO baseline for comparison
  benchmarks/
    ccb.py            # Confounded Causal Bandits environment
    od_ndt.py         # One-Demonstration No-Data Transfer harness
  energy/
    proxy.py          # Energy tracking (FLOP + BytesMoved)
scripts/
  train_ccb.py        # Training script with logging
tests/
  unit/               # Unit tests (226 total)
  integration/        # Integration tests
```

## Benchmarks

### CCB (Confounded Causal Bandits)
Tests causal reasoning under confounding. The agent must learn do()-operator competence.

**Pass criteria:**
- DoErr <= 0.05
- Confounding discrimination >= 0.90

### OD-NDT (One-Demonstration No-Data Transfer)
Tests one-shot transfer learning.

**Protocol:**
1. One expert demo (<=200 steps)
2. One fixed sleep cycle (B_sleep_1 = 100J)
3. No further environment interaction
4. Test on 100 held-out tasks

**Pass criteria:**
- SR_novel >= 0.60
- Transfer ratio T >= 0.80

## Emergence Metrics

The RPJ objective should produce emergent brain-like dynamics:

| Metric | Target | Description |
|--------|--------|-------------|
| CBR (Compute Burst Ratio) | Bimodal | Conscious/unconscious mode split |
| K_eff | [2, 6] | Effective neuromodulator count |
| BI (Broadcast Index) | Bimodal | Global workspace emergence |
| H(c_t) | > 0.05 | No action collapse |

## Energy Model

Energy is tracked via proxy:
```
E_step = kappa_F * FLOPs + kappa_M * BytesMoved
```

Default values:
- kappa_F = 10^-9 J/FLOP
- kappa_M = 5 * 10^-11 J/byte

Target: P_bar <= 20W equivalent

## Documentation

- `BLUEPRINT.md` - Full technical specification
- `tests/` - Comprehensive test suite (226 tests)

## License

Research use only. See BLUEPRINT.md for full specification.
