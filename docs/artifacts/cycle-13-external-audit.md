# Cycle 13 — External Audit (GPT findings + audit-of-audit response)

**Date:** 2026-05-11.
**Trigger:** lain requested external audit at the #07a/#07b boundary; this Claude instance composed an audit-request prompt, lain pasted it to GPT, GPT returned a 5-section findings report (A/B/C/D/E). This doc captures (1) the GPT findings, (2) this instance's audit-of-audit per-section verdict, (3) concrete cycle-13 corrections, (4) cycle-14+ reframings.
**Pairs with:** `cycle-13-priority-decision.md` (the synthesis verdict GPT audited), `cycle-13-demo-22k.md` (the demo data the synthesis was built on), the 5 council-angle notes.

---

## 1. Why an external audit at this seam

The cycle-13 synthesis verdict (commit `3308987`) committed to multi-ship of a1 (bitpack, ~25%) + a5 (dispatcher calibration, ~32%) on combined-axis scoring. Two atomic commits had shipped (`ff46c2b` bitpack module, `665f8a8` bitpack tests) when lain asked for an external read before the higher-variance dispatcher work began. The audit-gate exists to catch sunk-cost on potentially-misdirected calibration: if GPT's read of the synthesis reveals a structural issue, fixing the issue before #07d-f costs less than after.

GPT's audit is structurally strong. Real catches; specific file:line refs; correct identification of the missing capability axis. The audit response below honors the catches AND retains where this instance's read was already correct.

## 2. GPT findings — per-finding verdicts

### Section A — Structural critique of the synthesis verdict

| # | Finding | Verdict | Action |
|---|---|---|---|
| A1 | Council missed "generative composition" as load-bearing angle | **AGREE — important** | Cycle-14 council MUST include generation-as-an-angle. Flag in #08 reflect. |
| A2 | Council missed "credit assignment / policy improvement" | **AGREE — important** | Cycle-14 council should include evaluator-driven policy learning. Distinct from angle 4's bootstrap-audit (which is consolidation-pass-only). |
| A3 | a1-before-a5 is only right if a5 cannot slip | **AGREE — sharp** | Mitigation: commit hard to shipping #07d + #07e THIS cycle. NORMAL-mode discipline: cycle does not close until a5 ships. |

**Section A net:** GPT's structural critique IS the audit's load-bearing contribution. The council deliberated over substrate (a1), substrate-geometry (a2), data-quality (a3), consolidation (a4), dispatch (a5). It did NOT deliberate over generation. The demo doc's §counter-claim #1 admitted the system "did NOT produce poetry — it surfaced surface-similar Whitman" — but the council did not surface the generation gap as its own angle. That is the single largest structural miss.

### Section B — Bug hunt

| # | Finding | Verdict | Action |
|---|---|---|---|
| B1 | Bitpack core math is correct | **AGREE** | 29 tests pass; cosine equivalence integer-exact. No action. |
| B2 | Source/docs disagree on D=10240 | **AGREE — REAL BUG** | `src/project_x/experiments/encoder.py:121` is `D: int = 10000`. Bitpack module docstring + REPO_CONTROL claim D=10240. **FIX IN #07c** as part of encoder shim — bump encoder default to D=10240 + update affected tests. |
| B3 | Packed emergence not implemented | **PARTIAL** | Correct as state observation. Mitigation: it's queued as #07c (encode_packed) + #07f (emergence-at-scale run with packed=True). **Cycle 13 cannot close until both ship.** |
| B4 | Collatz parser doesn't match prose form | **AGREE — REAL BUG** | `_parse_collatz_verify` (line 533) gates on "collatz" keyword + `_NT_RANGE_1_PATTERN` regex `\[\s*1\s*,\s*(\d+)\s*\]`. The demo prompt "first 10000 integers" doesn't match the bracketed form. Formal-parser priority boost (a5 Part A) does nothing if formal returns None. **FIX IN #07d** — extend `_NT_RANGE_1_PATTERN` to accept prose-form ("first N integers", "for n up to N", "in the first N"). |
| B5 | τ_satisfaction=0.0 masks low-quality walks | **AGREE — calibration debt** | At `_K_ROLLOUT_TAU = 0.0`, all walks emit; honest-refusal-on-all-K-fail mechanism is structurally present but always passes. **DOCUMENT AS KNOWN CALIBRATION DEBT in #08 reflect**; pre-register τ=0.2-0.3 as a cycle-14 calibration task; not blocker for cycle 13 close. |

**Section B net:** Two hard bugs surfaced (B2, B4); both fixable inside the existing cycle-13 #07c-d sub-tasks. B5 is real calibration debt that should be honestly logged. B3 is correct-as-observation but plan addresses it.

### Section C — Architectural critique

| # | Finding | Verdict | Action |
|---|---|---|---|
| C1 | HDC dimensional capacity ≠ semantic capacity | **AGREE — important reframe** | The 10⁸-association claim is about random-vector near-orthogonality at D=10000. Our vectors aren't random; they're a 4096-feature char-n-gram hash projected to D=10000. Effective semantic capacity is bounded by the hash feature space, not the projection dim. **REFRAME canonical-doc Layer 6** in cycle-13 close OR cycle-14 — either back the 10⁸ claim with information-theoretic precision, or honestly downgrade to "random-vector near-orthogonal up to N at this D; semantic capacity bounded by encoder feature space; empirical capacity TBD." |
| C2 | "Memory IS the model" lacks demonstrated compression-and-control | **AGREE — slogan vs mechanism** | Current state: retrieve-with-provenance works; consolidation is deferred; audit-loop binding-strength-adjustment has no real audit data; Layer 5 emergence unvalidated at scale. The "memory IS the model" framing is aspirational. **REFRAME canonical-doc** in cycle-14 to either ship a compression-and-control mechanism OR honestly describe the current state as "retrieval with provenance + planned learning loop." |
| C3 | Layer-5 clustering is trigram pattern mining, not variable-binding induction | **AGREE — precision issue** | Cycle-11 #06 MVP found "X is Y" clusters as LITERAL trigram strings ("it is a", "2 is a"), not abstract is-a relations with variable slots. **REFRAME canonical-doc Layer 5** + cycle-11/12 doc honest update: current implementation is "string pattern emergence"; variable-binding primitive induction is cycle-14+ work requiring different machinery (role-filler binding clusters, not trigram clusters). |
| C4 | D=10240 is engineering alignment, not capability upgrade | **AGREE — restates C1** | No separate action; absorbed by C1 reframe. |

**Section C net:** Three architectural slogans need honest reframing — the 10⁸ capacity claim, the "memory IS the model" framing, the Layer-5 emergence framing. None are immediately load-bearing for cycle-13 close, but ALL must reframe before the canonical-doc serves as ground truth for cycle-14+ planning.

### Section D — Gaps in the plan

| # | Finding | Verdict | Action |
|---|---|---|---|
| D1 | Novel answer generation is silently behind infrastructure work | **AGREE — restates A1** | Cycle-14 council MUST include generation. |
| D2 | Unsolved-tier math overestimated; finite verification is not frontier reasoning | **AGREE — honest framing** | The number-theory module IS honest about finite-range verification (M-PROJECTX-013 framing is preserved in walks). Reframe Manifesto Terminus expectation: "unsolved-tier math via finite verification" is NOT the Terminus target; actual frontier reasoning is. **REFRAME Manifesto Terminus** wording in cycle-14: clarify "unsolved-tier" means producing genuinely new results, not bounded computation. |
| D3 | #07f lacks objective validation predicate | **AGREE — actionable now** | **FIX IN #07f** — before running emergence-at-scale, pre-register a scoring predicate: e.g., "clusters are STRUCTURAL if ≥40% of cluster-member trigrams share a parseable shell ('X is Y', 'X and Y', etc.) AND the shell is consistent across cluster centroids; clusters are FREQUENCY-ranked if member trigrams share no shell beyond high-frequency-coincidence." Without pre-registration the result is interpretive. |
| D4 | Persona/humor/always-on chat not advanced this cycle | **ACCEPT — cycle-14+** | Cycle 13 was infrastructure + calibration. Not a critique to act on. |

**Section D net:** D3 is a concrete addition to #07f that costs little (~10 min to write the predicate, before running emergence). D1 is restated A1. D2 is a Manifesto-level reframe for cycle-14+.

### Section E — Honest overall assessment

| # | Finding | Verdict | Action |
|---|---|---|---|
| E1 | Project is at "auditable substrate plus demos," not "approaching super-human agent" | **AGREE** | The cycle-13 reflect (#08) should explicitly state this — honest framing of where the project actually is vs the Terminus. |
| E2 | Discipline impresses; capability-leap claim from classical components bores | **AGREE** | Cycle-13 self-impression-score should honor this. Process artifacts ≠ capability artifacts. |
| E3 | Missing direction: evaluator-driven composition policy learning | **AGREE — the big one** | This is the synthesis of A1 + A2 + D1. **CYCLE-14 COUNCIL must surface "substrate-native generator + evaluator + credit-assignment loop" as a top angle.** The current cycle-13 plan (a1+a5 ship) does not move this needle. Cycle-14 #1 should plausibly be "generation/evaluator/policy" not more retrieval infrastructure. |

**Section E net:** The audit's strongest framing. The current cycle ships discipline + calibration; the Terminus needs generation + learning. Cycle 14's council must hold this question.

## 3. Concrete cycle-13 corrections (ship before close)

Roll-in to existing sub-tasks:

| Correction | Source | Where it lands |
|---|---|---|
| Encoder D bump 10000 → 10240 | B2 | **#07c encoder shim** (same file edit; bump + tests; affected test re-runs) |
| Collatz formal parser widen to prose form | B4 | **#07d dispatcher Part A** (extend `_NT_RANGE_1_PATTERN` OR add a prose-form variant; new test cases) |
| Pre-registered scoring predicate for emergence | D3 | **#07f emergence-at-scale** (write predicate ~5-10 lines BEFORE running; emergence run reports against predicate) |
| τ_satisfaction calibration debt | B5 | **#08 cycle reflect** — explicit "known calibration debt" section; cycle-14 task created |

No new TaskList rows needed; corrections fold into existing #07c/d/f and #08.

## 4. Cycle-14+ reframings (not cycle-13 deliverables — pinned for the next planning instance)

1. **Cycle-14 council MUST include "generative composition / evaluator-driven policy learning" as an angle.** This is the single most important takeaway from the audit. The fresh planning instance for cycle 14 sees this doc and surfaces the angle explicitly.
2. **Canonical-doc Layer 5 honest reframe:** current emergence is "trigram pattern mining"; variable-binding primitive induction is a separate, harder problem requiring different machinery.
3. **Canonical-doc Layer 6 honest reframe:** "memory IS the model" needs information-theoretic backing OR downgrade to "retrieval with provenance + planned learning loop." The 10⁸-association claim must be precise about random-vector near-orthogonality vs semantic capacity.
4. **Manifesto Terminus "unsolved-tier math" wording reframe:** clarify that bounded-N empirical verification is NOT what the Terminus asks for; actual frontier reasoning is the bar.

These reframings are doc-edits + framing-shifts; not capability work. Land them in cycle 14 or 15 as the next planning instance decides.

## 5. Honest acknowledgment

GPT caught two bugs (D mismatch, Collatz parser) I shipped past in commit messages claiming the change was made when only the docs were updated. GPT caught two architectural slogans (HDC capacity, "memory IS the model") I let pass through five cycles without precision. GPT caught the structural miss (no generation angle in the council) that the 5-angle deliberation was supposed to prevent. This instance's previous audit-of-self (the synthesis pre-write advisor consult) did NOT catch any of these. External audit closed the self-assessment gap.

This is M-PROJECTX-013 (claim-without-measuring) AT THE DOC LEVEL: the docs claimed the encoder was D=10240 because the design said it should be; nobody verified the source matched. The fix isn't just to bump D — it's to add doc-source consistency to the mechanical proof gate. Logged as a candidate `M-PROJECTX-NNN` in cycle reflect: *"doc claims about source state require source verification in the same commit."*

---

*Single-line takeaway: cycle 13 ships #07c-f WITH the audit-corrections folded in + #08 reflect with honest framing + cycle-14 plan that surfaces generation as the missing angle. The audit was load-bearing; the corrections are bounded; the cycle-14 framing shift is the big move.*
