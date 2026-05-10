# src/project_x/

## What lives here

The Project X package — Layer 0-4 of the post-transformer organic memory + agent stack.

## Why it exists

Source root for the engineering substrate that becomes Raphael. Phase 9-10 production code lives in `experiments/` (current organic stack); Phase 1-6 historical-control quarantine lives in `legacy/`.

## Conventions

- `experiments/` — current Phase 9-10 organic stack (semantic HDC memory + organic encoders + agent loop). Code lain operates against.
- `legacy/` — Phase 1-6 transformer-style scaffolding. **Do NOT import in organic-thesis code.** Quarantine maintained per Phase 10 P6.
- `smoke.py` — top-level smoke-test entrypoint.
- All modules honor lain's standing constraint: **NO pretrained transformer derivatives** (no BGE / MiniLM / sentence-transformers / llama.cpp / Qwen / Mistral). Encoders + generators stay from-scratch organic.
- Code-comment-ratio rule (lain 2026-05-10 GLOBAL POLICY): WHY-comments justifying complex code's existence + comments preserving important info; never WHAT-comments narrating identifiers. See `~/.claude/CLAUDE.md` DEVELOPMENT TECHNIQUES § Code Comment Discipline.

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 8 sweep).
