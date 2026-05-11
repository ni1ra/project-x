"""HebbianBank — substrate-wide reward-driven co-occurrence storage.

Cycle-14 #08a per `docs/artifacts/cycle-14-priority-decision.md` §7. The first
write path from rated experience back into the substrate.

Strict-strict-thesis fit (lain 2026-05-11 binding): the bank is keyed by
atom-pairs (substrate-wide), NOT by primitive-id or per-tool embedding. The
update formula and the I/O plumbing are hand-coded LEARNING MACHINERY; the
bank's CONTENT (which atom-pairs co-occur, with what reward-weighted
strength) is learned from experience. No new hand-coded knowledge introduced.

Cold-start contract: empty bank, all `lookup()` calls return 0.0, retrieval
blend (cycle-14 #08c) collapses to static cosine, cycle-13 baseline 639/639
preserved exactly. Capability lift over cycle-13 is gated on audit-rating
cadence — synthesis §5 honest framing.

As ratings accumulate via the audit-rating wire (cycle-14 #08b), the bank
populates; the retrieval-blend's alpha grows from 0.0 toward 1.0 in
proportion to bank entry count; agent behavior shifts toward reward-shaped
retrieval. The shift is substrate-wide — every (prompt, fragment) pair the
bank has seen, not per-tool, not per-primitive.

Persistence is pickle in cycle-14 v0 (simplicity); cycle-15+ may move to npz
or sqlite for larger banks.
"""

from __future__ import annotations

import hashlib
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# A prompt-atom or fragment-atom is any hashable string identifier derived
# from substrate content. They live in the same name-space because the bank
# is substrate-wide — a (X, Y) pair is just a co-occurrence record, neither
# half carries privileged structure.
PromptAtom = str
FragmentAtom = str

# Rating midpoint for the [1..5] audit scale (cycle-12 audit UI). The signed
# reward signal is rating - RATING_MIDPOINT — positive for >3, negative
# below. Callers using a different scale should normalize before update().
RATING_MIDPOINT = 3.0

# Default learning rate. Calibration sweep is queued cycle-15+ over the
# accumulating rated audit log.
DEFAULT_LEARNING_RATE = 0.1

# Default decay rate (fraction subtracted per decay() call). Cycle-15+ work
# may tune per-domain.
DEFAULT_DECAY_RATE = 0.01

# Decay-prune floor — entries below this magnitude are removed on decay().
# Keeps the bank's footprint bounded.
DECAY_EPSILON = 1e-4

# Atom-derivation knob: how many leading tokens of the prompt are hashed into
# the prompt-atom. Larger = more-specific atom; smaller = more-shared atom
# across paraphrases. 10 tokens is a defensible cycle-14 v0 default — captures
# the prompt's opening "shape" without over-fitting to surface phrasing.
_PROMPT_ATOM_TOKEN_LIMIT = 10


def _atom_from_prompt(prompt: str, max_tokens: int = _PROMPT_ATOM_TOKEN_LIMIT) -> PromptAtom:
    """Derive a stable prompt-atom from the prompt string.

    Strategy: lowercase + whitespace-split + take first max_tokens + rejoin.
    Same prompt shape (modulo capitalization + trailing content) maps to the
    same atom; different prompt shapes get different atoms.

    This is intentionally coarser than the encoder's char-n-gram hash —
    the bank tracks PROMPT-SHAPE → FRAGMENT-COOCCURRENCE, not exact-prompt
    → exact-fragment lookup. Paraphrases of "Write a poem about X" all
    land on a similar atom; the bank's reward signal generalises across
    them.
    """
    tokens = prompt.lower().split()
    return " ".join(tokens[:max_tokens])


def _atom_from_fragment(fragment_text: str) -> FragmentAtom:
    """Derive a stable fragment-atom from the fragment's content.

    Strategy: sha256(content)[:16] for compactness. Collision probability at
    substrate scale (≤ 10⁵ fragments) is vanishingly small — 16 hex chars
    = 64 bits, birthday-paradox collision risk for 10⁵ entries is ~10⁻¹⁰.
    """
    return hashlib.sha256(fragment_text.encode("utf-8")).hexdigest()[:16]


@dataclass
class HebbianBank:
    """Substrate-wide reward-driven co-occurrence bank.

    Sparse dict from `(prompt_atom, fragment_atom)` pairs to cumulative
    reward-weighted scalars. The update formula is Hebbian: co-occurring
    atom-pairs strengthen on positive ratings, weaken on negative; unused
    pairs decay on decay() calls.

    The strict-strict-thesis discipline lives in the storage shape: keys
    are (atom, atom) pairs — no privileged "primitive-id" key-half, no
    per-tool partition. The bank doesn't know the difference between a
    math walk and a poetry walk; it just knows which atom-pairs were
    rewarded together.
    """

    learning_rate: float = DEFAULT_LEARNING_RATE
    decay_rate: float = DEFAULT_DECAY_RATE
    decay_epsilon: float = DECAY_EPSILON
    _bank: dict[tuple[PromptAtom, FragmentAtom], float] = field(default_factory=dict)

    def update(
        self,
        prompt: str,
        fragments: Iterable[str],
        rating: float,
    ) -> None:
        """Apply a reward-weighted Hebbian update on a rated walk.

        For each fragment retrieved during the walk, the `(prompt_atom,
        fragment_atom)` entry in the bank accumulates:

            delta = learning_rate * (rating - RATING_MIDPOINT)

        Positive ratings (above 3 on the 1-5 scale) strengthen the pair;
        negative ratings (below 3) weaken it. Rating == 3 is the no-op
        midpoint — neither reinforce nor decay.

        This IS Hebbian "atoms that fire together, wire together" — applied
        to substrate co-occurrence under reward shaping. No per-fragment
        weight (every fragment in the walk receives the same delta on
        cycle-14 v0); per-step credit-distribution coefficients would be
        the A3-style hand-coded structure the strict-strict thesis rejects.
        """
        prompt_atom = _atom_from_prompt(prompt)
        delta = self.learning_rate * (rating - RATING_MIDPOINT)
        for fragment_text in fragments:
            fragment_atom = _atom_from_fragment(fragment_text)
            key = (prompt_atom, fragment_atom)
            self._bank[key] = self._bank.get(key, 0.0) + delta

    def lookup(self, prompt_atom: PromptAtom, fragment_atom: FragmentAtom) -> float:
        """Return the bank's accumulated score for `(prompt_atom, fragment_atom)`.

        Returns 0.0 for unseen pairs — cold-start safe. The retrieval blend
        (cycle-14 #08c) computes `(1-α)·cosine + α·bank.lookup(...)`; with
        all lookups at 0.0 the blend collapses to identity and cycle-13
        baseline is preserved.
        """
        return self._bank.get((prompt_atom, fragment_atom), 0.0)

    def lookup_for(self, prompt: str, fragment_text: str) -> float:
        """Convenience wrapper — derive atoms from raw prompt + fragment strings.

        Equivalent to: `lookup(_atom_from_prompt(prompt), _atom_from_fragment(fragment_text))`.
        Used by the retrieval-blend path (#08c) where the caller has the
        raw strings on hand and doesn't want to pre-derive atoms.
        """
        return self.lookup(
            _atom_from_prompt(prompt),
            _atom_from_fragment(fragment_text),
        )

    def decay(self, rate: float | None = None) -> int:
        """Apply multiplicative decay to all entries; prune below `decay_epsilon`.

        `rate=None` uses `self.decay_rate`. Returns the number of entries pruned.

        Decay is what keeps the bank's footprint bounded over many cycles
        of rating activity. Unused atom-pairs fade toward zero and prune;
        frequently-reinforced pairs persist above the prune floor.
        """
        if rate is None:
            rate = self.decay_rate
        factor = 1.0 - rate
        to_prune: list[tuple[PromptAtom, FragmentAtom]] = []
        for key in list(self._bank.keys()):
            self._bank[key] *= factor
            if abs(self._bank[key]) < self.decay_epsilon:
                to_prune.append(key)
        for key in to_prune:
            del self._bank[key]
        return len(to_prune)

    def entry_count(self) -> int:
        """Return the number of `(prompt_atom, fragment_atom)` pairs in the bank.

        Used by the retrieval blend (#08c) to compute the blend alpha:
        `alpha = min(1.0, entry_count / 100)`. Cold-start (entry_count=0)
        gives alpha=0; the blend collapses to static cosine.
        """
        return len(self._bank)

    def save(self, path: str | Path) -> None:
        """Persist the bank to disk via pickle.

        Cycle-14 v0 uses pickle for simplicity (single file, atomic write
        via tempfile rename is overkill until we have concurrent writers).
        Cycle-15+ may move to npz or sqlite for larger banks.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "learning_rate": self.learning_rate,
                    "decay_rate": self.decay_rate,
                    "decay_epsilon": self.decay_epsilon,
                    "bank": self._bank,
                },
                f,
            )

    @classmethod
    def load(cls, path: str | Path) -> "HebbianBank":
        """Load a bank from disk. Returns an empty bank if `path` does not exist.

        Cold-start agents at fresh-deployment time hit the missing-path
        branch and get an empty bank — exactly the regression-preserving
        behavior the cold-start contract requires.
        """
        path = Path(path)
        if not path.exists():
            return cls()
        with open(path, "rb") as f:
            data = pickle.load(f)
        bank = cls(
            learning_rate=data["learning_rate"],
            decay_rate=data["decay_rate"],
            decay_epsilon=data["decay_epsilon"],
        )
        bank._bank = data["bank"]
        return bank
