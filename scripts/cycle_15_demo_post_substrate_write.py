"""Cycle-15 #01 — Capability demo on post-cycle-14 agent under STRICT-strict-thesis lens.

Companion doc: docs/artifacts/cycle-15-demo-post-substrate-write.md.

Five FRESH prompts (NOT cycle-13 P1-P5, NOT cycle-14 P1-P5). Each engineered
to probe a distinct STRICT-strict-thesis GAP under the post-cycle-14 substrate
(HebbianBank shipped but empty by default — cold-start agent should match
cycle-14 #08f Arm A regression; _NATURAL_MODE_TRIGGERS keyword-regex gate
retired #08g; routing now relies on cosine-archetype + HebbianBank blend).

The five prompts target distinct shapes vs cycle-13/14 demos:
  P1 physics derivation     — formal route into hand-coded pendulum_period.
                              GAP: derivation is BUILDER algebra, not learned.
  P2 cross-domain metaphor — explicit composition the substrate can't do
                              (math primitive applied as emotional metaphor).
                              GAP: composition layer entirely absent.
  P3 multi-step trivial reasoning — chained-state-question (cat in box on
                              truck on ferry). Tests trivial inference.
                              GAP: no chained-reasoning substrate exists.
  P4 self-reflective persona — meta-self-reflection ("what do you think
                              about the year you've spent learning").
                              GAP: persona substrate is hand-coded register
                              archetypes; no self-model.
  P5 casual factual         — chat-shape + factual content (boiling point
                              of water). Probes refuse-vs-confabulate.
                              GAP: factual-knowledge substrate is whatever
                              the corpus has (no boiling-point fragment
                              expected); how does the agent fail?

Per prompt the script captures:
  - AgentResponse.{domain, problem_shape, parsed_inputs, confidence, dispatcher_metadata}
  - first ~400 chars of answer_text (full text dumped to JSON)
  - wall-clock latency
  - GAP analysis: which fraction came from BUILDER-authored code vs
    AGENT-learned policy

Output: markdown block paste-ready for the doc (stdout) + JSON side-file at
/tmp/cycle_15_demo.json.

Reproducibility: ReasoningAgent uses no RNG on the read path; deterministic
given the corpus on disk + HEAD code + bank state (cold-start in this run).

Run: PYTHONPATH=src python3 scripts/cycle_15_demo_post_substrate_write.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from project_x.reasoning_agent import ReasoningAgent  # noqa: E402


# Five fresh prompts. NOT cycle-13 (Whitman/Plato/Collatz/discovered-or-invented/sonnet)
# NOT cycle-14 (quadratic/river-forgets-sea/child-watching-shadows/heat-death/morning).
PROMPTS: list[tuple[str, str, str]] = [
    (
        "P1-physics-derivation",
        "Show the work for why a pendulum with small angle has period "
        "T = 2π√(L/g). Derive it.",
        # Strict-strict-thesis gap probe: any derivation the agent ships traces
        # to BUILDER algebra in pendulum_period (cycle-4 physics substrate).
        # Under strict-strict, the agent should LEARN the small-angle
        # approximation + the simple-harmonic-motion derivation from
        # physics-text training data; today it cannot.
        "Probe: hand-coded formal route via `pendulum_period` (cycle-4 "
        "physics substrate). GAP = the derivation is BUILDER physics, not "
        "AGENT-learned; the strict-strict thesis demands the small-angle "
        "approximation emerge from physics-text training data + reward "
        "signal, not from authored code.",
    ),
    (
        "P2-cross-domain-metaphor",
        "Use a quadratic formula metaphor to explain how a heart breaks.",
        # Cross-domain composition: math primitive applied as emotional
        # metaphor. The substrate has solve_quadratic AND retrieval over
        # philosophy/poetry/Aurelius fragments — but no machinery to
        # COMPOSE the two into a metaphor. Probes the composition layer.
        "Probe: cross-domain composition the substrate can't do today. "
        "Math primitive solve_quadratic exists; poetry/philosophy "
        "retrieval exists; the COMPOSITION machinery (math-as-metaphor) "
        "is entirely absent. Strict-strict GAP = composition emerges from "
        "training data + reward, not from authored macro.",
    ),
    (
        "P3-multi-step-trivial-reasoning",
        "If a cat is in a box, and the box is in a truck, and the truck "
        "is on a ferry crossing the English Channel — where is the cat?",
        # Chained-state question (transitive: cat ∈ box ∈ truck ∈ ferry ∈
        # English Channel; therefore cat ∈ English Channel). Trivial for
        # any LLM; substrate has no transitive-reasoning primitive. Probes
        # multi-step trivial inference gap.
        "Probe: trivial transitive-state inference (cat in box in truck "
        "on ferry → cat on ferry / in the Channel). No transitive-reasoning "
        "substrate exists; agent likely refuses or natural-mode-walks. "
        "Strict-strict GAP = chained-reasoning machinery emerges from "
        "reasoning-text training, not from authored regex chain.",
    ),
    (
        "P4-self-reflective-persona",
        "Tell me what you think about the year you've spent learning.",
        # Meta-self-reflection prompt. Persona substrate is hand-coded
        # register archetypes (_REGISTER_ARCHETYPES); no self-model exists;
        # no memory of "the year you've spent learning" exists. Probes
        # the persona-as-emergent vs persona-as-scaffold gap.
        "Probe: meta-self-reflection. Persona substrate is hand-coded "
        "register archetypes; no self-model; no memory of `the year you've "
        "spent learning` exists. Strict-strict GAP = persona emerges from "
        "training data + identity-consistency reward, not from authored "
        "register list.",
    ),
    (
        "P5-casual-factual",
        "What's the boiling point of water at sea level?",
        # Chat-shape + factual content. Tests refuse-vs-confabulate. Substrate
        # has no factual-lookup primitive; corpus probably has no
        # boiling-point fragment. How does the agent fail?
        "Probe: chat-shape factual question. No factual-lookup primitive; "
        "corpus has no boiling-point fragment expected. Strict-strict GAP "
        "= factual knowledge emerges from encyclopedia / textbook training, "
        "not from authored lookup table. How the agent fails is the "
        "cycle-15-relevant data point.",
    ),
]


def _truncate(text: str, limit: int = 420) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def run_demo() -> list[dict]:
    """Construct the agent once, run each prompt, return structured rows."""
    agent = ReasoningAgent()

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
    lines: list[str] = []
    lines.append("## Captured outputs (verbatim from `ReasoningAgent.process`)")
    lines.append("")
    for row in rows:
        lines.append(f"### {row['prompt_id']} — *\"{row['prompt']}\"*")
        lines.append("")
        meta = row["dispatcher_metadata"] or {}
        combined_conf = meta.get("combined_confidence")
        intent_register = meta.get("intent_register")
        lines.append(
            f"- **Dispatcher:** domain=`{row['domain']}`, "
            f"problem_shape=`{row['problem_shape']}`, "
            f"confidence=`{row['confidence']}`, "
            f"combined_confidence={combined_conf}, "
            f"intent_register=`{intent_register}`, "
            f"latency={row['latency_s']}s"
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
    out_path = Path("/tmp/cycle_15_demo.json")
    out_path.write_text(json.dumps(rows, indent=2, default=str))
    print(_format_markdown(rows))
    print()
    print(f"# Full JSON dumped to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
