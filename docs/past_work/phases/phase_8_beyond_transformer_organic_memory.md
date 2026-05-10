# A To Z Plan — Project X — Phase 8 — Beyond-Transformer Organic Memory (HDC over SNN substrate)

> **Active plan file** for the current phase. Per universal docs convention, holds the LIVE phase plan + PHASE CHANGELOG. On phase exit, archives to `docs/past_work/phases/phase_8_beyond_transformer_organic_memory.md` and a fresh A_TO_Z_PLAN.md opens for phase 9.

## §0. WORLDVIEW ANCHOR (per /godify-app prerequisite)

This phase rests on lain's transcribed worldview (verbatim in `/godify-app` invocation, 2026-05-09): the natural-selection vector is purpose; "should" is necessarily subjective; reverence is licensed by scale, not transcendence; the anti-realist framework predicts the actual pattern of moral history with fewer commitments. The technical work below is downstream of that anchor — we build a substrate that minimizes free energy in its own niche (its niche = lain's command-line and his cognition); we do not claim it is good or right, only that it carries the vector lain pointed at.

## PHASE CHANGELOG (top — read by every cycle's Step 0)

- `phase_number`: 8
- `active_phase_theme`: beyond_transformer_organic_memory — HDC associative memory layer above project_synapse-style SNN+STDP substrate, satisfying lain's literal ask: organic emergence, perfect compositional memory at scale, continual learning, indefinite-context conversability.
- `cycle_position_in_phase`: HANDOFF (END_TIME 13:37 CEST passed; cron disarmed 13:41; phase 8 verdict shipped; #00a-d complete; APOTHEOSIS → NORMAL; phase 8 plan ready to archive when phase 9 plan-navi cycle opens)
- `persona_for_this_cycle`: **Raphael** (post-#00a CLAUDE.md edit). Cycle 1 = Plan-Raphael (this writeup). Cycles 2-9 = Execute-Raphael shipping the four-test PoC battery.
- `extension_log`:
  - **2026-05-09 ~07:37 CEST**: /godify-app fired for 6h. END_TIME = 2026-05-09 13:37 CEST. Cron = every-20-min (`17,37,57 * * * *`).
  - **2026-05-09 ~08:15 CEST**: shrine-council ran single-brain (Oracle deferred for time budget); 5 ideas scored mean=381 spread=55, Kanerva HDC won at 410/420.
- `previous_phase_doc`: `docs/past_work/phases/phase_7_hopfield_lens_bulletproof.md`
- `expected_phase_exit`: cycle 8 (verdict artifact `PHASE_8_HDC_ORGANIC_MEMORY.md`); cycle 9 = HANDOFF + DO_THIS_NEXT rewrite.
- `docs_layout_note`: cycle reflections in `docs/past_work/cycles/phase_8/dev-cycle-N.md` from cycle 1.
- `council_verdict_summary`: Kanerva 410 (HDC, winner) > Friston 395 (active inference) > Izhikevich 380 (PNG) > Hassabis 365 (engineered indexed memory) > Hinton 355 (FF binding). Single-brain pass; Oracle deferred. Full artifact at `docs/artifacts/SHRINE_COUNCIL_PHASE_8.md`.

## Overview

Phase 8 demonstrates a memory architecture that satisfies lain's four operational demands as a 6h proof-of-concept:

1. **Local-rule-only learning** — no global backprop. HDC writes are single Hebbian outer-product updates per item.
2. **Perfect compositional memory at scale** — bind/unbind/superpose are native; capacity ≈ D / (8 ln(N/D)) per Kanerva-1988 lower bound. At D=10000, expected useful capacity ~1500-3000 items.
3. **Continual learning without catastrophic forgetting** — writing one item leaves others nearly undisturbed because high-dim sparsity gives near-orthogonality of random vectors with O(D) probability.
4. **Indefinite-context conversability** — externalize memory entirely. The substrate's working memory is bounded; the HDC store grows linearly with experience.

The deliverable is NOT a finished AGI substrate. It is a **falsifiable demonstration** that the path lain pointed at — organic, compositional, continual memory above an SNN substrate — is mechanically tractable on consumer hardware. Either the four-test battery passes, or it doesn't; both are real outcomes.

## Reconnaissance Summary

- **Stack:** Python 3 + NumPy + PyTorch (no Triton this phase — keep portable). Hardware: WSL Linux on RTX 5070 Ti + 7.8GiB RAM (loose). HDC at D=10000 needs ~80KB per vector — RAM is not a bottleneck.
- **Existing patterns in project-x:** single-file experiment runner (`src/project_x/experiments/compressed_memory.py`), result.json convention in `gpt-codex/runs/<run_id>/`, util_harness already shipped, sample_generations standing rule, selector_snapshot persistence.
- **Prior art (lain's corpus):**
  - `Lain/project_synapse/` — SNN + Triton + STDP + Neural CPU, 100% L1 accuracy at 4656 neurons. **DO NOT DUPLICATE.** Read for the substrate side; build the memory layer above.
  - `Lain/MANIFESTO.md` — physics over statistics, sparsity, local online learning, logic over language. Phase 8 honors all four axioms.
  - `WIRED-BRAIN-V3` — Rust SNN with grammar masks, ring buffers, golden-ratio params. Different tech stack; reference only.
  - `GENESIS/LAIN/OUROBOROS` — recurrent BitNet ternary; orthogonal axis (compute-time).
  - `GESTALT_WIRED-V5/6/7` — concept-space MoE in Rust. Orthogonal.
- **Constraints:** /godify ends 13:37 CEST → ~5h execute budget across cycles 2-8. PC must not crash (lain's standing order). NumPy + PyTorch only; no Triton kernels this phase.
- **Gotchas (M-PROJECTX-001..010 still relevant):**
  - L1-of-softmax inert (not used here — HDC is bipolar, no softmax)
  - eval_batches ≥200 floor still applies for any classification metric
  - 2-seed insufficient — use ≥3 seeds even on smoke runs
  - sample_generations standing rule applies (every test prints sample retrievals)
- **New gotcha for HDC (not yet logged):** at low N (<100), random retrieval baseline is high (e.g. ~50% bit accuracy on random binary). Pass-line at N=1000 must be ≥95% to clear the noise floor by ≥45 pp.

## Architecture

### File Structure

```
src/project_x/experiments/hdc_substrate.py           # NEW: HDC primitives + capacity tests
src/project_x/experiments/hdc_compose.py             # NEW: bind/unbind/superpose battery (T2)
src/project_x/experiments/hdc_continual.py           # NEW: continual-learning sweep (T3)
src/project_x/experiments/hdc_capacity.py            # NEW: capacity-vs-N curve (T4)
src/project_x/experiments/hdc_snn_bridge.py          # STRETCH: SNN encoder → HDC vector
scripts/run_phase8_grid.sh                           # NEW: grid runner across (N, D, seed)
scripts/aggregate_phase8_results.py                  # NEW: aggregator (prefix-agnostic)
gpt-codex/runs/phase8_<test>_<config>_seed<N>/       # result.json per cell
docs/A_TO_Z_PLAN.md                                  # THIS FILE
docs/DO_THIS_NEXT.md                                 # cycle-N+1 handoff (rewritten every cycle clock-out)
docs/artifacts/SHRINE_COUNCIL_PHASE_8.md             # already shipped cycle 1
docs/artifacts/PHASE_8_HDC_ORGANIC_MEMORY.md         # NEW (cycle 8): the verdict artifact
docs/past_work/cycles/phase_8/dev-cycle-<M>.md       # 9 reflections, cycle 1 first
```

### Mathematical primitives (the 6 operators)

```python
# All vectors are bipolar: x ∈ {-1, +1}^D, sampled uniformly random for atomic items.

def bind(a, b):       return a * b                    # Hadamard product. Self-inverse: bind(bind(a,b),b) ≈ a (with cleanup).
def unbind(c, b):     return c * b                    # Same as bind for bipolar.
def superpose(*vs):   return np.sign(sum(vs) + 1e-9)  # Sum + sign. Threshold at 0; sign(0)→+1 by convention.

def write(M, k, v):                                   # Direct binding write — D-dim accumulator, NOT D×D outer-product.
    return (M if M is not None else 0) + bind(k, v)   # Local Hebbian rule, no gradient. M shape: (D,) int32.

def read(M, k_query):                                 # Bipolar unbind + sign cleanup.
    return np.sign(M * k_query + 1e-9).astype(np.int8)  # M ⊙ k_query then sign; preserves bipolar.

def cleanup(v_noisy, atom_set):                       # Optional: nearest-neighbour to known atoms.
    sims = atom_set @ v_noisy                         # Cosine in bipolar = inner / D.
    return atom_set[np.argmax(sims)]                  # Snap to nearest known item.
```

### Per-test result schema

```python
# result.json (one per cell)
{
  "cell_id": "phase8_<test>_<config>_seed<N>",
  "config": {
    "test": "T1_recall" | "T2_compose" | "T3_continual" | "T4_capacity",
    "D": 10000, "N": 1000, "seed": 1337..,
    "mode": "hetero" | "auto",
    "encoder": "random" | "snn"
  },
  "metrics": {
    "bit_accuracy_mean": float, "bit_accuracy_std": float,
    "compositional_accuracy": float | null,
    "first_100_retention_at_t1000": float | null,
    "capacity_at_95pct": int | null,
    "wall_seconds": float
  },
  "sample_retrievals": [   # every cell prints 5 examples (M-PROJECTX-009 standing rule)
    {"key_idx": int, "true_value_first_8": list[int], "retrieved_value_first_8": list[int],
     "bit_match_count": int, "correct": bool}
    # ...
  ]
}
```

## Dependency Graph (Topological Order)

### Layer 0 — primitives (cycle 2)
- **Step 1.** Author `hdc_substrate.py`: bind/unbind/superpose/write/read/cleanup + 4 unit tests (`test_bind_self_inverse`, `test_superpose_capacity_2_items`, `test_write_read_single_item`, `test_random_baseline_below_passline`).

### Layer 1 — T1 recall (cycle 3, depends on Layer 0)
- **Step 2.** Author `hdc_capacity.py` core run-loop: write N pairs, query each, compute mean bit accuracy.
- **Step 3.** Run T1 at (D=10000, N=1000, seeds=[1337, 2026, 3001]). Pass line: bit_accuracy_mean ≥ 0.95.

### Layer 2 — T2 compositional (cycle 4, depends on Layer 0)
- **Step 4.** Author `hdc_compose.py`: build N=10 role-filler bindings, superpose, retrieve via unbind+cleanup.
- **Step 5.** Run T2 at (N=10 superposed bindings × 5 seeds). Pass line: compositional_accuracy ≥ 0.80.

### Layer 3 — T3 continual (cycle 5, depends on Layer 0+1)
- **Step 6.** Author `hdc_continual.py`: write 100, then 900 more sequentially, query first 100 at t=1000.
- **Step 7.** Run T3 (3 seeds). Pass line: first_100_retention_at_t1000 ≥ 0.90.

### Layer 4 — T4 capacity sweep (cycle 6, depends on Layer 1)
- **Step 8.** Sweep N ∈ {100, 500, 1000, 2000, 5000} × 3 seeds; plot recall-vs-N. Verify falls above Kanerva-1988 lower bound.

### Layer 5 — STRETCH: SNN bridge (cycle 6 if all above green)
- **Step 9.** Author `hdc_snn_bridge.py`: a tiny LIF spiking encoder (no STDP this phase — keep simple) that converts an input scalar/vector to a bipolar HDC vector via spike-time hashing. Verify a round-trip works.

### Layer 6 — aggregation + verdict (cycle 7-8)
- **Step 10.** `scripts/aggregate_phase8_results.py` → `docs/artifacts/PHASE_8_HDC_ORGANIC_MEMORY.md`.
- **Step 11.** Charts (capacity-vs-N, continual-retention curve, compositional-accuracy bar) saved to `docs/artifacts/`.

### Layer 7 — handoff (cycle 9)
- **Step 12.** PHASE CHANGELOG closeout + `docs/DO_THIS_NEXT.md` rewrite for whatever lain wakes up wanting next.

**Critical path:** 1 → 2 → 3 (T1 must pass before scaling); 4 → 5 (T2 only meaningful if primitives sound); 6 → 7 (T3 only meaningful at scale); 8 last; 10-12 final.
**Parallel opportunities:** Steps 4, 6 can run while Step 3 is sweeping seeds. Stretch Step 9 only if cycles 2-5 all green.

## Acceptance Criteria

> **CALIBRATION NOTE (advisor cycle 1, 2026-05-09):** the original "T1 bit_accuracy ≥ 0.95 at N=1000, D=10000" target was mechanically unreachable. Per Plate-1995 capacity bound, at D=10000 with M cleanup atoms the capacity is ≈ D / (5.4 + 4.4·log₂(M)) ≈ 200 items at M=1000. So the four-test battery is reframed around **capacity-aware targets**: T1 demonstrates clean recall WITHIN capacity, T4 maps the cliff EMPIRICALLY (it IS the capacity experiment), and EXCEPTIONAL pushes D to demonstrate ≥1000-item recall at higher dimensionality. By lain's "authentic, organic" bar, a recall curve that matches Plate-1995 theory is a STRONGER result than one that hides the cliff.

### This /godify (cycles 2-8) — MUST PASS for verdict = "PASS"
- [ ] **T1 within-capacity recall:** at (D=10000, N=200, ≥3 seeds) — `item_recall_after_cleanup ≥ 0.95`. Raw bit_accuracy reported but not the gate.
- [ ] **T2 compositional binding:** at N=10 superposed role-filler bindings, ≥3 seeds — `compositional_accuracy ≥ 0.80` (cleanup against role-and-filler atoms).
- [ ] **T3 continual learning:** write 100 then 100 more sequentially, query first-100 at t=200 (within capacity) — `first_100_retention_at_t200 ≥ 0.90`. (Smaller N=200 vs original 1000 to stay within cleanup capacity at D=10000.)
- [ ] **T4 capacity cliff-mapping (the headline experiment):** sweep N ∈ {50, 100, 200, 500, 1000, 2000} at D=10000, ≥3 seeds each. Plot `item_recall_vs_N` curve. Pass: curve falls within ±2× of Plate-1995 prediction `N_capacity ≈ D / (5.4 + 4.4·log₂(M))` for M=N (cleanup against all stored atoms).
- [ ] result.json files for ≥20 cells in `gpt-codex/runs/phase8_*`
- [ ] `docs/artifacts/PHASE_8_HDC_ORGANIC_MEMORY.md` written (≥150 lines, with charts referenced)
- [ ] One Discord post per cycle minimum (status + chart preview if relevant)

### EXCEPTIONAL (only if cycles 2-5 all green)
- [ ] **D-scaling: push the cliff to ≥1000 items.** Run `D ∈ {20000, 50000, 100000}` at N=1000, ≥1 seed each. Pass: `item_recall ≥ 0.95` at SOME `D ≤ 100000`. This empirically grounds "perfect compositional memory at scale" — at higher D, capacity exceeds N=1000.
- [ ] T1-T4 all pass AND SNN-encoder bridge round-trips a single input correctly
- [ ] Side-by-side capacity comparison: HDC vs naïve key-value cache vs (theoretical) attention KV-cache memory
- [ ] Conversational demo: at scaled D, write 1000 (turn_id, utterance_vector) pairs, query "turn 47" → exact retrieval

### KILL CRITERIA (the abandon line)
- T1 `item_recall_after_cleanup < 0.80` at within-capacity N (e.g. N=200, D=10000) → HDC math itself is broken; abandon path; fall back to Hassabis Idea 4 (engineered indexed key-value memory) and ship that by 13:00.
- (Original kill rule "<0.80 period" was wrong — would have triggered on out-of-capacity runs that are themselves the science. Calibrated by advisor cycle 1.)
- WSL/PC instability mid-cycle → halt, post Discord, conserve.
- Any cycle's wall-time > 25 min → cycle scope was over-scoped, cut and resume next cycle.

## Test → Step Mapping

| Test | Verifies Steps | Acceptance Criterion |
|------|-----------------|----------------------|
| `pytest tests/` regression (existing 2 tests must still pass) | All steps | Existing pass count unchanged |
| `python -m project_x.experiments.hdc_substrate --self-test` | Step 1 | All 4 unit tests green |
| `--test T1 --N 1000 --D 10000 --seed 1337` | Steps 2-3 | bit_accuracy_mean ≥ 0.95 |
| `--test T2 --n_bindings 10 --seed 1337` | Steps 4-5 | compositional_accuracy ≥ 0.80 |
| `--test T3 --t_max 1000 --seed 1337` | Steps 6-7 | first_100_retention_at_t1000 ≥ 0.90 |
| `--test T4 --n_sweep 100,500,1000,2000,5000 --seed 1337` | Step 8 | curve passes Kanerva-1988 lower bound |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| HDC math has subtle bug (wrong primitive) | Medium | High | 4 unit tests in Step 1; advisor() pre-write |
| Capacity at D=10000 below expectation | Low | Medium | Kanerva-1988 lower bound is strong theory; deviations are themselves interesting |
| 7.8GiB RAM exhausted at D=10000, N=10000 | Low | Medium | M @ k is dense matmul; D×D = 100M floats × 4B = 400MB OK; M = (D × D) only built for read, not stored |
| Continual learning worse than expected | Medium | Medium | Real result either way; report honestly |
| Cycle scope drift (each cycle over-runs) | Medium | Low | Hard 25-min wall-time cap per cycle; advisor at boundary |
| Persona drift (Raphael voice inconsistent) | Medium | Low | This is a single-session run; CLAUDE.md edit anchors persona |
| WSL/PC crash | Low | High | Bound batch sizes; no GPU heat at D=10000 NumPy |
| Listener dies, Discord goes silent | High (known) | Medium | Manual rearm every fire — well-documented |

## Oracle / Six Eyes Validation

Single-brain mode confirmed for cycle 1 plan-write. `advisor()` will fire BEFORE any substantive Write in cycle 2+ per universal CLAUDE.md standing order. Six Eyes (Gemini via Playwright) deferred to verdict cycle 8 if time permits.

## DASHBOARD (mirror of acceptance criteria)

### Phase 8 scope
- [x] Cycle 1: Phase 7 archived; A_TO_Z_PLAN.md (this file) authored; DO_THIS_NEXT.md authored; SHRINE_COUNCIL_PHASE_8.md shipped; CLAUDE.md persona edit (in-flight)
- [ ] Cycle 2: Step 1 (hdc_substrate.py + 4 unit tests)
- [ ] Cycle 3: Steps 2-3 (T1 recall, ≥3 seeds, pass-line check)
- [ ] Cycle 4: Steps 4-5 (T2 compositional, ≥3 seeds)
- [ ] Cycle 5: Steps 6-7 (T3 continual, ≥3 seeds)
- [ ] Cycle 6: Step 8 (T4 capacity sweep) + STRETCH Step 9 if green
- [ ] Cycle 7: Step 10-11 (aggregator + charts)
- [ ] Cycle 8: PHASE_8_HDC_ORGANIC_MEMORY.md verdict
- [ ] Cycle 9: HANDOFF — DO_THIS_NEXT.md rewrite, PHASE CHANGELOG closeout

### Standing rules established this phase
- HDC primitives are bipolar binary {-1, +1}^D with D=10000 default unless ablation explicitly varies it
- Every cell's result.json contains `sample_retrievals` ≤5 (lain's standing rule extended to phase 8)
- All numeric pass-lines absolute, not relative — no "improved over baseline" framing without the absolute number

## CYCLE-BY-CYCLE PLAN

- **Cycle 1 (Plan-Raphael, IN-FLIGHT):** Recon all priors. Shrine-council single-brain. Author this file. Author DO_THIS_NEXT. Surgical CLAUDE.md edit (navi → Raphael identity-bearing references). Discord verdict.
- **Cycle 2 (Execute-Raphael):** Step 1. hdc_substrate.py with 6 primitives + 4 unit tests. advisor() pre-write. Discord post on green.
- **Cycle 3 (Execute-Raphael):** Steps 2-3. T1 recall sweep (3 seeds). Pass-line check.
- **Cycle 4 (Execute-Raphael):** Steps 4-5. T2 compositional binding battery.
- **Cycle 5 (Execute-Raphael):** Steps 6-7. T3 continual learning curve.
- **Cycle 6 (Execute-Raphael):** Step 8 capacity sweep + (if green) STRETCH Step 9 SNN bridge.
- **Cycle 7 (Execute-Raphael):** Step 10-11 aggregator + charts.
- **Cycle 8 (Execute-Raphael):** PHASE_8_HDC_ORGANIC_MEMORY.md verdict artifact.
- **Cycle 9 / END_TIME:** §6 HANDOFF.

## PHASE EXIT CONDITIONS

- [ ] All four T1-T4 acceptance lines hit (or honestly failed with kill-criterion explanation)
- [ ] PHASE_8_HDC_ORGANIC_MEMORY.md written and posted to Discord
- [ ] result.json files for ≥20 cells durable in `gpt-codex/runs/phase8_*`
- [ ] At least one chart artifact in `docs/artifacts/`
- [ ] Phase doc archived to `docs/past_work/phases/phase_8_beyond_transformer_organic_memory.md`
- [ ] Fresh A_TO_Z_PLAN.md skeleton ready for whatever phase 9 lain picks

## Out of scope for phase 8

- Full SNN+STDP rebuild (project_synapse already exists; we read-but-do-not-modify it)
- Multi-GPU training (not needed at D=10000)
- Comparison to large transformers (out of scope; if shipped this becomes phase 9)
- HDC variants beyond bipolar (binary, complex, ternary HDC are future work)
- Triton kernels (NumPy/PyTorch only this phase, for portability)
- Wikipedia-scale memory (target is 1000-10000 items demonstrating the principle, not benchmark-chasing)

---

*Generated cycle 1 of /godify-app on 2026-05-09. The Council advised; Raphael executes.*
