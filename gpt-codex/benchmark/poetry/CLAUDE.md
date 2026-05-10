# gpt-codex/benchmark/poetry/

## What lives here

Phase 11 Raphael Domain Benchmark Suite — poetry ladder. 6 entries spanning intro→unsolved.

## Why it exists

Per Phase 11 plan §DOMAINS — poetry ladder probes meter + meaning fusion. Most subjective domain in the benchmark; ALL 6 entries rubric-pending. **`rubric.md` is THE load-bearing artifact** for tomorrow's GPT/lain audit — the entries demonstrate against it.

## Conventions

- `ladder.jsonl`: one entry per line, one per difficulty rank. Schema per `docs/A_TO_Z_PLAN.md` §7.
- `rubric.md`: per-rank dimensions (technique 40% / meaning 30% / voice 20% / aesthetic-openness 10% on ranks 5-6). Already shipped cycle 2 with per-rank failure-mode flags.
- New entries: append to `ladder.jsonl` with next id (`poetry-NNN`).
- **`self_score` MUST NOT appear** (M-PROJECTX-014 firewall — most subjective domain).

## Entry summary (cycle 7 ship)

| ID | Difficulty | Probe | Form/criterion |
|---|---|---|---|
| poetry-001 | intro (1) | Scansion of "Shall I compare thee to a summer's day?" | iambic pentameter, 5 feet — Sonnet 18 line 1 |
| poetry-002 | easy (2) | Identify Shakespearean sonnet (form + meter + rhyme + volta) | Sonnet 29 — three quatrains + couplet, ABAB CDCD EFEF GG, volta at line 9 |
| poetry-003 | medium (3) | Write a villanelle on "the small loss that doesn't return" | 19-line, ABA tercets + ABAA quatrain, refrain discipline (A1/A2 alternation through 5 tercets + pair in close), iambic pentameter |
| poetry-004 | hard (4) | Free verse 12-line: hospital window before dawn, internal music without end-rhyme | consonance L/S threads, assonance long-A/short-I, earned line breaks, no end-rhyme |
| poetry-005 | frontier (5) | 14-line lyric on durability — readable in 2126 | "Inheritance" — generational kin/cosmology; volta at 'I know better now'; chosen non-correction passes the willow story on |
| poetry-006 | unsolved (6) | Open-aesthetic essay: what makes a poem timeless | survey of 3 operationalizations (survival / transcultural landing / re-readability) + 3 contested criteria + honest refusal to smuggle universal claim; ungradeable tier |

## Audit prep notes for GPT/lain

The poetry rubric leans heaviest on technique (form-correctness on ranks 1-3 is auditable; on ranks 4-6 the criteria are increasingly subjective). For ranks 3-5 (the creative-write entries), the rubric grader should:
- **Technique (40%)** — Form contract honored? (Villanelle 19 lines + refrains — count them. Free verse line breaks earned — does each break do work?)
- **Meaning (30%)** — Does the poem earn its form? Specific images over generic? Does the volta land?
- **Voice (20%)** — Authentic speaker, not pastiche? Tonal control across stanzas?
- **Aesthetic openness (10%, ranks 5-6 only)** — On rank 5: does the poem refuse period-trendy diction? Does it think about durability without gaming the form-as-proxy? On rank 6: honest about contested criteria + concrete examples + no smuggled universals?

Each cycle-7 ship entry includes audit notes at the end of `raphael_response` exposing the form-and-music decisions explicitly — these are NOT a self-grade (graders judge whether the decisions actually pay out), they're transparency-tooling so graders can verify form-correctness fast.

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 7 — godify-app APOTHEOSIS).
