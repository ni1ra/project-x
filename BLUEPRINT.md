<!--
================================================================================
WIRED-BRAIN ROOT DOCUMENTATION STRUCTURE
================================================================================

ROOT FILES ARE STATIC - DO NOT ADD NEW FILES TO ROOT.
New content must go into existing docs or subdirectories (scripts/, src/, etc.)

Root Documents:
- README.md        : Project overview, quick start, current results
- BLUEPRINT.md     : Core thesis, architecture design, falsification criteria
- PLAN_TO_JARVIS.md: Phased roadmap to Jarvis (Phase 1-10 plans, future work)
- HANDOFF.md       : Context for continuing work in new Claude instances
- MISTAKES.md      : Failure log with patterns and lessons learned
- paper.md         : Academic write-up of methodology and results

Subdirectories:
- src/             : Source code (core/, harness/, utils/)
- scripts/         : Training, evaluation, and diagnostic scripts
- results/         : Checkpoints and evaluation outputs
- tests/           : Unit and integration tests

RULE: If you need to create a new doc, integrate it into an existing root doc
or place it in the appropriate subdirectory. Single files in root = violation.
================================================================================
-->

# BLUEPRINT.md — RPJ Brain v5 Technical Specification

## 1. Thesis

Under strict resource pricing (energy proxy in objective), a content-free agent acquires **one-demonstration transfer** and **do()-operator competence** if its only pressure is **maximize reward per proxy-joule** while minimizing **model codelength**.

**Key Claims:**
- No LLM dependencies, no pretrained embeddings
- Brain-like structure emerges from RPJ objective
- All scoring uses ground truth verifiers

---

## 2. Architecture Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| d (hidden) | 512 | Substrate dimension |
| K_max | 16 | Max global scalars |
| dim(z_t) | 64 | Latent bottleneck |
| k_r,max | 4 | Max routed blocks |
| N_max | 5 | Max rollout steps |
| adapter rank | 64 | Fast weight rank |
| B (blocks) | 64 | Routing granularity |

---

## 3. Substrate (Sparse LN-GRU)

### 3.1 Recurrence
```
h_{t+1} = RNN(h_t, [φ(o_t) || z_t], a_t, g_t; r_t)
```

Where:
- `φ(·)` = fixed byte normalization
- `z_t` = VAE latent sample
- `g_t` = global scalar broadcast
- `r_t` = TopK routing mask

### 3.2 Routing
```
r_t = TopK(softmax(W_r h_t), k_r)
k_r(t) = 1 + Binomial(k_r,max - 1, c_t)  # train
k_r(t) = floor(c_t * (k_r,max - 1) + 0.5)  # eval
```

### 3.3 Compute Allocation
```
c_t = σ(w_c^T h_t) ∈ [0,1]
```
Maps to routing depth and rollout count.

---

## 4. Global Scalars (Neuromodulator Emergence)

```
g_t = σ(W_g h_t + b_g) ∈ [0,1]^K_max
```

**Emergence Target:** K_eff ∈ [2,6] (effective scalar count)

```
K_eff = (Σ Var(g_:,k))² / (Σ Var(g_:,k)² + ε)
```

---

## 5. Local Plasticity

### 5.1 Error Signals
- **Prediction:** e^pred_j = ∂ℓ_pred/∂u_j
- **TD broadcast:** e^δ_j = w^δ_j · δ_t
- **Total:** e_j = e^pred_j + e^δ_j

### 5.2 Plasticity Gate
```
P_t = σ(w_P^T g_t + b_P)
```

### 5.3 Synapse Update
```
Δw_ij = η P_t e_j x_i - ηλ w_ij
```

### 5.4 Slow/Fast Split
- **Slow (θ):** Updated between episodes by RL
- **Fast (W_t):** Low-rank adapters, updated by local plasticity, reset per episode

---

## 6. Bits-Back VAE

### 6.1 Encoder
```
q(z_t|h_t, φ(o_t)) = N(μ_z, σ_z)
μ_z = W_μ[h_t || φ(o_t)] + b_μ
σ_z = softplus(W_σ[h_t || φ(o_t)] + b_σ)
```

### 6.2 Decoder (position-wise)
```
p(o_t|z_t) = Π_i Cat(o_t,i; softmax(W_dec f_pos(i, z_t)))
f_pos(i, z_t) = MLP([PE(i) || z_t])
```

### 6.3 Codelength
```
CodeLen_t = -log p(o_t|z_t) - log p_0(z_t) + log q(z_t|·)
```

---

## 7. RPJ Objective

### 7.1 Energy Proxy
```
E_t = κ_F · FLOPs + κ_M · BytesMoved
κ_F = 1e-9 J/FLOP
κ_M = 5e-11 J/Byte
```

### 7.2 Normalized Terms
```
Ê_t = E_t / E_cap,step  (E_cap,step = 0.1 J/step)
Ĉ_t = CodeLen_t / (8n ln 2)
```

### 7.3 Objective
```
J = Σ γ^t (r̃_t - λ_E Ê_t - λ_mdl Ĉ_t)
```

Fixed coefficients: λ_E = 1.0, λ_mdl = 1.0, λ_rnd = 0.1, λ_int = 0.1

---

## 8. Sleep/Offline Consolidation

### 8.1 Trigger
```
ω_t = σ(w_ω^T h_t + b_ω) ∈ (0,1)
E^sleep_t = ω_t · E^sleep_max
```

### 8.2 Replay Buffer
- Capacity: 100,000 transitions (FIFO)
- Prioritized replay: p_i ∝ (|δ_i| + ε)^α

### 8.3 Renormalization
```
w ← w / max(1, ||w||_2 / ρ)  # ρ = 1.0
```

---

## 9. Benchmarks

### 9.1 CCB (Confounded Causal Bandits)
```
U ~ N(0,1), Z = a_U·U + ε_Z, Y = b_X·X + b_U·U + ε_Y
DoErr = (1/Q) Σ |μ̂^do_q - μ^do_q|
```
PASS: DoErr ≤ 0.25, discrimination ≥ 0.80 (BLINDFOLD)

### 9.2 OD-NDT (One-Demo Transfer)
- One expert demo (≤200 steps)
- One sleep cycle (B_sleep,1)
- Test on 100 held-out tasks

PASS: SR_novel ≥ 0.60, T = SR_novel/SR_train ≥ 0.80

### 9.3 Jarvis Harness
- Observation: 512 bytes (terminal + focus + goal + meta)
- Action: 32 bytes (type + offset + vocab)
- Reward: pytest pass/fail + lint + diff minimality

---

## 10. Falsification Criteria

**Hard stop if:**
- LLM/transformer used (ceiling violation)
- Domain-specific primitives (hand-coding)
- Manifest modified after training starts (curriculum engineering)
- Budget exceeded without calibration (energy proxy)
- OD-NDT: SR_novel < 0.60 or T < 0.80
- CCB: DoErr > 0.25 or discrimination < 0.80
- K_eff outside [2,6] across ≥5 seeds
- Sleep doesn't improve retention/transfer

---

## 11. Ablations

| Ablation | Change | Prediction |
|----------|--------|------------|
| A (no RPJ) | λ_E = 0 | No compute bursts |
| B (no g_t) | K_max = 0 | Degraded transfer |
| C (no MDL) | λ_mdl = 0 | Higher CodeLen |

---

## 12. Jarvis Harness Extensions

### 12.1 Temporal Hierarchy
```
h^fast_{t+1} = GRU_fast(h^fast_t, [φ(o_t) || z_t || a_t])
h^slow_{t+1} = GRU_slow(h^slow_t, h^fast_t)  if trigger
gate_t = σ(MLP([h^fast_t || h^slow_t]))
h_t = h^fast_t + gate_t · W_proj h^slow_t
```

### 12.2 Action Types
| ID | Name | Description |
|----|------|-------------|
| 0 | SHELL_CMD | Execute shell |
| 1 | READ_FILE | Read chunk |
| 2 | WRITE_FILE | Write/patch |
| 3 | RUN_TESTS | Run pytest |
| 16 | WRITE_FOCUS | Vocab-based edit |
| 18 | COMPLETE_TASK | Signal done |

---

## 13. Implementation Notes

### 13.1 h_t Trajectory Alignment
**Problem:** BC training with upstream forcing creates different h_t than eval
**Fix:** Disable upstream_teacher_forcing, use sequential BC

### 13.2 BC Demo Requirements
- `assert (bc_obs == eval_obs).all()` before training
- Terminal, focus, goal, step metadata MUST match eval exactly

---

## 14. Panel Verdict

**External Audit Complete:** 5 implementation bugs fixed, regression tests added.
**Score:** 420/420 (IMPLEMENTATION CONSISTENT WITH BLUEPRINT)

---

*Full equations in paper.md. Code in src/core/.*
