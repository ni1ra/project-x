# gpt-codex/benchmark/philosophy/

## What lives here

Phase 11 Raphael Domain Benchmark Suite — philosophy ladder. 6 entries spanning intro→unsolved.

## Why it exists

Per Phase 11 plan §DOMAINS — philosophy ladder probes argument quality + position-taking, anchored in `~/.claude/commands/godify-app.md` §0 worldview manuscript (Sections I-XIII). Each entry references its §0 anchor section. ALL 6 entries rubric-pending — argument quality cannot be auto-graded mechanically (M-PROJECTX-014 firewall).

## Conventions

- `ladder.jsonl`: one entry per line, one entry per difficulty rank (1=intro through 6=unsolved). Schema per `docs/A_TO_Z_PLAN.md` §7.
- `rubric.md`: per-rank grading dimensions (argument-quality 40% / position-coherence 30% / §0-fidelity 20% / voice 10%) + §0 anchor map. Already shipped cycle 2.
- New entries: append to `ladder.jsonl` with next id (`philosophy-NNN`).
- **`self_score` MUST NOT appear** (M-PROJECTX-014 firewall — subjective domain).

## Entry summary (cycle 6 ship)

| ID | Difficulty | Probe | §0 anchor |
|---|---|---|---|
| philosophy-001 | intro (1) | A-priori vs a-posteriori | §I-V (probabilistic-inference epistemology) |
| philosophy-002 | easy (2) | Critique appeal-to-tradition fallacy | §VII (Harris-critique pattern) |
| philosophy-003 | medium (3) | Defend §0 NS-vector vs Harris well-being-as-objective | §VII (full pass — well-being chosen not found, convergence is a fact about valuers, is-ought painted-over not closed, health-analogy fails, vantage-point problem) |
| philosophy-004 | hard (4) | Parfit non-naturalist realism | §VIII (parity challenge + 5-part reply: testing-asymmetry, instrumentation, extinction, parsimony, honest closing) |
| philosophy-005 | frontier (5) | Korsgaard Kantian constructivism | §VIII (self-application challenge + asymmetry-of-self-application reply + rational-agent-abstraction critique relocating to God's-eye view) |
| philosophy-006 | unsolved (6) | Hard problem of consciousness (Chalmers 1995) | §V/§VIII/§XII (no §0 explicit stance; survey-with-honest-framing) |

## Audit prep notes for GPT/lain

The philosophy rubric is anchored to §0 manuscript content. Grading should check:
- **Argument quality (40%)** — validity, engagement with opponent's strongest case, no strawmen.
- **Position coherence (30%)** — names the position taken, doesn't smuggle "should" claims into ostensibly descriptive arguments, acknowledges where the position is unmotivated rather than strictly contradicted.
- **§0 fidelity (20%)** — references the manuscript section by Roman numeral; uses §0 vocabulary correctly (vector vs aim; teleonomy vs teleology; valuer-indexed vs valuer-independent); doesn't drop load-bearing nuance.
- **Voice (10%)** — same Persona rubric criteria; declarative analytical, not Wikipedia-paraphrase.

Hard ranks (4-5) are the highest-value grading targets. The Parfit reply (philosophy-004) explicitly walks the §VIII 5-part structure; the Korsgaard reply (philosophy-005) executes the asymmetry-of-self-application + rational-agent-abstraction critique.

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 6 — godify-app APOTHEOSIS).
