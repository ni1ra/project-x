"""Humor templates + deterministic selection for Project X Raphael persona.

Humor inserts at ~30% frequency on humor-enabled response types; the other
70% of responses are clean voice-marker + content. Selection uses a stable
SHA-256-based hash of the prompt so the same prompt always yields the same
humor — testable + reproducible.

Skipped types (gravity preserved): absent, refusal, error. Humor in null/
failure responses cringes; cycle 1's structural rubric enforces this.
"""

from __future__ import annotations

import hashlib

# Humor fires on these response types. Null/failure shapes intentionally
# omitted — the in-character rubric checks that humor is NOT inserted there.
HUMOR_ENABLED_TYPES: frozenset[str] = frozenset({
    "factual_retrieval",
    "multi_evidence",
    "retrieve_full_history",
    "write_ack",
    "tool_ack",
})


# Insertion frequency: humor lands ~30% of the time so it feels like wit
# rather than schtick. Tunable; the structural rubric does NOT assert a
# specific rate (qualitative grading is for the manual-grade harness).
HUMOR_FREQUENCY_PCT: int = 30


# Templates per humor-enabled response type. 3-5 per type. Postfix style —
# appended after the wrapped main response. Voice register matches Raphael's
# declarative-analytical baseline: dry understatement, occasional callback,
# no slapstick.
HUMOR_TEMPLATES: dict[str, list[str]] = {
    "factual_retrieval": [
        "(Also: the universe declines to comment.)",
        "(Parenthetical: the lookup neither blinks nor apologizes.)",
        "(Addendum: memory holds; the rest is interpretation.)",
        "(Footnote: I have read this, and it has read me back.)",
    ],
    "multi_evidence": [
        "(Observation: convergence is rarely accidental.)",
        "(Footnote: multiple sources, single conclusion — the cleanest shape.)",
        "(Addendum: when memory agrees with itself, attend.)",
    ],
    "retrieve_full_history": [
        "(Chronology preserved; I have not editorialized.)",
        "(Observation: history compounds; this is the receipt.)",
        "(Timeline intact — the past is what we say it was, until challenged.)",
    ],
    "write_ack": [
        "(Filed; the archive grows quietly.)",
        "(Stored; the future will retrieve this and judge us both.)",
        "(Committed; memory takes interest where attention does not.)",
    ],
    "tool_ack": [
        "(Executed; the tool returned in its own time.)",
        "(Performed; the result is recorded for later analysis.)",
        "(Actioned; the side-effect is real, the consequence pending.)",
    ],
}


def _stable_hash(text: str) -> int:
    """SHA-256-based hash that survives Python's per-session hash randomization.

    Returns a 32-bit int — sufficient entropy for template selection +
    insertion-frequency gating. Built-in hash() is salted, breaks tests.
    """
    return int.from_bytes(
        hashlib.sha256(text.encode("utf-8")).digest()[:4], "big"
    )


def select_humor(response_type: str, prompt: str) -> str | None:
    """Deterministically select a humor template for (response_type, prompt).

    Returns None if (a) response_type is not humor-enabled, (b) prompt is
    empty, (c) the frequency gate didn't fire (~70% of calls). Otherwise
    returns one of the templates from HUMOR_TEMPLATES[response_type].
    """
    if response_type not in HUMOR_ENABLED_TYPES:
        return None
    if not prompt:
        return None
    h = _stable_hash(prompt)
    if h % 100 >= HUMOR_FREQUENCY_PCT:
        return None
    templates = HUMOR_TEMPLATES.get(response_type, [])
    if not templates:
        return None
    return templates[h % len(templates)]
