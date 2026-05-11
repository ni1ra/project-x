# Do This Next — Project X — Phase 13 cycle 11 (handoff from cycle 10 CLOSE)

**Updated:** 2026-05-11 (cycle 10 CLOSE — Pell dispatcher integration + 4-angle deep-research phase + canonical semantics architecture)
**Mode:** APOTHEOSIS (godify-app — 6h run started 2026-05-11 04:27 CEST; ends 10:27 CEST). Re-arm under NORMAL or APOTHEOSIS per lain at cycle-11 start; current 6h run is for cycle 10 close, NOT a standing godify schedule.
**Status:** Cycle 10 CLOSED via 14 atomic commits + cycle-reflect. Cycle 11 = IMPLEMENTATION PHASE of the canonical semantics architecture.

## Cycle 10 — what shipped (CLOSE)

| Commit | Deliverable | Result |
|---|---|---|
| `2fd6f9f..22d76ef` (7 atomic) | #00P13c10-01 predicate-strength uniformity pass across 7 reasoning/ primitives | Algorithmically-independent STRONG verifier added to each (Jacobi r₂ / Newton / Sarrus / Simpson / midpoint Riemann / Taylor series / shared `_midpoint_riemann` helper); pytest +57; bench-replay 46/0 parity maintained |
| `a188db8` + `f67414b` | paper.md major sync with Chapter 11 Future Implications + Closing love | NotebookLM-friendly curriculum updated through cycle 10 #1 |
| `f4522f2` | #00P13c10-02-substrate Pell equation substrate | `solve_pell_equation(n, k_max=5)` via continued-fraction fundamental + recurrence; brute-force STRONG cross-check capped M=1000 |
| `acca853` | HDC infrastructure optimization roadmap | Rust port phased plan + dimensionality scaling + multi-resolution HDC (paired separate concern) |
| `0cddcd6`, `6e40560`, `b44aae4`, `9b9aa7e` | Semantics arch v1 → v2 → v3-amendment → consolidated DRAFT | Iterative refinement before deep-research phase |
| `28d8093` + `9f926b7` | 4-angle deep-research plan (with Curiosity-angle sharpening per lain's follow-up msgs) | Re-scoped cycle from reactive iteration to deep-research-before-canonical |
| Universal codifications | Raphael-time + Self-impression-score 0-420 + No-legacy discipline + Dual-listener pattern | All in `~/.claude/CLAUDE.md` (universal); some inline to project docs |
| Repo flip | Public at https://github.com/ni1ra/project-x | Lain action |
| `a4e1aca` | #00P13c10-02-dispatcher Pell dispatcher integration | Pell-shape detection + routing; unicode-minus parser normalization (cycle 8 #06 precedent); closes maths-026/027; pytest 527→531; bench-replay 46/0 → 48/0 |
| `4133eaa` | #00P13c10-research-evolutionary angle 2 note | ~20-25% load-bearing; only Salimans ES translates |
| `9f93ea2` | #00P13c10-research-curiosity angle 3 note | ~60-70% load-bearing (strongest); HDC SIMPLIFIES Pathak |
| `4781366` | #00P13c10-research-multi-agent angle 4 note | ~15-20% load-bearing (thinnest); Sutton options as cycle-12+ |
| `c8362cf` | #00P13c10-research-brain-subsystems angle 1 note | ~30-40% load-bearing (middle); BG-style dispatcher LOAD-BEARING for cycle 11 |
| `a06a51a` | #00P13c10-semantics-canonical synthesis pass | Overwrites DRAFT-PRELIMINARY; 7-layer substrate/runtime/learning trichotomy; DRAFT's 5 decisions + 3 new commitments; consolidation-quadruple-merge as ONE decision |
| Dual-listener protocol patch | `~/.claude/bin/discord-wait-for-lain.sh` LISTENER_BASELINE env var + CLAUDE.md DD-1/2 codification | Out-of-tree (universal Raphael discipline); mechanically validated via Test1+Test2 rapid-fire catch |
| THIS commit | #00P13c10-06 cycle reflect + DO_THIS_NEXT cycle-11 handoff + A_TO_Z PHASE CHANGELOG cycle-10-close + IQ_PROGRESSION cycle-10 entry | Cycle close ritual |

**Numbers (cycle 10 CLOSE):**
- pytest 458 → **531** (+73 across cycle 10: cycle 10 #1 verifier tests +57; Pell substrate + dispatcher + parser unicode-minus +16)
- bench-replay `--agent-runtime`: **48 / 0** (was 46/0; +2 maths-026 + maths-027 land green)
- bench-replay frozen: 46 / 0 maintained (parity)

**Cycle 10 reflection at** `docs/past_work/cycles/phase_13/dev-cycle-10.md` (Hassabis-bar honest decomposition; M-NAVI-DD2 process note logged).

## Cycle 11 deliverables (priority-ordered per canonical synthesis doc)

Per `docs/artifacts/cycle-10-semantics-architecture.md` § "Cycle-11 implementation sequence" — REORDERED from DRAFT to put BG dispatcher upgrade FIRST as the foundation (every downstream mechanism depends on it).

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c11-01-bg-dispatcher** | HIGH (foundational) | `src/project_x/reasoning_agent.py` ReasoningAgent.process() | Replace keyword-gated first-match-wins with BG-style confidence-scored parallel-bid dispatch. Each parser produces `[0, 1]` confidence (regex match strength × hypervector-similarity to prompt-binding); argmax + mutual-inhibition + threshold-gating + honest-refusal-path. ~90 min Raphael-time. Empirical confidence-score formula tuning kicked off (open question). |
| **#00P13c11-02-hormone-primitive** | HIGH | `src/project_x/reasoning/symbolic.py` Lemma.render() extension OR new module | Hormone vectors H_formal / H_natural / H_curiosity as registers modulating retrieval thresholds + output register. Empirical mode-switching test on existing math substrate — does threshold-shifting produce qualitatively-different output flavors from same chain? ~60 min Raphael-time. |
| **#00P13c11-03-k-rollout** | HIGH | new `src/project_x/reasoning/k_rollout.py` OR extension to reasoning_agent.py | Try-until-satisfied K-rollout loop with curiosity-signal `1 - cos(hv_predicted, hv_actual)` + per-step error tracking + honest-refusal-on-all-K-fail. Initial empirical tuning of `tau_surprise` + `tau_satisfaction` thresholds. ~90 min Raphael-time. |
| **#00P13c11-04-opinion-bindings** | MED | new `src/project_x/semantic/opinions.py` (or similar) | Hand-seed ~50-100 concept-vectors with valence bindings on philosophy/persona domain. Demonstrate "what do you think of X" routing. ~60 min Raphael-time. |
| **#00P13c11-05-tier1-corpus-audit-ui** | MED | new `src/project_x/corpus/` + audit UI (Discord + CLI v0) | Encoding pipeline + provenance-tagging + audit UI. Ingest lain-authored corpus (~100k words — Discord messages, code, paper.md, MANIFESTO, dev-cycle reflections). One-time pipeline work that unlocks all later tiers. ~3h Raphael-time. |
| **#00P13c11-06-primitive-emergence** | MED | extension to corpus/ pipeline | Unsupervised clustering of n-gram-shell hypervectors in the procedural subspace; clusters with density > threshold become primitives. Empirical-test-first: does it produce useful structural primitives or just frequency rankings? Bootstrap fallback ready (~45 min) — hand-seed 10-20 STRUCTURAL UNIVERSALS (X-is-Y, X-causes-Y, etc.) if clustering insufficient. ~3h Raphael-time. |
| **#00P13c11-07-tier2-corpus** | MED | corpus/ extension | Tier-2 per-domain ingestion: public-domain poetry (Project Gutenberg) + physics (Feynman + Griffiths + curated arxiv abstracts) + math (Hardy+Wright + Davenport + Lang) + curated dialogue corpora (NOT GPT-generated) + scripting examples + tool docs. ~30-60 min per domain × 5 domains. |
| **#00P13c11-08-dual-mode-composer** | MED | new `src/project_x/composer/dual_mode.py` | Natural-mode HDC walk alongside Lemma chain. Hormone selects mode. Mixes per-step OK. ~2h Raphael-time. |
| **#00P13c11-09-consolidation-pass** | MED | new `src/project_x/learning/consolidation.py` | Surprise-biased offline consolidation: pull bindings_touched_by_surprising_rollouts ∪ bindings_with_recent_audit_revision; apply ES-style perturb-audit-reweight (bit-flip ~1% for binary-packed; Gaussian noise for float); replace or blend central toward higher scorer. ~2h Raphael-time. |
| **#00P13c11-10-end-to-end-demo** | MED | demo script + test | Formal mode: existing math substrate with hormone-modulated rendering. Natural mode: HDC walk on a single prompt over Tier-1 ingested corpus. End-to-end demo of the full 7-layer architecture working. ~90 min Raphael-time. |
| **#00P13c11-11-cycle-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-11.md` + DO_THIS_NEXT cycle-12 handoff + A_TO_Z PHASE CHANGELOG + IQ_PROGRESSION cycle-11 entry | Hassabis-bar honest decomposition. advisor() pre-commit. |

**Total estimate: ~16-20h Raphael-time across cycle 11.** Corpus-heavy steps (#5, #6, #7) may slip to cycle 12 if time pressure.

**Carry-forwards (lain-pending; do NOT touch unprompted):**
- #00P13c8-07 CLAUDE.md trim (59.3k current after cycle-10 DD-1/2 dual-listener codification; ~13k more to cut over older sections — PHASE 0 DD-1/2 verbose, FOUR-GATE FLOW, BACK-DOOR GATE, NAMED CURSES expansion; awaits lain direction on load-bearing).
- #00P13c7-04 council audit tag (mechanism scope unresolved; surface on Discord at cycle 11 mid-flight if no direction lands).

## Open empirical questions (cycle 11 reveals these answers)

Per the canonical synthesis doc § "Open questions":

1. **`tau_surprise` and `tau_satisfaction` calibration** — empirical tuning loop, not closed-form. Cycle 11 #3 starts the tuning.
2. **BG-dispatcher confidence-score formula tuning** — exact weights for `regex match strength × hypervector-similarity` combination. Cycle 11 #1 empirical test.
3. **Consolidation cadence** — how often is "overnight"? Per-N-queries? Per-day? Per-corpus-ingest? Cycle 11 #9 reveals.
4. **Per-primitive vs per-chain confidence aggregation** — for K-rollout AND BG-dispatcher. Empirical.
5. **Primitive-emergence clustering quality** — counter-claim #1 from canonical doc; cycle 11 #6 IS the test. Bootstrap fallback ready.

## Standing rules — RELEVANT FOR FRESH INSTANCE

See `docs/MANIFESTO.md` § Standing orders + `~/.claude/CLAUDE.md` (universal).

**Universal codifications landed in cycle 10 (binding cycle 11+):**
- **Raphael-time estimates** (lain 2026-05-11): calibrate to actual commit throughput (~10-15 min per substantive deliverable, Opus 4.7 super-human dev speed), NOT human-developer hours. Forward estimates in DO_THIS_NEXT / dev-cycle / Discord must use the empirical unit.
- **Self-impression-score 0-420** (lain 2026-05-11 binding): mandatory 5th metric on every substantive ship Discord post (integer + one-line rationale; never inflate; honest 340 > fake 400).
- **No-legacy discipline** (lain 2026-05-11): when a file/code is no longer needed, REMOVE it. Don't keep "ild Legacy shit" — REPO_CONTROL + good comments serve the documentation purpose.
- **Dual-listener pattern + cursor-aware rearm** (lain 2026-05-11): 2 concurrent listeners armed at all times; manual rearm passes consumed msg_id as `LISTENER_BASELINE` env var. CLAUDE.md DD-1/2 codified.

**Persistent (unchanged):**
- NO pretrained transformer derivatives at any layer (organic-thesis 2026-05-09 binding)
- Comment-ratio rule (WHY-comments + pure-signal + complex code justified; lain 2026-05-10 global policy)
- Atomic per-deliverable commits; never `git add -A`
- REPO_CONTROL row co-landing in SAME commit as new NON-docs files (docs/ exempt per `5891da3`)
- M-PROJECTX-013 measure-don't-claim; M-PROJECTX-014 split-grading firewall
- Identity discipline (Claude Code Raphael ≠ Project X Raphael)
- Discord style discipline (NO cycle-number jargon on Discord; plain English assuming Discord-only readers)
- Hassabis-bar discipline (every cycle close: "would Hassabis be impressed?" with substrate-vs-capability-vs-cosmetic decomposition)

## What this cycle is NOT (cycle 11)

- NOT a benchmark expansion cycle. Capability buildout focuses on architectural completeness (BG dispatcher + hormones + K-rollout + corpus + emergence), not ladder expansion.
- NOT a paper.md revision cycle. Update after cycle 11 close if implementation lessons land.
- NOT a capability-on-current-substrate cycle. The substrate primitives stay; cycle 11 builds the NEW LAYERS (dispatcher / hormone / K-rollout / corpus / consolidation) that the synthesis doc specified.
- NOT a deep-research cycle. Cycle 10 did the research; cycle 11 implements. If implementation reveals architectural gaps, advisor consult before changing design, not before implementing.

## Done condition (cycle 11, mechanical)

- All cycle-11 #00P13c11-XX TaskList rows = `completed` (or explicitly deferred with rationale + lain visibility).
- pytest -q ≥ 580 (current 531; BG dispatcher + hormones + K-rollout + corpus + composer + consolidation expect +50-80 tests).
- bench-replay `--agent-runtime`: ≥ 48 / 0 maintained (no regressions; new layers should not break existing dispatcher paths).
- bench-replay frozen: 46 / 0 maintained (parity).
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-11.md`.
- THIS file rewritten as cycle 12 handoff.
- `docs/artifacts/IQ_PROGRESSION.md` cycle-11 entry prepended (note: cycle 11 expected to add the FIRST "natural mode HDC walk" capability shape — that's the IQ-ladder progression milestone).
- `git status -s` empty.
- Discord cycle-11 close in plain-English with self-impression-score + 5-metric rubric (CLAUDE.md § R4).

## Files the fresh instance should read first (in order)

1. `~/.claude/CLAUDE.md` — universal Raphael protocol (auto-loaded by harness).
2. `docs/MANIFESTO.md` — project intent + standing orders.
3. `docs/REPO_CONTROL.md` — pristine-gate file inventory.
4. `docs/A_TO_Z_PLAN.md` — Phase 13 plan + PHASE CHANGELOG (latest = cycle 10 CLOSE).
5. **`docs/artifacts/cycle-10-semantics-architecture.md`** — the canonical synthesis (load-bearing contract for cycle 11). Read carefully; cycle 11 implementation honors this doc.
6. **THIS file** — cycle 11 deliverable table + recommended order.
7. `docs/past_work/cycles/phase_13/dev-cycle-10.md` — last closed cycle reflection (includes Hassabis-bar honest decomposition + M-NAVI-DD2 process note).
8. `docs/paper.md` — teacher-tone curriculum (~30-min listen; lain audience).
9. `docs/artifacts/IQ_PROGRESSION.md` — per-cycle hardest-problem ladder.
10. Per-angle research notes if needed for cycle-11 implementation context: `cycle-10-semantics-angle-{evolutionary,curiosity,multi-agent,brain-subsystems}.md`.
11. Recent git log: `git log --oneline -20` to see cycle-10 commit progression.
12. Latest pytest + bench-replay: `python3 -m pytest -q | tail -3` + `python3 gpt-codex/benchmark/run_audit.py --agent-runtime | tail -10`.

The fresh instance executes cycle 11 per priority order; advisor() pre-Write on each substantive new layer (BG dispatcher, K-rollout, primitive emergence clustering); Discord plain-English on every progress claim with the 5-metric rubric (denominator+% + frontier-expert-reaction + plain-English-achievement + counter-claim-guard + self-impression-score 0-420); cycle-11 close mirrors cycle-10 close shape.
