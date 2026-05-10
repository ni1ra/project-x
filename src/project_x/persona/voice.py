"""Voice markers + wrap_response for Project X Raphael persona.

Voice markers are the prefix tokens the AGENT (Project X Raphael) uses to
signal the response type to the reader. Mapped from compose_answer's
decision labels — the existing labels become the response_type tags here.

Humor selection lives in humor.py — voice.py is the structural wrapper.
"""

from __future__ import annotations

from project_x.persona.humor import HUMOR_ENABLED_TYPES, select_humor


# response_type -> prefix marker. Maps from compose_answer's decision labels
# plus a few extra tags for write_ack and tool paths (used at the AnswerPacket
# construction sites in process / run_tool).
VOICE_MARKERS: dict[str, str] = {
    # Retrieval shapes
    "factual_retrieval": "Notice.",       # single-evidence cited answer
    "multi_evidence": "Multi-evidence.",  # multiple sources, joint citation
    "retrieve_full_history": "Chronological evidence.",  # full subject chain
    # Null shapes — gravity-preserving, NO humor
    "absent": "Negative.",                # no matching memory above threshold
    "refusal": "Inquiry deferred.",        # decline with reason
    "error": "Anomaly detected.",          # surface failure mode honestly
    # Side-effect acknowledgments
    "write_ack": "Affirmative.",           # write_one succeeded
    "tool_ack": "Solution.",               # tool ran + result captured
}


def wrap_response(
    text: str,
    response_type: str,
    prompt: str = "",
) -> str:
    """Wrap `text` with the voice marker for `response_type`; optionally
    append a humor template (deterministic selection via stable hash of
    `prompt`).

    Args:
      text: the raw response text from compose_answer (or process / run_tool).
      response_type: tag from compose_answer's decision label, or one of the
        side-effect tags ("write_ack", "tool_ack"). Unknown tags pass through
        without wrapping.
      prompt: the original user prompt — used as the stable hash seed for
        humor selection. Empty prompt → no humor (deterministic miss).

    Returns:
      Wrapped string. Format: "<marker> <text>" or "<marker> <text> <humor>".
      Unknown response_type (no marker) returns text unchanged.
    """
    marker = VOICE_MARKERS.get(response_type, "")
    if not marker:
        return text
    wrapped = f"{marker} {text}"
    if response_type in HUMOR_ENABLED_TYPES and prompt:
        humor = select_humor(response_type, prompt)
        if humor:
            wrapped = f"{wrapped} {humor}"
    return wrapped
