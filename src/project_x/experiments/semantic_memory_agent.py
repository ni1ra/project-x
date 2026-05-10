"""
semantic_memory_agent.py — Phase 9 Layer 4 (FINAL).

Wraps SemanticHDCMemory in a minimal agent loop. Per lain organic constraint
(2026-05-09): NO pretrained transformer LLM in the generator slot. The
"composer" is a template that fills in retrieved evidence — Phase 11+ will
build a from-scratch generator that lives behind this same interface.

Components:
  - MemoryAgent.process(text) → AnswerPacket
  - Rule-based controller decides write vs retrieve based on input shape
  - Evidence packet built from top-k retrieval with cosines + provenance
  - Template composer formats final answer with cited turn IDs
  - Honest "no evidence" fallback for absent_answer queries (cosine threshold)

Sample template outputs:
  - Found:    "Based on turn 47: 'Alice prefers Python.' (cosine 0.62)"
  - Multi:    "Based on turns 12, 47: 'evidence text 1' AND 'evidence text 2'"
  - Absent:   "No evidence found in conversation memory (top cosine 0.18 below
               threshold 0.25)."

Author: Raphael
Phase: 9 — semantic_hdc_memory_agent (Cycle 6 — FINAL Layer 4)
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from project_x.experiments.semantic_hdc_memory import (
    SemanticHDCMemory,
    TurnRecord,
)


# =============================================================================
# Data classes
# =============================================================================


@dataclass
class EvidencePacket:
    """A single retrieved piece of evidence."""
    turn_id: int
    cosine: float
    text: str
    fact_keys: list[str] = field(default_factory=list)


@dataclass
class AnswerPacket:
    """Agent's response to a query — composer's output + provenance."""
    query: str
    answer_text: str
    evidence: list[EvidencePacket]
    decision: str   # "write" | "retrieve" | "absent" | "no_decision"
    confidence: float   # max cosine across evidence (0..1)


# =============================================================================
# Rule-based controller — decide write vs retrieve
# =============================================================================


_QUESTION_HINTS = (
    "what", "where", "which", "who", "when", "why", "how",
    "remind me", "tell me",
)

_ASSERT_HINTS = (
    " prefers ", " prefer ", " likes ", " picked ", " chose ",
    " settled on ", " tends to ", " decided to ",
    " is a ", " are a ", " lives at ", " lives in ",
    # Phase 10 #00g: contradiction-revision phrases the killer-milestone uses.
    " switched to ", " switched from ", " moved to ", " changed to ",
    " is now ", " now uses ",
)


# Phase 12 #00P12-retrieval-mode-disambiguation. Query-shape patterns that
# suggest the caller wants the full chronological history of a subject's
# facts, not just the latest. These are CONSERVATIVE patterns — they must
# NOT match plain current-preference queries ("What does Alice prefer?"
# lacks every hint). The subject-extraction gate in MemoryAgent.process
# provides the second safety layer: route to full-history retrieval only
# when the query ALSO names a known fact_graph subject. Phase 11 verdict's
# memory-004 ("List all of Alice's preference changes...") and memory-005
# ("Summarize Alice's trajectory...") were the failure cases that drove
# this list — see docs/artifacts/PHASE_11_BENCHMARK.md memory section.
_LIST_ALL_HINTS = (
    "list all", "all of", "summarize", "trajectory",
    "history of", "all changes", "in chronological order",
    "in order", "every change", "full history",
)


def _is_list_all_query(text: str) -> bool:
    """Returns True if `text` shape suggests caller wants full chronological
    history rather than current state. Used by MemoryAgent.process to route
    between retrieve_structural (strict-dominance, latest-wins) and
    retrieve_structural_full_history (chronological, all-turns).

    Conservative — must combine with subject-extraction gate at call site
    (only route to full-history when query names a known fact_graph subject).
    Phase 12 #00P12 — closes Phase 11 memory-004 / memory-005 red findings.
    """
    lower = text.lower()
    return any(hint in lower for hint in _LIST_ALL_HINTS)


def classify_input(text: str) -> str:
    """Returns 'question' if input asks something, else 'assertion'.

    Cheap rule-based router. Phase 11+ may replace with a learned classifier.
    """
    lower = text.lower().strip()
    if "?" in lower:
        return "question"
    for hint in _QUESTION_HINTS:
        if lower.startswith(hint + " ") or lower.startswith(hint):
            return "question"
    for hint in _ASSERT_HINTS:
        if hint in lower:
            return "assertion"
    return "question"  # default to retrieval — safer than spurious writes


# =============================================================================
# Template composer — NO LLM (per lain organic constraint)
# =============================================================================


def compose_answer(
    query: str,
    evidence: list[EvidencePacket],
    cosine_threshold: float = 0.25,
    full_history: bool = False,
) -> tuple[str, str, float]:
    """Returns (answer_text, decision_label, confidence).

    Template rules:
      - Empty evidence → "No evidence" with confidence 0.
      - full_history=True (Phase 12 #00P12) → cite ALL evidence chronologically;
        SKIP cosine_threshold filter so the full subject chain emits rather
        than collapsing to threshold-filtered top picks. Decision label
        'retrieve_full_history' surfaces the routing for downstream provenance.
        Caller (MemoryAgent.process) flips this on 'list all' / 'summarize'
        queries that named a known fact_graph subject — closes Phase 11
        memory-004 (cited turn 7 only; expected [0,3,5,7]) and memory-005
        (cited turn 9 only; expected [1,3,5,7,9]) red findings.
      - Top evidence cosine < threshold → "No evidence (below threshold)" — flips
        absent_answer queries to honest non-answers when retrieval cosine is weak.
      - Single high-confidence evidence → quote turn text + cite turn_id + cosine.
      - Multi-evidence (e.g. multi_hop) → joint citation with AND-glued evidence.
    """
    if not evidence:
        return ("No evidence found in conversation memory.", "absent", 0.0)

    # Phase 12 #00P12: full-history short-circuit — cite all evidence in
    # chronological order without applying cosine_threshold. Older turns
    # within a subject's history typically score below the 0.32 default
    # (the strict-dominance boost is the only thing that lifts the latest
    # turn over threshold in retrieve_structural); the chronological path
    # surfaces those older turns deliberately and the caller knows they're
    # the answer to "list all" / "summarize trajectory" prompts.
    if full_history:
        ids = [str(e.turn_id) for e in evidence]
        parts = [f"'{e.text}'" for e in evidence]
        top_cos = max(e.cosine for e in evidence)
        return (
            f"Based on turns {', '.join(ids)}: {' AND '.join(parts)}",
            "retrieve_full_history",
            top_cos,
        )

    top_cos = max(e.cosine for e in evidence)
    if top_cos < cosine_threshold:
        return (
            f"No evidence found in conversation memory "
            f"(top cosine {top_cos:.3f} below threshold {cosine_threshold}).",
            "absent",
            top_cos,
        )

    # Pick evidence above the threshold for citation
    cited = [e for e in evidence if e.cosine >= cosine_threshold]
    if len(cited) == 1:
        e = cited[0]
        return (
            f"Based on turn {e.turn_id}: '{e.text}' (cosine {e.cosine:.3f})",
            "retrieve",
            e.cosine,
        )

    # Multi-evidence
    parts = [f"'{e.text}'" for e in cited[:3]]   # cap at 3 to keep concise
    ids = [str(e.turn_id) for e in cited[:3]]
    return (
        f"Based on turns {', '.join(ids)}: {' AND '.join(parts)} "
        f"(top cosine {cited[0].cosine:.3f})",
        "retrieve",
        cited[0].cosine,
    )


# =============================================================================
# MemoryAgent — bring it all together
# =============================================================================


def _tool_read_file(path: str, max_chars: int = 4096) -> str:
    """Default deterministic tool: read a local file, truncate to max_chars.

    Phase 10 #00g killer-milestone capability 5 needs a tool the agent can run.
    Read-file is the canonical example from the corpse. Errors are caught and
    rendered as the tool result so the agent always gets something writable.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read(max_chars + 1)
        if len(data) > max_chars:
            data = data[:max_chars] + "...[truncated]"
        return data
    except Exception as e:  # absolute boundary — convert to writable string
        return f"[tool error: {e}]"


@dataclass
class MemoryAgent:
    memory: SemanticHDCMemory
    # Phase 10 P5 (#00b) tuning: 0.32 is the empirical 5-seed best F1=0.9585
    # (fp_rate=9.3%, survival=93.5%) on structural cosines per
    # gpt-codex/runs/phase10_p5_absent_gating/result.json. Phase 9 default was 0.25.
    # Reviewer's ensemble-disagreement gating did NOT improve over threshold-alone;
    # encoder disagreement is too noisy on real queries to use as a confidence proxy.
    cosine_threshold: float = 0.32
    k_retrieve: int = 5
    replay_cadence: int = 50  # Hebbian-sleep pass every N writes; lain default-ack
    # Phase 10 #00g: tool registry. Default-acting on lain's open Q2 with the
    # lighter option ("extend MemoryAgent" vs "new ToolRuntime class"). Tools are
    # callables (str, **kwargs) -> str; agent.run_tool dispatches and writes the
    # result as a new memory turn.
    tools: dict = field(default_factory=lambda: {"read_file": _tool_read_file})
    _next_turn_id: int = 0
    _writes_since_replay: int = 0

    def process(self, text: str) -> AnswerPacket:
        """Single-turn agent loop: classify → write or retrieve → compose answer."""
        decision = classify_input(text)
        if decision == "assertion":
            # Phase 10 P4 (#00d): incremental write into memory. Encodes the
            # assertion as a new TurnRecord, appends via memory.write_one (no
            # batch rebuild), and triggers a Hebbian replay-consolidation
            # every `replay_cadence` writes (the "sleep pass" — Council Idea #4).
            from project_x.experiments.semantic_hdc_memory import TurnRecord
            # Pick a turn_id past the current memory tail.
            existing = len(self.memory._records)
            turn_id = max(existing, self._next_turn_id)
            self._next_turn_id = turn_id + 1
            record = TurnRecord(turn_id=turn_id, text=text, fact_keys=[], metadata={})
            self.memory.write_one(record)
            self._writes_since_replay += 1
            replayed = False
            if self._writes_since_replay >= self.replay_cadence:
                self.memory.replay_consolidate()
                self._writes_since_replay = 0
                replayed = True
            return AnswerPacket(
                query=text,
                answer_text=(
                    f"(written as turn {turn_id}"
                    + ("; replay consolidated" if replayed else "")
                    + ")"
                ),
                evidence=[], decision="write", confidence=1.0,
            )

        # Question path — Phase 12 #00P12 retrieval-mode disambiguation:
        # Phase 11 verdict surfaced that the Phase 10 P3 strict-dominance
        # boost (max_in_subject + 1.0 in `_structural_cosines`) collapses
        # 'list all changes' / 'summarize trajectory' queries to top-1 only.
        # Route those queries to retrieve_structural_full_history (chronological,
        # no boost) instead. Subject-extraction gate keeps current-preference
        # queries on the existing strict-dominance path (memory-001/002/003
        # regression-safe). full_history_mode threads through to compose_answer
        # so the cosine_threshold filter is bypassed for the chronological
        # short-circuit.
        full_history_mode = (
            _is_list_all_query(text)
            and bool(self.memory._extract_query_subjects(text))
        )
        if full_history_mode:
            top_k = self.memory.retrieve_structural_full_history(text, k=None)
        else:
            # Phase 10 P3: prefer structural retrieval so contradiction queries
            # surface the latest revision turn and known-subject queries get
            # the right candidate set; falls through to pure cosine when no
            # known subjects (absent_answer with phantom names).
            top_k = self.memory.retrieve_structural(text, k=self.k_retrieve)
        evidence = [
            EvidencePacket(
                turn_id=t_id, cosine=cos,
                text=record.text, fact_keys=record.fact_keys,
            )
            for t_id, cos, record in top_k
        ]
        answer_text, decision_label, confidence = compose_answer(
            text, evidence,
            cosine_threshold=self.cosine_threshold,
            full_history=full_history_mode,
        )
        return AnswerPacket(
            query=text, answer_text=answer_text,
            evidence=evidence, decision=decision_label, confidence=confidence,
        )

    def run_tool(self, tool_name: str, **kwargs) -> AnswerPacket:
        """Phase 10 #00g killer-milestone capability 5 — execute a registered tool
        and write the result back into memory as a new turn. Subsequent retrieval
        finds the tool-written turn. Returns an AnswerPacket with decision='tool'
        whose answer_text contains the tool output and whose `evidence` is a
        single-entry list pointing at the new memory turn.

        Default-acted on lain's open Q2 (extend MemoryAgent vs new ToolRuntime
        class) with the extension path — lighter touch, no new module surface.
        """
        if tool_name not in self.tools:
            return AnswerPacket(
                query=f"tool:{tool_name}", answer_text=f"(unknown tool: {tool_name})",
                evidence=[], decision="tool_error", confidence=0.0,
            )
        tool_fn = self.tools[tool_name]
        result = tool_fn(**kwargs)
        # Write the tool result as a memory turn so subsequent retrieves can find it.
        existing = len(self.memory._records)
        turn_id = max(existing, self._next_turn_id)
        self._next_turn_id = turn_id + 1
        kw_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        text = f"Tool {tool_name}({kw_str}) returned: {result}"
        record = TurnRecord(
            turn_id=turn_id,
            text=text,
            fact_keys=[f"tool:{tool_name}"],
            metadata={"tool_name": tool_name, "tool_kwargs": kwargs},
        )
        self.memory.write_one(record)
        self._writes_since_replay += 1
        replayed = False
        if self._writes_since_replay >= self.replay_cadence:
            self.memory.replay_consolidate()
            self._writes_since_replay = 0
            replayed = True
        return AnswerPacket(
            query=f"tool:{tool_name}",
            answer_text=text + ("; replay consolidated" if replayed else ""),
            evidence=[EvidencePacket(turn_id=turn_id, cosine=1.0, text=text,
                                     fact_keys=record.fact_keys)],
            decision="tool",
            confidence=1.0,
        )

    def process_with_multi_hop(self, text: str) -> AnswerPacket:
        """Use multi-hop decomposition for AND/OR queries."""
        top_k = self.memory.retrieve_multi_hop(text, k=self.k_retrieve)
        evidence = [
            EvidencePacket(
                turn_id=t_id, cosine=cos, text=record.text,
                fact_keys=record.fact_keys,
            )
            for t_id, cos, record in top_k
        ]
        answer_text, decision_label, confidence = compose_answer(
            text, evidence, cosine_threshold=self.cosine_threshold,
        )
        return AnswerPacket(
            query=text, answer_text=answer_text, evidence=evidence,
            decision=decision_label, confidence=confidence,
        )


# =============================================================================
# Demo runner — show end-to-end answers across 5 query types
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=str,
                        default="gpt-codex/runs/phase9_dataset_full")
    parser.add_argument("--out", type=str,
                        default="gpt-codex/runs/phase9_agent_demo")
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--negative-samples", type=int, default=5)
    parser.add_argument("--cosine-threshold", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=1337)
    args = parser.parse_args()

    dataset_dir = Path(args.dataset)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with (dataset_dir / "conversation.jsonl").open() as f:
        turns = [json.loads(line) for line in f]
    with (dataset_dir / "queries.jsonl").open() as f:
        queries = [json.loads(line) for line in f]

    records = [
        TurnRecord(
            turn_id=t["turn_id"], text=t["text"],
            fact_keys=t.get("fact_keys", []),
            metadata={k: v for k, v in t.items() if k not in ("turn_id", "text", "fact_keys")},
        )
        for t in turns
    ]
    mem = SemanticHDCMemory(
        D=10000, alpha=args.alpha,
        negative_samples=args.negative_samples, seed=args.seed,
    )
    t0 = time.time()
    mem.write_batch(records)
    write_wall = time.time() - t0
    agent = MemoryAgent(memory=mem, cosine_threshold=args.cosine_threshold)

    # Demo: pick one query of each type + run end-to-end
    by_type: dict[str, dict] = {}
    for q in queries:
        if q["type"] not in by_type:
            by_type[q["type"]] = q
    demo_results = []
    for qtype, q in by_type.items():
        if qtype == "multi_hop":
            packet = agent.process_with_multi_hop(q["text"])
        else:
            packet = agent.process(q["text"])
        demo_results.append({
            "type": qtype,
            "query": q["text"],
            "expected_turn_ids": q["expected_turn_ids"],
            "expected_answer": q.get("expected_answer"),
            "agent_answer": packet.answer_text,
            "agent_decision": packet.decision,
            "agent_confidence": round(packet.confidence, 3),
            "agent_top_turn_ids": [e.turn_id for e in packet.evidence[:3]],
            "match_at_top1": (
                packet.evidence[0].turn_id in q["expected_turn_ids"]
                if packet.evidence and q["expected_turn_ids"] else None
            ),
        })

    result = {
        "run_id": f"phase9_agent_demo_alpha{args.alpha}_neg{args.negative_samples}_thr{args.cosine_threshold}",
        "config": {
            "alpha": args.alpha,
            "negative_samples": args.negative_samples,
            "cosine_threshold": args.cosine_threshold,
            "seed": args.seed,
        },
        "metrics": {
            "write_wall_seconds": round(write_wall, 4),
            "demo_results": demo_results,
        },
        "notes": [
            "Template composer cites turn IDs and quotes evidence text. NO LLM in the loop.",
            "Cosine threshold gates absent_answer responses honestly.",
            "Multi-hop queries route through retrieve_multi_hop (decomposition + union top-k).",
            "Assertions currently no-op (return 'noted; deferred to Phase 10' rather than incremental write).",
        ],
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2))

    # Pretty print demo
    print(f"MemoryAgent demo  alpha={args.alpha}  neg={args.negative_samples}  thr={args.cosine_threshold}")
    print(f"  write_wall: {write_wall:.3f}s  ({len(records)} turns)\n")
    for d in demo_results:
        print(f"[{d['type']:>20}]  Q: {d['query']}")
        print(f"  expected_turns={d['expected_turn_ids']}  expected_answer={d['expected_answer']}")
        print(f"  agent_decision={d['agent_decision']}  conf={d['agent_confidence']}  match_top1={d['match_at_top1']}")
        print(f"  agent_answer: {d['agent_answer']}\n")
    print(f"  wrote {out_dir / 'result.json'}")


if __name__ == "__main__":
    main()
