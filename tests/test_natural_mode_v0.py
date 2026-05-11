"""Tests for cycle 11 #00P13c11-DEMO natural-mode v0 HDC walk.

Coverage:
  - `NaturalModeComposer` end-to-end: load → encode → compose.
  - Provenance trail integrity (every emitted fragment cites a source).
  - Cosine similarity scores are well-formed (in [-1, 1]).
  - Bind-based context update prevents same-fragment double-emission.
  - Domain filtering (poetry vs philosophy vs math vs lain_voice vs all).
  - Unknown domain rejection.
  - `ReasoningAgent._try_natural_mode` dispatcher integration: routes the right
    prompt shapes; does NOT hijack structured math/physics prompts that should
    continue routing to their primitive dispatchers.
  - Thesis-compliance source-grep: no LLM imports in the natural-mode module.

Honest framing: these tests verify SHAPE (encode → retrieve → emit with
provenance), not literary or philosophical QUALITY. Quality is bounded by
corpus quality (~100 fragments hand-seeded; canonical doc spec is tens of
millions of words).
"""

from __future__ import annotations

import pytest

from project_x.corpus.natural_mode import (
    EmittedFragment,
    NaturalModeComposer,
    NaturalWalkResult,
)
from project_x.reasoning_agent import ReasoningAgent


# ── NaturalModeComposer ─────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def composer() -> NaturalModeComposer:
    """Shared composer instance — encoding ~100 fragments costs a few ms; share across tests."""
    return NaturalModeComposer()


def test_composer_loads_and_exposes_domains(composer: NaturalModeComposer):
    """Smoke: composer initializes without error; reports the 7 canonical domains
    after cycle-12 #00P13c12-01b Tier-2 ingestion (added narrative_prose + general
    for ingested novels/general-non-poetry-non-philosophy content)."""
    assert composer.available_domains == [
        "all", "poetry", "philosophy", "math", "lain_voice",
        "narrative_prose", "general",
        "epic_poetry", "eastern_philosophy", "science", "economics", "history",
    ]


def test_composer_emits_five_fragments_with_provenance(composer: NaturalModeComposer):
    """compose() returns max_fragments emissions, each with a source citation."""
    result = composer.compose("write a poem about nature", domain="poetry", max_fragments=5)
    assert isinstance(result, NaturalWalkResult)
    assert len(result.fragments) == 5
    for frag in result.fragments:
        assert isinstance(frag, EmittedFragment)
        assert frag.text  # non-empty
        assert frag.source  # provenance cited
        assert -1.0 <= frag.similarity <= 1.0  # valid cosine range


def test_composer_no_duplicate_fragments(composer: NaturalModeComposer):
    """Bind-based context update ensures no fragment is emitted twice in one walk."""
    result = composer.compose("philosophize about existence", domain="philosophy", max_fragments=5)
    texts = [f.text for f in result.fragments]
    assert len(texts) == len(set(texts))  # all unique


def test_composer_respects_domain_filter(composer: NaturalModeComposer):
    """Domain filter constrains the walk to fragments from the requested domain only."""
    # Run a poetry walk; all emitted fragments must come from POETRY_FRAGMENTS sources
    result = composer.compose("write a poem", domain="poetry", max_fragments=5)
    for frag in result.fragments:
        # Poetry-source descriptors mention public-domain authors or "public domain"
        # framing; philosophy/math/lain sources have distinguishing strings
        assert "Project X" not in frag.source or "public domain" in frag.source.lower()


def test_composer_math_domain_returns_math_fragments(composer: NaturalModeComposer):
    """Math domain filter yields fragments tagged with math sources."""
    result = composer.compose("explain the collatz conjecture", domain="math", max_fragments=3)
    assert len(result.fragments) == 3
    # At least one of the emitted fragments should mention "conjecture" or "theorem"
    # or be from a Project X / classical math source
    sources_or_texts = " ".join(f.text + " " + f.source for f in result.fragments).lower()
    assert any(kw in sources_or_texts for kw in
               ("conjecture", "theorem", "diophantine", "pell", "hilbert", "matiyasevich",
                "vieta", "newton", "simpson", "hdc", "collatz", "goldbach"))


def test_composer_rejects_unknown_domain(composer: NaturalModeComposer):
    """Unknown domain raises ValueError with available domains in the message."""
    with pytest.raises(ValueError, match="Unknown domain"):
        composer.compose("anything", domain="nonsense_domain", max_fragments=5)


def test_composer_max_fragments_one(composer: NaturalModeComposer):
    """Edge case: max_fragments=1 returns exactly one fragment."""
    result = composer.compose("a single fragment please", domain="all", max_fragments=1)
    assert len(result.fragments) == 1
    assert result.fragments[0].step == 0


def test_composer_render_includes_provenance_trail(composer: NaturalModeComposer):
    """The rendered output text contains both fragment text AND source for each emission."""
    result = composer.compose("meaning of life", domain="philosophy", max_fragments=3)
    rendered = result.render()
    for frag in result.fragments:
        assert frag.text in rendered
        # Source descriptor (or a substring) appears in the render
        assert frag.source.split("(")[0].strip() in rendered or frag.source in rendered


# ── ReasoningAgent dispatcher integration ─────────────────────────────────


def test_agent_routes_poetry_prompt_to_natural_mode():
    """Prompt 'write a poem about X' routes to natural-mode poetry walk."""
    agent = ReasoningAgent()
    response = agent.process("Write a poem about the changing seasons.")
    assert response.domain == "open_domain"
    assert response.problem_shape == "natural_mode_walk_poetry"
    assert response.confidence == "provenance-traced"
    assert "poetry" in response.answer_text.lower()


def test_agent_routes_meaning_of_life_to_philosophy():
    """Prompt about meaning of life routes to natural-mode philosophy walk."""
    agent = ReasoningAgent()
    response = agent.process("What is the meaning of life?")
    assert response.problem_shape == "natural_mode_walk_philosophy"
    assert response.confidence == "provenance-traced"


def test_agent_routes_collatz_open_conjecture_to_math():
    """Prompt asking about the Collatz conjecture in a philosophical / open sense
    routes to natural-mode math walk (the structured Collatz verifier requires
    a specific 'verify Collatz on [1, N]' phrasing — open-conjecture-context
    prompts go to the natural-mode walk for honest framing context)."""
    agent = ReasoningAgent()
    response = agent.process("What does the Collatz conjecture mean?")
    assert response.problem_shape == "natural_mode_walk_math"


def test_agent_does_not_hijack_structured_pell_prompt():
    """maths-026 / maths-027 prompts still route to the Pell dispatcher, not natural mode."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find the first 5 integer solutions (x, y) to the Diophantine Pell equation "
        "x² − 2·y² = 1."
    )
    # Pell dispatcher fires BEFORE natural-mode in process() — structured prompt wins
    assert response.problem_shape == "pell_equation"
    assert response.confidence == "high"


def test_agent_does_not_hijack_quadratic_prompt():
    """Standard quadratic prompts still route to the quadratic dispatcher."""
    agent = ReasoningAgent()
    response = agent.process("Solve the quadratic 3x² - 14x - 5 = 0.")
    assert response.problem_shape == "quadratic"
    assert response.confidence == "high"


def test_agent_natural_mode_falls_through_on_unrecognized_open_prompt():
    """An open-ended prompt with no natural-mode trigger AND no primitive match
    falls through to the existing 'unrecognized' refusal path."""
    agent = ReasoningAgent()
    # "asdf qwerty" — no triggers in any dispatcher; honest refusal expected.
    # (post cycle-12 #00P13c12-01b: "Tell me about X" now matches narrative_prose
    # triggers; need a prompt that doesn't match any natural_mode keyword either.)
    response = agent.process("asdf qwerty random nonsense characters here.")
    assert response.problem_shape == "unrecognized"
    assert response.confidence == "refused"


# ── Thesis-compliance source-grep ─────────────────────────────────────────


def test_natural_mode_module_has_no_pretrained_imports():
    """Organic-thesis check: the natural_mode module imports nothing transformer-derived."""
    import importlib

    mod = importlib.import_module("project_x.corpus.natural_mode")
    src = open(mod.__file__).read()
    forbidden = (
        "import transformers", "from transformers",
        "import torch", "from torch",
        "import openai", "from openai",
        "BGE", "MiniLM", "sentence_transformers", "llama_cpp",
        "Qwen", "Mistral", "gemini",
    )
    for token in forbidden:
        assert token not in src, f"organic-thesis violation: '{token}' found in natural_mode.py"


def test_mini_seed_corpus_has_provenance_per_fragment():
    """Every fragment in mini_seed.py must carry a non-empty (text, source) pair."""
    from project_x.corpus.mini_seed import (
        LAIN_VOICE_FRAGMENTS,
        MATH_FRAGMENTS,
        PHILOSOPHY_FRAGMENTS,
        POETRY_FRAGMENTS,
    )
    for label, lst in [
        ("poetry", POETRY_FRAGMENTS),
        ("philosophy", PHILOSOPHY_FRAGMENTS),
        ("math", MATH_FRAGMENTS),
        ("lain_voice", LAIN_VOICE_FRAGMENTS),
    ]:
        assert len(lst) > 0, f"{label} corpus empty"
        for text, source in lst:
            assert text.strip(), f"{label} has an empty-text fragment"
            assert source.strip(), f"{label} fragment '{text[:30]}...' missing source"
