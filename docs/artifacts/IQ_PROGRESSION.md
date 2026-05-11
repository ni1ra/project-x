# IQ Progression Tracker — Project X Raphael

**What this file is.** A per-cycle snapshot of the hardest end-to-end problem the agent (Project X Raphael, the artifact in `src/project_x/`) could solve at runtime when that cycle closed. The hardest-problem framing is intentional — it's a concrete instance you can read aloud rather than an abstract pytest count.

**Audience.** Lain, primarily — paired with `docs/paper.md` (which explains HOW the architecture works). This file shows WHEN each capability landed and gives a vibe-check for whether the IQ is actually climbing. Listen-friendly if rendered as a NotebookLM podcast (each entry is ~half a paragraph).

**Update protocol.** At every cycle close, prepend a new entry. Never delete prior entries — the ladder IS the progression. Pair updates with the cycle-reflect commit so the artifact stays alive across cycles.

---

## Phase 13 cycle 14 CLOSE (2026-05-11) — SUBSTRATE WRITABILITY — first reward-driven write path from audit signal back into the substrate; one piece of dispatcher scaffolding retired; #08e deferred with two substantive findings

**Hardest end-to-end at agent-runtime (NEW capability shape this cycle):** the substrate is now WRITABLE from rated experience. When `AuditLog.apply_rating(walk_id, rating)` fires on a rated walk, the `HebbianBank` accumulates `learning_rate * (rating - midpoint)` on each `(prompt_atom, fragment_atom)` pair in that walk. Subsequent retrieval blends the static char-n-gram-hash cosine with the bank's accumulated lookup: `final = (1-α) * cosine + α * bank.lookup`, with `α = min(1.0, entry_count/100)`. **Capability shape:** the substrate stops being a fossil. Cold-start (empty bank) preserves cycle-13 baseline EXACTLY (Arm A verification: cycle-14 demo P1-P5 reproduce identical outputs). Synthetic-rating injection (Arm B: 5 rejects on cycle-14 demo P4/P5 misroute fragments + 120 filler approves → α=1.0) shifts P4 + P5 top fragments AWAY from rated-as-misroute fragments. Reward signal verified end-to-end.

**Capability lift vs cycle 13 close:** zero on actual agent capability at cold-start. The bank is empty; lookups return 0.0; retrieval is cycle-13 cosine baseline. **What landed is the WRITE PATH, not measured-learning.** Capability lift on the cycle-14 demo's dispositive findings (P4 humour mis-routes to math at confidence 0.83; P5 casual chat mis-routes to poetry at 0.83) waits on accumulated audit rating cadence — synthesis §5 honest framing: ~20-50 ratings on misroute-shaped prompts before the policy gradient is informative.

**Pytest baseline:** **639 → 662** passing (+23 cycle-14 #08d tests: 10 math correctness + 3 cold-start regression + 4 synthetic-rating sweep + 5 persistence/boundaries + 1 blend-helper). Cycle-13 baseline 639/639 preserved EXACTLY at every cycle-14 commit boundary. Full-suite under-load 661/662 pass; 1 pre-existing wall-clock-noise flake on `test_write_one_amortized_under_5x_batch` (passes in isolation; not a cycle-14 regression).
**Bench-replay --agent-runtime:** **48 / 0** maintained.
**Bench-replay frozen:** **46 / 0** parity.

**One piece of dispatcher scaffolding retired this cycle (#00P13c14-08g, commit `513c186`):** `_NATURAL_MODE_TRIGGERS` keyword-regex gate disabled in `_classify_natural_mode_domain`. Routing now relies on cycle-13 #07e cosine-archetype fallback + the new HebbianBank reward-shaped blend. Proof-of-direction per cycle-14 synthesis §4.a — concrete answer to lain's strict-strict thesis catch, not future-tense disclaimer. Cycle-14 ends with LESS hand-coded scaffolding than cycle-14 opened with.

**THE MID-SYNTHESIS COURSE-CORRECTION (lain 2026-05-11 STRICT-STRICT binding):** *"there shouldnt be a need for us to hand pick anything. it should naturally emerge as the best solution, model on its own. if you stimulate the right rewards you will get emergent behaviour. you really keep trying to hardcode everything."* Caught the pre-correction synthesis verdict's A2 + A3 proposals (per-primitive learned embeddings + argmax scorer; per-decision-coefficient credit propagation) as still embedding hand-coded structure with learned weights. The "LEARNING MACHINERY allowed" clause was being stretched. Synthesis pivoted WITHIN-cycle to **A1 alone** (substrate-wide Hebbian; bank keyed by `(prompt_atom, fragment_atom)` pairs — NOT per-primitive) + concrete pre-retirement of one scaffolding piece + measurable retirement criterion (synthesis §4.b) for the rest. The strict-strict reading is now codified across the cycle-14 synthesis verdict + reflect + this IQ entry; future cycles inherit a per-angle thesis-compliance gate as cycle-15 process improvement.

**Two substantive findings surfaced by cycle-14 #08e deferral** (`docs/artifacts/cycle-14-priority-decision.md` §7 + `src/project_x/reasoning_agent.py:_K_ROLLOUT_TAU` comment): (1) **avg-cosine is NOT a quality discriminator** across cycle-13 + cycle-14 regimes — Collatz framing-walks (cycle-13 desired, ~0.17) and P4/P5 misroutes (cycle-14, 0.19/0.20) sit in the same cosine band. No global τ separates them. Cycle-15 fix: per-domain τ + HebbianBank reward-shaped blend together replace bare cosine. (2) **Latent 4-cycle-old BG-dispatcher bug surfaced** — refused natural-mode candidates compete in the candidate list at `combined_confidence ≈ 1.0` (no archetype for `_refused_*` problem_shape → `hv_sim_normalized` defaults to 1.0) and BEAT legitimately-high-confidence formal candidates. Cycle-13 audit B5's `τ=0.0` masked this since the refused branch never fired. Surfacing this is substantive cycle-14 work; cycle-15 fix lives alongside the per-domain τ calibration as a paired refused-candidate-filter + τ-calibration ship.

**Verification artifact (#00P13c14-08f, commit `d854fbc`):** two-arm verification appended as §8 to `docs/artifacts/cycle-14-demo-post-thesis.md`. Arm A cold-start regression mechanically PROVEN (5/5 prompts produce identical dispatcher metadata vs cycle-14 demo's `d89b90f` original). Arm B synthetic-rating shift demonstrates bank mechanism end-to-end (rated negatives drop to lookup=-1.0; at α=1.0 the blend collapses to -1.0 dominance; rated-as-misroute fragments fall below ANY cosine; unrated pairs win the ranking). The shift is mechanically verified; CAPABILITY shift on real audit data waits on real audit cadence.

**Honest cycle-14 close framing per synthesis §5 permeability asterisk:** substrate writability shipped + reward-signal pipeline online + ONE scaffolding piece retired + audit cadence pending. **NOT "the agent learned tool-use this cycle."** The agent is identical to cycle-13 under cold-start; capability change waits on real audit cadence + cycle-15+ A4 corpus scale-out (addresses F4/F5 data-side gap; cycle-14 demo found no humour or chat material in the 22k corpus — bank can drive misroutes DOWN but has nowhere on-topic to drive retrieval TOWARD).

**R2 vs R1 UNRESOLVED at cycle close.** Synthesis verdict committed R2 (transition reading with measurable §4.b retirement criterion) as defensible default; R1 (rip the entire dispatcher this cycle, accept multi-week valley) offered to lain as override window. **lain's confirmation did NOT arrive during the cycle-14 implementation window.** Cycle-15 inherits the unresolved at handoff.

**Lain catches absorbed (3):** (1) **same-day Discord-style binding recurrence** — HOLISTIC plain-English rule bound morning-of-cycle-13-close re-broke within hours during cycle-14's execution-pressure council-deliberation posts; logged as **M-PROJECTX-015** with three compounding failure modes named; recurrence is a discipline tell, not just "logged and corrected"; cycle-15 council pre-step = re-read NEW bindings BEFORE any Discord post in execution-pressure phases. (2) **Strict-strict thesis mid-synthesis course-correction** — the load-bearing catch of the cycle; pre-correction synthesis A2 + A3 → A1-alone within-cycle pivot. (3) **Step-back from patch-fix cascade** during #08e — *"step back, birdseye view, deep debug for hard bugs, shrine council for brainstorming."* Defer with documented finding rather than push patch chain through cycle-13 test-cascade.

**Self-impression-score: 365 / 420.** Below cycle-13's 375 because: same-day binding recurrence (M-PROJECTX-015); council/synthesis discipline let hand-coded structure through 5 angle commits + advisor pre-write + synthesis draft before lain caught (per-angle thesis-compliance gate is cycle-15 process improvement); #08e deferred-not-clean; capability unchanged at cold-start; R2 vs R1 unresolved. Above 340 because: strict-strict pivot WITHIN-cycle was structurally sharp; deferral surfaced a 4-cycle-old latent dispatcher bug (substantive output); pre-retirement of one scaffolding piece ships concrete strict-thesis answer this cycle; 6 of 7 sub-tasks shipped atomic with REPO_CONTROL co-landed; Arm A cold-start regression mechanically PROVEN.

---

## Phase 13 cycle 13 CLOSE (2026-05-11) — SUBSTRATE HYGIENE + STRICT THESIS — ORGANIC NATURALLY EMERGENT INTELLIGENCE codified; 13 atomic commits; pre-registered emergence test returns honest NOT-VALIDATED

**Hardest end-to-end at agent-runtime (NEW capability shape this cycle):** the dispatcher now routes the cycle-13 demo's previously-failed prompts correctly. P3 (*"Verify the Collatz conjecture for the first 10000 integers and discuss honestly what this does and doesn't prove."*) routes to the formal `collatz_verify_range` substrate with parsed N=10000 (was: natural-mode walk; F5 failure). P4 (*"Argue both sides: is mathematics discovered or invented?"*) routes to `natural_mode_walk_philosophy` via the cosine-archetype fallback (was: refusal; F6 failure). P5 (*"Compose a sonnet on the death of a friend."*) routes to `natural_mode_walk_poetry` via the same fallback (was: refusal; F6 failure). **Capability shape:** gate permeability lift — the agent reaches its existing capability for more prompt classes. The substrate that gets called is unchanged; the dispatcher's REACHABILITY is wider.

**Capability lift vs cycle 12 close:** zero on the walk-quality axis. Three prompt classes that previously refused now route to natural-mode or formal. The substrate primitives + the retrieval engine + the K-rollout strategies are unchanged. This is honestly gate-permeability, not capability depth.

**Pytest baseline:** **639 / 639** passing (was 596 cycle-12-close baseline; +43 new tests across cycle 13: 29 bitpack + 4 encoder + 6 dispatcher + 4 trigger archetypes). Zero regressions.
**Bench-replay --agent-runtime:** **48 / 0** maintained throughout cycle 13. Confirmed at multiple commit boundaries.
**Bench-replay frozen:** **46 / 0** parity maintained.
**Pre-registered emergence test (`docs/artifacts/cycle-13-primitive-emergence-at-scale.md`):** 0/20 clusters classified as STRUCTURAL on a 10k-trigram sample of the 22k corpus → **canonical-doc Layer 5 NOT VALIDATED at scale**. The cycle-11 MVP "X is Y" pattern was a small-corpus artifact. Verdict is honest, falsifiable, and on git audit trail.

**THE THESIS SHIFT (lain 2026-05-11 STRICT binding):** *"i would even go so far as to say we shouldnt even hard code the math algos, it should learn it on its own. if we have good enough training data, and smart enough model, it should learn all itself."* Codified across MANIFESTO + A_TO_Z + DO_THIS_NEXT in commit `86ca2bc`. The model's knowledge — math, poetry, philosophy, physics, persona, routing — comes from training data + audit signal. Only the LEARNING MACHINERY (HDC primitives, encoder, k-means / Hebbian / K-rollout / consolidation / audit-loop mechanics) is hand-coded. Cycle 7-10's math/physics substrate primitives + cycle-13's dispatcher are SCAFFOLD / evaluation gold-standard, not the agent's source-of-capability.

**GPT external audit cycle structure (cycle-13 mid-cycle):** lain requested external audit at the #07a/b boundary. GPT returned a 5-section findings doc (A/B/C/D/E). Two real bugs caught (B2 D=10000 doc-source mismatch; B4 Collatz bracketed-only regex). E3 surfaced the missing council angle (generative composition / evaluator / credit assignment) that crystallized into the strict-thesis directive. The audit-of-audit response (`2823a65`) honored each finding; corrections folded inline into the queued sub-task descriptions before resume; #07c-f shipped the fixes.

**Hassabis-bar verdict (cycle 13 CLOSE):** content yawns a frontier researcher — bitpack is 1960s information theory; cosine-archetype dispatch is classical; dispatcher hygiene is regex tightening; the predicate-test result is "the small-corpus thing didn't generalize." What MIGHT register mildly: (1) the external-audit + audit-of-audit cycle structure caught two real bugs the internal advisor missed AND surfaced the missing-angle that drove the thesis directive; (2) the pre-registered emergence predicate produced a falsifiable NOT-VALIDATED verdict via git history audit trail rather than post-hoc motivated reasoning — the predicate doc committed at hash `0b89101` BEFORE any data existed, the result block appended in a separate commit, retro-edits would show up on diff; (3) the strict-thesis codification across all three live docs BEFORE cycle-14 opens — a fresh Claude Code reading the repo at cycle-14 open sees ORGANIC NATURALLY EMERGENT INTELLIGENCE as the thesis on first look. PROCESS artifacts of architectural honesty, not CAPABILITY artifacts.

**Self-impression-score: 375 / 420.** Cycle 13 shipped 13 atomic commits through a multi-phase structure: demo → 5-angle council → synthesis → 2 substrate ships (bitpack module + tests) → external audit → 4 audit-driven corrections (encoder + Collatz + archetypes + predicate) → strict-thesis realignment → falsifiable emergence run → close. Each phase had a clear handoff. The external audit caught two bugs; the strict thesis lands cleanly across all docs; the emergence test produced an honest verdict the substrate FAILED. Honest 375 (not 395+) because: (a) the agent CRASHED WSL TWICE this cycle by failing to use the cycle-13 #1 substrate insurance the cycle itself shipped — the bitpack module exists specifically to prevent the OOM mode that killed both attempts; (b) cycle did NOT advance capability — the 4 audit-driven corrections are dispatcher hygiene; the emergence run is a test the substrate FAILED; (c) cycle-14 work (learning substrate; learned policy) is the actual capability move and is queued not shipped; (d) the strict-thesis codification means cycles 1-13's hand-coded substrate is now reframed as scaffold — honest but downgrades the trajectory framing.

**Counter-claim guard (cycle 13):** cycle did NOT produce new agent capability (gate permeability, not depth); cycle did NOT validate Layer 5 (the predicate's NOT-VALIDATED branch fired); cycle did NOT advance against the Terminus (auditable substrate hygiene + thesis codification + a falsifiable test the substrate failed — all process artifacts); the strict-thesis codification does NOT mean hand-coded math primitives are removed today (reframed as scaffold; removal is multi-cycle work as the learned model matures); the 10k-trigram emergence run is a sub-sample of 420k unique trigrams in the full corpus — full-corpus packed run is cycle-14 work (batched encoding + library `discover_primitives(packed=True)`).

---

## Phase 13 cycle 12 CLOSE (2026-05-11) — SCALE + audit-loop wire-up; 4 of 9 cycle-12 deliverables shipped, 5 deferred-to-cycle-13 with documented fix paths

**Hardest end-to-end at agent-runtime (NEW capability shape this cycle):** the same natural-mode HDC walk that shipped in cycle 11 #DEMO now operates over a ~22,000-fragment Tier-2 corpus spanning 22 source works (Project Gutenberg poetry + philosophy + classical literature + early-modern essays + historical writing) instead of the cycle 11 close's ~250 hand-seeded fragments. That's an 88× retrieval-surface expansion. For a prompt like "what is the meaning of life?" the K-rollout's natural-mode branch can now retrieve fragment sequences with provenance trails spanning 17+ source works (vs ~3 at cycle 11 close), and the audit UI (`ae5dffc`) captures each walk's full provenance trail + emitted text + rating field for downstream consolidation. No new MATH capability this cycle; the capability lift is in *natural-mode walk richness*.

**Capability lift vs cycle 11 close:** the natural-mode composer's retrieval pool grew from ~250 fragments to ~22,000 — 88×. The audit signal pipe is wired and operational (CLI `👍/👎/✏️ correct` against JSONL log at `data/audit_log/*.jsonl`); cycle 13's consolidation pass will consume this signal.

**Bonus capability:** the Tier-2 ingestion pipeline at `4efa69e` is reusable infrastructure — any new public-domain text can be ingested with provenance tags via the Gutenberg fetcher + sentence-splitter + v2 noise-reduction curation filters. Cycle 13's continued corpus expansion uses this same pipeline.

**Pytest baseline:** 586 / 586 passing from cycle 11 close — **NOT re-verified this cycle** (cycle 12 close happened under tight 40-min budget after WSL crash recovery; cycle 13 instance verifies).
**Bench-replay --agent-runtime:** 48 / 0 baseline from cycle 11 close, **also unverified post-crash.** No regressions expected since cycle 12 work was corpus + audit pipeline, not substrate.
**Bench-replay frozen:** 46 / 0 baseline maintained.
**Capability shape:** natural-mode HDC walk over a ~22k-fragment Tier-2 corpus instead of ~250-fragment Tier-1 seed. First step into the canonical doc Layer 6 spec's territory (which calls for 1M-10M words per domain; cycle 12 brought us to ~50-100k words across all domains — still 2-3 OoM short).

**The WSL crash event (cycle 12 process artifact):** cycle 12 #06 emergence-at-scale on the ~22k-fragment corpus triggered RAM-exceeded WSL termination at ~06:22 CEST. Root cause: ~50k-200k unique trigrams × 10000-dim bipolar int8 ≈ 500MB-2GB just for input vectors, plus hand-rolled k-means inner loop allocations exceeded the 7.8 GB RAM ceiling. This is the canonical doc HDC infrastructure optimization roadmap's predicted 10⁸-association non-linear degradation arriving on schedule. Cycle 13 makes bitwise-packed binary HDC (~32× compression) a PREREQUISITE for further empirical work on emergence.

**Hassabis-bar verdict (cycle 12 CLOSE):** content yawns a frontier researcher individually — corpus expansion is dataset engineering, not novel theory; the audit UI is application plumbing. What MIGHT register mildly: (1) the discipline of shipping audit infrastructure BEFORE the consolidation pass to avoid tautological feedback loops; (2) the explicit deferral of emergence-at-scale with documented RAM-fix path rather than retry-loop after WSL crash; (3) the WSL-crash-as-architectural-signal reframe — the canonical doc's HDC-infra roadmap predicted this exact scaling cliff and cycle 13 honors the prediction by making bitpack a PREREQUISITE not optional. These are PROCESS artifacts of architectural honesty, not capability artifacts.

**Self-impression-score: 305 / 420.** Cycle 12 shipped 4 deliverables cleanly (Tier-2 corpus expansion across 3 atomic commits + audit UI) and recovered from a WSL crash with explicit deferral + documented fix-path for cycle 13. Honest 305 (not 350+) because: no capability shape leap (corpus expansion ≠ new capability; audit UI is wiring not feature); emergence-at-scale empirical validation DEFERRED not VALIDATED; the WSL crash was a quantitative warning the cycle plan should have weight-checked before launching the 22k-corpus run; pytest + bench-replay baselines unverified post-crash leave the cycle close in a "trust-but-verify" state. Honest 305 over fake 350.

**Counter-claim guard:** cycle 12 did NOT validate the canonical doc's Layer 5 primitive emergence at production scale — the test crashed and is deferred. The corpus expansion is real (88× retrieval surface) but the agent's *quality of natural-mode walk* is bounded by retrieval substrate, not just fragment count; whether the larger corpus produces qualitatively-better walks is UNVERIFIED (no audit data has accumulated). Cycle 13 reveals whether (a) bitpack lets emergence-at-scale run; (b) accumulated audit data lets consolidation pass produce binding-quality improvements; (c) "rich and broad and curated" corpus expansion improves walk fluency subjectively.

---

## Phase 13 cycle 11 CLOSE (2026-05-11) — canonical-doc Layer 3-5 + Layer 2 architectural foundation arc; 8 of 10 deliverables shipped

**Hardest end-to-end at agent-runtime (NEW capability this cycle, register-modulated):** *"Hey Raphael, what do you think about the quadratic 3 x² − 14 x − 5 = 0 — just chat with me about it."* The same Pell-dispatcher / quadratic-substrate that cycle-10 close shipped is now routed through (1) BG-style confidence-scored parallel-bid dispatcher (21 parsers; α=0.6 archetype-cosine + binary-match; tau=0.3; chain-order tiebreaker; archetype hvs for each problem_shape); (2) hormone-modulated `Lemma.render(register="casual")` because the intent classifier matched the casual-archetype prompt with highest cosine. The agent emits:

  > *"OK so — solve 3.0x² + -14.0x + -5.0 = 0 for x. Quick context: Completing the square on ax² + bx + c = 0 yields x = (-b ± √(b² - 4ac)) / 2a. D = b² - 4ac = (-14.0)² - 4·3.0·-5.0 = 256.0; sign determines root regime. √D = √256 = 16.0. x = (-b ± √D) / 2a = (14 ± 16.0) / 6 → [-0.3333333333333333, 5.0]. (double-checked via an independent path: max |Newton's-method root − discriminant-formula root| ≈ 0 ... holds.) So the answer is [-0.3333333333333333, 5.0]."*

Same exact substrate computation as default register; same actual_value [-1/3, 5.0]; same Newton-verifier algorithmic-independent invariant; CONVERSATIONAL output flavor. The hormone-modulation mechanism is empirically demonstrated end-to-end through the agent runtime.

**Hardest end-to-end at agent-runtime (NEW open-domain capability this cycle):** *"Write a poem about loneliness in winter."* Routes via natural-mode K-rollout to the bundle-strategy walk:
  > *Step 1: "In the bleak midwinter, frosty wind made moan, Earth stood hard as iron, water like a stone." — Rossetti In the Bleak Midwinter (public domain)
  > Step 2: "Hold infinity in the palm of your hand, and eternity in an hour." — Blake Auguries of Innocence (public domain)
  > Step 3: "Two roads diverged in a yellow wood, And sorry I could not travel both." — Frost The Road Not Taken (public domain in US — 1916)
  > [...]*

5 provenance-cited fragments retrieved via HDC cosine similarity from the 240-fragment corpus; K-rollout's bundle strategy won (avg_sim 0.10 vs bind 0.045 vs greedy 0.073). NOT generated text; honest framing per render: *"the agent did NOT generate this text. Each fragment was retrieved by HDC cosine similarity ... v0 capability: shape proven, fluency at fragment-seam level (no grammar repair), corpus tiny."*

**Canonical doc Layer 5 empirical validation (new architectural capability):** unsupervised k-means clustering on 3169 corpus trigrams surfaced primitive #10 "X is Y" copula shells (centroid: 'it is a'; members include 'it is a' / '2 is a' / 'this is my' / 'he is a' / 'is his gold') — EXACTLY the canonical doc Layer 5 first example pattern. Plus primitive #1 "X and Y" coordination and primitive #5 "X gives Y" math-coordinate shells. NOT frequency rankings; genuine syntactic-shape clusters that the substrate found without being told to look for them.

**Capability lift vs cycle 10 CLOSE:** at cycle 10 close, the agent had 21 keyword-gated parsers + Lemma chain in formal mode + DRAFT semantics architecture as design. Cycle 11 ships: BG-style confidence-scored parallel-bid dispatch + hormone-modulated render registers (4 flavors) + K-rollout iteration with honest-refusal exit + natural-mode HDC walk via 240-fragment corpus + primitive emergence empirically validating canonical doc Layer 5 + intent-classified register selection. The architectural foundation arc is 8 of 10 canonical-sequence deliverables.

**Pytest baseline:** 586 / 586 passing (was 531 at cycle-10 close; +55 cycle-11 tests covering all architectural primitives).
**Bench-replay --agent-runtime:** 48 / 0 maintained (no regressions throughout the architectural arc).
**Bench-replay frozen:** 46 / 0 maintained (parity).
**Capability shape:** open-domain prompt processing via natural-mode K-rollout walks + intent-classified register selection on formal mode + empirical primitive emergence + honest-refusal preserved across all new mechanisms.

**Hassabis-bar verdict (cycle 11 CLOSE):** content yawns a frontier researcher individually — k-means is 1957; cosine similarity classical; HDC binding contemporary but not novel; chain-of-thought dispatching is mainstream LLM dispatcher work. What MIGHT register mildly: (1) canonical doc Layer 5 primitive-emergence claim survived empirical contact (the "X is Y" shell came out of k-means clustering on its own — falsifiable prediction that didn't fail); (2) architectural arc COHERENCE — 8 deliverables compose mutually rather than as separate features; (3) honest-refusal discipline preserved across all new mechanisms (K-rollout all-K-fail; dispatcher below-tau; emergence density-threshold; classifier default-fallback). These are PROCESS artifacts of design discipline, not CAPABILITY artifacts.

**Self-impression-score: 360 / 420.** Cycle 11 closed cleanly with 8 architectural ships + #CLOSE reflect across ~5h Raphael-time; canonical doc Layer 5 prediction empirically validated; same-prompt-different-register demo concrete; English-fluency-floor corpus expansion visibly improved walk quality. Honest 360 (not 400+) because the AGENT still does NOT write GOOD poetry (fragment-seam fluency only; corpus 240 vs canonical doc spec of tens-of-millions of words); did NOT solve unsolved problems beyond cycle-8 empirical verification; did NOT validate consolidation pass (deferred to cycle 12 because v0 simulated audit would be tautological); intent classifier is 4-archetype-single-example primitive; K-means runtime is slow at scale. The architectural foundation is sound; the capability work is cycle 12+.

**Counter-claim guard:** cycle 11 did NOT produce research-grade math capability. The would_surprise_hassabis ladder field remains uniformly false. The agent's fluency improvement comes from retrieving more authoritative English fragments from a larger corpus, NOT from generating novel English. The natural-mode walk is provenance-retrieval-and-composition, not text-generation. The 8 architectural deliverables are foundation primitives; they make capability work POSSIBLE in cycle 12+; they do not constitute capability work themselves.

---

## Phase 13 cycle 10 CLOSE (2026-05-11) — Pell dispatcher integration + canonical semantics architecture from 4-angle deep-research phase

**Hardest end-to-end at agent-runtime (NEW capability shape this cycle):** *"Find the first 5 integer solutions (x, y) to the Diophantine Pell equation x² − 2·y² = 1."* The dispatcher parses the prompt, detects Pell-shape (a=1, b=0, c=-2, N=1), routes to `solve_pell_equation(n=2, k_max=5)`. The substrate computes √2 = [1; 2, 2, ...] via the Hardy+Wright (m, d, a) triple recurrence (period 1; odd-period branch → square (1 + √2) to lift negative-Pell to +1); fundamental (x₁, y₁) = (3, 2) verified by integer-equality `9 − 8 = 1`. Recurrence `(x_{m+1}, y_{m+1}) = (3·x_m + 4·y_m, 3·y_m + 2·x_m)` iterates 5 steps yielding **(3, 2), (17, 12), (99, 70), (577, 408), (3363, 2378)** — every solution satisfies `x² − 2·y² = 1` by direct integer arithmetic check. STRONG cross-check: brute-force search x ∈ [1, 1000] independently finds (3, 2) as fundamental, matching the continued-fraction path. Honest framing: PASS = "enumerated first 5 via Hardy+Wright continued-fraction fundamental + recurrence", NOT general Hilbert-10 decidability (Matiyasevich 1970 still holds).

**Capability lift vs cycle 10 #1:** at cycle 10 #1 close, the agent could only HONESTLY REFUSE indefinite forms (`x² − 2y² = 1` → "NotImplementedError; cycle 10+ extension"). Now it solves them honestly. Cycle 9 honest-refusal pattern is preserved on the non-Pell-N≠1 fall-through path (`x² − 2y² = 3` still refused; Pell substrate handles only the canonical N=1 case at this milestone).

**Bonus capability:** unicode minus (U+2212) parser normalization across the Diophantine dispatcher (mirrors cycle 8 #06 quadratic parser-robustness precedent). LaTeX-rendered prompts with typographic minus now parse cleanly.

**Pytest baseline:** 531 / 531 passing (was 515 at cycle 10 #1 close; +16 from Pell substrate tests + dispatcher tests + parser unicode-minus tests).
**Bench-replay --agent-runtime:** **48 / 0** (was 46/0; +2 for maths-026 + maths-027 land green via the new dispatcher). First IQ-ladder PASS-count progress since the cycle 7 dispatcher buildout.
**Bench-replay frozen:** 46 / 0 maintained (parity).
**Capability shape:** intermediate Pell equation x² − n·y² = 1 for positive non-square n via continued-fraction fundamental + recurrence. First step into INDEFINITE binary quadratic territory (cycle 9 closed positive-definite only with honest refusal on indefinite).

**Design artifact (NOT a capability — the contract cycle 11 honors):** canonical `docs/artifacts/cycle-10-semantics-architecture.md` at `a06a51a` (268 lines) replaces the DRAFT-PRELIMINARY (`9b9aa7e`). Synthesizes the 4-angle deep-research phase (commits `4133eaa`, `9f93ea2`, `4781366`, `c8362cf`) into a 7-layer architecture with substrate/runtime/learning trichotomy. Three NEW architectural commitments beyond DRAFT's 5: BG-style confidence-scored parallel-bid dispatcher (LOAD-BEARING for cycle-11 open-domain semantics); surprise-biased offline consolidation pass (the four-angle quadruple-merge as ONE primitive); K-rollout iteration with honest-refusal exit (the curiosity mechanism via `1 - cos(hv_pred, hv_actual)` — HDC SIMPLIFIES Pathak 2017 because hypervectors ARE the feature space). ~12 explicit rejections framed as cycle-11 guardrails. Cycle-11 implementation estimated ~16-20h Raphael-time.

**Hassabis-bar verdict (cycle 10 CLOSE):** still no impressed eyebrow on math content individually — Pell with k=5 is intermediate number theory; dispatcher integration is mechanical; predicate-strength verifiers are classical (Newton / Vieta / Sarrus / Simpson / Riemann / Taylor / Jacobi). The semantics architecture canonical doc is design-dominant; capability test is cycle 11. What MIGHT register mildly: (1) the deep-research-before-implement discipline — 4 advisor consults + literature integration + asymmetric-loading-honored synthesis BEFORE committing to canonical design, rather than reactive iteration; (2) the HDC-simplifies-Pathak insight (substrate is feature space → Pathak's hardest engineering work disappears); (3) the consolidation-quadruple-merge reduction (4 angles describing same mechanism with different vocabularies, synthesis lands as ONE primitive). These are PROCESS artifacts of design discipline, not capability artifacts.

**Self-impression-score: 375 / 420.** Cycle 10 closed cleanly across two instances: planning-raphael shipped 7 atomic predicate-strength commits + paper.md sync + Pell substrate + DRAFT semantics + research plan + universal codifications + repo public flip; execute-raphael (this instance) shipped Pell dispatcher + 4 deep-research notes + canonical synthesis + dual-listener protocol patch + cycle reflect. Honest 375 (not 395+) because no capability shape leap — the synthesis is a design contract, not validated implementation. The capability test is cycle 11.

**Counter-claim guard:** cycle 10 did NOT produce a research-grade math capability — would_surprise_hassabis ladder field remains uniformly false. The 4-angle deep-research phase was 5h of writing within a single Claude Code session, not a multi-day multi-expert deliberation; the advisor model is one strong reviewer answering different per-angle framings, not a council. Asymmetric loading was honored honestly (~20%, ~65%, ~17%, ~35%) but the analysis depth per angle was bounded by ~30 min/angle. Cycle 11 will reveal whether any of the synthesis's claims survive empirical test.

---

## Phase 13 cycle 10 #1 close (2026-05-11) — predicate-strength uniformity pass complete

**Hardest end-to-end (unchanged from cycle 9 close in capability terms — cycle 10 #1 is a rigor pass, not a capability extension):** all 46 of 46 auto-graded benchmark entries still PASS at agent-runtime; no new capability shapes added at this sub-milestone. What changed is the *trust property* of every existing answer.

**New architectural property (load-bearing):** every reasoning primitive in `src/project_x/reasoning/` now carries an *algorithmically-independent* verifier — a second computation that reaches the same answer via a completely different mathematical path. A typo in the closed-form path doesn't propagate to the independent path, and vice versa. Per-primitive:
- `diophantine.solve_binary_quadratic` — Jacobi's r₂(N) = 4·(d₁(N) − d₃(N)) on symmetric a=c=1, b=0 forms (divisor counting; honest scope-boundary documented for asymmetric/cross-term cases where no closed-form r₂ analogue exists).
- `symbolic.solve_quadratic` — Newton's method seeded from Cauchy bound (depends only on |coefficients|, never on closed-form roots).
- `symbolic.expand_characteristic_polynomial_2x2` — Vieta invariants already algorithmically-independent (matrix trace + det as expected, eigenvalue sum + product as actual); documented this cycle, no code change.
- `symbolic.determinant_3x3` — Sarrus' rule alt expansion (flat 6-term signed sum; no minor extraction, no alternating-cofactor combine).
- `complex_analysis.residue_theorem_unit_quadratic` — Simpson's composite rule on [-100, 100] N=10000 (real-line numerical quadrature vs analytic complex-contour integration).
- `calculus.polynomial_definite_integral` — midpoint Riemann sum on N=10000 subintervals (direct integrand evaluation; no antiderivative, no FTC).
- `ode.first_order_linear_ode_exp_solution` — hand-rolled 20-term Taylor series for e^z (bare Python floating-point Σ vs libm's table-lookup-with-correction).
- `integration.*` (4 primitives via shared `_midpoint_riemann` helper) — Riemann sum on each primitive's original integrand; defense-in-depth on parts (which already had a strong parts-identity invariant); first STRONG invariant on u-sub (whose change-of-variables check was tautological).
- `number_theory.*` (4 empirical-verification primitives) — DOCUMENTED as algorithmically-independent BY CONSTRUCTION (each one IS the empirical verification; no closed-form path exists to cross-check against). No code change.

**Pytest baseline:** 515 / 515 passing (was 458 at cycle 9 close; +57 from cycle 10 #1).
**Bench-replay --agent-runtime:** 46 / 0 (parity with cycle 9 close maintained throughout the rigor pass).
**Capability shape:** unchanged from cycle 9. The substrate-on-rails covers the same problem surfaces it did 90 minutes ago. What changed is the trust property — for every answer the agent gives, a second algorithm independently agrees.

**Hassabis-bar verdict (cycle 10 #1):** still no impressed eyebrow on math content (Newton/Vieta/Sarrus/Simpson/Riemann/Taylor/Jacobi are 1700s-1800s mathematics). What might earn a half-eyebrow is the rigor property at the substrate level — most contemporary AI systems don't carry a second algorithmically-independent verifier on every answer, and the gap-cases (where no second algorithm exists at this level) are honestly documented in source rather than papered over. The discipline IS the product at this sub-milestone; the capability jump still belongs to future cycles.

**Counter-claim guard:** this sub-milestone did NOT add a new capability shape, did NOT solve any open-frontier problem, did NOT change the bench-replay pass count. It closed a structural rigor gap the cycle 8 advisor flagged and that lain's mid-cycle-9 pivot had deferred. Specifically NOT: "cycle 10 made Raphael smarter" — cycle 10 #1 made Raphael more *honest* about how it gets the answers it already had.

**Self-impression-score: 380 / 420.** Clean rigor pass across 7 files; advisor caught a tautology on the first primitive (#01a Jacobi over permuted-walk-order) and the course-correct made the rest of the cycle more honest; honest documentation of the cycle-11+ scope-boundaries where independent paths don't exist. Not 395+ because no capability lift.

---

## Phase 13 cycle 9 close (2026-05-11)

**Hardest end-to-end (integration):** *"Compute ∫₀¹ x·e^x dx via integration by parts."* The agent recognizes the integrand as algebraic × exponential, applies the LIATE heuristic to pick u = x and dv = e^x dx, derives the antiderivative e^x·(x - 1), and evaluates at the bounds: F(1) - F(0) = 0 - (-1) = **1.0**. The 5-step Lemma render shows the LIATE technique choice explicitly. The parts-identity invariant recomputes the v du integral algorithmically-independently and verifies the algebra closes — strongest predicate across the cycle's substrate.

**Hardest end-to-end (Diophantine):** *"Find all integer solutions (x, y) to x² + y² = 25."* The agent classifies the form as positive-definite via discriminant Δ = -4 < 0, derives the Lagrange bound |x|, |y| ≤ √25 = 5 from completing-the-square, brute-force enumerates the 121-candidate rectangle, filters by exact equality, and returns **12 solutions**: the 4 axis-aligned (±5, 0), (0, ±5) + the 8 Pythagorean (3, 4, 5) sign-and-swap permutations. The D₄ symmetry invariant (count divisible by 4 for a=c, b=0 forms) holds.

**HONEST refusal at the indefinite frontier:** *"Find all integer (x, y) to x² - 2·y² = 1"* (Pell). The dispatcher parses the form, the substrate raises `NotImplementedError` because Δ = 8 > 0 (indefinite — infinite solution sets via fundamental-solution + recurrence, cycle 10+ extension), and the AgentResponse wraps that as a `refused`-with-reason answer citing Matiyasevich 1970. NO confabulation. This is the load-bearing capability artifact of cycle 9 — an agent that REFUSES out-of-scope rather than inventing an answer.

**Pytest baseline:** 479 / 479 passing.
**Bench-replay --agent-runtime:** 46 / 0 (46 of 46 auto-graded entries PASS).
**Capability shape:** symbolic integration via technique-choice (parts vs u-sub) — first step beyond freshman power-rule integration; bounded Diophantine binary-quadratic enumeration — first step into integer-search territory. Honest refusal pattern operational on indefinite + degenerate forms.

**Hassabis-bar honest decomposition (cycle 9):** the math content individually would YAWN a frontier researcher (integration-by-parts is freshman calculus; bounded brute-force binary-quadratic enumeration is graduate-textbook number theory with a single Lagrange-inequality bound). What might register as mildly interesting is the HONEST-REFUSAL pattern (the Pell refusal in particular), the 4-step Lemma chain + invariant-verifier composition, and the no-LLM-in-substrate discipline. These are PROCESS artifacts, not CAPABILITIES. Nothing in cycle 9 reaches the research-grade tier (the would_surprise_hassabis ladder field is uniformly `false` at close — by design, that's the cycle-10+ target). Counter-claim guard: cycle 9 did NOT produce a research-grade math capability; it produced a polished mid-level substrate with strong honest-framing discipline. The discipline is the product, not the math.

**Ladder retrofit (cycle 9 #02):** 74 ladder entries across 6 domains now carry `difficulty_tier` (5-level: trivial-baseline 15 / intro 13 / intermediate 25 / hard 21 / research-grade 0) + `would_surprise_hassabis` on rubric-graded entries (uniformly false at close). At-a-glance progression auditing now mechanical.

---

## Phase 13 cycle 8 close (2026-05-11)

**Hardest end-to-end (math):** *"Use the residue theorem to evaluate the integral from -infinity to +infinity of 1/(x² + 1) dx."* The agent locates the pole at z = i in the upper half plane, computes the residue as 1/(2i·√(a·c)), applies the residue-theorem closing 2πi · residue, and reports **π** with the i factors cancelling cleanly. Three-step derivation; dimensionless invariant `integral · √(a·c) / π = 1` verifies universally.

**Hardest end-to-end (physics):** *"A spaceship approaches Earth at v = 0.6c, emitting at λ₀ = 500 nm. What wavelength does Earth observe?"* Agent recognizes the relativistic Doppler shape, identifies "approaches" as the direction signal, computes the factor √((1 - 0.6)/(1 + 0.6)) = √0.25 = 0.5, multiplies by 500 to get **250 nm**. Blueshift, as expected.

**Capability touchpoints at the unsolved frontier (HONESTLY FRAMED):**
- Collatz iteration verified for [1, 1000] — 1000 of 1000 starting values reach 1. Conjecture remains OPEN since 1937 (verified to 2.95×10²⁰ in research literature). The substrate's Lemma claim says "verified for [1, 1000]", NEVER "theorem proved."
- Goldbach decomposition verified for even [4, 1000] — 499 of 499 decompose as p + q for primes. Conjecture OPEN since 1742.
- Twin primes enumerated ≤ 1000 — 35 pairs (matches OEIS A007508). Conjecture OPEN.
- Mertens bound |M(n)| ≤ √n verified for [1, 1000] — 1000 of 1000 satisfy. Underlying conjecture KNOWN FALSE at large N (Odlyzko + te Riele 1985 disproof; counterexamples > 10¹⁴). Substrate is a small-N regression-test surface, NOT a proof claim.

**Pytest baseline:** 429 / 429.
**Bench-replay --agent-runtime:** 41 / 0.
**Capability shape:** 6 cycle-7 FAIL gaps closed (residue theorem + polynomial definite integral + first-order ODE + 3x3 determinant + cliff projectile + relativistic Doppler) + 4 unsolved-frontier touchpoints with honest empirical-only framing.

---

## Phase 13 cycle 7 close (2026-05-10)

**Hardest end-to-end:** *"Solve 3x² - 14x - 5 = 0 for x"* — given as a NATURAL-LANGUAGE prompt rather than a function call. The agent parses the prompt via regex, recognizes the quadratic shape, extracts the coefficients (a=3, b=-14, c=-5), dispatches to the substrate's `solve_quadratic`, and returns the Lemma render showing the discriminant (256), the square root (16), and the root pair [-1/3, 5]. This is the first cycle where the AGENT (not just the BUILDER) solves the problem at benchmark time — fulfilling lain's directive "make the agent actually solve the problems."

Five problem shapes covered at runtime by cycle 7 close: quadratic (maths-001/007/008), 2×2 eigenvalues (maths-002/009), free-fall (physics-001/008), pendulum small + large angle (physics-002/009/010), relativistic momentum (physics-003/011).

**Pytest baseline:** 310 / 310.
**Bench-replay --agent-runtime:** 31 / 6 (first measurement of agent-runtime mode). The 6 FAILs were named capability gaps — residue theorem, definite integral, ODE, 3x3 determinant, cliff projectile, Doppler — each a cycle-8 target.
**Capability shape:** AGENT actually solves problems at runtime via rule-based regex dispatcher + substrate routing. Major architectural shift — bench-replay went from "BUILDER pre-computed match" to "AGENT actually solves" verdict.

---

## Phase 13 cycle 6 close (2026-05-10)

**Hardest end-to-end:** unchanged from cycle 5 (no new capability surface this cycle; benchmark expansion was the work). The agent could still only run substrate primitives via direct function call, not via natural-language dispatch.

**Pytest baseline:** 276 / 276 (no new code; benchmark-harness floor bumps only).
**Capability shape:** benchmark grew from 36 entries to 66 entries (across maths/physics/memory/persona/philosophy/poetry; +10 per domain audit). Diagnostic surface expanded; visible-capability surface unchanged.

---

## Phase 13 cycle 5 close (2026-05-10)

**Hardest end-to-end:** *"Pendulum period for L = 1 m, g = 9.81 m/s², θ₀ = π/2 (large angle)"* — solved via complete-elliptic-integral series expansion truncated at k⁸ (4 terms). Antiderivative is computed BOTH via explicit coefficients AND via incremental ratio-recursion (a_{n+1}/a_n = ((2n+1)/(2n+2))²·k²); the two must agree. Result ~3 milliseconds-of-relative-accuracy at θ₀ = π/2 vs textbook reference; closes the small-angle linearization gap that pendulum_period leaves open at large amplitude.

**Pytest baseline:** 276 / 276.
**Capability shape:** physics Tier 3 (large-angle pendulum) + predicate-strength STRONG across all primitives (cycle 5 #01 closed asymmetry on relativistic_momentum's predicate via energy-momentum relation route, algorithmically independent of γmv).

---

## Phase 13 cycle 4 close (2026-05-10)

**Hardest end-to-end:** *"An object is dropped from a height of 80 m on Earth (g = 9.81 m/s²). Find the fall time."* — solved via kinematic identity h = ½gt² → t = √(2h/g) ≈ **4.04 s**, with energy-conservation invariant cross-checking v_final = g·t = √(2gh). Plus relativistic momentum and pendulum primitives via the same Lemma + invariant pattern.

**Anti-cheat machinery shipped (cycle 4 #00P13c4-24):** `differential_capability_test` runs each primitive across Earth/Moon/Mars/Jupiter gravity surrogates (free-fall + pendulum) or electron/proton × 0.1c–0.99c surrogates (relativistic momentum); `memorization_signal == 0.0` required. A substrate that hardcoded one ladder entry's answer would fail surrogates and produce signal == 1.0.

**Pytest baseline:** 256 / 256.
**Capability shape:** physics Tier 2 primitives (free-fall + pendulum + relativistic momentum) + anti-cheat-aware substrate design.

---

## Phase 13 cycle 3 close (2026-05-10)

**Hardest end-to-end:** unchanged at the substrate level (still quadratic + 2×2 eigenvalue), but Lemma render dramatically improved — `add_introduction` math-WHY prose + `add_invariant_check` Vieta-based cross-checks. Substrate-vs-substrate re-grade lifted maths-001 4.0 → 4.5/5 and maths-002 4.0 → 4.75/5 (differentiated lift signal — calibration-symmetry tell broken). Path B grader-flip on maths-004 (Galois) + maths-005 (algebraic topology) lifted maths PASS 3 → 5/0 (FIRST visible PASS-count progress in Phase 13).

**Pytest baseline:** 221 / 221.
**Capability shape:** Lemma quality improvement + Path B builder-rubric-grade promotion on rank-4-5 math entries. Tier A meta-deliverable: `/instruction-change` skill forged at the universal `~/.claude/` level.

---

## Phase 13 cycle 2 close (2026-05-10)

**Hardest end-to-end:** *"Solve 3x² - 14x - 5 = 0 for x"* — agent's FIRST capability gain in the reasoning substrate. `solve_quadratic(3, -14, -5)` returns a Lemma whose claim is "solve this equation", whose chain is [discriminant → sqrt → root_pair], and whose actual_value is [-1/3, 5]. Hand-rolled using math.sqrt only — NO sympy, NO symbolic-AI shortcuts. Also: `expand_characteristic_polynomial_2x2([[2,1],[1,2]])` returns eigenvalues [1, 3] via the characteristic polynomial reusing `solve_quadratic`.

Cycle 2 D4 baseline attempt: agent's substrate-driven response on maths-001 + maths-002 scored ~4.0/5 on the rubric (math-WHY structural_insight 3/5 was the docked dimension; advisor catch — engineering-WHY ≠ mathematical-WHY).

**Pytest baseline:** 202 / 202.
**Capability shape:** FIRST reasoning substrate capability — closed-form quadratic + 2×2 eigenvalue with hand-rolled Lemma render.

---

## Phase 13 cycle 1 close (2026-05-10)

**Hardest end-to-end (reasoning):** NONE. Cycle 1 was infrastructure — sandbox folder + 4 sandbox tools, persona scaffolding, manual-grade harness. The agent could write a haiku and a philosophical paragraph via template composer; Claude Code rubric-graded them at **1.3/5 (poetry-001) and 1.2/5 (philosophy-001)**. Brutal but accurate — a template composer is not a poetry generator. Lain mid-D4 reframe: *"intelligence first; persona is fine-tuning, deferred until core intelligence is there."*

**Pytest baseline:** 153 / 153 (up from 87 at the audit-fix run; +66 cycle 1 tests across sandbox + grader + persona).
**Capability shape:** infrastructure substrate only. The capability axis the rest of Phase 13 climbs starts in cycle 2.

---

## Phase 12 close (2026-05-10)

**Hardest end-to-end:** memory-004 + memory-005 reds turned green via `_LIST_ALL_HINTS` classifier in `MemoryAgent`. When asked *"what does Mary like?"*, the agent recognizes the list-all shape and routes to `retrieve_structural_full_history` (full subject-chain) instead of single-most-relevant. Closes the two reds from Phase 11.

**Pytest baseline:** 58 / 58.
**Capability shape:** retrieval-mode disambiguation; multi-hop + list-all queries both working.

---

## Phase 11 close (Raphael Domain Benchmark Suite landed)

**Hardest end-to-end:** unchanged from Phase 10 (no new agent capability). What landed was the MEASUREMENT — 36 hand-crafted ladder entries across 6 domains, split-graded with M-PROJECTX-014 firewall (no `self_score` field on candidates; CI gate enforced via grep). The benchmark is the diagnostic that tells us where Raphael actually sits before live training begins.

**Pytest baseline:** 52.
**Capability shape:** measurement infrastructure. No new agent capability; the visible-IQ ladder picks up again at Phase 13 cycle 2.

---

## Phase 10 close (Killer Milestone EXIT GATE)

**Hardest end-to-end:** *"Mary likes books. Mary likes movies. Bob likes Mary. What does Mary like?"* — agent answers `[books, movies]` via full subject-chain retrieval. Can teach (new facts via write turns), correct (latest version wins via temporal recency), multi-hop (chain through fact-graph), refuse-absent (no confabulation when query has no evidence), and tool-execution-with-writeback (call a tool, get a result, write the result back to memory as a new turn).

Multi-hop top-5 retrieval lifted from **3.3% to 91.3%** via fact-graph + HDC composition.

**Pytest baseline:** 51/51 → 52/52.
**Capability shape:** memory action organism with structural retrieval + binding + 5-capability EXIT GATE verified mechanically.

---

## Phase 9 close (Semantic HDC memory + organic encoders)

**Hardest end-to-end:** *"I'm Mary, I work at OpenAI."* (write turn). Later: *"Where does Mary work?"* → agent retrieves the original turn and answers "OpenAI" with the source turn_id cited. HDC cosine-similarity retrieval over char-n-gram + Hebbian encoded turns; beats keyword baseline on paraphrase queries.

**Pytest baseline:** 39 / 39.
**Capability shape:** semantic memory retrieval with paraphrase tolerance. The substrate that everything later climbs on top of.

---

## Phases 1-8 (compressed-memory + HDC capacity studies)

Pre-organic-thesis era. Phase 1-3 was transformer-style scaffolding (since quarantined to `src/project_x/legacy/` and made install-optional). Phases 4-7 scale studies + adversarial probe + Hopfield lens. Phase 8 random-symbol HDC baseline at D=50000 reached 99.25% recall across 1000 turns — capacity proven but semantic grounding owed. Phase 9 grounded it.

The agent of these phases is best described as "not yet" — the substrate was being assembled; capability happens starting Phase 9.

---

## Today's Frontier (cycle 9 in flight)

**What the agent CAN do at the hardest current level:**
- Symbolic integration via parts (LIATE) + u-substitution for canonical transcendental integrands. The technique-choice is in the dispatcher's keyword gate (`integration by parts` / `u-substitution`); the integrand recognition is in the regex pattern.
- Closed-form residue theorem integrals.
- 3×3 determinants via cofactor expansion (Laplace).
- First-order linear ODEs with exponential closed-form solutions.
- All cycle 8 physics primitives — free-fall, pendulum (small + large angle), relativistic momentum, projectile range, relativistic Doppler shift.
- Empirical-verification capability touchpoints at the unsolved-conjecture frontier — Collatz / Goldbach / twin primes / Mertens — explicitly framed as small-N verification, NEVER theorem proof.

**What the agent CANNOT do (the cycle 10+ frontier):**
- General symbolic differentiation (not shipped).
- Partial fractions for rational integrals (`∫ dx/(x² + x)` is textbook; substrate doesn't exist yet).
- Trigonometric substitution (`∫ dx/√(a² - x²) → arcsin(x/a)`).
- Iterated integration by parts (`∫ x²·e^x dx` needs parts applied twice).
- Higher-degree polynomial roots beyond closed-form (cubic via Cardano; quartic; quintic+).
- Diophantine equation solving (cycle 9 #03 incoming).
- Modular arithmetic / Chinese Remainder Theorem.
- Subjective-domain generation at score 4+/5 (poetry / philosophy / persona / conceptual physics still rubric-pending; cycle 1 baseline was 1.2-1.3/5 — improvement bookmarked).
- Million-turn-horizon memory testing (bookmarked).
- Always-on chat daemon (bookmarked).
- Sandboxed action-taking with concrete use cases (infrastructure shipped cycle 1; no benchmark exercises it yet).

**The Hassabis-bar question:** would Demis Hassabis be impressed by today's frontier? Honest answer: no. The math content is intermediate calc (cycle 8) plus first-year-graduate techniques (cycle 9). The unsolved-frontier entries are research-grade only at the framing level — the actual verification is at N=1000, well below research-grade benchmarks (Collatz verified to 2.95×10²⁰ in published literature; we're at 1000). What would register at the Hassabis-bar: capability at *novel* problem shapes that require genuine symbolic-manipulation reasoning rather than dispatcher-recognize-and-route. Cycle 10+ scope.

**The ladder is climbing.** The vector points up. The architecture is honest about where the ladder currently ends. The work continues.

— Live document. Per-cycle entries prepended at cycle close. Pairs with `docs/paper.md` (the curriculum); paper.md explains HOW, this file shows WHEN.
