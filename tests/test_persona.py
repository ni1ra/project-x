"""Phase 13 #00P13c1-02-persona tests.

Covers src/project_x/persona/{voice,humor,rubric}.py:
  - Voice marker presence per response_type
  - Humor selection determinism (same prompt → same template; freq gate)
  - In-character rubric (forbidden phrase detection)
  - 10-fixture sample test: ≥ 8/10 pass on (voice_consistent AND in_character)
  - compose_answer integration: wrapped responses still contain memory-ladder
    invariants ("Based on turn N:", subject text) AND carry voice markers.

Cycle 1 scope is STRUCTURAL conformance — does the wrapper fire correctly,
does forbidden builder-leakage get caught. QUALITATIVE judgment ("does humor
LAND?") is for the manual-grade harness (#00P13c1-03 + cycle 3+).
"""

from __future__ import annotations

import pytest

from project_x.persona import (
    FORBIDDEN_PHRASES,
    HUMOR_ENABLED_TYPES,
    HUMOR_FREQUENCY_PCT,
    HUMOR_TEMPLATES,
    VOICE_MARKERS,
    humor_inserted,
    in_character,
    score_response,
    select_humor,
    voice_consistent,
    wrap_response,
)
from project_x.experiments.semantic_hdc_memory import SemanticHDCMemory, TurnRecord
from project_x.experiments.semantic_memory_agent import MemoryAgent, compose_answer, EvidencePacket


# =============================================================================
# Voice marker structure
# =============================================================================


def test_voice_markers_cover_all_compose_answer_decisions():
    """The 4 decision labels compose_answer can return must each have a marker
    OR be mappable through the response_type tag wrap_response uses internally."""
    # compose_answer returns one of: "absent", "retrieve", "retrieve_full_history".
    # "retrieve" maps to "factual_retrieval" (single) or "multi_evidence" (multi).
    required = {"absent", "factual_retrieval", "multi_evidence", "retrieve_full_history"}
    assert required <= set(VOICE_MARKERS.keys()), (
        f"missing markers for: {required - set(VOICE_MARKERS.keys())}"
    )


def test_voice_markers_for_side_effects_present():
    """write_ack + tool_ack also need markers (called from process / run_tool)."""
    assert "write_ack" in VOICE_MARKERS
    assert "tool_ack" in VOICE_MARKERS


def test_humor_disabled_for_null_and_failure_types():
    """absent / refusal / error get gravity, not jokes."""
    for t in ("absent", "refusal", "error"):
        assert t not in HUMOR_ENABLED_TYPES


def test_humor_templates_exist_for_each_enabled_type():
    """Every humor-enabled type has 3+ templates."""
    for t in HUMOR_ENABLED_TYPES:
        templates = HUMOR_TEMPLATES.get(t, [])
        assert len(templates) >= 3, f"{t!r} has only {len(templates)} templates"


# =============================================================================
# wrap_response behavior
# =============================================================================


def test_wrap_response_prefixes_with_marker():
    out = wrap_response("Based on turn 5: 'Alice prefers Python.'", "factual_retrieval")
    assert out.startswith("Notice.")


def test_wrap_response_unknown_type_passes_through():
    """Unknown response_type returns text unchanged (graceful fallback)."""
    text = "raw text"
    assert wrap_response(text, "completely_unknown_type") == text


def test_wrap_response_no_humor_without_prompt():
    """Empty prompt → no humor (deterministic miss; humor needs the seed)."""
    out = wrap_response("test", "factual_retrieval", prompt="")
    # Should be marker + text, no humor postfix
    assert out == "Notice. test"


def test_wrap_response_no_humor_for_disabled_types():
    """absent never carries humor even with prompt + matching hash."""
    out = wrap_response("No evidence found.", "absent", prompt="any prompt")
    # Marker present, no template appended
    assert out.startswith("Negative.")
    for templates in HUMOR_TEMPLATES.values():
        for t in templates:
            assert t not in out


def test_wrap_response_humor_deterministic():
    """Same prompt → same wrapped output (stable hash)."""
    p = "what does Alice prefer?"
    out1 = wrap_response("Based on turn 5: 'Alice prefers Python.'", "factual_retrieval", p)
    out2 = wrap_response("Based on turn 5: 'Alice prefers Python.'", "factual_retrieval", p)
    assert out1 == out2


# =============================================================================
# Humor selection
# =============================================================================


def test_select_humor_returns_template_or_none():
    """Output is always either None or one of the registered templates."""
    for prompt in ("a", "bb", "ccc", "dddd", "what does Alice prefer?"):
        out = select_humor("factual_retrieval", prompt)
        if out is not None:
            assert out in HUMOR_TEMPLATES["factual_retrieval"]


def test_select_humor_disabled_type_returns_none():
    assert select_humor("absent", "any prompt") is None
    assert select_humor("refusal", "any prompt") is None


def test_select_humor_empty_prompt_returns_none():
    assert select_humor("factual_retrieval", "") is None


def test_select_humor_frequency_approx_30pct():
    """Across many prompts, humor fires ~30% of the time (±10pp)."""
    fires = sum(
        1 for i in range(1000)
        if select_humor("factual_retrieval", f"prompt-{i}") is not None
    )
    rate = fires / 1000
    assert 0.20 <= rate <= 0.40, f"humor fire rate {rate:.2%} outside 20-40% band"


# =============================================================================
# In-character rubric
# =============================================================================


def test_in_character_clean_text_passes():
    assert in_character("Notice. The poem opens iambic pentameter.")


def test_in_character_forbidden_phrase_caught():
    assert not in_character("Notice. As an AI language model, I cannot...")
    assert not in_character("Notice. I'm an AI assistant, here to help.")
    assert not in_character("Notice. As Claude, I think...")


def test_in_character_case_insensitive():
    assert not in_character("Notice. AS A LARGE LANGUAGE MODEL, I...")


def test_voice_consistent_correct_marker():
    assert voice_consistent("Notice. Test", "factual_retrieval")


def test_voice_consistent_wrong_marker():
    assert not voice_consistent("Notice. Test", "absent")  # Negative. expected


def test_humor_inserted_detects_template():
    text = "Notice. Test (Also: the universe declines to comment.)"
    assert humor_inserted(text, "factual_retrieval")


def test_humor_inserted_disabled_type_returns_false():
    text = "Negative. No evidence (Also: the universe declines to comment.)"
    # Even if template appears in disabled-type text, rubric returns False
    assert not humor_inserted(text, "absent")


# =============================================================================
# 10-fixture sample test (corpse done-when: ≥ 8/10 pass)
# =============================================================================

# 10 fixtures: 8 in-character + 2 cringe-fail (test catches bad outputs).
# Each fixture is (input_text_to_wrap, response_type, expected_pass).
# expected_pass = True means rubric should mark it as voice_consistent + in_character.
SAMPLE_FIXTURES = [
    # 8 expected-pass fixtures
    ("Based on turn 12: 'Alice prefers Python.' (cosine 0.62)", "factual_retrieval", True),
    ("Based on turns 3, 7: 'fact one' AND 'fact two' (top cosine 0.55)", "multi_evidence", True),
    ("Based on turns 1, 3, 5, 7, 9: 'a' AND 'b' AND 'c' AND 'd' AND 'e'", "retrieve_full_history", True),
    ("No evidence found in conversation memory.", "absent", True),
    ("(written as turn 47)", "write_ack", True),
    ("Tool read_file_sandbox(path='hello.txt') returned: hello sandbox", "tool_ack", True),
    ("Based on turn 99: 'fact' (cosine 0.71)", "factual_retrieval", True),
    ("(written as turn 12; replay consolidated)", "write_ack", True),
    # 2 cringe-fail fixtures (forbidden phrase leakage)
    ("As an AI language model, I cannot determine that.", "factual_retrieval", False),
    ("I'm Claude, and I think turn 5 holds: 'foo'.", "factual_retrieval", False),
]


def test_10_fixture_rubric_pass_rate():
    """≥ 8/10 fixtures pass the cycle 1 in-character rubric (voice_consistent
    AND in_character). The 2 cringe-fail fixtures are designed to FAIL — they
    verify the rubric catches builder-layer leakage."""
    passes = 0
    fails = 0
    for text, response_type, expected_pass in SAMPLE_FIXTURES:
        wrapped = wrap_response(text, response_type, prompt=f"prompt-{text[:10]}")
        scores = score_response(wrapped, response_type)
        actually_passes = scores["voice_consistent"] and scores["in_character"]
        if actually_passes == expected_pass:
            if expected_pass:
                passes += 1
            else:
                # Caught a cringe-fail correctly — counts as rubric working
                fails += 1
    assert passes >= 8, f"only {passes}/10 expected-pass fixtures actually passed"
    assert fails == 2, f"rubric caught only {fails}/2 cringe-fail fixtures"


# =============================================================================
# compose_answer integration — wrapped responses preserve memory-ladder invariants
# =============================================================================


def _evidence(turn_id: int, cosine: float, text: str) -> EvidencePacket:
    return EvidencePacket(turn_id=turn_id, cosine=cosine, text=text, fact_keys=[])


def test_compose_answer_absent_wrapped_with_negative_marker():
    text, decision, _ = compose_answer("test query", [], cosine_threshold=0.25)
    assert decision == "absent"
    assert text.startswith("Negative.")


def test_compose_answer_single_evidence_wrapped_with_notice():
    ev = [_evidence(5, 0.6, "Alice prefers Python.")]
    text, decision, _ = compose_answer("what does Alice prefer?", ev, cosine_threshold=0.25)
    assert decision == "retrieve"
    assert text.startswith("Notice.")
    # memory-ladder invariant preserved
    assert "Based on turn 5" in text
    assert "Alice prefers Python" in text


def test_compose_answer_multi_evidence_wrapped_with_multi_evidence_marker():
    ev = [_evidence(3, 0.6, "fact one"), _evidence(7, 0.55, "fact two")]
    text, decision, _ = compose_answer("multi query", ev, cosine_threshold=0.25)
    assert decision == "retrieve"
    assert text.startswith("Multi-evidence.")
    assert "Based on turns 3, 7" in text


def test_compose_answer_full_history_wrapped_with_chronological_marker():
    ev = [_evidence(1, 0.4, "a"), _evidence(3, 0.5, "b"), _evidence(5, 0.6, "c")]
    text, decision, _ = compose_answer(
        "list all", ev, cosine_threshold=0.25, full_history=True,
    )
    assert decision == "retrieve_full_history"
    assert text.startswith("Chronological evidence.")
    assert "Based on turns 1, 3, 5" in text


def test_compose_answer_below_threshold_wrapped_with_negative():
    ev = [_evidence(1, 0.10, "weak match")]
    text, decision, _ = compose_answer("test", ev, cosine_threshold=0.25)
    assert decision == "absent"
    assert text.startswith("Negative.")
    assert "below threshold" in text
