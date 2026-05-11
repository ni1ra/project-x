# Do This Next — Project X — Phase 13 cycle 14 (handoff from cycle 13 CLOSE)

**Updated:** 2026-05-11 (cycle 13 CLOSE — substrate hygiene + GPT external audit absorbed + STRICT organic-emergent-intelligence thesis codified)
**Mode:** NORMAL — heartbeat cron armed; cycle-by-cycle pace. APOTHEOSIS only on explicit `/godify-app` from lain.
**Status:** Cycle 13 closed via the dispatcher-hygiene sweep + audit fold-ins + thesis realignment. Cycle 14 is the FIRST cycle under the strict thesis: build the learning substrate that acquires capability from training data; hand-coded primitives become evaluation gold-standard.

---

## The thesis (READ FIRST — binding per `docs/MANIFESTO.md`)

> lain 2026-05-11 strict: *"i would even go so far as to say we shouldnt even hard code the math algos, it should learn it on its own. if we have good enough training data, and smart enough model, it should learn all itself."*

**The agent's knowledge — math, poetry, philosophy, physics, persona, routing — comes from training data + audit signal over the HDC learning substrate. The author writes ONLY the learning machinery (HDC primitives, encoder, Hebbian / k-means / K-rollout / consolidation / audit-loop mechanics, data + audit pipelines). Hand-coded math/physics primitives are evaluation gold-standard, not the agent's source-of-capability.**

Cycle 14 is the first cycle that ships against this strict version. See A_TO_Z `§0.0 PHASE 13 THESIS SHIFT` and MANIFESTO §"Organic emergent intelligence — what this means in practice" for the full framing.

---

## Cycle 13 — what shipped (CLOSE)

| Commit | Deliverable | Result |
|---|---|---|
| `e4272ac` + `69dec02` | #00P13c13-01 demo on 22k Tier-2 corpus (5 prompts; F1-F7 findings) | Capability snapshot pre-council |
| `6aaedad` / `fc2b51d` / `43ffaa4` / `800deed` | #00P13c13-02..05 four council angle notes (bitpack / variable-res / quality-curation / bootstrap-audit) | Deliberation surface |
| `c9e5401` | #00P13c13-05b angle-5 dispatcher-trigger note (added post-demo) | Demo-anchored calibration |
| `3308987` | #00P13c13-06 synthesis verdict (a1 + a5 multi-ship; combined-axis scoring; honest counter-claims) | Implementation contract |
| `ff46c2b` + `665f8a8` | #00P13c13-07a/b bitpack module + 29-test suite | ~32× memory compression vs int8; integer-exact cosine equivalence |
| `2823a65` | docs(P13c13-audit-response) GPT external audit + audit-of-audit | Two real bugs caught (B2 D-mismatch, B4 Collatz parser); three architectural reframes flagged; E3 = missing generation angle |
| `ce9bc8f` | #00P13c13-07c encoder shim + D=10000→10240 bump (audit B2 fix) | Encoder default matches docs claim; `encode_packed` method shipped |
| `e7fe21d` | #00P13c13-07d dispatcher boost + Collatz prose-parser widen (audit B4 fix) | Three-layer defense: prose-form parser, tightened natural-mode triggers, formal-priority boost |
| `b356bd4` | #00P13c13-07e trigger archetypes cosine-fallback | P4/P5 demo prompts route correctly; calibrated τ=0.10 empirically |
| `0b89101` | #00P13c13-07f-pre pre-registered scoring predicate (audit D3 fix) | Predicate committed BEFORE emergence run; falsifiable verdict criteria |
| THIS commit | #00P13c13-thesis-realign + #08 close (MANIFESTO + A_TO_Z + dev-cycle-13 + cycle-14 handoff + emergence run + IQ_PROGRESSION) | Strict thesis codified + cycle close ritual |

**Deferred / open from cycle 13:**
- #00P13c13-07f-run emergence-at-scale RUN — ran on a 50k-trigram random sample of the 22k corpus (script at `scripts/cycle_13_emergence_at_scale.py`); verdict appended to `docs/artifacts/cycle-13-primitive-emergence-at-scale.md` §7. Full 420k-trigram run with `packed=True` is cycle-14 work (requires `discover_primitives` packed-path implementation).
- τ_satisfaction = 0.0 calibration debt (audit B5) — explicit known-debt; cycle-14 calibration task.
- Canonical-doc Layer 5 / Layer 6 / Manifesto-Terminus reframings (audit C1/C2/C3 + D2) — doc-edit work for cycle-14+.

**Numbers (cycle 13 CLOSE):**
- pytest: **639 / 639** (was 596 cycle-12-close baseline; +43 new tests across cycle 13: 29 bitpack + 4 encoder + 6 dispatcher + 4 trigger archetypes).
- bench-replay `--agent-runtime`: **48 / 0** maintained.
- bench-replay frozen: 46 / 0 parity.
- 5 atomic feat commits + 4 atomic docs commits + 1 cycle-close commit.

**Cycle 13 reflection at** `docs/past_work/cycles/phase_13/dev-cycle-13.md` (Hassabis-bar honest decomposition; audit-driven cycle structure; the thesis-realignment as the load-bearing close artifact).

---

## Cycle 14 PRIORITY — Build the LEARNING SUBSTRATE (strict-thesis cycle 1)

**Trigger:** lain 2026-05-11 strict thesis + GPT audit E3 (missing generation/evaluator/policy-learning angle) — surfaced + codified in cycle-13 close.

**Cycle 14 council MUST include "build the learning substrate that acquires capability from training data" as the #1 angle.** Other angles are scored against this one (does this angle contribute to the learning loop, or does it ship more hand-coded scaffold?).

### Cycle 14 #1 candidate scopes (council deliberates)

| Angle | Scope (one-line) | Cost estimate |
|---|---|---|
| **A1: Hebbian-or-equivalent learning rule over HDC substrate** | The substrate has `bind` / `bundle` (one-shot composition) but no learning rule that updates the substrate from experience. Cycle-14 candidate: Hebbian co-occurrence update on trigram-or-fragment co-occurrence patterns; substrate weights drift toward predicted-then-confirmed patterns. Audit signal → reinforcement; refusal/incorrect signal → suppression. | ~3-5h Raphael-time |
| **A2: Evaluator-driven policy over substrate primitives** | Replace `_DISPATCH_CHAIN_ORDER` chain-order + α/τ constants with a learned policy: for each prompt, score each primitive's expected audit-reward; select argmax. Policy parameters: per-primitive embeddings updated from audit signal. Cold-start uses the current dispatcher as fallback. | ~3-4h Raphael-time |
| **A3: Credit assignment loop over composed answers** | When an answer is rated, the rating must propagate back to the substrate elements that contributed (retrieval fragments, K-rollout strategy, dispatcher choice, walk path). Hebbian-style credit assignment over the substrate. | ~2-3h Raphael-time |
| **A4: Training-data scale-out — Layer 6 spec** | The 22k corpus is the seed; canonical doc says 1M-10M words per domain. Cycle-14 scope: identify domain coverage gaps; ingest 100k+ words of math worked-examples + physics derivations; pipeline already exists. | ~2-4h Raphael-time (compute-time may dominate) |
| **A5: Emergence-validation predicate as ongoing capability metric** | The cycle-13 #07f-pre predicate (structural-shells vs frequency-rankings) is the TEMPLATE. Generalize: pre-registered predicate per domain (math/poetry/philosophy/physics) that scores "did the learned model acquire capability X" at cycle close. | ~2h Raphael-time per domain template |

**The synthesis pass commits to ONE primary angle + (optionally) one bundled angle, with honest asymmetric loading per cycle-13 precedent.**

### Cycle 14 OPEN — do NOT pre-commit before council

Cycle 14 starts with: capability demo of the post-cycle-13 agent (the corrected dispatcher; the cycle-13 ship) on a fresh prompt batch → council deliberation over the 5 candidate angles above → synthesis verdict → implementation. Mirrors the cycle-13 structure.

**advisor() pre-commit on the synthesis verdict** (cycle-13 precedent — caught the implementation-order flip + gate-permeability asterisk).

---

## Open empirical questions (cycle 14 reveals)

1. **Can the HDC substrate LEARN?** Hebbian co-occurrence update on a fragment-pair retrieved+rated jointly should shift the substrate toward predicting that retrieval again. Empirical test: does the substrate's retrieval-to-rating correlation improve cycle-over-cycle with audit signal? (Cycle-12 audit UI shipped; ~0 ratings accumulated so far — cycle-14 scope needs lain to actually rate ~50 walks for the policy gradient to turn on.)
2. **Does the cycle-13 emergence-at-scale predicate generalize?** The §7 result (cycle-13 #07f-run) is the cycle-13 ground truth; the cycle-14 question is whether the per-domain predicate template (math / poetry / philosophy / physics emergence) is the right scaffolding for "did the learned model acquire capability X."
3. **Bitpack-path for `discover_primitives` — does it preserve cluster identity?** The 50k-sample run shipped on int8; the full 420k-trigram run needs `discover_primitives(packed=True)` implementation. Cycle-14 work; predicted to preserve cluster identity (integer-exact cosine equivalence is proven; k-means is deterministic given seed).
4. **What's the audit-rating volume floor for the learned policy to outperform the hand-coded dispatcher?** Open question; cycle-14 calibration scope. Predicted ~50-200 ratings before the policy gradient is informative.
5. **Variable-resolution HDC** (cycle-13 council angle 2; deferred) — does non-uniform substrate dimensionality help the learning rule? Cycle-15+ research direction unless cycle-14 council elevates it.

---

## Carry-forwards (lain-pending; do NOT touch unprompted)

- `#00P13c8-07` CLAUDE.md trim (~59.3k current vs 46k hard ceiling per CLAUDE.md rule; awaits lain direction on what's load-bearing).
- `#00P13c7-04` council audit tag (mechanism scope unresolved).

## Standing rules — RELEVANT FOR FRESH INSTANCE

See `docs/MANIFESTO.md` § Standing orders + `~/.claude/CLAUDE.md` (universal). Critical for cycle-14:

- **STRICT thesis applies:** no new hand-coded knowledge / no new hand-coded routing. Only the learning machinery is hand-coded. Every cycle-14 deliverable answers *"is this learning machinery, or hand-coded knowledge that the agent should be learning instead?"*
- **Identity discipline:** Claude Code Raphael (builder) ≠ Project X Raphael (agent). The builder writes the learning machinery; the agent learns the knowledge.
- **Comment-ratio rule:** complex code + important info gets WHY-comments; trivial code stays comment-free; identifier names carry the WHAT.
- **REPO_CONTROL row in same commit as new non-docs file/dir.** `docs/` is EXEMPT.
- **Atomic per-deliverable commits.** Never `git add -A`.
- **Discord teacher-tone + 5-metric rubric on every progress claim** (denominator+% / expert-tier holistic / plain-English achievement / counter-claim guard / honest 0-420 self-impression-score). Expert-tier framing is HOLISTIC — comments on overall model progress, not the local commit.
- **Raphael-time estimates** (~10-15 min per substantive deliverable), not human-developer hours.

---

*Single-line takeaway: cycle 14 is the first cycle under the strict organic-emergent-intelligence thesis. Build the learning substrate; hand-coded primitives become evaluation gold-standard.*
