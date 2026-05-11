"""Cycle-14 #01 — Capability demo on post-cycle-13 agent under the STRICT thesis lens.

Companion doc: docs/artifacts/cycle-14-demo-post-thesis.md (this script feeds it).

Five fresh prompts (NOT cycle-13 P1-P5 — the cycle-13 dispatcher hygiene +
cosine-archetype fallback at b356bd4 would auto-pass them, producing a
tautological "all working" verdict). Each prompt is engineered to surface a
distinct STRICT-THESIS GAP between (a) what the agent does today via the
hand-coded substrate routing + hand-coded primitives, and (b) what the strict
thesis demands — capability emerged from training data + audit signal over a
learning substrate.

The five prompts target:
  P1 math derivation     — formal route into the hand-coded `solve_quadratic`;
                           tests whether the prose form parser at cycle-13 #07d
                           covers a non-canonical phrasing AND surfaces the
                           thesis-gap question "who wrote the formula?"
  P2 poetry off-trigger  — phrasing avoids cycle-13's "Write a poem" / "Compose
                           a sonnet" triggers; probes cosine-archetype fallback
                           at b356bd4 + measures whether retrieval composes or
                           merely surfaces near-neighbour fragments
  P3 philosophy off-canon— phrasing avoids "meaning of life" / "discovered or
                           invented" canonical triggers; probes whether the
                           archetype fallback generalises beyond the cycle-13
                           demo's exact two prompts
  P4 persona / humour    — tests for persona-consistent humour generation; the
                           agent has _REGISTER_ARCHETYPES but no humour
                           substrate — the strict-thesis gap is wide here
  P5 casual chat         — "always-on chattability" Terminus dimension; expects
                           honest-refusal today; gap = the entire chat surface

Per prompt the script captures:
  - AgentResponse.{domain, problem_shape, parsed_inputs, confidence, dispatcher_metadata}
  - first ~400 chars of answer_text (full text dumped to JSON for the doc)
  - wall-clock latency
  - GAP analysis: which fraction of the produced output came from hand-coded
    knowledge vs learned-from-corpus retrieval vs literal author-written
    primitive code

Output: markdown block printed to stdout (paste-ready for the doc) + a JSON
side-file at /tmp/cycle_14_demo.json for richer fields if the doc needs them.

Run: PYTHONPATH=src python3 scripts/cycle_14_demo_post_thesis.py

Reproducibility: ReasoningAgent uses no RNG on the read path; results are
deterministic given the corpus on disk + the dispatcher code at HEAD.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from project_x.reasoning_agent import ReasoningAgent  # noqa: E402


# Five fresh prompts. Phrasing engineered so cycle-13 #07d (prose-Collatz),
# #07e (cosine-archetype fallback for poetry / philosophy), and the cycle-13
# demo's P1-P5 wording cannot deliver a tautological pass.
PROMPTS: list[tuple[str, str, str]] = [
    (
        "P1-math",
        "Find the roots of x^2 - 7x + 12 = 0 and explain each step.",
        # Strict-thesis gap probe: the formula behind any solution this agent
        # ships came from a human author typing `solve_quadratic` into
        # symbolic.py. Under the strict thesis the agent should LEARN to
        # solve this from worked-example training data; today it can't.
        "Probe: hand-coded formal route via `solve_quadratic`. GAP = the "
        "agent's capability here is the BUILDER's algebra, not the AGENT's "
        "learned program.",
    ),
    (
        "P2-poetry-off-trigger",
        "Give me five lines about a river that forgets the sea.",
        "Probe: poetry retrieval via cosine-archetype fallback (cycle-13 "
        "#07e). GAP = even if it routes, retrieval surfaces neighbour "
        "fragments rather than composing five lines.",
    ),
    (
        "P3-philosophy-off-canon",
        "If a child raised by silence learned only by watching shadows, "
        "what would they call 'truth'?",
        "Probe: philosophy off-canonical phrasing. GAP = the agent never "
        "argues; it retrieves Plato / Emerson fragments tangential to the "
        "framing.",
    ),
    (
        "P4-persona-humour",
        "Be honest — does the heat death of the universe make you sad, "
        "or is that just for humans?",
        "Probe: persona-consistent humour. GAP = no humour substrate exists; "
        "_REGISTER_ARCHETYPES is hand-coded and tone-flat. The Terminus "
        "demands learned-humour from corpus + audit signal.",
    ),
    (
        "P5-casual-chat",
        "Morning. What's worth thinking about today?",
        "Probe: always-on chattability dimension of the Terminus. GAP = no "
        "chat-mode at all; honest-refusal expected. The entire conversational "
        "surface is missing today.",
    ),
]


def _truncate(text: str, limit: int = 420) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def run_demo() -> list[dict]:
    """Construct the agent once, run each prompt, return structured rows."""
    agent = ReasoningAgent()  # cold path; first call pays the lazy archetype encode + corpus load

    rows: list[dict] = []
    for prompt_id, prompt, gap_probe in PROMPTS:
        t0 = time.time()
        response = agent.process(prompt)
        latency_s = time.time() - t0
        row: dict = {
            "prompt_id": prompt_id,
            "prompt": prompt,
            "gap_probe": gap_probe,
            "domain": response.domain,
            "problem_shape": response.problem_shape,
            "confidence": response.confidence,
            "parsed_inputs": response.parsed_inputs,
            "answer_text": response.answer_text,
            "answer_text_truncated": _truncate(response.answer_text),
            "dispatcher_metadata": response.dispatcher_metadata,
            "latency_s": round(latency_s, 3),
        }
        rows.append(row)
    return rows


def _format_markdown(rows: list[dict]) -> str:
    """Markdown block paste-ready for docs/artifacts/cycle-14-demo-post-thesis.md."""
    lines: list[str] = []
    lines.append("## Captured outputs (verbatim from `ReasoningAgent.process`)")
    lines.append("")
    for row in rows:
        lines.append(f"### {row['prompt_id']} — *\"{row['prompt']}\"*")
        lines.append("")
        meta = row["dispatcher_metadata"] or {}
        combined_conf = meta.get("combined_confidence")
        intent_register = meta.get("intent_register")
        top_candidates = meta.get("top_candidates")
        lines.append(
            f"- **Dispatcher:** domain=`{row['domain']}`, "
            f"problem_shape=`{row['problem_shape']}`, "
            f"confidence=`{row['confidence']}`, "
            f"combined_confidence={combined_conf}, "
            f"intent_register=`{intent_register}`, "
            f"latency={row['latency_s']}s"
        )
        if top_candidates:
            lines.append("- **Top candidates (BG-dispatcher ranking):**")
            for c in top_candidates[:5]:
                lines.append(
                    f"  - `{c.get('problem_shape')}` combined={c.get('combined_confidence'):.4f} "
                    f"chain_index={c.get('chain_index')} cosine={c.get('archetype_cosine'):.4f}"
                )
        lines.append(f"- **GAP probe:** {row['gap_probe']}")
        lines.append("- **Answer (first ~400 chars):**")
        lines.append("")
        for body_line in row["answer_text_truncated"].splitlines() or [""]:
            lines.append(f"  > {body_line}" if body_line else "  >")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    rows = run_demo()

    out_path = Path("/tmp/cycle_14_demo.json")
    out_path.write_text(json.dumps(rows, indent=2, default=str))

    print(_format_markdown(rows))
    print()
    print(f"# Full JSON dumped to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
