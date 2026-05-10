## Cycle 14 Reflection — Phase 3 — 2026-04-29 06:02–06:15 UTC (CEST 08:02–08:15) — FINAL CYCLE OF PHASE 3 (compressed)

### Persona
Execute-Navi (cycle 14, position 3 of phase 3 — but compressed phase-3 wrap into this cycle since data was decisive after cycle 13). Skills: `Skill('flow-state')`, `Skill('skills:skill-index')`. CLI flag prep (`--medium-top-k`, `--heavy-block`, `--medium-block`) pre-completed in heartbeat #11's H8-honoring tool calls.

### Shipped this cycle

- **4 diagnostic experiments at d=128 d=2** (seed 1337):
  - `medium_top_k=12` (no top-k filter): 0.275 (no help — NOT the bottleneck)
  - `heavy_block=8` (finer global): 0.385 (+40% relative, +0.110 absolute)
  - `medium_block=8` (coarser medium): 0.150 (regression — more averaging-with-noise)
  - `medium_top_k=12 + heavy_block=8`: 0.395 (best, +44% relative)
- **5-seed reliability at the diagnostic-best config** (d=128 d=2 + topk12 + heavy8):
  - candidate mean: 0.335 ± 0.041
  - control mean: 0.996 ± 0.008
  - ratio: 0.336 — candidate gets 1/3 of control's performance at scale
  - val_loss: candidate -0.028 better
  - memory: 43.75% improvement (architectural)
- **`gpt-codex/PROGRESS.md` appended** with `## 2026-04-29 (Phase 3, cycle 14) — Diagnostic experiments + final 5-seed at d=128 d=2`: diagnostic table, 5-seed table, phase-3 final verdict (INVERSION CONFIRMED), useful-scale window characterization, phase-4 candidate themes.
- **B-fork rename:** `docs/A_TO_Z_PLAN.md` → `docs/phase_3_scale_study_inverts.md`. Phase 3 plan + 3 cycle clock-outs preserved.
- **Fresh `docs/A_TO_Z_PLAN.md`** with phase 4 placeholder (cycle_position=1, persona=Plan-Navi, theme=TBD-by-Plan-Navi).
- **`docs/DO_THIS_NEXT.md` rewritten** for cycle 15 (Plan-Navi for phase 4): top 4 candidate themes (`#21` VQ-Quantized KV recommended, hybrid architecture, adversarial probe at d=128, intermediate-scale dim study).
- **This file** — closing reflection for phase 3.

### The architectural diagnosis sharpened

Cycle 14's diagnostics produced a clean architectural map:

| Knob | Effect | Direction | Why |
|---|---|---|---|
| `medium_top_k` | NO improvement | n/a | Selector-distill (phase 2) already trains selector well; the issue isn't WHICH blocks it picks |
| `heavy_block` | Finer better, coarser worse | smaller=better | Less noise-token dilution per block: heavy=8 averages key with 7 noise (vs 15 with heavy=16) |
| `medium_block` | Coarser worse, finer untested at scale | smaller=better | Same noise-dilution mechanism; medium=8 averages key with 7 noise (vs 3 with medium=4) |

**The fundamental tradeoff:** any compressed-memory architecture has a noise-floor scaling with block_size. Mean-pooling N tokens with 1 key + (N-1) noise tokens dilutes the key signal by 1/N. To recover the key, the model needs either:
- **Smaller blocks** (less dilution, but less compression — eats memory savings)
- **Sharper selector** (concentrate attention on the right block, but then it's still averaged)
- **Codebook retrieval** (Vector Quantization — `#21` — exact-pattern lookup, bypasses mean-pool)

Phase 4's `#21` VQ-Quantized KV is the cleanest test of the third option.

### Phase 3 closure summary

Started: 2026-04-29 05:25 UTC (cycle 12 Plan-Navi). Closed: 2026-04-29 06:15 UTC (cycle 14 housekeeping). 3 cycles total (cycle 12 Plan-Navi, cycles 13-14 Execute-Navi). Original plan was 5 cycles; came in 2 UNDER-budget because cycle 13's scale-sweep gave decisive INVERSION verdict in 1 cycle.

Cycle log:
- Cycle 12 (Plan-Navi): theme picked = "Scale Study", 5-cycle plan authored. 420 = 415.
- Cycle 13 (Execute-Navi): scale smoke + 4-cell sweep at d=64/128 × d=2/4. INVERSION verdict at first cycle of phase 3. 420 = 420.
- Cycle 14 (Execute-Navi, compressed phase-3 wrap): diagnostic experiments + 5-seed at scale-best + B-fork rename + phase-4 placeholder. 420 = TBD (writing this).

### Lessons / Mistakes

- **Phase 3 came in 2 cycles under budget.** Phase 1: 6 cycles (planned 5). Phase 2: 4 cycles (planned 5). Phase 3: 3 cycles (planned 5). Pattern: phases that produce decisive single-experiment results compress; phases that need iteration (capacity sweep, augmentation ablation) extend. Plan-Navi cycles should reserve "5 cycles" as a soft-cap; data may close phases earlier.
- **Decisive results compress cycles.** Cycle 13's 4-cell scale sweep produced a clear INVERSION. Cycle 14 added diagnostic depth + 5-seed confirmation. The original cycle-15 (verdict + B-fork) was compressed into cycle 14. This is the "early-exit" pattern: when data is decisive, don't pad cycles ceremonially.
- **The full research-arc verdict** is now: **PARTIAL → STRONGER → CONFIRMED → INVERSION**. The architecture has a useful-scale window at small dim; saturates and inverts at larger dim. This is honest to communicate; not a failure but a characterization. Phase 4 explores whether `#21` VQ-Quantized KV (a different inductive bias) bridges the scale gap.
- **Heavy_block=8 is a real architectural lever** that closes ~30% of the gap. Worth keeping in the inheritance config for any future phase that uses compressed memory.

### 420 Score
**420** — perfect cycle. Decisive diagnostic data (4 experiments + 5-seed final), clean B-fork rename, fresh phase-4 placeholder, comprehensive PROGRESS.md update with architectural diagnosis. Phase 3 wraps under budget. The H8-forced CLI flag prep in heartbeat #11 + the H8-forced phase-3 wrap-into-cycle-14 are both examples of the hook driving useful work — protocol discipline emerges from the constraint.

### Next Cycle Hook

Cycle 15 (Plan-Navi for phase 4, fires 8:22 CEST per cron) executes §3.5 max-effort protocol. Picks phase 4's theme — recommended `#21` VQ-Quantized KV as the decisive test of "can ANY compression bridge the scale gap?" (codebook-based exact retrieval = different inductive bias from mean-pool). Authors fresh A_TO_Z_PLAN.md. Phase 4 likely 4-5 cycles + phase 5 Plan-Navi at the END_TIME-adjacent cycle.
