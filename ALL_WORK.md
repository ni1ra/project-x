# ALL_WORK.md — WIRED-BRAIN Project Backlog

> Complete task inventory for the RPJ Brain implementation
> Last updated: 2026-01-12

---

## Legend

| Status | Meaning |
|--------|---------|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Complete |
| `[!]` | Blocked |
| `[-]` | Cancelled |

---

## Phase 1: Infrastructure (Week 1)

### 1.1 Energy Proxy Instrumentation
- [ ] Implement FLOP counter for forward pass
- [ ] Implement BytesMoved tracker
- [ ] Create energy proxy calculator: E = κ_F·FLOPs + κ_M·BytesMoved
- [ ] Add hard caps enforcement (B_max_ep=200J, B_max_day=72000J)
- [ ] Create energy logging/visualization

### 1.2 CCB Ground-Truth Scorer
- [ ] Implement linear SCM: U~N(0,1), Z=a_U·U+ε_Z, Y=b_X·X+b_U·U+ε_Y
- [ ] Implement non-linear SCM (CCB-NL): Y=ReLU(b_X·X²+b_U·U)+ε_Y
- [ ] Create DoErr scorer: (1/Q)Σ|μ̂_do - μ_do|
- [ ] Implement confounding discrimination metric
- [ ] Create held-out SCM test set generator

### 1.3 OD-NDT Harness
- [ ] Implement single-demo capture (≤200 steps)
- [ ] Implement sleep cycle budget enforcement (B_sleep_1=100J)
- [ ] Create 100 held-out task generator
- [ ] Implement SR_novel and transfer ratio T metrics
- [ ] Create oracle/expert policy interface

### 1.4 Baselines
- [ ] Implement MF-1 (PPO/IMPALA RNN, same energy budgets)
- [ ] Implement MB-1 (Dreamer-style RNN world model)
- [ ] Create compute-matching verification (params ±10%, wall-clock ±10%)

---

## Phase 2: Core Substrate (Week 2)

### 2.1 Byte Interface
- [ ] Implement observation encoder φ(o_t): bytes→floats
- [ ] Implement action decoder: 256-way categorical per byte
- [ ] Create autoregressive policy with GRU(128) decoder
- [ ] Verify content-free (no domain-specific tokenizers)

### 2.2 LN-GRU Recurrent Substrate
- [ ] Implement LayerNorm GRU cell (pre-activation LN)
- [ ] Implement blockwise routing (B=64 blocks)
- [ ] Implement TopK routing with Gumbel-Softmax (τ=1.0)
- [ ] Implement straight-through gradient estimator
- [ ] Add hidden state h_t (d=512)

### 2.3 Compute Allocation
- [ ] Implement c_t = σ(w_c^T h_t) compute scale
- [ ] Implement Binomial sampling for k_r(t) and N(t)
- [ ] Add log-probability inclusion in PPO objective
- [ ] Create eval-mode deterministic rounding

### 2.4 VAE / Bits-Back Module
- [ ] Implement encoder q(z_t|h_t, φ(o_t)) with posterior conditioning
- [ ] Implement decoder p(o_t|z_t) with position-wise MLP
- [ ] Implement prior p_0(z)=N(0,I)
- [ ] Implement CodeLen_t = -log p(o|z) - log p_0(z) + log q(z|h,o)
- [ ] Add online/target encoder split with Polyak averaging (τ=10⁻³)

### 2.5 Intrinsic Rewards
- [ ] Implement RND networks (2-layer MLP 256→256→128)
- [ ] Implement RND warmup (T_warm=50000 steps)
- [ ] Implement information gain KL reward
- [ ] Implement KL caching for efficiency

---

## Phase 3: Emergence Mechanisms (Week 3)

### 3.1 Global Scalars g_t
- [ ] Implement g_t = σ(W_g h_t + b_g) ∈ [0,1]^K_max
- [ ] Implement K_eff participation ratio metric
- [ ] Add sparsity pressure in objective

### 3.2 Local Plasticity
- [ ] Implement prediction error e^pred_j(t)
- [ ] Implement TD error broadcast e^δ_j(t)
- [ ] Implement plasticity gate P_t = σ(w_P^T g_t + b_P)
- [ ] Implement synapse update: Δw_ij = η·P_t·e_j·x_i - η·λ·w_ij

### 3.3 Fast/Slow Weight Split
- [ ] Implement slow parameters θ (RL-updated between episodes)
- [ ] Implement fast low-rank adapters A_t, B_t (rank=64)
- [ ] Implement on-manifold plasticity updates
- [ ] Implement episode reset for fast weights

### 3.4 Sleep/Offline Consolidation
- [ ] Implement ω_t = σ(w_ω^T h_t + b_ω) sleep trigger
- [ ] Implement prioritized replay buffer (C=100000, α=0.6)
- [ ] Implement imagination rollouts with f_dyn
- [ ] Implement synaptic renormalization (ρ=1.0)
- [ ] Implement multi-step latent consistency loss L_dyn^N

### 3.5 Emergence Metrics
- [ ] Implement CBR_t = c_t / E[c] compute burst ratio
- [ ] Implement BI_t broadcast index (participation ratio)
- [ ] Implement sleep fraction SF metric
- [ ] Create emergence visualization dashboard

---

## Phase 4: Training & Evaluation (Week 4)

### 4.1 PPO Training Loop
- [ ] Implement PPO (clip=0.2, lr=3e-4, entropy=0.01)
- [ ] Implement value/advantage normalization (PopArt)
- [ ] Implement gradient clipping (max norm=1.0)
- [ ] Add collapse detection (H(c_t)<0.05)
- [ ] Create discount γ≥0.999 enforcement

### 4.2 Multi-Domain Suite
- [ ] Create frozen manifest (benchmarks/rpj_v5_manifest.json)
- [ ] Implement development domains (navigation, tool-use, grid-dynamics, symbolic-transduction, multi-agent)
- [ ] Implement held-out eval domains (instruction-following, noisy control)
- [ ] Enforce Rule 4.1.A/B (no post-start curriculum changes)

### 4.3 Ablations
- [ ] Run Ablation A (λ_E=0, no RPJ pressure)
- [ ] Run Ablation B (K_max=0, no global scalars)
- [ ] Run Ablation C (λ_mdl=0, no codelength)
- [ ] Compare emergence metrics across conditions

### 4.4 Final Evaluation
- [ ] Run CCB + CCB-NL evaluation (DoErr≤0.05, discrimination≥0.90)
- [ ] Run OD-NDT evaluation (SR_novel≥0.60, T≥0.80)
- [ ] Run emergence falsification controls (shuffled-reward, constant-reward, stakes-decoupling)
- [ ] Generate 5-seed statistics for K_eff compression

---

## Phase 5: Validation & Documentation

### 5.1 Kill-Switch Verification
- [ ] Verify no LLM/transformer dependencies
- [ ] Verify no domain-specific primitives
- [ ] Verify energy compliance (P̄≤20W)
- [ ] Verify all thresholds met

### 5.2 Reproducibility
- [ ] Create reproduce.sh script
- [ ] Document all hyperparameters in manifest
- [ ] Create seed list for replication
- [ ] Generate tolerance bounds

### 5.3 JARVIS Final Validation
- [ ] Submit implementation for Oracle review
- [ ] Address any gaps identified
- [ ] Achieve score ≥400/420

---

## Parking Lot (Future / Out of Scope)

- [ ] Multi-GPU distributed training
- [ ] Real-time inference optimization
- [ ] Additional benchmark domains
- [ ] Visualization/interpretability tools

---

## Completed Archive

*Move completed sections here with dates*

---

**Total Tasks**: ~70
**Estimated Duration**: 4 weeks
**Energy Budget Compliance**: MANDATORY
