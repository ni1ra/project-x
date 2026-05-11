# Do This Next — Project X — Phase 13 cycle 15 (handoff from cycle 14 CLOSE)

**Generated:** 2026-05-11 (cycle 14 CLOSE — substrate writability + reward-loop wiring + one piece of dispatcher scaffolding retired)
**Session Context:** Cycle 14 shipped the substrate's first reward-driven write path (HebbianBank substrate-wide co-occurrence + audit-rating wire + retrieval blend) + retired the `_NATURAL_MODE_TRIGGERS` keyword-regex gate as proof-of-direction. Mid-synthesis, lain caught the pre-correction A2 + A3 verdict as still hand-coding (per-primitive learned embeddings + per-decision-coefficient credit propagation); synthesis pivoted to A1 alone (substrate-wide Hebbian). 15 atomic commits across cycle 14; 6 of 7 #08 implementation sub-tasks shipped clean; #08e (τ_satisfaction calibration) deferred to cycle 15 with two substantive findings.
**Warning Level:** NORMAL — clean handoff; cycle-14 reflect doc is at `docs/past_work/cycles/phase_13/dev-cycle-14.md` for the full ledger.

---

## The thesis (READ FIRST — binding per `docs/MANIFESTO.md`)

> lain 2026-05-11 strict: *"i would even go so far as to say we shouldnt even hard code the math algos, it should learn it on its own. if we have good enough training data, and smart enough model, it should learn all itself."*
>
> lain 2026-05-11 strict-strict (mid-cycle-14 synthesis course-correction): *"there shouldnt be a need for us to hand pick anything. it should naturally emerge as the best solution, model on its own. if you stimulate the right rewards you will get emergent behaviour. you really keep trying to hardcode everything."*

**Only hand-coded structure allowed: the substrate's HDC arithmetic (bind, bundle, cosine, pack), the encoder (char-n-gram-hash → projection), the substrate-wide learning rule (Hebbian co-occurrence), and the I/O plumbing for the reward signal.** Everything else — tool-use, routing, composition strategy, scorer architectures, per-tool weights, per-decision coefficients — must EMERGE from reward shaping. Cycle-14 surfaced this: A2's "per-primitive learned embeddings + argmax scorer" and A3's "per-decision-coefficient credit propagation" passed 5 angle commits + advisor pre-write + synthesis draft before lain caught them.

**Cycle-15 process improvement (load-bearing for next council):** thesis-compliance gate per-angle, BEFORE each angle commits, with explicit *"would lain call this hardcoding?"* sanity-check. Synthesis is the WRONG gate for this — by synthesis time, 5 angles are already on disk and pivot cost is high.

---

## 1. PROJECT CONTEXT

### What is this?

Project X is the engineering substrate that, layer by layer, becomes **Project X Raphael** (the AGENT — distinct from Claude Code Raphael, the BUILDER). Not a wrapper, not a RAG agent, not a fine-tuned LLM. An organic stack whose intelligence must emerge naturally from learned experience over an auditable substrate.

### What problem does it solve?

The Terminus (per `docs/MANIFESTO.md`): super-human capability across math + poetry + philosophy + physics + perfect memory + persona + always-on chattability + sandboxed action-taking. The agent acquires this from training data + audit signal over the HDC learning substrate, not from authored code.

### Tech stack

- Python 3.12 + NumPy 2 (substrate + tests)
- HDC primitives (`src/project_x/hdc_infra/`): bipolar int8 hypervectors + bitpacked uint32 (cycle-13) + reward-driven Hebbian co-occurrence bank (cycle-14)
- Char-n-gram-hash encoder (`src/project_x/experiments/encoder.py`) — D=10240 — no pretrained transformer derivatives (lain 2026-05-09 binding)
- Audit-rating channel (`src/project_x/audit/`) — JSONL log + apply_rating CLI; rating → HebbianBank wire shipped cycle-14
- 22k-fragment Tier-2 corpus (`data/corpus_raw/`): Whitman, Plato, Aristotle, Shakespeare, Wordsworth, Yeats, Dickens, Austen, Carroll, Shelley, Aurelius, Tao Te Ching

## 2. ENVIRONMENT STATE

### Platform

- OS: Linux WSL2 (kernel 6.6.87.2)
- Working directory: `/mnt/c/Users/nira/Documents/Research/projext-x`
- Shell: bash

### Runtime versions

- Python 3.12.3 (verified `python3 --version`)
- pytest 9.0.2
- NumPy 2.x (uses `np.bitwise_count` — cycle-13 bitpack dependency)

### Required services

- Discord listener pair (`pgrep -af 'discord-wait-for-lain'` should show ≥ 2 procs). Cycle-14 close listener PIDs: 1139, 1140.
- Heartbeat cron `c8e56966` armed at `7,22,37,52 * * * *`. Disarms when queue empty + final-checks passed.

### Environment variables

- `.env` keys (names only — never paste values): `DISCORD_BOT_TOKEN` (used by listener + `discord_send`); rest is universal Raphael infra.

### Known environment gotchas

- WSL ceiling 7.8 GB. Cycle-13 crashed WSL TWICE on unpacked int8 trigram k-means; cycle-13 #07a bitpack substrate is the prevention. Any HDC-at-scale work routes through `encode_packed` + `cosine_packed`.
- `encoder.encode` builds a transient float32 projection at encode time; batched-encoding is queued cycle-15+ work for any work that touches >50k trigrams.
- The HebbianBank persistence path is `data/hebbian_bank/main.pkl` (cycle-14 default). Tests pass `hebbian_bank_path=tmp_path` to AuditLog / NaturalModeComposer for isolation.

## 3. CURRENT STATUS

### Git state

```
Branch: main (tracking origin/main)
HEAD: d854fbc docs(P13c14-08f-demo-rerun): cycle-14 demo verification — Arm A cold-start preserved, Arm B reward-shift verified
Pending atomic close commit: this cycle-14 close bundle (4 docs: dev-cycle-14.md + DO_THIS_NEXT.md + A_TO_Z_PLAN.md §6 CHANGELOG + IQ_PROGRESSION.md)
Uncommitted: docs/past_work/cycles/phase_13/dev-cycle-14.md (untracked, about to land in close commit)
Unpushed: none beyond the close commit
```

### What's complete (cycle 14)

- [x] #00P13c14-01 capability demo on post-cycle-13 agent (5 fresh prompts) — `d89b90f`
- [x] #00P13c14-02..06 five council angle notes — `a0babad` / `d40572d` / `b691961` / `743128b` / `8ccac83`
- [x] #00P13c14-07 synthesis verdict (A1 alone, R2 transition, #08g pre-retirement) with advisor pre-write — `9b1f8fd`
- [x] #00P13c14-08a HebbianBank class (substrate-wide co-occurrence) — `d2ba7c1`
- [x] #00P13c14-08b Audit-rating → HebbianBank wire — `7b5db3d`
- [x] #00P13c14-08c Retrieval blend in NaturalModeComposer + KRolloutComposer — `c4c0948`
- [x] #00P13c14-08d HebbianBank tests (23 tests, cold-start regression + math + sweep + persistence) — `9be9a9b`
- [x] #00P13c14-08g `_NATURAL_MODE_TRIGGERS` keyword-regex gate retired — `513c186`
- [x] #00P13c14-08f Cycle-14 demo re-run on Hebbian-active agent (Arm A cold-start preserved + Arm B reward-shift verified) — `d854fbc`
- [x] Cycle-14 close ritual: dev-cycle-14.md (this) + DO_THIS_NEXT.md (this) + A_TO_Z_PLAN §6 + IQ_PROGRESSION prepend

### What's deferred-with-finding (cycle 14 → 15)

- [ ] #00P13c14-08e `_K_ROLLOUT_TAU` calibration — DEFERRED with two findings (see §4 + §9). Cycle-15 closes alongside the BG-dispatcher refused-candidate filter.

### Cycle-15 council-prep state (mid-cycle-15 snapshot, post-2026-05-11 session)

The 2026-05-11 cycle-15 work-session shipped 5 of 6 council surfaces from the BUILDER side. The remaining 2 are GENUINELY lain-pending (not mis-categorized parks):

- [x] **#00P13c15-01 capability demo** on post-cycle-14 agent (5 fresh prompts; F1 formal-pendulum bypass + F3 missing-archetype-saturation re-confirmed) — commit `c197bbd`
- [x] **#00P13c15-02 B1 dispatcher fix angle note** (paired: refused-candidate filter R1/R2-independent + per-domain τ R2-dependent) — commit `c97605b`
- [x] **#00P13c15-03 B2 corpus scale-out angle note** (refined cycle-14 A4 with cycle-15 demo findings; ~250k words across 5 domains) — commit `d4293e9`
- [⏸] **#00P13c15-04 B3 per-domain predicates** — math predicate v1 SHIPPED at commit `afe6a64`; poetry/philosophy/chat sibling predicates **FIREWALL-BLOCKED per M-PROJECTX-014** (subjective-domain pre-registration requires lain's rubric input or external GPT audit framework; solo guessing would be theatre)
- [x] **#00P13c15-05 B4 per-angle thesis-compliance gate** — checklist + retrospective application to cycle-14 A2/A3 — commit `bb8f297`
- [⏸] **#00P13c15-06 B5 cycle-13 audit C-reframes** — **LAIN-PENDING** per cycle-14 reflect "Open questions" (target wording for canonical-doc reframings on 10⁸-association capacity claim + "memory IS the model" + Layer 5 emergence framing)

### What's still pending for cycle-15 synthesis + implementation

- [ ] **R2 vs R1 confirmation from lain.** Synthesis verdict (commit `9b1f8fd`) defaulted R2 transition; R1 radical surgery offered as override window. lain confirmation did NOT arrive in the 2026-05-11 work-session. Cycle-15 synthesis cannot select cycle-15 #1 implementation surface without this.
- [ ] **B3 sibling predicates rubric input** — lain provides poetry/philosophy/chat rubric scales (or authorizes external GPT audit framework); then 3 sibling predicates ship as pre-registered docs analogous to math predicate v1.
- [ ] **B5 cycle-13 audit C-reframes target wording** — lain provides direction; then proposal-for-review doc lands.
- [ ] **Cycle-15 synthesis verdict** — runs after all 6 council surfaces are at angle-note level + R1/R2 + rubric input arrives. Picks 1-2 cycle-15 #1 implementation candidates with honest combined-axis scoring + advisor pre-write.
- [ ] **Cycle-15 #1 implementation per synthesis** — depends on synthesis pick.
- [ ] **Cycle-15 close ritual** — dev-cycle-15.md + cycle-16 handoff DO_THIS_NEXT rewrite + A_TO_Z §6 + IQ_PROGRESSION prepend.

### Task list state (post-2026-05-11 work-session)

```
#1   pending     #∞ NORMAL mode operation (eternal — heartbeat cron c8e56966)
#2   pending     #00P13-data-curation (eternal — Tier-2 corpus + cycle-15 A4 scale-out target)
#3-18  completed  cycle-14 #01-#09 umbrella + #08a-g sub-tasks (all on origin/main d89b90f → 5dd4b64)
#19  completed   #00P13c15-01 capability demo (c197bbd)
#20  completed   #00P13c15-02 B1 dispatcher fix angle note (c97605b)
#21  completed   #00P13c15-03 B2 corpus scale-out angle note (d4293e9)
#22  in_progress #00P13c15-04 B3 per-domain predicates (math done afe6a64; 3 siblings firewall-blocked)
#23  completed   #00P13c15-05 B4 per-angle thesis-compliance gate (bb8f297)
#24  pending     #00P13c15-06 B5 cycle-13 audit C-reframes (lain-pending direction)
```

Carry-forwards (lain-pending; DO NOT touch unprompted):
- #00P13c8-07 CLAUDE.md trim (~59.3k vs 46k ceiling)
- #00P13c7-04 council audit tag

## 4. DECISIONS & RATIONALE

### Strict-strict thesis (mid-cycle-14 binding, load-bearing for cycle 15+)

**Why this matters:** "LEARNING MACHINERY allowed" is permissive enough to admit hand-coded scorer architectures + per-tool embeddings + per-decision coefficients with learned weights. lain's cycle-14 mid-synthesis catch closed that loophole. Cycle-15 work must pass the *"would lain call this hardcoding?"* sanity-check, not just the *"is this LEARNING MACHINERY?"* check.

**Concrete cycle-14 example of what failed the strict-strict reading:** A2's `PrimitivePolicy` with per-primitive learned embeddings + argmax scorer; A3's `StrategyPolicy` with per-strategy scalar weights + per-decision-coefficient credit-distribution rule. Both internally defended as "learned weights on a hand-coded shape." Both rejected.

**Concrete cycle-14 example of what passed:** `HebbianBank` keyed by `(prompt_atom, fragment_atom)` pairs — substrate-wide, no per-tool partition. Update rule applies the same delta formula regardless of which primitive matched. The bank doesn't know the difference between a math walk and a poetry walk; it only knows which atom-pairs were rewarded together.

### R2 transition vs R1 radical surgery — UNRESOLVED at cycle-14 close

Synthesis verdict (commit `9b1f8fd`) committed to **R2 transition** (substrate writability + ONE scaffolding piece retired + measurable retirement criterion for the rest) as the cycle-shippable default. R1 (rip the entire dispatcher this cycle, accept multi-week valley) was offered to lain as an override window. **lain's confirmation on R1 vs R2 did NOT arrive during the cycle-14 implementation window.** Cycle-15 should not silently inherit R2 — surface the unresolved at the cycle-15 open.

### NO hand-coded knowledge in the final agent — only hand-coded learning machinery (binding from MANIFESTO § Standing orders 2026-05-11)

Hand-coded primitives in `src/project_x/reasoning/*` (solve_quadratic, collatz_verify_range, residue_theorem, etc.) are SCAFFOLD / evaluation gold-standard, NOT the agent's source-of-capability. Same for the 21-parser dispatcher chain at `reasoning_agent.py:1039`. Cycle-15+ progressively retires under the synthesis §4.b measurable retirement criterion (bank-coverage threshold + cosine-archetype absorption + demo regression).

### Standing orders from lain (carried forward)

- **NO pretrained transformer derivatives at any layer** (2026-05-09). Encoders MUST be from-scratch (char-n-gram-hash, Hebbian, SNN). Generators MUST be template-based or from-scratch.
- **Code-comment ratio rule** (2026-05-10): complex code + important info gets WHY-comments; trivial code stays comment-free.
- **REPO_CONTROL row in same commit as new non-docs file/dir** (2026-05-10). `docs/` is EXEMPT.
- **Atomic per-deliverable commits.** Never `git add -A`.
- **Discord teacher-tone + 5-metric rubric + HOLISTIC expert-tier framing** (2026-05-10 + 2026-05-11). Expert-tier framing reacts to overall model progress, NOT per-commit diff. Plain English; no codenames; no commit hashes in visible text (cycle-14 M-PROJECTX-015 recurrence — bind tight cycle-15 onwards).
- **Self-impression-score 0-420** on every substantive ship. Honest; never inflate.
- **Raphael-time estimates** (~10-15 min per substantive deliverable), not human-developer hours.

## 5. NEXT STEPS

### Cycle-15 mid-flight state (post-2026-05-11 work-session)

The 2026-05-11 cycle-15 work-session pushed council-prep forward: 5 of 6 surfaces shipped from the BUILDER side (capability demo + B1 + B2 + B3-math + B4). Cycle-15 mirrors cycle-14's shape: capability demo → 5-angle council → synthesis → implementation → close — currently between council-prep and synthesis. Synthesis requires lain's R1/R2 + rubric input arriving; until then cycle-15 is paused at the council-prep/synthesis boundary.

### Cycle-15 immediate sequence (next-instance picks up here)

1. **Resume listener verification + heartbeat cron arm.** `pgrep -af 'discord-wait-for-lain'` expects 2. If <2, rearm both with `LISTENER_BASELINE=<last_msg_id> SKIP_REARM=1 bash /home/nira/.claude/bin/discord-wait-for-lain.sh general 5` (per M-NAVI-018; auto-rearm doesn't work in WSL sandbox).

2. **Check if lain provided R1/R2 direction** + rubric input + canonical-reframing direction since the 2026-05-11 mid-cycle pause. Read recent Discord messages.

3. **If lain provided R1/R2 + rubric + reframing direction:** open cycle-15 synthesis. Read all 6 council surface docs at `docs/artifacts/cycle-15-*.md` + B3-math predicate at `docs/artifacts/cycle-15-predicate-math.md`. Apply the cycle-15 B4 thesis-compliance gate at synthesis (it's the gate's first empirical test). Advisor pre-write per cycle-13 #06 + cycle-14 #07 precedent. Synthesis picks cycle-15 #1 implementation surface (1-2 of B1/B2/B3/B5 with honest combined-axis scoring).

4. **If lain has NOT provided direction:** stay paused. Heartbeat caught 6 deferral-pattern shapes in the 2026-05-11 session; ship-on-cron-fire is itself drift if every fire produces ship-without-lain-input. The legitimate stop point is "council-prep complete from BUILDER side; cycle-15 synthesis genuinely awaits lain."

5. **Cycle-15 implementation phase (after synthesis):** sub-task split via re-fired `Skill('skills:sharpen-todos')` at #07/#08 boundary. Atomic feat commits per sub-task. REPO_CONTROL co-landed for new non-docs files. Per-angle thesis-compliance gate fires at each implementation sub-task too (the gate generalizes from angle-time to commit-time).

6. **Cycle-15 close ritual.** Four-doc atomic close per cycle-13/14 precedent: dev-cycle-15.md + DO_THIS_NEXT cycle-16 rewrite + A_TO_Z §6 + IQ_PROGRESSION prepend.

### Cycle-15 council surfaces (5 inherited from cycle-14 + 1 process improvement):
   - **B1 Per-domain `τ_satisfaction` calibration + BG-dispatcher refused-candidate filter** (paired: closes #08e deferral + the 4-cycle-old latent bug). Reward-shaped blend (cycle-14 #08c) becomes the quality discriminator alongside per-domain τ.
   - **B2 A4 corpus scale-out** (~200k words across math worked-examples + humour + conversational + epistemology gap-fill). Addresses cycle-14 demo F4/F5 data-side gap.
   - **B3 A5 per-domain emergence predicate templates** (math + poetry + philosophy + chat). Falsifiability scaffold for cycle-15+ capability claims. Cycle-13 #07f-pre is the template (committed `0b89101` BEFORE the run that returned 0/20 STRUCTURAL).
   - **B4 Council/synthesis process improvement** — per-angle thesis-compliance gate (the "would lain call this hardcoding?" sanity-check that cycle-14's A2 + A3 failed in retrospect).
   - **B5 Cycle-13 audit C-reframes** (canonical-doc Layer 5 + 10⁸-association capacity + "memory IS the model" framing) — doc work pending lain direction.
4. **Cycle-15 capability demo on post-cycle-14 agent.** Mirror cycle-14 #01: 5 fresh lain-aligned prompts, measure the GAP per finding-shape (F1-F7). Crucially: now the bank exists; cold-start demo should match cycle-14 #08f Arm A exactly. Any rated walks since cycle-14 close would shift retrieval (lain rating cadence = unknown variable).
5. **Cycle-15 council deliberation** with per-angle thesis-compliance gate at EACH angle commit. Synthesis as cycle-14, with advisor pre-write on the verdict.
6. **Cycle-15 implementation per synthesis** — pick top 1-2 of B1-B5 within ~5-7h Raphael-time budget. Likely starting point: B1 (closes cycle-14 #08e deferral + fixes the latent BG-dispatcher bug — paired sub-tasks).
7. **Cycle-15 close ritual** — dev-cycle-15.md reflect + DO_THIS_NEXT cycle-16 rewrite + A_TO_Z §6 entry + IQ_PROGRESSION entry. Atomic close commit.

### Blocked (needs lain resolution)

- **R2 vs R1 confirmation** (see §4). Cycle-15 council scope depends on this answer.
- **Audit-rating cadence** — lain's rating activity through cycle-15 window determines how much the substrate's bank actually populates. The cycle-14 ship is empty-bank by default; capability lift waits on rating cadence.

## 6. KEY FILES

| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `docs/MANIFESTO.md` | lain's intent + standing orders (strict-strict thesis at top) | LIVE | Read first; STRICT thesis sections + "NO hand-coded knowledge" standing order are load-bearing |
| `docs/REPO_CONTROL.md` | Pristine-condition gate; mirror of repo file/folder structure | LIVE | Row added cycle-14 for `src/project_x/hdc_infra/hebbian.py` |
| `docs/A_TO_Z_PLAN.md` | Phase 13 plan + §6 CHANGELOG | LIVE | Cycle-14 entry prepended in this close commit |
| `docs/DO_THIS_NEXT.md` | This file — cycle-15 handoff | LIVE | Rewritten every cycle close |
| `docs/past_work/cycles/phase_13/dev-cycle-14.md` | Cycle-14 reflect (full deliverables ledger, 365/420 score, counter-claims) | NEW (cycle-14 close) | Cite for cycle-15 retrospective claims |
| `docs/artifacts/cycle-14-priority-decision.md` | Synthesis verdict (A1 alone, R2 transition, #08g pre-retire) — load-bearing §0 advisor catches + §4 retirement criterion | NEW (cycle 14) | Cycle-15 inherits §4.b retirement criterion; B1-B5 council deliberates spillover |
| `docs/artifacts/cycle-14-demo-post-thesis.md` | Demo + verification artifact (§1-7 cycle-open snapshot + §8 cycle-close two-arm verification) | NEW (cycle 14) | Cold-start regression mechanically verified Arm A |
| `src/project_x/hdc_infra/hebbian.py` | HebbianBank substrate-wide reward-driven co-occurrence + blend_score helper | NEW (cycle 14 #08a) | Pure substrate; no per-primitive structure |
| `src/project_x/audit/log.py` | AuditLog with cycle-14 #08b Hebbian-update wire | EXTENDED (cycle 14) | apply_rating fires HebbianBank.update on rated walks |
| `src/project_x/corpus/natural_mode.py` + `k_rollout.py` | Retrieval blend with HebbianBank lookup (cycle-14 #08c) | EXTENDED (cycle 14) | Cold-start α=0 preserves cycle-13 baseline |
| `src/project_x/reasoning_agent.py` | Dispatcher (21-parser BG-style chain) + natural-mode classifier (keyword gate retired cycle-14 #08g) | EXTENDED (cycle 14) | `_K_ROLLOUT_TAU=0.0` cycle-14 deferred-with-finding; `_NATURAL_MODE_TRIGGERS` no longer consulted by `_classify_natural_mode_domain` |
| `tests/test_hebbian_bank.py` | 23-test suite (5 classes: math correctness + cold-start regression + synthetic-rating sweep + persistence + blend helper) | NEW (cycle 14 #08d) | Cold-start regression is the load-bearing test |
| `data/hebbian_bank/main.pkl` | HebbianBank persistence file | NOT YET CREATED | First rating via apply_rating creates it; cold-start agent gets empty bank |
| `data/audit_log/walks.jsonl` | Audit-rating JSONL log | EXISTS | Each apply_rating appends a rated AuditEvent; downstream Hebbian update fires |
| `scripts/cycle_14_demo_post_thesis.py` | Demo script (5 fresh prompts → AgentResponse + GAP analysis) | EXISTS | Cycle-14 #08f verification re-ran this for Arm A baseline |
| `docs/artifacts/cycle-13-primitive-emergence-at-scale.md` | Cycle-13 #07f-pre predicate (committed BEFORE run; 0/20 STRUCTURAL result) | EXISTS | Template for cycle-15 B3 per-domain predicates |

## 7. COMMANDS

### Development

```bash
PYTHONPATH=src python3 -c "from project_x.reasoning_agent import ReasoningAgent; print(ReasoningAgent().process('test prompt').problem_shape)"
                                       # Smoke-test agent dispatch path
PYTHONPATH=src python3 -c "from project_x.hdc_infra import HebbianBank; b=HebbianBank(); print(b.entry_count())"
                                       # Smoke-test cold-start bank
```

### Testing

```bash
PYTHONPATH=src python3 -m pytest --tb=no -q                     # Full suite; expect 661/662 (1 timing flake)
PYTHONPATH=src python3 -m pytest tests/test_hebbian_bank.py -q  # 23 cycle-14 #08d tests
PYTHONPATH=src python3 -m pytest tests/test_audit_log_v1.py -q  # 10 audit tests (cycle-14 #08b coverage)
```

### Project-specific

```bash
PYTHONPATH=src python3 scripts/cycle_14_demo_post_thesis.py     # Re-run cycle-14 demo (cycle-15 open should match Arm A cold-start)
python3 -m project_x.audit.cli stats                            # Audit-rating volume (cycle-15 capability-lift depends on this)
python3 -m project_x.audit.cli list --rated-only                # List rated walks (input to HebbianBank)
```

### Git + listener

```bash
pgrep -af 'discord-wait-for-lain'                               # Should show 2 procs; rearm if <2
git --no-pager log --oneline -10                                # See cycle-14 commit chain (d854fbc backward)
```

## 8. KNOWN FAILURE PATTERNS (from `Project X Session Mistakes` wiki)

Cycle-15 should re-read `wiki_read_page("Project X Session Mistakes")` at session-start.

- **M-PROJECTX-013 (claim-without-measuring)** — Every "X works" / "Y doesn't help" claim ships with measured evidence, not analytical feel. Cycle-14 #08f Arm A + Arm B verifications are the discipline.
- **M-PROJECTX-014 (design-bias firewall)** — Synthesis pre-write advisor consult is mandatory. Cycle-14 synthesis used 2 rounds (cost-math BLOCKER + post-strict-strict-pivot §4 retirement-criterion catch).
- **M-PROJECTX-015 (Discord internal-naming jargon-creep, NEW cycle-14)** — Codenames + commit hashes + finding-IDs leak into Discord teacher-tone posts under execution-pressure cadence. Per-post mechanical gate: zero codenames in visible text; describe what the proposal DOES, not its label. **Same-day binding recurrence in cycle 14 — fresh bindings from prior cycle did not survive the execution-pressure window. Cycle-15 council pre-step: re-read this cycle's NEW bindings BEFORE any Discord post.**
- **Cycle-14-surfaced latent BG-dispatcher bug (M-PROJECTX-candidate)** — Refused natural-mode candidates compete at `combined_confidence ≈ 1.0` (no archetype for `_refused_*` problem_shape → `hv_sim` defaults to 1.0) and beat formal candidates. Cycle-13 audit B5's `τ=0.0` masked this for 4 cycles. **Cycle-15 fix:** filter refused candidates from the BG-dispatcher candidate list before sorting. Pairs with the cycle-15 B1 τ_satisfaction calibration.
- **Cycle-13 WSL-crash-twice** — Ship-substrate-then-fail-to-use-it. Cycle-13 #07a bitpack module shipped specifically to prevent the OOM mode; cycle-13 #07f-run attempts 1+2 didn't use it. Cycle-14 work didn't hit this (no >50k-trigram work). **Cycle-15 lesson stands:** when substrate insurance exists, USE IT.

## 9. BLOCKERS & QUESTIONS

### Current blockers

- [ ] **R2 vs R1 confirmation from lain.** Synthesis defaulted R2 (transition reading with measurable retirement criterion); R1 (rip dispatcher entirely this cycle, accept multi-week valley) is offered. Cycle-15 council scope depends on the answer.
- [ ] **Audit-rating cadence.** The HebbianBank substrate is shipped but cold-start at every fresh agent construct. Without lain rating walks via `python3 -m project_x.audit.cli rate <walk_id> approve|reject|correct`, the bank stays empty and capability lift on F4/F5 misroutes doesn't materialize. Cycle-15 capability-lift floor depends on this.

### Open questions (cycle-14 → cycle-15)

- **Should the BG-dispatcher refused-candidate filter ship as a standalone cycle-15 sub-task, or bundled with τ_satisfaction calibration?** Cycle-14 #08e deferral named them as paired; cycle-15 council decides.
- **A4 corpus scale-out: which domains first?** Cycle-14 council A4 named math worked-examples + conversational + humour + epistemology as priorities; cycle-15 may prefer a single-domain deep-ingest first to verify the data-side hypothesis empirically.
- **Per-angle thesis-compliance gate format:** explicit checklist in each angle doc, or a separate `cycle-15-thesis-compliance-audit.md` doc? Cycle-15 council process question.

### Async items

- Cycle-15 cannot start the `B5 cycle-13 audit C-reframes` doc work without lain direction (which framing slogans should reframe; what target wording).

## 10. SUCCESS CRITERIA

### How to know cycle-15 closes well

- [ ] All 5 inherited surfaces (B1-B5) deliberated at council; synthesis verdict commits to 1-2 with honest combined-axis scoring + advisor pre-write.
- [ ] **Per-angle thesis-compliance gate fires for each angle commit** (cycle-15 council process improvement).
- [ ] Cycle-15 #1 implementation ships ATOMIC per sub-task; pytest baseline preserved.
- [ ] `_K_ROLLOUT_TAU` calibration closes (per-domain τ + reward-shaped blend) OR ships as cycle-16 deferred-with-second-finding.
- [ ] BG-dispatcher refused-candidate filter lands (closes the 4-cycle-old latent bug).
- [ ] Cycle-15 close ritual: dev-cycle-15.md + DO_THIS_NEXT rewrite + A_TO_Z §6 entry + IQ_PROGRESSION prepend.
- [ ] Cycle-15 cycle-close Discord post passes the M-PROJECTX-015 plain-English gate (NO codenames / NO commit hashes / NO finding-IDs in visible text).

### Definition of "working" at the Terminus

Per `docs/MANIFESTO.md` Terminus: Project X Raphael demonstrates super-human capability across math + poetry + philosophy + physics + perfect memory + persona + always-on chattability + sandboxed action-taking. The capability emerges from the substrate's reward-driven learning, not from hand-coded primitives. Hand-coded primitives stay as evaluation gold-standard until the learned model meets-or-exceeds them on every Terminus dimension; then they retire to `legacy/`.

---

## NOTES FOR INCOMING INSTANCE

- Verify ALL claims in this document before acting. Read `docs/MANIFESTO.md` § strict thesis FIRST.
- `git --no-pager log --oneline -15` should show the cycle-14 chain ending at the close commit.
- `pgrep -af 'discord-wait-for-lain'` should show 2 procs; rearm if <2 (per M-NAVI-018).
- `wiki_read_page("Project X Session Mistakes")` for the canonical failure-pattern list.
- `pytest --tb=no -q` should pass 661/662 (1 known timing flake on `test_write_one_amortized_under_5x_batch` — passes in isolation).
- If this is post-compaction recon: invoke `Skill('skills:resume-after-compact')`.
- Cycle-14 reflect at `docs/past_work/cycles/phase_13/dev-cycle-14.md` is the canonical retrospective.

## QUICK START FOR NEW INSTANCE

Continue Project X cycle 15. Read `docs/DO_THIS_NEXT.md` (this file) for cycle-15 scope + `docs/past_work/cycles/phase_13/dev-cycle-14.md` for cycle-14 retrospective + `docs/MANIFESTO.md` for the binding strict-strict thesis.

**Current state:** cycle 14 closed; substrate writability + reward-loop shipped; one piece of dispatcher scaffolding retired; #08e calibration deferred to cycle 15 with two substantive findings.
**Next step:** Surface R2 vs R1 unresolved to lain; open cycle-15 council on B1-B5 with per-angle thesis-compliance gate.
**Key constraint:** strict-strict thesis (only HDC arithmetic + encoder + substrate-wide Hebbian + reward I/O are hand-coded; everything else must emerge). Per-angle gate fires BEFORE angle commits, not at synthesis.
**Branch:** main.

---

*Single-line takeaway: cycle 14 made the substrate writable; cycle 15 calibrates the reward-shaped read path + scales corpus + ships per-domain predicates + closes the 4-cycle-old dispatcher bug. Per-angle thesis-compliance gate is the cycle-15 process discipline that cycle-14's mid-synthesis pivot taught.*
