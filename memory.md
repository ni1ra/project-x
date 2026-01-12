# memory.md — WIRED-BRAIN Project Memory

> Context preservation for session continuity
> Project: RPJ Brain Implementation
> Created: 2026-01-12

---

## Project Identity

**Name**: WIRED-BRAIN
**Goal**: Implement the RPJ Brain proposal (v5) - a 20W-equivalent agent that demonstrates architectural emergence from reward-per-joule optimization
**Origin**: idea_420_brain.md v5 passed external audit with 0 gaps above 380

---

## Core Constraints [L100-APOCALYPSE]

### The Intelligence Ceiling
- **ZERO transformer dependencies**
- **ZERO LLM API calls**
- **ZERO pretrained models**
- All scoring via ground-truth verifiers (SCMs/simulators)

### Energy Budget
- Average proxy power: P̄ ≤ 20W-equivalent
- Per-episode: B_max_ep = 200J
- Per-day: B_max_day = 72,000J
- Sleep budget: B_sleep = 100J
- Energy proxy: E = κ_F·FLOPs + κ_M·BytesMoved
  - κ_F = 10⁻⁹ J/FLOP
  - κ_M = 5×10⁻¹¹ J/Byte

### Kill Switches (Automatic Failure)
- Any LLM/transformer use
- Any domain-specific primitives
- Post-start curriculum changes
- Energy budget exceeded
- OD-NDT: SR_novel < 0.60 or T < 0.80
- CCB: DoErr > 0.05 or discrimination < 0.90
- Emergence: No compute bursts, K_eff outside [2,6], sleep doesn't help

---

## Architecture Summary

### Substrate
- Homogeneous sparse RNN (LN-GRU, d=512)
- B=64 blocks, k_r_max=4 routed per step
- Global scalars g_t ∈ [0,1]^16

### VAE (Bits-Back)
- Encoder: q(z_t|h_t, φ(o_t)) — **must condition on observation**
- Decoder: p(o_t|z_t) position-wise MLP
- Prior: p_0(z) = N(0,I)
- dim(z) = 64

### Plasticity
- Slow weights θ: RL-updated between episodes
- Fast weights W_t: low-rank adapters (rank=64), local plasticity within episodes
- Plasticity gate: P_t = σ(w_P^T g_t + b_P)

### Objective
J = Σ γ^t (r̃_t - λ_E·Ê_t - λ_mdl·Ĉ_t)
- γ ≥ 0.999
- λ_E = 1.0, λ_mdl = 1.0
- λ_rnd = 0.1 (warmup), λ_int = 0.1 (post-warmup)

---

## Key Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-12 | Encoder must be q(z|h,o) not q(z|h) | Without o_t, it's a prior not posterior; bits-back impossible |
| 2026-01-12 | Online/target encoder split | Prevents representation drift after sleep |
| 2026-01-12 | Imagination uses replay actions | Not policy sampling; imagination is auxiliary training only |
| 2026-01-12 | Binomial sampling for k_r, N | Enables gradient flow through discrete compute decisions |

---

## Audit History

| Version | Date | Auditor | Score | Key Fixes |
|---------|------|---------|-------|-----------|
| v1 | - | - | ~350 | Initial draft |
| v2 | - | Claude | ~380 | LN-GRU explicit, expert demo defined |
| v3 | - | Claude+JARVIS | ~390 | Decoder SGD, k_r Binomial |
| v4 | - | Claude+JARVIS | 378 | E^sleep_max, imagination actions, online/target encoder |
| v5 | 2026-01-12 | Claude+JARVIS | 420* | Encoder q(z|h,o) fixed |

*Provisional pending implementation validation

---

## Current State

### Files
- `/WIRED/WIRED-BRAIN/ALL_WORK.md` - Full backlog (~70 tasks)
- `/WIRED/WIRED-BRAIN/CURR_WORK.md` - Current sprint (Week 1)
- `/WIRED/WIRED-BRAIN/memory.md` - This file
- `/WIRED/WIRED-BRAIN/BLUEPRINT.md` - Full specification from idea_420_brain.md v5
- `/WIRED/WIRED-BRAIN/src/` - Source code
- `/WIRED/WIRED-BRAIN/tests/` - Test suite

### Progress
- Phase: Week 1 Infrastructure (6/7 tasks complete)
- Tests passing: 51/51
- Energy compliance: Proxy implemented, not yet calibrated

### Implemented Components
1. **Energy Proxy** (`src/energy/proxy.py`)
   - FLOP + BytesMoved counting
   - Budget enforcement with kill-switch
   - κ_F = 10⁻⁹ J/FLOP, κ_M = 5×10⁻¹¹ J/Byte (uncalibrated)

2. **Byte Interface** (`src/core/byte_interface.py`)
   - φ(o): bytes → [-1, 1] normalized floats
   - AutoregressiveActionDecoder: GRU(128) + 16-d embeddings

3. **CCB Environment** (`src/benchmarks/ccb.py`)
   - Linear SCM: Y = b_X·X + b_U·U + ε
   - Non-linear CCB-NL: Y = ReLU(b_X·X² + b_U·U) + ε
   - DoErr scorer, confounding discrimination

4. **MF-1 Baseline** (`src/core/mf1_baseline.py`)
   - PPO + GRU agent
   - RolloutBuffer with GAE
   - Integrated energy tracking

---

## Session Recovery Protocol

If context is compacted:
1. Read this file first
2. Read CURR_WORK.md for active tasks
3. Read BLUEPRINT.md for full specification
4. Continue from last TodoWrite state

---

## Critical Equations (Quick Reference)

```
# Energy proxy
E_t = κ_F·FLOPs + κ_M·BytesMoved

# Encoder (MUST condition on o_t)
q(z_t|h_t, φ(o_t)) = N(μ_z, σ_z)
μ_z = W_μ[h_t || φ(o_t)] + b_μ

# Codelength
CodeLen_t = -log p(o_t|z_t) - log p_0(z_t) + log q(z_t|h_t, φ(o_t))

# Intrinsic reward
r^int_t = KL(q(z_t|h_t, φ(o_t)) || q(z_{t-1}|h_{t-1}, φ(o_{t-1})))

# Objective
J = Σ γ^t (r̃_t - λ_E·Ê_t - λ_mdl·Ĉ_t)

# Compute allocation
k_r(t) = 1 + Binomial(k_r_max-1, c_t)
N(t) ~ Binomial(N_max, c_t)
```

---

## Contacts & Resources

- Original proposal: `/WIRED/WIRED-SDK/idea_420_brain.md`
- Validation protocol: `/WIRED/WIRED-SDK/AM_I_DONE.md`
- JARVIS Oracle: `~/.jarvis/jarvis ask`

---

**Last Updated**: 2026-01-12
**Session**: Project initialization
