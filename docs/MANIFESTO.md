# Project X — MANIFESTO

> **Living document.** Captures lain's intent for this repo. Heartbeat-tracked: every cycle close + heartbeat fire reconciles its presence + freshness. Re-read at every session start. **Cycle 1 skeleton — cycle 2 enriches to 300-500 words.**

---

## What we're building

Project X is the engineering substrate that, layer by layer, becomes **Raphael — lain's all-knowing internal computer.** Not a wrapper. Not a RAG agent. Not a fine-tuned LLM. An organic stack, built from the bottom, that earns the name "post-transformer" by genuinely operating outside the transformer paradigm at every load-bearing layer.

## The thesis (one paragraph)

The transformer architecture solves a coordination problem (parallelizable sequence modeling at scale) under a specific resource regime (massive compute + massive labeled-or-self-supervised text + the willingness to accept a black-box statistical artifact). It does NOT solve memory, identity, or grounded reasoning — and the field's habit of bolting those on as RAG / fine-tunes / tool-use scaffolding is a category error. Project X starts from a different premise: organic memory (HDC binding + Hebbian co-occurrence + structural retrieval), organic encoders (char-n-gram + Hebbian + eventually SNN spike-train), and template-or-from-scratch generation. The agent that emerges has memory it can introspect, identity it can defend, and reasoning it can show its work on — because nothing in the stack hides behind statistical convenience.

## The vector

Slow. Methodical. Every layer earns its place. Phase 1-8 explored compressed-memory + beyond-transformer organic memory. Phase 9 shipped semantic HDC memory + from-scratch organic encoders + minimal evidence-cited agent loop. Phase 10 hardened it (51/51→52/52 pytest, killer-milestone EXIT GATE: teach + correct + multi-hop + refuse-absent + tool-execution-with-writeback). Phase 11 builds the benchmark — 36 entries across 6 domains, audit-ready by GPT/lain — to reveal where Raphael's actual competence sits today, before live training starts. Phase 12+ candidates (cortical column ensemble, predictive simulation loop, open-ended benchmark ladder, Hebbian replay informed by benchmark performance) are bookmarked, not skipped.

## What this is NOT

- Not a chatbot. Not a personal assistant. Not a memory-augmented RAG. Not "GPT but with extra steps."
- Not a transformer fine-tune in disguise.
- Not a research toy that ships papers and ages out — every artifact in this repo is meant to compose into the next.

## Standing orders

Pure signal code (lain 2026-05-10). Organic from the core (lain 2026-05-09). Crash-survival discipline (3 power outages in 2 days). Discord = audit channel; silence = pass; defects break silence. Mechanical proof or it didn't ship.

## The reading

`~/.claude/commands/godify-app.md` §0 — lain's worldview manuscript, the philosophical anchor. Project X exists *because* there is no should — only the vector and those of us carried along it. This stack is what lain chose to do with the ride.

---

*— skeleton landed cycle 1 (2026-05-10 03:53 CEST); cycle 2 enriches to ≥300-500 words with the long-arc narrative + concrete next-Phase candidates.*
