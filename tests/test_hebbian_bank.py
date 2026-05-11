"""Cycle-14 #08d — HebbianBank test suite + cold-start regression + synthetic-rating sweep.

Verifies the strict-strict-thesis contract for the substrate-wide
reward-driven co-occurrence bank shipped at cycle-14 #08a/b/c.

Test classes by intent:
  - Class A: hand-coded-math correctness (update / lookup / decay arithmetic).
  - Class B: cold-start regression (empty bank → cycle-13 baseline preserved).
  - Class C: synthetic-rating sweep (populated bank → retrieval shifts).
  - Class D: persistence round-trip + edge cases.
  - Class E: blend_score helper correctness.

M-PROJECTX-013 measure-don't-claim: every "the substrate can learn" claim
made in cycle-14's synthesis verdict (commit 9b1f8fd) gets a falsifiable
test here. The cold-start regression test (Class B) is the load-bearing
one — it proves cycle-14's strict-thesis ship does NOT accidentally
regress cycle-13 capability.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from project_x.hdc_infra import HebbianBank, blend_score
from project_x.hdc_infra.hebbian import (
    DEFAULT_LEARNING_RATE,
    RATING_MIDPOINT,
    _atom_from_fragment,
    _atom_from_prompt,
)


# =========================================================================
# Class A — hand-coded-math correctness
# =========================================================================


def test_atom_derivation_is_case_insensitive_on_token_match():
    """Same first-N tokens across casing differences → same prompt_atom.

    Honest framing: _atom_from_prompt is a first-N-tokens hash, NOT a
    paraphrase-aware semantic match. Same tokens (modulo case) → same atom;
    different leading tokens → different atom. Punctuation attaches to the
    token it follows, so "stones." and "stones" tokenize as different.
    Cycle-15+ could add a punctuation-strip pass for broader generalization.
    """
    atom1 = _atom_from_prompt("Write a poem about stones")
    atom2 = _atom_from_prompt("write A POEM about stones")  # case-only difference
    atom3 = _atom_from_prompt("Different question about clouds")
    assert atom1 == atom2  # case-insensitive
    assert atom1 != atom3  # genuine difference detected
    # Punctuation attaches to token → different atom (acknowledged limitation)
    atom_with_comma = _atom_from_prompt("Write a poem about stones, please")
    assert atom_with_comma != atom1  # 5th token "stones," != "stones"


def test_atom_derivation_fragment_is_stable_hash():
    """Same fragment text → same fragment_atom; different → different."""
    a = _atom_from_fragment("Whitman leaf of grass")
    b = _atom_from_fragment("Whitman leaf of grass")
    c = _atom_from_fragment("Shakespeare sonnet 18")
    assert a == b
    assert a != c
    assert len(a) == 16  # sha256[:16] truncation


def test_update_applies_correct_delta():
    """Hebbian delta = learning_rate * (rating - RATING_MIDPOINT)."""
    bank = HebbianBank(learning_rate=0.1)
    bank.update("test prompt", ["frag A"], rating=5.0)
    # delta = 0.1 * (5.0 - 3.0) = 0.2
    assert bank.lookup_for("test prompt", "frag A") == pytest.approx(0.2)


def test_update_accumulates_across_calls():
    """Repeated rating on same pair accumulates the delta."""
    bank = HebbianBank(learning_rate=0.1)
    bank.update("test", ["frag"], rating=5.0)  # +0.2
    bank.update("test", ["frag"], rating=5.0)  # +0.2
    bank.update("test", ["frag"], rating=5.0)  # +0.2
    assert bank.lookup_for("test", "frag") == pytest.approx(0.6)


def test_update_with_rating_below_midpoint_decays_pair():
    """Rating below RATING_MIDPOINT produces negative delta."""
    bank = HebbianBank(learning_rate=0.1)
    bank.update("test", ["frag"], rating=5.0)  # +0.2
    bank.update("test", ["frag"], rating=1.0)  # -0.2
    assert bank.lookup_for("test", "frag") == pytest.approx(0.0)


def test_update_at_midpoint_is_noop():
    """Rating = RATING_MIDPOINT (3.0) produces zero delta."""
    bank = HebbianBank(learning_rate=0.1)
    bank.update("test", ["frag"], rating=RATING_MIDPOINT)
    assert bank.lookup_for("test", "frag") == 0.0


def test_update_writes_each_fragment_independently():
    """Each fragment in the walk gets its own (prompt_atom, fragment_atom) entry."""
    bank = HebbianBank(learning_rate=0.1)
    bank.update("test", ["frag A", "frag B", "frag C"], rating=5.0)
    assert bank.entry_count() == 3
    for frag in ("frag A", "frag B", "frag C"):
        assert bank.lookup_for("test", frag) == pytest.approx(0.2)


def test_lookup_unseen_pair_returns_zero():
    """Cold-start contract: unseen (prompt_atom, fragment_atom) → 0.0."""
    bank = HebbianBank()
    assert bank.lookup_for("nothing", "nothing") == 0.0
    assert bank.lookup("a", "b") == 0.0
    # Even after some entries, unseen pairs still return 0.0
    bank.update("known", ["known frag"], rating=5.0)
    assert bank.lookup_for("unknown", "known frag") == 0.0


def test_decay_multiplies_and_prunes():
    """decay(rate=0.5) halves all entries; prunes those below decay_epsilon."""
    bank = HebbianBank(learning_rate=0.1, decay_epsilon=0.05)
    bank.update("p", ["f1"], rating=5.0)  # 0.2
    bank.update("p", ["f2"], rating=4.0)  # 0.1
    # decay by 50% → 0.1, 0.05 — second is right at floor; floor uses < not ≤
    pruned = bank.decay(rate=0.5)
    assert bank.lookup_for("p", "f1") == pytest.approx(0.1)
    # 0.1 * 0.5 = 0.05, which fails abs(value) < 0.05 → kept (floor is strict <)
    assert pruned == 0
    # Decay again → 0.05, 0.025 — second drops below floor
    pruned = bank.decay(rate=0.5)
    assert pruned == 1  # f2 entry pruned
    assert bank.lookup_for("p", "f2") == 0.0


# =========================================================================
# Class B — cold-start regression (load-bearing per synthesis §5)
# =========================================================================


def test_cold_start_bank_is_empty():
    """Fresh HebbianBank() has zero entries → blend collapses to identity."""
    bank = HebbianBank()
    assert bank.entry_count() == 0


def test_cold_start_blend_score_is_identity():
    """Empty bank → blend_score returns cosine unchanged. THE cycle-13-preserved test."""
    bank = HebbianBank()
    for cosine in (-1.0, -0.5, 0.0, 0.25, 0.5, 0.99, 1.0):
        assert blend_score(bank, cosine, "any", "any") == cosine


def test_blend_score_none_bank_is_identity():
    """blend_score(bank=None, ...) returns cosine unchanged — explicit opt-out."""
    for cosine in (-1.0, 0.0, 0.5, 1.0):
        assert blend_score(None, cosine, "any", "any") == cosine


def test_composer_default_is_cold_start():
    """NaturalModeComposer at default args + missing bank file → empty bank.

    The cold-start composer's first compose() call should match cycle-13's
    output bit-for-bit (alpha=0; blend identity; cosine retrieval unchanged).
    """
    from project_x.corpus.natural_mode import NaturalModeComposer

    # Pass a non-existent bank path so this test never sees on-disk state.
    composer = NaturalModeComposer(
        include_ingested=False,
        hebbian_bank_path=Path("/nonexistent/path/main.pkl"),
    )
    assert composer._hebbian_bank.entry_count() == 0


# =========================================================================
# Class C — synthetic-rating sweep (populated bank shifts retrieval)
# =========================================================================


def test_synthetic_rating_populates_bank_with_correct_entry_count():
    """20 synthetic ratings on 3-fragment walks → bank populates 60-ish entries."""
    bank = HebbianBank(learning_rate=0.1)
    for i in range(20):
        bank.update(f"prompt {i}", [f"frag_{i}_a", f"frag_{i}_b", f"frag_{i}_c"], rating=5.0)
    # 20 prompts × 3 fragments each = 60 unique (prompt_atom, fragment_atom) pairs
    assert bank.entry_count() == 60


def test_synthetic_rating_shifts_blend_for_rated_pair():
    """After rating, blend_score for the rated pair shifts measurably."""
    bank = HebbianBank(learning_rate=0.1)
    # Cold-start: blend is identity
    cosine_baseline = 0.3
    assert blend_score(bank, cosine_baseline, "p", "f") == cosine_baseline
    # Populate the bank with 100 entries to drive alpha to ~1.0
    for i in range(100):
        bank.update(f"prompt {i}", [f"frag {i}"], rating=5.0)
    # Now rate the target pair
    bank.update("p", ["f"], rating=5.0)
    # Bank has 101 entries → alpha=min(1.0, 1.01) = 1.0
    # blend = 0*cosine + 1.0*lookup(p, f) = 0.2
    assert blend_score(bank, cosine_baseline, "p", "f") == pytest.approx(0.2)


def test_synthetic_rating_alpha_grows_proportionally():
    """alpha = min(1.0, entry_count / 100); blend shifts smoothly with bank growth."""
    bank = HebbianBank(learning_rate=0.1)
    # Add 50 entries → alpha should be 0.5
    for i in range(50):
        bank.update(f"prompt {i}", [f"frag {i}"], rating=5.0)
    # Rate the target — adds entry 51, alpha=0.51
    bank.update("p", ["f"], rating=5.0)
    blended = blend_score(bank, 0.4, "p", "f")
    # alpha=0.51; cosine=0.4; lookup=0.2 → 0.49*0.4 + 0.51*0.2 = 0.196 + 0.102 = 0.298
    assert blended == pytest.approx(0.298, abs=0.01)


def test_misroute_correction_pattern():
    """Synthetic misroute-correction: low ratings on a (prompt, fragment) pair
    drive the blend score AWAY from that pair, simulating the F4/F5 fix.

    Demo-derived shape: P4 ("humour about heat death") misrouted to math-corpus
    fragments. If those misrouted walks accumulate reject ratings, the bank
    should decay the (humour-prompt-atom, math-fragment-atom) pairs.
    """
    bank = HebbianBank(learning_rate=0.1)
    # Reject the misroute 5 times
    for _ in range(5):
        bank.update(
            "be honest does the heat death of the universe",
            ["Aleph-null is the cardinality of the natural numbers"],
            rating=1.0,  # reject
        )
    # Each reject = -0.2 delta; 5 rejects = -1.0 accumulated
    score = bank.lookup_for(
        "be honest does the heat death of the universe",
        "Aleph-null is the cardinality of the natural numbers",
    )
    assert score == pytest.approx(-1.0)
    # The blend now NEGATIVELY weights this pair. With cosine 0.3 + alpha = 1.0
    # (saturate the bank) → final score = -1.0 dominates and the pair drops in ranking.
    # Bring bank to >=100 entries for alpha=1.0
    for i in range(100):
        bank.update(f"filler {i}", [f"filler frag {i}"], rating=5.0)
    blended = blend_score(
        bank,
        0.3,
        "be honest does the heat death of the universe",
        "Aleph-null is the cardinality of the natural numbers",
    )
    # alpha=1.0 → blended = 1.0 * -1.0 = -1.0; misroute drops below ANY cosine
    assert blended == pytest.approx(-1.0)


# =========================================================================
# Class D — persistence + boundaries
# =========================================================================


def test_persistence_round_trip(tmp_path: Path):
    """save() + load() preserves entry count + lookups."""
    bank = HebbianBank(learning_rate=0.15, decay_rate=0.02)
    bank.update("test prompt", ["frag A", "frag B"], rating=5.0)
    bank.update("other prompt", ["frag C"], rating=1.0)
    path = tmp_path / "bank.pkl"
    bank.save(path)
    loaded = HebbianBank.load(path)
    assert loaded.entry_count() == bank.entry_count()
    assert loaded.lookup_for("test prompt", "frag A") == bank.lookup_for("test prompt", "frag A")
    assert loaded.lookup_for("other prompt", "frag C") == bank.lookup_for("other prompt", "frag C")
    assert loaded.learning_rate == 0.15
    assert loaded.decay_rate == 0.02


def test_load_missing_file_returns_empty_bank():
    """HebbianBank.load() on a non-existent path → empty bank (cold-start safe)."""
    nonexistent = Path("/tmp/__definitely_does_not_exist__hebbian_test.pkl")
    if nonexistent.exists():
        nonexistent.unlink()
    bank = HebbianBank.load(nonexistent)
    assert bank.entry_count() == 0


def test_determinism_same_updates_same_state(tmp_path: Path):
    """Same prompt + fragments + rating sequence → bit-identical bank state."""
    bank1 = HebbianBank(learning_rate=0.1)
    bank2 = HebbianBank(learning_rate=0.1)
    sequence = [
        ("p1", ["f1", "f2"], 5.0),
        ("p2", ["f3"], 1.0),
        ("p1", ["f1"], 5.0),  # accumulates with first update
    ]
    for prompt, fragments, rating in sequence:
        bank1.update(prompt, fragments, rating)
        bank2.update(prompt, fragments, rating)
    assert bank1._bank == bank2._bank


def test_update_with_empty_fragments_is_noop():
    """update(prompt, fragments=[], rating=...) should not modify the bank."""
    bank = HebbianBank()
    bank.update("test", [], rating=5.0)
    assert bank.entry_count() == 0


def test_learning_rate_scales_delta_linearly():
    """Larger learning_rate → larger per-rating delta."""
    bank_low = HebbianBank(learning_rate=0.01)
    bank_high = HebbianBank(learning_rate=0.5)
    bank_low.update("p", ["f"], rating=5.0)  # delta = 0.02
    bank_high.update("p", ["f"], rating=5.0)  # delta = 1.0
    assert bank_low.lookup_for("p", "f") == pytest.approx(0.02)
    assert bank_high.lookup_for("p", "f") == pytest.approx(1.0)


def test_default_learning_rate_matches_constant():
    """DEFAULT_LEARNING_RATE constant matches the dataclass default."""
    bank = HebbianBank()
    assert bank.learning_rate == DEFAULT_LEARNING_RATE
