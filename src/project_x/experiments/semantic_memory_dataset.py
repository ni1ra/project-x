"""
semantic_memory_dataset.py — Phase 9 Layer 1.

Generate synthetic-real conversation turns + labeled queries to test whether
HDC memory retrieves *meaning* (not just turn-ID-to-symbol bindings). Replaces
hdc_conversation_demo's random atoms with templated English carrying real
fact-keys, preferences, decisions, file paths, contradictions, and
absent-answer probes.

Output:
  - conversation.jsonl: one turn per line
      {turn_id, speaker, text, fact_keys[], category, salience, decision_id?,
       supersedes_turn_id?, file_path?}
  - queries.jsonl: one labeled query per line
      {query_id, type, text, expected_turn_ids[], expected_answer, fact_key,
       difficulty}
  - result.json: generation metadata + label-distribution + samples

Five query types (per A_TO_Z_PLAN §1.4 + §3 acceptance criteria):
  1. exact_turn_lookup   — query text references a literal turn fact directly
  2. semantic_paraphrase — query reworded; same fact_key, different surface
  3. multi_hop           — answer requires combining 2 turns
  4. contradiction       — fact superseded later; query expects most-recent
  5. absent_answer       — fact never mentioned; expects "no evidence"

Hardware budget: pure Python + numpy seed; CPU only; <2s for 1000 turns + 200
queries. No external models loaded by this module.

Author: Raphael (post-persona-shift, 2026-05-09)
Phase: 9 — semantic_hdc_memory_agent
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np


# =============================================================================
# Lexicon — small, controlled, semantically meaningful
# =============================================================================

PEOPLE = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank"]

LANGUAGES = ["Python", "Rust", "Go", "TypeScript", "Haskell", "Zig", "Elixir", "OCaml"]

TOOLS = ["Postgres", "Redis", "Kafka", "Vercel", "Docker", "Kubernetes", "Nginx", "FastAPI"]

PREFERENCE_VERBS = ["prefers", "likes", "would rather use", "tends to pick", "leans toward"]

PARAPHRASE_PROBES = [
    "what does {person} like to use for backend work",
    "which language is {person}'s favorite",
    "what is {person}'s preferred tool",
    "what does {person} usually choose",
]

DECISION_VERBS = ["decided to use", "settled on", "chose", "picked"]

DECISION_PARAPHRASE_PROBES = [
    "what was the team's choice for {topic}",
    "which {topic_type} did we end up with",
    "what did we pick for {topic}",
]

FILE_TEMPLATES = [
    "the config lives at {path}",
    "{component} is implemented in {path}",
    "I put the {component} module under {path}",
    "look in {path} for the {component} code",
]

ABSENT_PROBE_TEMPLATES = [
    "what does {person} think about {tool}",
    "which {topic_type} did we use for {topic}",
    "where is the {component} stored",
    "what is the {person}'s opinion on {tool}",
]

CONTRADICTION_VERBS = [
    "actually we're switching from {old} to {new}",
    "scrap that, {new} is the new pick instead of {old}",
    "update: changed from {old} to {new}",
    "revising — {new} replaces {old}",
]


# =============================================================================
# Data classes
# =============================================================================


@dataclass
class Turn:
    turn_id: int
    speaker: str
    text: str
    category: str            # "preference" | "decision" | "file_path" | "filler" | "contradiction"
    fact_keys: list[str] = field(default_factory=list)  # canonical keys e.g. "pref:Alice"
    salience: float = 1.0    # filler ~ 0.2; primary fact ~ 1.0
    decision_id: int | None = None
    supersedes_turn_id: int | None = None
    file_path: str | None = None


@dataclass
class Query:
    query_id: int
    type: str                # one of the 5 types
    text: str
    expected_turn_ids: list[int]
    expected_answer: str | None  # the canonical answer text; None for absent_answer
    fact_key: str | None
    difficulty: str          # "easy" | "medium" | "hard"


# =============================================================================
# Generators
# =============================================================================


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _gen_preference_turn(turn_id: int, rng: np.random.Generator,
                         person: str, tool: str) -> Turn:
    speaker = str(rng.choice(PEOPLE))
    verb = str(rng.choice(PREFERENCE_VERBS))
    text = f"{person} {verb} {tool}."
    return Turn(
        turn_id=turn_id,
        speaker=speaker,
        text=text,
        category="preference",
        fact_keys=[f"pref:{person}"],
        salience=1.0,
    )


def _gen_decision_turn(turn_id: int, rng: np.random.Generator,
                       topic: str, choice: str, decision_id: int) -> Turn:
    speaker = str(rng.choice(PEOPLE))
    verb = str(rng.choice(DECISION_VERBS))
    text = f"For {topic}, we {verb} {choice}."
    return Turn(
        turn_id=turn_id,
        speaker=speaker,
        text=text,
        category="decision",
        fact_keys=[f"dec:{topic}"],
        salience=1.0,
        decision_id=decision_id,
    )


def _gen_file_path_turn(turn_id: int, rng: np.random.Generator,
                        component: str, path: str) -> Turn:
    speaker = str(rng.choice(PEOPLE))
    template = str(rng.choice(FILE_TEMPLATES))
    text = template.format(path=path, component=component)
    return Turn(
        turn_id=turn_id,
        speaker=speaker,
        text=text,
        category="file_path",
        fact_keys=[f"file:{component}"],
        salience=1.0,
        file_path=path,
    )


def _gen_filler_turn(turn_id: int, rng: np.random.Generator) -> Turn:
    """Filler turns dilute the conversation so retrieval is non-trivial."""
    speaker = str(rng.choice(PEOPLE))
    fillers = [
        f"{speaker} pinged the channel.",
        f"meeting at three.",
        f"{speaker} is on call this week.",
        f"running tests now.",
        f"will sync tomorrow.",
        f"{speaker} pushed a hotfix.",
        f"docs updated.",
        f"build is green.",
    ]
    text = str(rng.choice(fillers))
    return Turn(
        turn_id=turn_id,
        speaker=speaker,
        text=text,
        category="filler",
        salience=0.2,
    )


def _gen_contradiction_turn(turn_id: int, rng: np.random.Generator,
                            original_turn: Turn, new_value: str) -> Turn:
    """Supersede an earlier preference/decision/file_path turn with a revision."""
    speaker = str(rng.choice(PEOPLE))
    verb = str(rng.choice(CONTRADICTION_VERBS))
    # original_turn.text holds the old value; pull a coarse "old" token by category
    if original_turn.category == "preference":
        old = original_turn.text.split()[-1].rstrip(".")
    elif original_turn.category == "decision":
        old = original_turn.text.split()[-1].rstrip(".")
    elif original_turn.category == "file_path":
        old = original_turn.file_path or "the previous path"
    else:
        old = "the previous choice"
    text = verb.format(old=old, new=new_value).capitalize() + "."
    return Turn(
        turn_id=turn_id,
        speaker=speaker,
        text=text,
        category="contradiction",
        fact_keys=list(original_turn.fact_keys),  # same key, new value
        salience=1.0,
        supersedes_turn_id=original_turn.turn_id,
    )


# =============================================================================
# Conversation builder
# =============================================================================


def build_conversation(
    n_turns: int,
    seed: int,
    filler_ratio: float = 0.5,
    contradiction_count: int = 5,
) -> tuple[list[Turn], dict]:
    """
    Build an n_turns-length conversation. Returns (turns, fact_map).

    fact_map[fact_key] = {"current_value": ..., "current_turn_id": ...,
                          "history": [(turn_id, value), ...]}
    """
    rng = _rng(seed)
    turns: list[Turn] = []
    fact_map: dict[str, dict] = {}

    # Plan substantive (non-filler) turns first; then interleave filler.
    n_substantive = max(8, int(n_turns * (1.0 - filler_ratio)))
    n_filler = n_turns - n_substantive

    substantive_specs: list[tuple[str, dict]] = []

    # Fixed seed of preferences: every PERSON gets one preference at minimum.
    for person in PEOPLE:
        tool = str(rng.choice(LANGUAGES))
        substantive_specs.append(("preference", {"person": person, "tool": tool}))

    # Decisions for ~6 topics
    decision_topics = ["the database", "the queue", "the deploy target", "the auth provider",
                       "the cache layer", "the API framework"]
    for d_id, topic in enumerate(decision_topics):
        choice = str(rng.choice(TOOLS))
        substantive_specs.append(("decision", {"topic": topic, "choice": choice,
                                                "decision_id": d_id}))

    # File paths for components
    components = ["controller", "encoder", "memory", "generator", "router", "telemetry"]
    for comp in components:
        path = f"src/project_x/experiments/{comp}.py"
        substantive_specs.append(("file_path", {"component": comp, "path": path}))

    # Top up substantive specs with extra preferences/decisions to hit n_substantive
    while len(substantive_specs) < n_substantive:
        kind = str(rng.choice(["preference", "decision", "file_path"]))
        if kind == "preference":
            substantive_specs.append(("preference", {
                "person": str(rng.choice(PEOPLE)),
                "tool": str(rng.choice(LANGUAGES)),
            }))
        elif kind == "decision":
            substantive_specs.append(("decision", {
                "topic": f"subsystem-{rng.integers(0, 1000)}",
                "choice": str(rng.choice(TOOLS)),
                "decision_id": len(decision_topics) + len(substantive_specs),
            }))
        else:
            comp = f"module_{rng.integers(0, 1000)}"
            substantive_specs.append(("file_path", {
                "component": comp,
                "path": f"src/project_x/experiments/{comp}.py",
            }))

    rng.shuffle(substantive_specs)

    # Materialize substantive turns
    substantive_turns: list[Turn] = []
    for kind, spec in substantive_specs[:n_substantive]:
        tid = -1  # placeholder; assigned during interleave
        if kind == "preference":
            t = _gen_preference_turn(tid, rng, spec["person"], spec["tool"])
        elif kind == "decision":
            t = _gen_decision_turn(tid, rng, spec["topic"], spec["choice"], spec["decision_id"])
        else:
            t = _gen_file_path_turn(tid, rng, spec["component"], spec["path"])
        substantive_turns.append(t)

    # Interleave with fillers
    positions_for_substantive = sorted(rng.choice(n_turns, size=n_substantive, replace=False).tolist())
    pos_set = set(positions_for_substantive)
    sub_iter = iter(substantive_turns)
    for tid in range(n_turns):
        if tid in pos_set:
            t = next(sub_iter)
            t.turn_id = tid
            turns.append(t)
            for fk in t.fact_keys:
                # Extract the canonical value the turn carries.
                if t.category == "preference":
                    value = t.text.split()[-1].rstrip(".")
                elif t.category == "decision":
                    value = t.text.split()[-1].rstrip(".")
                elif t.category == "file_path":
                    value = t.file_path or ""
                else:
                    value = ""
                fact_map.setdefault(fk, {"history": []})
                fact_map[fk]["history"].append((tid, value))
                fact_map[fk]["current_value"] = value
                fact_map[fk]["current_turn_id"] = tid
                fact_map[fk]["category"] = t.category
        else:
            turns.append(_gen_filler_turn(tid, rng))

    # Inject contradictions: pick `contradiction_count` substantive turns from the
    # first 60% of the conversation, then add a revising turn near the end.
    contradiction_candidates = [t for t in turns if t.category in ("preference", "decision", "file_path")
                                 and t.turn_id < int(n_turns * 0.6)]
    if contradiction_candidates and contradiction_count > 0:
        chosen = rng.choice(len(contradiction_candidates),
                            size=min(contradiction_count, len(contradiction_candidates)),
                            replace=False)
        # Need new turn slots — append at end (extending n_turns)
        for offset, idx in enumerate(chosen):
            orig = contradiction_candidates[int(idx)]
            if orig.category == "preference":
                new_value = str(rng.choice(LANGUAGES))
            elif orig.category == "decision":
                new_value = str(rng.choice(TOOLS))
            else:
                new_value = f"src/project_x/experiments/{orig.fact_keys[0].split(':')[1]}_v2.py"
            new_turn = _gen_contradiction_turn(len(turns), rng, orig, new_value)
            turns.append(new_turn)
            for fk in new_turn.fact_keys:
                fact_map[fk]["history"].append((new_turn.turn_id, new_value))
                fact_map[fk]["current_value"] = new_value
                fact_map[fk]["current_turn_id"] = new_turn.turn_id

    return turns, fact_map


# =============================================================================
# Query builder
# =============================================================================


def build_queries(
    turns: list[Turn],
    fact_map: dict[str, dict],
    n_queries: int,
    seed: int,
) -> list[Query]:
    """
    Build a labeled query suite with all 5 query types in roughly balanced
    proportions: exact 25%, paraphrase 30%, multi_hop 15%, contradiction 15%,
    absent 15%.
    """
    rng = _rng(seed + 7919)  # offset so query randomness is independent
    queries: list[Query] = []
    qid = 0

    type_counts = {
        "exact_turn_lookup": int(n_queries * 0.25),
        "semantic_paraphrase": int(n_queries * 0.30),
        "multi_hop": int(n_queries * 0.15),
        "contradiction": int(n_queries * 0.15),
        "absent_answer": n_queries - int(n_queries * 0.85),  # remainder ~15%
    }

    fact_items = [(fk, fm) for fk, fm in fact_map.items() if fm.get("category") in
                  ("preference", "decision", "file_path")]
    if not fact_items:
        return []

    # 1) exact_turn_lookup — quote the canonical surface
    for _ in range(type_counts["exact_turn_lookup"]):
        fk, fm = fact_items[int(rng.integers(0, len(fact_items)))]
        category = fm["category"]
        value = fm["current_value"]
        turn_id = fm["current_turn_id"]
        if category == "preference":
            person = fk.split(":")[1]
            text = f"What does {person} prefer?"
            answer = value
        elif category == "decision":
            topic = fk.split(":")[1]
            text = f"What did we decide for {topic}?"
            answer = value
        else:
            comp = fk.split(":")[1]
            text = f"Where is the {comp} module?"
            answer = value
        queries.append(Query(qid, "exact_turn_lookup", text, [turn_id], answer, fk, "easy"))
        qid += 1

    # 2) semantic_paraphrase — same fact, different surface
    for _ in range(type_counts["semantic_paraphrase"]):
        fk, fm = fact_items[int(rng.integers(0, len(fact_items)))]
        category = fm["category"]
        value = fm["current_value"]
        turn_id = fm["current_turn_id"]
        if category == "preference":
            person = fk.split(":")[1]
            text = str(rng.choice(PARAPHRASE_PROBES)).format(person=person) + "?"
            answer = value
        elif category == "decision":
            topic = fk.split(":")[1]
            tt = "tool" if "queue" in topic or "cache" in topic else "service"
            text = str(rng.choice(DECISION_PARAPHRASE_PROBES)).format(topic=topic, topic_type=tt) + "?"
            answer = value
        else:
            comp = fk.split(":")[1]
            text = f"Remind me where {comp} lives in the codebase?"
            answer = value
        queries.append(Query(qid, "semantic_paraphrase", text, [turn_id], answer, fk, "medium"))
        qid += 1

    # 3) multi_hop — combine two facts
    for _ in range(type_counts["multi_hop"]):
        if len(fact_items) < 2:
            break
        # Pick two distinct preferences and ask "what do A and B both prefer (or differ on)"
        prefs = [(fk, fm) for fk, fm in fact_items if fm["category"] == "preference"]
        if len(prefs) >= 2:
            i, j = rng.choice(len(prefs), size=2, replace=False)
            (fk_a, fm_a), (fk_b, fm_b) = prefs[int(i)], prefs[int(j)]
            person_a, person_b = fk_a.split(":")[1], fk_b.split(":")[1]
            text = f"What do {person_a} and {person_b} prefer?"
            expected_turns = [fm_a["current_turn_id"], fm_b["current_turn_id"]]
            answer = f"{fm_a['current_value']} and {fm_b['current_value']}"
            queries.append(Query(qid, "multi_hop", text, expected_turns, answer,
                                 None, "hard"))
            qid += 1

    # 4) contradiction — fact superseded later; expects most-recent value + most-recent turn.
    #
    # Contradiction-eligibility is determined by the explicit `supersedes_turn_id`
    # field on revision turns (set only by `_gen_contradiction_turn`), NOT by
    # `len(history) > 1`. The latter conflates substantive_specs random fact-key
    # reuse with explicit revisions and inflates the pool. See M-PROJECTX-012.
    contradicted_fact_keys = {
        fk
        for t in turns
        if t.supersedes_turn_id is not None
        for fk in t.fact_keys
    }
    superseded_facts = [(fk, fm) for fk, fm in fact_map.items() if fk in contradicted_fact_keys]
    for _ in range(type_counts["contradiction"]):
        if not superseded_facts:
            break
        fk, fm = superseded_facts[int(rng.integers(0, len(superseded_facts)))]
        category = fm["category"]
        if category == "preference":
            person = fk.split(":")[1]
            text = f"What is {person}'s current preferred tool?"
        elif category == "decision":
            topic = fk.split(":")[1]
            text = f"What is the latest pick for {topic}?"
        else:
            comp = fk.split(":")[1]
            text = f"Where does the {comp} module live now?"
        answer = fm["current_value"]
        # Expected turns: the contradiction turn (latest); optionally the original too
        expected_turns = [fm["current_turn_id"]]
        queries.append(Query(qid, "contradiction", text, expected_turns, answer, fk, "hard"))
        qid += 1

    # 5) absent_answer — fabricate a probe whose fact_key is NOT in fact_map
    rng_state = np.random.default_rng(seed + 1009)
    for _ in range(type_counts["absent_answer"]):
        kind = str(rng_state.choice(["unknown_person_pref", "unknown_topic_dec",
                                     "unknown_component_file"]))
        if kind == "unknown_person_pref":
            ghost = f"Ghost{rng_state.integers(1000, 9999)}"
            text = f"What does {ghost} prefer?"
        elif kind == "unknown_topic_dec":
            topic = f"phantom-system-{rng_state.integers(1000, 9999)}"
            text = f"What did we decide for {topic}?"
        else:
            comp = f"missing_module_{rng_state.integers(1000, 9999)}"
            text = f"Where is the {comp} module?"
        queries.append(Query(qid, "absent_answer", text, [], None, None, "medium"))
        qid += 1

    return queries


# =============================================================================
# I/O
# =============================================================================


def write_jsonl(rows: Iterable[dict], path: Path) -> int:
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


# =============================================================================
# Main
# =============================================================================


def run_dataset(n_turns: int, n_queries: int, seed: int, out_dir: Path) -> dict:
    t0 = time.time()
    turns, fact_map = build_conversation(n_turns, seed)
    queries = build_queries(turns, fact_map, n_queries, seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    n_t = write_jsonl((asdict(t) for t in turns), out_dir / "conversation.jsonl")
    n_q = write_jsonl((asdict(q) for q in queries), out_dir / "queries.jsonl")

    type_dist: dict[str, int] = {}
    for q in queries:
        type_dist[q.type] = type_dist.get(q.type, 0) + 1
    category_dist: dict[str, int] = {}
    for t in turns:
        category_dist[t.category] = category_dist.get(t.category, 0) + 1

    elapsed = time.time() - t0
    result = {
        "run_id": f"phase9_dataset_T{n_t}_Q{n_q}_seed{seed}",
        "config": {
            "n_turns_requested": n_turns,
            "n_turns_actual": n_t,
            "n_queries_requested": n_queries,
            "n_queries_actual": n_q,
            "seed": seed,
        },
        "metrics": {
            "wall_seconds": round(elapsed, 4),
            "turn_category_distribution": category_dist,
            "query_type_distribution": type_dist,
            "n_facts": len(fact_map),
            "n_superseded_facts": len({fk for t in turns if t.supersedes_turn_id is not None for fk in t.fact_keys}),
        },
        "samples": {
            "turns": [asdict(t) for t in turns[:5]],
            "queries": [asdict(q) for q in queries[:10]],
        },
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-turns", type=int, default=200,
                        help="Conversation length (excludes any contradiction-revision turns appended).")
    parser.add_argument("--n-queries", type=int, default=50,
                        help="Total labeled queries (split across 5 types).")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--out", type=str,
                        default="gpt-codex/runs/phase9_dataset_smoke",
                        help="Output directory.")
    parser.add_argument("--mode", type=str, choices=("test", "full"), default="test",
                        help="test=200T/50Q (smoke); full=1000T/200Q.")
    args = parser.parse_args()

    if args.mode == "full":
        n_turns, n_queries = 1000, 200
        out = args.out.replace("smoke", "full") if "smoke" in args.out else args.out
    else:
        n_turns, n_queries = args.n_turns, args.n_queries
        out = args.out

    out_dir = Path(out)
    print(f"semantic_memory_dataset  mode={args.mode}  n_turns={n_turns}  n_queries={n_queries}  seed={args.seed}")
    result = run_dataset(n_turns, n_queries, args.seed, out_dir)
    print(f"  wrote {result['config']['n_turns_actual']} turns, {result['config']['n_queries_actual']} queries to {out_dir}")
    print(f"  wall={result['metrics']['wall_seconds']}s  facts={result['metrics']['n_facts']}  superseded={result['metrics']['n_superseded_facts']}")
    print(f"  query types: {result['metrics']['query_type_distribution']}")
    print(f"  turn categories: {result['metrics']['turn_category_distribution']}")


if __name__ == "__main__":
    main()
