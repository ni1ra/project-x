"""Local REPL chat loop for Project X Raphael.

Wires ReasoningAgent + SemanticHDCMemory + MemoryAgent into a minimal
stdin/stdout conversational interface. The substrate's first measurable
chat-loop bootstrap.

Usage:
    PYTHONPATH=src python3 src/project_x/experiments/chat_loop.py
    PYTHONPATH=src python3 src/project_x/experiments/chat_loop.py --smoke
"""

from __future__ import annotations

import argparse
import sys

from project_x.experiments.semantic_hdc_memory import SemanticHDCMemory, TurnRecord
from project_x.experiments.semantic_memory_agent import MemoryAgent
from project_x.persona import wrap_response
from project_x.reasoning_agent import ReasoningAgent


class ChatSession:
    """Minimal multi-turn chat session.

    Pipeline per turn:
      1. User text → ReasoningAgent.process() (formal dispatch)
      2. If refused → MemoryAgent.process() (memory retrieve / natural mode)
      3. If absent → honest refusal
      4. Persona wrap → output
      5. Both user + assistant text written to SemanticHDCMemory for
         retrieval on future turns (multi-turn coherence scaffold).
    """

    def __init__(self, memory: SemanticHDCMemory | None = None) -> None:
        self.memory = memory or SemanticHDCMemory(D=10240, seed=42)
        # SemanticHDCMemory requires write_batch before write_one/retrieve.
        # Seed with an empty batch so the encoder is fitted and _is_built=True.
        if not getattr(self.memory, "_is_built", False):
            self.memory.write_batch([])
        self.reasoning_agent = ReasoningAgent()
        self.memory_agent = MemoryAgent(memory=self.memory, cosine_threshold=0.25)
        self._next_turn_id = 0

    def _write_turn(self, text: str) -> None:
        """Append a turn to the HDC memory store."""
        record = TurnRecord(
            turn_id=self._next_turn_id,
            text=text,
            fact_keys=[],
            metadata={},
        )
        self.memory.write_one(record)
        self._next_turn_id += 1

    def respond(self, user_text: str) -> str:
        """Generate a response to `user_text`."""
        # 1. Formal reasoning dispatch first
        agent_response = self.reasoning_agent.process(user_text)

        if agent_response.confidence != "refused":
            answer = agent_response.answer_text
            response_type = "factual_retrieval"
        else:
            # 2. Memory / natural-mode fall-through
            packet = self.memory_agent.process(user_text)
            if packet.decision not in ("absent", "no_decision"):
                answer = packet.answer_text
                response_type = (
                    "multi_evidence"
                    if packet.decision == "retrieve"
                    else "factual_retrieval"
                )
            else:
                # 3. Honest refusal
                answer = "I don't have an answer for that yet."
                response_type = "absent"

        # 4. Persona wrap
        answer = wrap_response(answer, response_type, user_text)

        # 5. Record in memory for multi-turn coherence
        self._write_turn(f"User: {user_text}")
        self._write_turn(f"Assistant: {answer}")

        return answer

    def run_repl(self) -> None:
        """Interactive stdin/stdout loop."""
        print("Project X Raphael — Chat Loop v1")
        print("Type 'exit' or press Ctrl-D to quit.\n")
        while True:
            try:
                user_text = input("You> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break
            if not user_text:
                continue
            if user_text.lower() in ("exit", "quit", "bye"):
                print("Goodbye.")
                break
            answer = self.respond(user_text)
            print(f"Raphael> {answer}\n")


def _smoke_test(session: ChatSession) -> bool:
    """3-turn automated smoke test. Returns True if all turns complete."""
    prompts = [
        "Solve 3x^2 - 14x - 5 = 0",
        "What did we just discuss?",
        "Tell me something interesting about entropy.",
    ]
    ok = True
    for prompt in prompts:
        try:
            answer = session.respond(prompt)
            print(f"[SMOKE] Q: {prompt}")
            print(f"[SMOKE] A: {answer[:200]}{'...' if len(answer) > 200 else ''}\n")
        except Exception as exc:
            print(f"[SMOKE FAIL] Q: {prompt} — {exc}", file=sys.stderr)
            ok = False
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="Run automated smoke test")
    args = parser.parse_args()

    session = ChatSession()
    if args.smoke:
        success = _smoke_test(session)
        sys.exit(0 if success else 1)
    session.run_repl()


if __name__ == "__main__":
    main()
