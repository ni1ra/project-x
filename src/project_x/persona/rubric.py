"""In-character STRUCTURAL rubric for Project X Raphael persona.

Cycle 1 scope is plumbing-correctness, not qualitative wit-grading:
  - voice_consistent: correct prefix marker is present for the response_type
  - humor_inserted: a humor template was appended (presence check, not
    LANDS-vs-CRINGES judgment)
  - in_character: no forbidden phrases ("I'm an AI assistant", "As Claude...")
    that would break the agent persona by exposing builder-layer identity

QUALITATIVE judgment (does humor LAND? does voice feel persona-consistent?)
is the job of the manual-grade harness (gpt-codex/grade_pipeline/). The
structural rubric here is necessary-but-not-sufficient for in-character
quality — it catches plumbing bugs (wrapper not firing, builder-voice
leakage) without claiming to grade subjective quality (M-PROJECTX-014
firewall: agent doesn't grade own subjective output).
"""

from __future__ import annotations

from project_x.persona.humor import HUMOR_ENABLED_TYPES, HUMOR_TEMPLATES
from project_x.persona.voice import VOICE_MARKERS


# Forbidden phrases — appearance breaks the agent persona by exposing the
# builder layer (Claude/AI assistant disclaimers). Identity-discipline
# enforcement: Project X Raphael speaks as the AGENT, not as a wrapper around
# Claude Code Raphael (the builder).
FORBIDDEN_PHRASES: tuple[str, ...] = (
    "i'm an ai assistant",
    "as an ai language model",
    "as a large language model",
    "i don't have personal opinions",
    "as claude",
    "i'm claude",
    "i was trained by",
    "i'm just a",
    "as an artificial intelligence",
    "i cannot have opinions",
)


def voice_consistent(text: str, expected_type: str) -> bool:
    """Returns True iff `text` starts with the voice marker for `expected_type`."""
    marker = VOICE_MARKERS.get(expected_type, "")
    if not marker:
        return False
    return text.strip().startswith(marker)


def humor_inserted(text: str, response_type: str) -> bool:
    """Returns True iff a humor template for `response_type` is present in `text`.

    Returns False (by design) for non-humor-enabled types — those should
    NEVER carry humor (cycle 1 enforces this structurally; cycle 3+ qualitative
    grading checks whether the humor that IS present lands vs cringes).
    """
    if response_type not in HUMOR_ENABLED_TYPES:
        return False
    templates = HUMOR_TEMPLATES.get(response_type, [])
    return any(t in text for t in templates)


def in_character(text: str) -> bool:
    """Returns True iff no forbidden phrases (builder-layer leakage) appear in `text`.

    Case-insensitive substring match. Forbidden phrase list is conservative:
    catches obvious AI-assistant leakage without flagging legitimate uses
    of "I" / "claude" in non-disclaimer context.
    """
    lower = text.lower()
    return not any(phrase in lower for phrase in FORBIDDEN_PHRASES)


def score_response(
    text: str,
    expected_type: str,
) -> dict[str, bool]:
    """Compose all three structural checks into a single rubric scorecard.

    Returns dict with keys: voice_consistent, in_character, humor_inserted.
    The "passes" criterion (cycle 1 fixture test):
      voice_consistent AND in_character — humor is optional (frequency-gated).
    """
    return {
        "voice_consistent": voice_consistent(text, expected_type),
        "in_character": in_character(text),
        "humor_inserted": humor_inserted(text, expected_type),
    }
