# Do This Next — Project X — Phase 13 cycle 13 (handoff from cycle 12 CLOSE)

**Updated:** 2026-05-11 (cycle 12 CLOSE — Tier-2 corpus expansion + audit UI v1; emergence-at-scale + consolidation pass + Rust/bitpack deferred to cycle 13 with documented fix paths)
**Mode:** TBD by lain at cycle 13 start — APOTHEOSIS EXTENDED window expired 2026-05-11 11:00 CEST Oslo (lain hard rule); re-arm under NORMAL heartbeat or new APOTHEOSIS window per lain.
**Status:** Cycle 12 CLOSED via 5 atomic commits (4 feat + 1 close). Cycle 13 = SCALE INFRASTRUCTURE (bitpack / mini-batch) + emergence-at-scale re-attempt + continued corpus expansion + consolidation pass (after audit data accumulates).

## Cycle 12 — what shipped (CLOSE)

| Commit | Deliverable | Result |
|---|---|---|
| `5f0b2f2` | #00P13c12-01a Tier-2 poetry corpus 80 → 158 fragments | Multi-line poem sequences preserving volta/caesura |
| `4efa69e` | #00P13c12-01b Tier-2 ingestion pipeline + 10 Gutenberg works + v2 noise filters | Reusable pipeline; "no GPT-generated text" sourcing |
| `21a191a` | #00P13c12-01c +12 public-domain works; 5 new domain tags | Net Tier-2 corpus ~22k fragments |
| `ae5dffc` + `768db37` | #00P13c12-02 audit UI v1 (JSONL log + CLI rating tool + composer hook + gitignore) | Audit signal pipe operational for cycle-13 consolidation pass |
| THIS commit | #00P13c12-07 cycle-12-CLOSE (dev-cycle-12.md + A_TO_Z + IQ_PROGRESSION + cycle-13 handoff) | Cycle close ritual |

**Deferred to cycle 13** (with documented fix paths):
- #00P13c12-06 emergence-at-scale (WSL crashed; bitpack prerequisite identified)
- #00P13c12-03 consolidation pass (needs audit data accumulation)
- #00P13c12-04 HDC-infra Rust-or-bitpack (now reframed as cycle-13 #1 PREREQUISITE)
- #00P13c12-05 natural-mode register extension (lower priority)
- #00P13c12-06 intent-classifier multi-example (lower priority)

**Numbers (cycle 12 CLOSE):**
- pytest 586 baseline from cycle 11 close — **NOT re-verified this cycle** (40-min close budget after WSL crash recovery; cycle 13 verifies)
- bench-replay `--agent-runtime`: 48 / 0 baseline from cycle 11 close — **also unverified post-crash** (no substrate code changed cycle 12; no regression expected)
- bench-replay frozen: 46 / 0 baseline maintained (parity)
- Corpus scale: ~250 fragments → ~22,000 fragments (88× retrieval-surface expansion)

**Cycle 12 reflection at** `docs/past_work/cycles/phase_13/dev-cycle-12.md` (Hassabis-bar honest decomposition; WSL crash analysis; 3 lain catches absorbed; cycle-13 fix paths).

## Cycle 13 PRIORITY UPDATE — capability-demo-first per advisor catch (2026-05-11 10:36 CEST)

**Trigger:** lain Discord msg `1503368472` ("Ok try moving the needle even further. Long term goals in mind. Try to make the model as smart as possible. A new round of council is smart maybe. Biggest leverage work should be done first. Enter normal mode.") + advisor pushback on the original "bitpack-first" sequence.

**Advisor catch (verbatim summary):**
1. "Maybe" in lain's msg = optional, not mandatory. A 3-4h council that converges on bitpack-as-cycle-13-#1 (which the original DO_THIS_NEXT already encoded) is council-as-decoration.
2. Cycle 12 expanded the corpus 88× (250 → ~22,000 fragments) and **NEVER re-ran the v0 natural-mode dispatcher against it**. Capability demo on the unseen 22k corpus is the cheapest high-leverage move (~30-60 min) that captures actual model state BEFORE deliberation.
3. The council should be informed by demo data; synthesis then commits to cycle-13 #1 with reality data rather than abstract priority-ranking.

**Verified wiring:** `src/project_x/corpus/natural_mode.py` line 156-180 — `NaturalModeComposer(include_ingested=True)` (default args) auto-loads the 22k Tier-2 corpus from `data/corpus_raw/` at init time via `ingest_corpus_dir`. The reasoning_agent natural-mode branch uses this composer. **Running 5 prompts through the existing AGENT picks up the 22k corpus automatically — no new wiring needed.**

### Cycle 13 sequenced deliverables (capability-demo-first → council → synthesis → implementation)

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c13-01-demo-22k** | HIGH; first substantive ship | `ReasoningAgent.process()` on 5 prompts + Discord post + capture as audit-log JSONL | Capability demo on the 22k Tier-2 corpus. 5 lain-aligned prompts (poem-on-impermanence-of-stone / meaning-of-life / Collatz-empirical-verification / mathematics-discovered-or-invented / sonnet-on-death-of-a-friend). Captured: emitted output + provenance trails + walk strategy that won (bind/bundle/greedy per K-rollout). ~30-60 min Raphael-time. Atomic commit `docs(P13c13-01-demo-22k)`. |
| **#00P13c13-02-council-angle-1-bitpack-emergence** | HIGH | `docs/artifacts/cycle-13-council-angle-bitpack-emergence.md` (~50-100 lines) | advisor consult: bitpack + emergence-at-scale as the deterministic-infrastructure capability-lift path. Load-bearing %. Brief lit scan. ~30-45 min Raphael-time. Atomic commit. |
| **#00P13c13-03-council-angle-2-variable-resolution-hdc** | HIGH | `docs/artifacts/cycle-13-council-angle-variable-resolution-hdc.md` | advisor consult on lain msg `1503248974` "variable HDC resolution / higher detail at certain geometric positions". Load-bearing % + concrete implementation sketch. ~30-45 min. Atomic commit. |
| **#00P13c13-04-council-angle-3-quality-curation** | HIGH | `docs/artifacts/cycle-13-council-angle-quality-curation.md` | advisor consult: is the bottleneck DATA QUALITY not architecture (per lain "underestimating how much data you need" + "rich and broad and curated, high quality, low noise")? Automated curation filter + scale to 100k-1M fragments per domain. Load-bearing %. ~30-45 min. Atomic commit. |
| **#00P13c13-05-council-angle-4-bootstrap-audit** | HIGH | `docs/artifacts/cycle-13-council-angle-bootstrap-audit.md` | advisor consult: can simulated/heuristic audit (e.g. similarity-to-lain-voice-corpus as proxy reward) bootstrap the consolidation feedback loop BEFORE accumulated lain ratings? Would unlock canonical Layer 7 primitive earlier. Load-bearing %. ~30-45 min. Atomic commit. |
| **#00P13c13-06-synthesis-priority-decision** | HIGH; gates cycle-13 #1 implementation | `docs/artifacts/cycle-13-priority-decision.md` | Synthesis pass — read all 4 angle notes + capability demo output + canonical doc + cycle 12 close. Each angle gets a load-bearing % verdict. Commit to ONE cycle-13 #1 winning angle with honest asymmetric loading (mirrors cycle-10 synthesis pass). advisor() pre-commit. ~45-60 min. Atomic commit. |
| **#00P13c13-07-cycle-13-#1-implementation** | HIGH; depends on #06 | TBD per synthesis verdict | Whatever the synthesis selects. Estimated 45-min to 5h depending on winner (bitpack ~45-75 min per its design doc; variable-resolution HDC ~3-4h; quality-curation ~2-3h; bootstrap audit ~2h). |
| **#00P13c13-08-cycle-13-reflect** | LOW; after #07 | `docs/past_work/cycles/phase_13/dev-cycle-13.md` + DO_THIS_NEXT cycle-14 + A_TO_Z + IQ_PROGRESSION | Cycle close ritual mirroring dev-cycle-12.md shape. Hassabis-bar honest decomposition. advisor() pre-commit. |

**Total estimate: ~5-8h Raphael-time** depending on which angle synthesis selects.

### Original "candidate cycle-13 #1" priorities (now reframed as council inputs)

The following were the original cycle-13 priorities from the cycle-12 CLOSE handoff. The council deliberates over them; the synthesis commits to ONE as cycle-13 #1. Each original priority maps to one or more council angles:

- **Original #1-#3 bitpack + mini-batch + emergence-at-scale** → council angle 1
- **Original #6 variable-resolution HDC** → council angle 2
- **Original #4 corpus expansion + automated curation** → council angle 3
- **Original #5 consolidation pass + #7 infinite attention/generation** → council angle 4 (consolidation specifically; infinite-attention is an analysis question that the synthesis may surface as a separate deliverable)
- **Original #8 natural-mode register / #9 intent-classifier multi-example** → low-priority deferrables; council may surface them or push to cycle 14

(Original entries preserved below for council reference; the council operates over their substance, not over this table directly.)

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **(original) #00P13c13-01-bitpack** | HIGH; PREREQUISITE for #3 | new `src/project_x/hdc_infra/bitpack.py` + integration in encoder + emergence | Bitwise-packed binary HDC: pack 32 bipolar ±1 bits into one int32. ~32× compression — 50k-200k trigrams × packed 10000-dim ≈ 16-65MB instead of 500MB-2GB. Cosine-via-popcount on the packed representation: `cos(a, b) ≈ (D - 2·popcount(a XOR b)) / D` for D-bit vectors. Validate against existing `cosine_bipolar` on a small bench. ~2-3h Raphael-time. |
| **#00P13c13-02-minibatch-kmeans** | HIGH; fallback if #1 hits complications | extend `_kmeans_cosine_bipolar` in `corpus/primitive_emergence.py` | Mini-batch k-means: process trigrams in batches of 1k-5k; assign each batch to current centroids; incremental centroid update via sign(bundle(prev_centroid, batch_members)). Lower peak RAM at a slight clustering quality cost. ~90 min Raphael-time. Land regardless of #1's status — useful for cycle-14+ even-larger corpora. |
| **#00P13c13-03-emergence-at-scale** | HIGH; depends on #1 OR #2 | run `primitive_emergence` on ~22k-fragment Tier-2 corpus | The deferred cycle-12 #06 work. Run k-means on ~50k-200k unique trigrams using bitpack and/or mini-batch infrastructure. Empirical result: do the discovered primitives at scale represent structural shells ("X is Y", "X because Y") consistent with cycle-11 #06 MVP's findings, or do they shift toward frequency rankings as scale grows? Document in `docs/artifacts/cycle-13-primitive-emergence-at-scale.md`. ~60-90 min post #1/#2. |
| **#00P13c13-04-corpus-expansion** | HIGH; on-going | Tier-2 ingestion pipeline (`4efa69e`) | Target another 50-200 Project Gutenberg works toward the canonical doc Layer 6 spec (1-10M words per domain). Continue per-domain atomic commits via the existing pipeline. Lain's "rich and broad and curated, high quality, low noise" bar applies; v2 noise filters in place. ~3-5h per domain × 5 domains; can ship per-batch atomic. |
| **#00P13c13-05-consolidation-pass** | MED; after #3 + accumulated audit data | new `src/project_x/learning/consolidation.py` | Canonical doc Layer 7 surprise-biased perturb-audit-reweight. Selection rule: bias toward bindings with high audit-rejection-rate AND high recent K-rollout-curiosity. Update: bit-flip ~1% perturbation; score via audit-loop predicate; replace central if perturbation scores higher on audit-aligned retrieval. Real audit data accumulates as lain rates walks via the cycle-12 #02 CLI; without ~50+ ratings the consolidation pass is tautological. ~2h post audit data accumulation. |
| **#00P13c13-06-variable-resolution-hdc** | MED; advisor consult first | new module TBD | Lain msg `1503248974` (~04:14 UTC 2026-05-11): *"Variable HDC resolution, like it can give higher detail to certain geometric positions where needed. This is just optional, I'm just thinking out loud."* Research direction: hierarchical HDC where the substrate's effective dimensionality is non-uniform across the vector — high-detail subspaces for frequently-retrieved concepts, low-detail for rarely-touched. Needs advisor consult to map the architecture's options before implementing. ~60 min advisor + ~3h prototype if pursued. |
| **#00P13c13-07-infinite-attention-generation** | MED | analysis + demo | Lain msg `1503248281` (~04:11 UTC 2026-05-11): *"It must be able to perform infinite attention and infinite generation output capability too like it should be able to understand a long input, and generate long output."* The HDC walk substrate already supports arbitrary-length retrieval chains and arbitrary-length input prompts (no fixed context window like transformers). So "infinite" may already be implemented — needs analysis to confirm and a demo on a long-prompt + long-output benchmark to validate. ~60 min advisor consult + demo. |
| **#00P13c13-08-natural-mode-register** | LOW; deferred from cycle 12 #05 | extend `_try_natural_mode` in reasoning_agent.py | Apply register selection to natural-mode walks: terse natural-mode = single best fragment with citation; tutorial natural-mode = annotated meta-commentary on why each fragment was retrieved; casual natural-mode = remove formal "STEP N" markers, present as conversational quote. Currently register selection only re-renders formal-mode Lemmas. ~60 min. |
| **#00P13c13-09-intent-classifier-multi-example** | LOW; deferred from cycle 12 #06 | `_REGISTER_ARCHETYPES` in reasoning_agent.py extended | Multi-example archetypes per register + centroid averaging via HDC bundle. Currently 1 archetype per register. ~30 min. |
| **#00P13c13-10-cycle-13-reflect** | LOW | dev-cycle-13.md + DO_THIS_NEXT cycle-14 + A_TO_Z + IQ_PROGRESSION | Hassabis-bar honest decomposition. advisor() pre-commit. |

**Total estimate: ~10-16h Raphael-time across cycle 13.** Bitpack + emergence is the bulk; everything else is composable.

**Carry-forwards (lain-pending; do NOT touch unprompted):**
- #00P13c8-07 CLAUDE.md trim (~59.3k current vs 46k hard ceiling; ~13k more to cut over older sections; awaits lain direction on what's load-bearing).
- #00P13c7-04 council audit tag (mechanism scope unresolved).

## Open empirical questions (cycle 13 reveals)

1. **Does bitpack (#1) cleanly substitute for bipolar int8 in cosine + k-means without quality loss?** (Cosine-via-popcount is mathematically equivalent for binary vectors; the question is whether downstream consumers — encoder, retrieval, emergence — accept the packed representation without regression.)
2. **Does primitive emergence at production scale (~50k-200k trigrams) produce structural shells or frequency rankings?** (Cycle 11 #06 MVP at ~3k trigrams produced clean shells: "X is Y" copula + "X and Y" coordination. Whether this survives at 60× scale is the empirical question cycle 13 #3 answers.)
3. **Does accumulated audit data + consolidation pass measurably improve walk quality across cycles?** (Requires ~50+ real lain ratings before the test is meaningful.)
4. **Does variable-resolution HDC produce qualitatively-different retrieval?** (Lain's "thinking out loud" suggestion; needs advisor consult before commitment.)
5. **Does the HDC walk already implement "infinite attention/generation" in the lain-msg sense?** (Substrate analysis question; likely yes with caveats.)

## Standing rules — RELEVANT FOR FRESH INSTANCE

See `docs/MANIFESTO.md` § Standing orders + `~/.claude/CLAUDE.md` (universal).

**Universal codifications binding cycle 13+:**
- **WSL/RAM caution** (lain 2026-05-11 post-crash): "be careful of WSL and ram usage etc." Codified as: no emergence-at-scale or other 22k+-fragment k-means runs without bitpack or mini-batch landed first.
- **English-fluency floor + training-data-needed** (lain 2026-05-11): English fluency is mandatory floor; other-language fluency last priority; training data IS needed (not deprioritized).
- **Data-quality discipline** (lain 2026-05-11 cluster `1503244000` → `1503248974`): "very well curated and high quality, low noise. But rich and broad." Public-domain sourcing only; NO GPT-generated text (would distill a transformer through the back door); v2 noise-reduction filters mandatory on Tier-2 ingestion.
- **Long-term-goal-addressing primary axis + research-when-needed self-check** (lain 2026-05-11): every shift answers "am I directly addressing long-term goals" + "do I need research/brainstorming first" + "am I being proactive in deep thinking, not just executing."
- **Raphael-time estimates** (lain 2026-05-11): calibrate to actual commit throughput (~10-15 min per substantive deliverable); NOT human-developer hours.
- **Self-impression-score 0-420** (lain 2026-05-11): mandatory 5th metric on every substantive ship; integer + one-line rationale; never inflate; honest 340 > fake 400.
- **No-legacy discipline** (lain 2026-05-11): when a file/code is no longer needed, REMOVE it.
- **Dual-listener pattern + cursor-aware rearm** (lain 2026-05-11): 2 concurrent listeners; manual rearm passes consumed msg_id as `LISTENER_BASELINE` env var. CLAUDE.md DD-1/2 codified.

**Persistent (unchanged):**
- NO pretrained transformer derivatives at any layer (organic-thesis 2026-05-09 binding)
- Comment-ratio rule (WHY-comments + pure-signal + complex code justified; lain 2026-05-10 global policy)
- Atomic per-deliverable commits; never `git add -A`
- REPO_CONTROL row co-landing in SAME commit as new NON-docs files (docs/ exempt)
- M-PROJECTX-013 measure-don't-claim; M-PROJECTX-014 split-grading firewall
- Identity discipline (Claude Code Raphael ≠ Project X Raphael)
- Discord style discipline (NO cycle-number jargon on Discord; plain English assuming Discord-only readers)
- Hassabis-bar discipline (every cycle close: "would Hassabis be impressed?" with substrate-vs-capability-vs-cosmetic decomposition)

## What this cycle is NOT (cycle 13)

- NOT a benchmark expansion cycle. Capability buildout focuses on the SCALE INFRASTRUCTURE (bitpack + emergence-at-scale) plus continued corpus + audit-driven consolidation. Bench-replay PASS-count progress is not the cycle theme.
- NOT a paper.md revision cycle. Update after cycle 13 close if implementation lessons land.
- NOT a fluency-evaluation cycle. Whether the larger corpus produces qualitatively-better walks is an empirical question — cycle 13 generates the AUDIT signal that answers it across cycles 13-14.

## Done condition (cycle 13, mechanical)

- All cycle-13 #00P13c13-XX TaskList rows = `completed` (or explicitly deferred with rationale + lain visibility).
- pytest -q ≥ 600 (current 586 baseline; bitpack + mini-batch + emergence-at-scale + consolidation pass expect +20-40 tests).
- bench-replay `--agent-runtime`: ≥ 48 / 0 maintained (no regressions; bitpack must be empirically equivalent to int8 bipolar; emergence-at-scale is documentation work that shouldn't touch bench).
- bench-replay frozen: 46 / 0 maintained (parity).
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-13.md`.
- THIS file rewritten as cycle 14 handoff.
- `docs/artifacts/IQ_PROGRESSION.md` cycle-13 entry prepended.
- `git status -s` empty.
- Discord cycle-13 close in plain-English with self-impression-score + 5-metric rubric.

## Files the fresh instance should read first (in order)

1. `~/.claude/CLAUDE.md` — universal Raphael protocol (auto-loaded by harness).
2. `docs/MANIFESTO.md` — project intent + standing orders.
3. `docs/REPO_CONTROL.md` — pristine-gate file inventory.
4. `docs/A_TO_Z_PLAN.md` — Phase 13 plan + PHASE CHANGELOG (latest = cycle 12 CLOSE).
5. **`docs/artifacts/cycle-10-semantics-architecture.md`** — the canonical synthesis (load-bearing contract; cycle 13 implements the HDC-infra optimization layer per its roadmap).
6. **THIS file** — cycle 13 deliverable table + recommended order.
7. `docs/past_work/cycles/phase_13/dev-cycle-12.md` — last closed cycle reflection (includes WSL crash analysis + bitpack/mini-batch fix paths).
8. `docs/past_work/cycles/phase_13/dev-cycle-11.md` — architectural foundation cycle for context on the layers being scaled.
9. `docs/artifacts/IQ_PROGRESSION.md` — per-cycle hardest-problem ladder.
10. `src/project_x/corpus/primitive_emergence.py` + `src/project_x/experiments/encoder.py` — the code touched by cycle-13 #1/#2/#3.
11. Recent git log: `git log --oneline -20` to see cycle-12 commit progression.
12. Verify baselines BEFORE substantive new work: `python3 -m pytest -q | tail -3` + `python3 gpt-codex/benchmark/run_audit.py --agent-runtime | tail -10`. Cycle 12 close did NOT re-verify these post-WSL-crash; cycle 13's first action is verification.

The fresh instance executes cycle 13 per priority order; advisor() pre-Write on bitpack design (substantive new infra) + variable-resolution HDC (research direction); Discord plain-English on every progress claim with the 5-metric rubric (denominator+% + frontier-expert-reaction + plain-English-achievement + counter-claim-guard + self-impression-score 0-420); cycle-13 close mirrors cycle-12 close shape.
