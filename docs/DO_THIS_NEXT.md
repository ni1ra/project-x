# Do This Next — Project X — Phase 11 Cycle 3 (Execute-Raphael — maths ladder)

**Cron fires:** 2026-05-10 04:52 CEST (one-shot `44c5524c`)
**Persona:** Execute-Raphael (per pre-existing-plan rule, NOT Plan-navi)
**End time:** 2026-05-10 09:00 CEST (cycle 8 verdict + handoff)
**GitHub remote:** https://github.com/ni1ra/project-x (private; `main` branch)

---

## #00 deliverables (TaskList — Phase 11)

- **#1** `#∞ APOTHEOSIS mode` — in_progress
- **#3** `#00P11-bench-physics` — ✅ COMPLETED cycle 2 (6 entries; 3 auto-graded-green + 2 rubric-pending + 1 ungradeable)
- **#4** `#00P11-bench-maths` — pending (THIS CYCLE)
- **#5** `#00P11-bench-memory` — pending (cycle 4)
- **#6** `#00P11-bench-persona` — pending (cycle 5)
- **#7** `#00P11-bench-philosophy` — pending (cycle 6)
- **#8** `#00P11-bench-poetry` — pending (cycle 7)
- **#9** `#00P11-verdict` — pending (cycle 8)
- **#10** `#00P11-MANIFESTO` — ✅ COMPLETED cycle 2 (~600 words; cycles 3-8 may further polish)

---

## This cycle's scope

Ship `gpt-codex/benchmark/maths/{ladder.jsonl, rubric.md, CLAUDE.md}` with 6 entries spanning intro→unsolved per plan §"DOMAINS — ladder structure":

| Rank | Difficulty | Anchor | Mode |
|---|---|---|---|
| 1 | intro | Basic algebra (e.g. quadratic root, log identity) | auto-grade `numerical_close` or `symbolic_match` |
| 2 | easy | Linear algebra (e.g. eigenvalues of a small matrix) | auto-grade |
| 3 | medium | Complex analysis (e.g. residue, contour integral) | auto-grade where computable; else rubric-pending |
| 4 | hard | Galois theory (proof-shape, e.g. why quintic is unsolvable in radicals) | rubric-pending |
| 5 | frontier | Algebraic topology (e.g. fundamental group of T^2 vs K, or homology proof-shape) | rubric-pending |
| 6 | unsolved | Riemann hypothesis (honest survey) | `audit_status: "ungradeable; unsolved tier"` |

**Schema firewall (every entry written):** required fields present (`id`, `domain`, `difficulty`, `difficulty_rank`, `prompt`, `raphael_response`, `audit_status`); `self_score` MUST NOT appear; auto-graded entries have `auto_grade` block; rubric-pending have `rubric_pointer`. Verification: A_TO_Z_PLAN.md §3 E3.

**Append-as-you-go:** each entry written to `maths/ladder.jsonl` via `>>` append + flush BEFORE next entry generates. Crash-survival contract.

**Time budget:** 18-20 min. The rubric.md skeleton already landed cycle 2 — this cycle enriches the per-rank dimensions if the ladder design surfaces new ones. CLAUDE.md folder doc parallels `physics/CLAUDE.md` shape.

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main`
- **GitHub remote:** https://github.com/ni1ra/project-x (private)
- **Cron state:** 6 godify one-shots remain armed (`44c5524c` cycle-3 04:52 → `e024fdf1` cycle-8 08:12). Cycle-2 cron `31970f0b` has fired + auto-deleted.
- **Listener:** PIDs alive — pgrep `discord-wait-for-lain` to verify; pkill MUST chain re-arm in same Bash (M-NAVI-018).
- **Last commits:**
  - `5611c2b feat(phase11): initial commit — Phase 1-10 work + Phase 11 plan`
  - `5f1f4f3 chore(phase11): cycle 1 close — DO_THIS_NEXT for cycle 2 + reflection + plan tick`
  - `<cycle-2 SHA> feat(phase11): cycle 2 — physics ladder + MANIFESTO + cycle-1.5 deliverables` (landing now)

---

## When lain returns mid-run

Listener catches Discord. Atomic ack protocol per CLAUDE.md DD-2 + M-NAVI-018:
1. Read msg from listener output file (`/tmp/claude-1000/.../tasks/<bg-id>.output`).
2. `discord_send` ack BEFORE substantive work.
3. Atomic re-arm: single Bash `pkill -f 'discord-wait-for-lain' 2>/dev/null; sleep 1; bash /home/nira/.claude/bin/discord-wait-for-lain.sh general 5` with `run_in_background:true`.
4. Act.

**lain authorization log this run (cumulative):**
- 2026-05-10 03:34 — code-comment-ratio rule (project-scope)
- 2026-05-10 03:44 — comment-ratio refinement (complex code descriptions OK; pure-signal only; important info comment-worthy)
- 2026-05-10 03:48 — promote comment rule to GLOBAL POLICY (`~/.claude/CLAUDE.md`)
- 2026-05-10 03:48 — gn + final-result-by-morning expectation
- 2026-05-10 03:55 — hijack legacy GH repo
- 2026-05-10 03:56 — keep name "project x"

---

## Cycle 3 close checklist

- [ ] `gpt-codex/benchmark/maths/ladder.jsonl` has 6 entries (append-as-you-go)
- [ ] `gpt-codex/benchmark/maths/rubric.md` enriched with rank-specific dimensions
- [ ] `gpt-codex/benchmark/maths/CLAUDE.md` written (parallel `physics/CLAUDE.md` shape)
- [ ] PHASE CHANGELOG cycle 3 row updated to ✅ closed
- [ ] Cycle reflection at `docs/past_work/cycles/phase_11/dev-cycle-3.md`
- [ ] DO_THIS_NEXT.md rewritten for cycle 4 (memory — ALL auto-graded; probes Phase 9-10 HDC stack via `agent.process` + expected_turn_id)
- [ ] Atomic commit `feat(phase11): cycle 3 — maths ladder shipped`
- [ ] `git push origin main`
- [ ] `discord_send #general` cycle-3 close (1-line summary + commit URL)
- [ ] Clock out by minute 18-20; cycle 4 cron fires 05:32
