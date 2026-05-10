"""Project X Raphael persona scaffolding — Phase 13 #00P13c1-02.

Voice markers + humor templates + in-character structural rubric for the
AGENT (distinct from Claude Code Raphael, the BUILDER — see MANIFESTO §
Identity discipline). Wraps `compose_answer` outputs in `semantic_memory_agent`.

Cycle 1 ships STRUCTURAL conformance only:
  - voice_consistent: correct prefix per response_type
  - humor_inserted: a template was applied (presence check)
  - in_character: no forbidden phrases ("I'm an AI assistant", "As Claude...")

QUALITATIVE judgment (does humor LAND? does voice CRINGE?) is for the
manual-grade harness (gpt-codex/grade_pipeline/) starting at cycle 1's
baseline-attempt and scaling at cycle 3+. M-PROJECTX-014 firewall: the
agent's structural rubric is NOT a self-grade of subjective quality —
it's a plumbing check that the wrapper fired correctly.
"""

from project_x.persona.voice import (
    VOICE_MARKERS,
    HUMOR_ENABLED_TYPES,
    wrap_response,
)
from project_x.persona.humor import (
    HUMOR_TEMPLATES,
    HUMOR_FREQUENCY_PCT,
    select_humor,
)
from project_x.persona.rubric import (
    FORBIDDEN_PHRASES,
    voice_consistent,
    humor_inserted,
    in_character,
    score_response,
)

__all__ = [
    "VOICE_MARKERS",
    "HUMOR_ENABLED_TYPES",
    "wrap_response",
    "HUMOR_TEMPLATES",
    "HUMOR_FREQUENCY_PCT",
    "select_humor",
    "FORBIDDEN_PHRASES",
    "voice_consistent",
    "humor_inserted",
    "in_character",
    "score_response",
]
