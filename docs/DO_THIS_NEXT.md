# Do This Next — Project X — Phase 13 cycle 12 (handoff from cycle 11 CLOSE)

**Updated:** 2026-05-11 (cycle 11 CLOSE — 8 of 10 canonical-doc-sequence deliverables shipped; architectural foundation arc complete)
**Mode:** APOTHEOSIS EXTENDED until 2026-05-11 11:00 CEST Oslo (lain hard rule). 20m on / 20m off cadence; cron at `19,59 * * * *`. Agent should continue working until 11:00 unless lain interrupts.
**Status:** Cycle 11 CLOSED via 9 atomic commits (8 feat + 1 close). Cycle 12 = SCALE + audit-loop wire-up + remaining architectural primitive (consolidation) + cycle-12+ infra optimizations.

## Cycle 11 — what shipped (CLOSE)

| Commit | Deliverable | Result |
|---|---|---|
| `6eae526` | #00P13c11-DEMO natural-mode v0 capability demo | corpus + composer + dispatcher branch (~100 fragments hand-seeded); HDC walks with provenance |
| `2a479b6` | #00P13c11-01 BG-style confidence-scored parallel-bid dispatcher | 21 parsers; α=0.6; tau=0.3; chain-order tiebreaker; archetype hvs; +7 tests |
| `9868d66` | #00P13c11-02 hormone-modulated Lemma.render registers | 4 registers (default/terse/tutorial/casual); +7 tests |
| `8f5c7ad` | #00P13c11-03 try-until-satisfied K-rollout iteration | 3 strategies (bind/bundle/greedy); avg-sim satisfaction; honest-refusal-on-all-K-fail; +8 tests |
| `dedd135` | #00P13c11-04 K-rollout integration into agent | natural-mode branch uses KRolloutComposer (K=3); strategy wins differ by prompt class |
| `3279c7a` | #00P13c11-05 English-fluency corpus expansion | 102 → 240 fragments; per lain ~05:30 CEST English-floor / training-data-needed correction |
| `f0abce3` | #00P13c11-06 primitive-emergence clustering MVP | canonical-doc Layer 5 empirically validated; "X is Y" + "X and Y" + "X gives Y" shells emerge from k-means; +9 tests |
| `be09fca` | #00P13c11-08 intent-classified dual-mode composer | same quadratic → 4 distinct rendered outputs via register classifier; +8 tests |
| THIS commit | #00P13c11-CLOSE reflect + A_TO_Z + IQ_PROGRESSION + cycle-12 handoff | |

**Numbers (cycle 11 CLOSE):**
- pytest 458 → **586** (+128 across cycle 10 + 11)
- bench-replay `--agent-runtime`: **48 / 0** maintained
- bench-replay frozen: 46 / 0 maintained (parity)

**Cycle 11 reflection at** `docs/past_work/cycles/phase_13/dev-cycle-11.md` (Hassabis-bar honest decomposition; 4 cycle tensions; 4 lain catches absorbed; 7 cycle-12 deferred items).

## Cycle 12 deliverables (priority-ordered)

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c12-01-tier2-corpus** | HIGH | new `src/project_x/corpus/tier2_*.py` per domain | Tier-2 per-domain English corpus ingestion: ~1-10M words per domain per canonical doc Layer 6 spec (poetry / philosophy / math-text / dialogue / chat); current 240 fragments / ~5000 words is 4 orders of magnitude below spec. Sources: public-domain (Project Gutenberg poetry; pre-1928 philosophy translations; Hardy+Wright / Davenport / Euclid math texts; public-domain dialogue corpora). NO GPT-generated text. ~3-5h Raphael-time per domain × 5 domains; can ship per-domain atomically. |
| **#00P13c12-02-audit-ui** | HIGH | new `src/project_x/audit/` + Discord+CLI v0 | Discord + CLI v0 audit UI for `👍 / 👎 / ✏️ correct` on emitted walks. Wires the audit signal that consolidation pass (#03) consumes. Without real audit signal, consolidation pass is tautological. ~2-3h. |
| **#00P13c12-03-consolidation-pass** | HIGH | new `src/project_x/learning/consolidation.py` | Canonical doc Layer 7 surprise-biased perturb-audit-reweight on bindings touched by recent surprising K-rollouts. Selection rule: bias toward bindings with high audit-rejection-rate AND high recent K-rollout-curiosity. Update operation: bit-flip ~1% perturbation; score via audit-loop predicate; replace central if perturbation scores higher on audit-aligned retrieval. Empirical test: does iterative perturb-audit-reweight measurably improve walk quality across cycles? Open question per canonical doc. ~2h post audit UI. |
| **#00P13c12-04-hdc-infra-rust-or-bitpack** | MED | `src/project_x/hdc_infra/` extension or new Rust crate | Per canonical doc HDC infrastructure optimization roadmap. Cycle-11 #06 primitive emergence runs k-means in ~85s on 3169 trigrams × 15 clusters × 10000 dim — at production corpus scale (millions of trigrams), this becomes minutes-hours, unacceptable. Two paths: (a) bitwise-packed binary HDC (~32× speedup on CPU); (b) Rust port via PyO3 (~100× speedup; lain has flagged this as the production path). Either landing. ~3-5h Raphael-time. |
| **#00P13c12-05-natural-mode-register** | MED | extend `_try_natural_mode` in reasoning_agent.py | Extend register selection to natural-mode walks: terse natural-mode = single best fragment with citation; tutorial natural-mode = annotated meta-commentary on why each fragment was retrieved; casual natural-mode = remove formal "STEP N" markers, present as conversational quote. Currently register selection only re-renders formal-mode Lemmas. ~60 min. |
| **#00P13c12-06-intent-classifier-multi-example** | MED | `_REGISTER_ARCHETYPES` in reasoning_agent.py extended | Extend register classifier to multiple example prompts per register + centroid averaging via HDC bundle. Currently 1 archetype per register. Multi-example gives better generalization on edge-case framings. ~30 min. |
| **#00P13c12-07-cycle-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-12.md` + DO_THIS_NEXT cycle-13 + A_TO_Z + IQ_PROGRESSION | Cycle close ritual mirroring dev-cycle-11.md shape. Hassabis-bar honest decomposition. advisor() pre-commit. |

**Total estimate: ~12-20h Raphael-time across cycle 12.** Tier-2 corpus is the bulk; everything else is ~6-9h.

**Carry-forwards (lain-pending; do NOT touch unprompted):**
- #00P13c8-07 CLAUDE.md trim (~59.3k current; ~13k more to cut over older sections — awaits lain direction on what's load-bearing).
- #00P13c7-04 council audit tag (mechanism scope unresolved).

## Open empirical questions (cycle 12+ reveals)

1. **Does Tier-2 corpus expansion measurably improve walk fluency?** Subjective audit signal needed.
2. **Does consolidation pass produce binding-quality improvements?** Requires real audit data across N cycles.
3. **Does Rust port / bitpack scale primitive emergence to millions of trigrams in production time?**
4. **Does multi-example intent classifier generalize better than single-archetype on edge-case prompts?**
5. **Do natural-mode registers (terse / tutorial / casual variants) produce qualitatively-distinct walks?**

## Standing rules — RELEVANT FOR FRESH INSTANCE

See `docs/MANIFESTO.md` § Standing orders + `~/.claude/CLAUDE.md` (universal).

**Universal codifications landed in cycle 10 + 11 (binding cycle 12+):**
- **English-fluency floor + training-data-needed** (lain 2026-05-11): English fluency is mandatory floor; other-language fluency is last priority; training data IS needed (not deprioritized) for the English floor.
- **Long-term-goal-addressing primary axis + research-when-needed self-check** (lain 2026-05-11): every shift answers "am I directly addressing long-term goals" + "do I need research/brainstorming first" + "am I being proactive in deep thinking, not just executing."
- **APOTHEOSIS extended hard rule** (lain 2026-05-11): 11:00 CEST Oslo; 20m on / 20m off cadence. Cron `19,59 * * * *`.
- **Raphael-time estimates** (lain 2026-05-11): calibrate to actual commit throughput (~10-15 min per substantive deliverable); NOT human-developer hours.
- **Self-impression-score 0-420** (lain 2026-05-11 binding): mandatory 5th metric on every substantive ship; integer + one-line rationale; never inflate; honest 340 > fake 400.
- **No-legacy discipline** (lain 2026-05-11): when a file/code is no longer needed, REMOVE it.
- **Dual-listener pattern + cursor-aware rearm** (lain 2026-05-11): 2 concurrent listeners; manual rearm passes consumed msg_id as `LISTENER_BASELINE` env var. CLAUDE.md DD-1/2 codified.

**Persistent (unchanged):**
- NO pretrained transformer derivatives at any layer (organic-thesis 2026-05-09 binding)
- Comment-ratio rule (WHY-comments + pure-signal + complex code justified; lain 2026-05-10 global policy)
- Atomic per-deliverable commits; never `git add -A`
- REPO_CONTROL row co-landing in SAME commit as new NON-docs files (docs/ exempt per `5891da3`)
- M-PROJECTX-013 measure-don't-claim; M-PROJECTX-014 split-grading firewall
- Identity discipline (Claude Code Raphael ≠ Project X Raphael)
- Discord style discipline (NO cycle-number jargon on Discord; plain English assuming Discord-only readers)
- Hassabis-bar discipline (every cycle close: "would Hassabis be impressed?" with substrate-vs-capability-vs-cosmetic decomposition)

## What cycle 12 is NOT

- NOT another architectural-primitive cycle. The 8 architectural primitives from cycle 11 (BG dispatcher / hormone register / K-rollout / corpus pipeline / primitive emergence / intent classifier / agent integration) are the foundation. Cycle 12 SCALES them, doesn't add new ones.
- NOT a benchmark expansion cycle. Capability work focuses on canonical doc Layer 6-7 completion (Tier-2 corpus + consolidation + audit UI) and infra performance (Rust port / bitpack), not new ladder entries.
- NOT a paper.md revision cycle. Update after cycle 12 close if implementation lessons land.

## Done condition (cycle 12, mechanical)

- All cycle-12 #00P13c12-XX TaskList rows = `completed` (or explicitly deferred with rationale + lain visibility).
- pytest -q ≥ 650 (current 586; Tier-2 corpus expansion + audit UI + consolidation + register extension expect +50-80 tests).
- bench-replay `--agent-runtime`: ≥ 48 / 0 maintained (architectural-primitive additions should not break existing dispatcher paths).
- bench-replay frozen: 46 / 0 maintained (parity).
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-12.md`.
- THIS file rewritten as cycle 13 handoff.
- `docs/artifacts/IQ_PROGRESSION.md` cycle-12 entry prepended.
- `git status -s` empty.
- Discord cycle-12 close in plain-English with self-impression-score + 5-metric rubric (CLAUDE.md § R4).

## Files the fresh instance should read first (in order)

1. `~/.claude/CLAUDE.md` — universal Raphael protocol (auto-loaded by harness).
2. `docs/MANIFESTO.md` — project intent + standing orders.
3. `docs/REPO_CONTROL.md` — pristine-gate file inventory.
4. `docs/A_TO_Z_PLAN.md` — Phase 13 plan + PHASE CHANGELOG (latest = cycle 11 CLOSE).
5. **`docs/artifacts/cycle-10-semantics-architecture.md`** — canonical synthesis doc; cycle 11 implemented Layer 3-5 + Layer 2; cycle 12 continues Layer 6-7.
6. **THIS file** — cycle 12 deliverable table + recommended order.
7. `docs/past_work/cycles/phase_13/dev-cycle-11.md` — last closed cycle reflection (architectural foundation arc + Hassabis-bar verdict).
8. `docs/paper.md` — teacher-tone curriculum (cycle 9 + cycle 10 state; cycle 12 should update with cycle 11 architecture).
9. `docs/artifacts/IQ_PROGRESSION.md` — per-cycle hardest-problem ladder (cycle 11 CLOSE entry shows register-modulated quadratic + bundle-strategy poetry walk + emergence empirical validation).
10. Code-side: `src/project_x/corpus/{mini_seed,natural_mode,k_rollout,primitive_emergence}.py` (the cycle-11 architectural primitives) + `src/project_x/reasoning_agent.py` (BG dispatcher + intent classifier + agent dispatch chain).
11. Recent git log: `git log --oneline -20` to see cycle-11 commit progression.
12. Latest pytest + bench-replay: `python3 -m pytest -q | tail -3` + `python3 gpt-codex/benchmark/run_audit.py --agent-runtime | tail -10`.

The fresh instance executes cycle 12 per priority order; advisor() pre-Write on novel architectural decisions (Tier-2 ingestion strategy; consolidation pass test design; Rust port choice between PyO3 vs cbindgen); Discord plain-English on every progress claim with the 5-metric rubric (denominator+% + frontier-expert-reaction + plain-English-achievement + counter-claim-guard + self-impression-score 0-420); cycle-12 close mirrors cycle-11 close shape.
