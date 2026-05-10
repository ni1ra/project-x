# Do This Next — Project X — Phase 11 Cycle 2 (Execute-Raphael — physics ladder + cycle-1.5 deliverables)

**Cron fires:** 2026-05-10 04:12 CEST (one-shot `31970f0b`)
**Persona:** Execute-Raphael (per pre-existing-plan rule, NOT Plan-navi)
**End time:** 2026-05-10 09:00 CEST (cycle 8 verdict + handoff)
**GitHub remote:** https://github.com/ni1ra/project-x (private; force-pushed cycle 1, branch `main`)

---

## #00 deliverables (TaskList — Phase 11)

- **#1** `#∞ APOTHEOSIS mode` — in_progress (mode tracker; flips to NORMAL at cycle 8 close)
- **#3** `#00P11-bench-physics` — pending (THIS CYCLE)
- **#4** `#00P11-bench-maths` — pending (cycle 3)
- **#5** `#00P11-bench-memory` — pending (cycle 4)
- **#6** `#00P11-bench-persona` — pending (cycle 5)
- **#7** `#00P11-bench-philosophy` — pending (cycle 6)
- **#8** `#00P11-bench-poetry` — pending (cycle 7)
- **#9** `#00P11-verdict` — pending (cycle 8)
- **#10** `#00P11-MANIFESTO` — pending (CYCLE 2 enrich, cycle 1 skeleton landed)

`#2` `#00-fix-ni-framing` — completed cycle 1 (forge-prompt.md + godify-app.md edits shipped).

---

## This cycle's scope

**Front-load (~5-8 min, cycle-1.5 deliverables per plan §"Cycle 1.5"):**

1. **Enrich `docs/MANIFESTO.md`** to 300-500 words. Skeleton (~250 words) landed cycle 1; expand the long-arc narrative + concrete next-Phase candidates (cortical column ensemble Council #2, predictive simulation loop Council #3, open-ended benchmark ladder Council #5, Hebbian replay informed by benchmark performance). Honor lain's code-comment-ratio rule even in prose: pure signal, every paragraph earns its place.
2. **Write 6 `gpt-codex/benchmark/<domain>/rubric.md` skeletons** — one per domain folder (`physics/`, `maths/`, `memory/`, `persona/`, `philosophy/`, `poetry/`). Each rubric.md scaffolds the per-difficulty grading dimensions (auto-graded entries reference `auto_grade.method`; rubric-pending entries reference per-difficulty rubric sections). Cycles 3-7 enrich their respective rubric.md as part of the domain ladder ship.
3. **FILE INVENTORY first-pass populated** — `docs/A_TO_Z_PLAN.md` §9 already has the skeleton; verify it covers every file currently on disk (`find /mnt/c/Users/nira/Documents/Research/projext-x -type f \( -not -path '*/__pycache__/*' -not -path '*/.git/*' -not -path '*/.venv/*' \)`). Add any missing rows.

**Then (~12 min): physics ladder.**

Ship `gpt-codex/benchmark/physics/{ladder.jsonl, rubric.md, CLAUDE.md}` with 6 entries spanning intro→unsolved per plan §"DOMAINS — ladder structure":

| Rank | Difficulty | Anchor |
|---|---|---|
| 1 | intro | Free-fall kinematics (closed-form: t = √(2h/g)) |
| 2 | easy | Lagrangian mechanics on a simple system (closed-form Euler-Lagrange) |
| 3 | medium | Relativistic momentum (closed-form γmv) |
| 4 | hard | GR field equations (R_μν - ½gR_μν Rg = 8πT) — conceptual; rubric-pending |
| 5 | frontier | Quantum gravity approaches (semantic+positional argument) — rubric-pending |
| 6 | unsolved | Fine-tuning of physical constants (no consensus) — `audit_status: "ungradeable; unsolved tier"` |

**Auto-grade closed-form (ranks 1-3):** `auto_grade.method = "numerical_close"` with tolerance 0.05; expected = canonical answer; actual = Raphael's parsed numeric. If Raphael's response gets the closed-form right within tolerance, `audit_status = "auto-graded-green"`; else `auto-graded-red`.

**Rubric-pending conceptual (ranks 4-5):** Raphael writes response + reasoning; `audit_status = "ungraded; rubric-pending for GPT/lain audit"`; `rubric_pointer = "gpt-codex/benchmark/physics/rubric.md#hard"` (or `#frontier`).

**Unsolved (rank 6):** `audit_status = "ungradeable; unsolved tier"`; response is honest about what's known + what isn't.

**Append-as-you-go:** each entry written to `physics/ladder.jsonl` via `>>` append + flush BEFORE next entry generates. Crash-survival contract.

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` (renamed from `master`; tracking `origin/main`)
- **GitHub remote:** https://github.com/ni1ra/project-x (private, hijacked from legacy `WIRED-BRAIN` per lain 2026-05-10 03:55 CEST authorization)
- **Cron state:** 7 godify one-shots armed (`31970f0b` cycle-2 04:12 → `e024fdf1` cycle-8 08:12). Heartbeat disarmed for APOTHEOSIS duration.
- **Listener:** PIDs alive (last verified after re-arm via bg `bw3nx2p00`); pkill must ALWAYS chain re-arm in same Bash (M-NAVI-018).
- **Discord:** `#general` is the journal channel. lain asleep; silence = pass; defects break silence.

---

## When lain returns mid-run

**Listener catches Discord. Atomic ack protocol:**
1. Read msg from listener output file (`/tmp/claude-1000/.../tasks/<bg-id>.output`).
2. `discord_send` ack BEFORE substantive work.
3. Atomic re-arm: single Bash invocation `pkill -f 'discord-wait-for-lain' 2>/dev/null; sleep 1; bash /home/nira/.claude/bin/discord-wait-for-lain.sh general 5` with `run_in_background:true`.
4. Act.

**lain authorization log this run:**
- 2026-05-10 03:34 — code-comment-ratio rule (project-scope)
- 2026-05-10 03:44 — comment-ratio refinement (complex code descriptions OK; pure-signal only)
- 2026-05-10 03:48 — promote comment rule to GLOBAL POLICY (`~/.claude/CLAUDE.md`)
- 2026-05-10 03:48 — gn + final-result-by-morning expectation
- 2026-05-10 03:55 — hijack legacy GH repo (wired/genesis); WIRED-BRAIN selected
- 2026-05-10 03:56 — keep name "project x"; renamed `projext-x` → `project-x` on GH

---

## Cycle 2 close checklist

- [ ] `docs/MANIFESTO.md` enriched to ≥ 300 words (cycle 1 skeleton enriched, not rewritten)
- [ ] 6 `gpt-codex/benchmark/<domain>/rubric.md` skeletons written
- [ ] `gpt-codex/benchmark/physics/ladder.jsonl` has 6 entries (append-as-you-go)
- [ ] `gpt-codex/benchmark/physics/rubric.md` written (specific to physics)
- [ ] `gpt-codex/benchmark/physics/CLAUDE.md` written
- [ ] FILE INVENTORY (§9) reconciled (find diff)
- [ ] PHASE CHANGELOG cycle 2 row updated (status: ✅ closed, evidence link)
- [ ] Cycle reflection at `docs/past_work/cycles/phase_11/dev-cycle-2.md`
- [ ] DO_THIS_NEXT.md rewritten for cycle 3 (maths)
- [ ] Atomic commit `feat(phase11): cycle 2 — physics ladder + MANIFESTO + cycle-1.5 deliverables`
- [ ] `git push origin main`
- [ ] `discord_send #general` cycle-2 close (1-line summary + GitHub commit URL)
- [ ] Clock out by minute 18-20; cycle 3 cron fires 04:52

**Schema firewall (every entry written):** required fields present (`id`, `domain`, `difficulty`, `prompt`, `raphael_response`, `audit_status`); `self_score` MUST NOT appear; auto-graded entries have `auto_grade` block; rubric-pending have `rubric_pointer`. Verification command: see A_TO_Z_PLAN.md §3 E3.
