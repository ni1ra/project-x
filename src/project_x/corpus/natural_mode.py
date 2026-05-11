"""v0 natural-mode HDC walk composer — cycle 11 #00P13c11-DEMO.

Per the canonical synthesis doc (`docs/artifacts/cycle-10-semantics-architecture.md`)
Layer 4 Dual-mode composition § Natural mode: "HDC walk through fragment-space.
Each step retrieves the next fragment by HDC similarity to (current-state ⊗
intent ⊗ accumulated-context). Provenance trail per fragment (every emitted
phrase points back to corpus source)."

This is the v0 — a minimal-viable implementation proving the SHAPE of natural-
mode retrieval. The full canonical implementation (Tier-1 + Tier-2 corpus
ingestion + primitive emergence clustering + hormone modulation + K-rollout
iteration) is cycle-11 remaining work.

v0 capability:
  - Encode each fragment via `CharNgramHashEncoder` (no learning; deterministic
    char-n-gram → hash → multi-hot → random projection → sign).
  - Initialize context as the prompt's HDC encoding ⊗ optional intent vector.
  - For up to `max_fragments` steps: retrieve nearest-unseen fragment by cosine
    similarity to current context; emit (text, source, similarity); update
    context via HDC bind (elementwise bipolar multiplication).
  - Return a `NaturalWalkResult` with the fragment trail + provenance + a
    rendered string suitable for AGENT response.

Honest framing per M-PROJECTX-013:
  - Output quality is bounded by corpus quality (v0 corpus is ~100 fragments).
  - Fluency is fragmentary — fragments concatenate by similarity, not by
    grammatical composition; the v0 doesn't repair grammar at fragment seams.
  - Provenance is the honesty layer — every emitted fragment cites its source.
  - The agent is NOT generating novel text; it is retrieving and composing
    existing public-domain or project-authored material with cited provenance.

Organic-thesis compliance:
  - No LLM in the loop. CharNgramHashEncoder is deterministic hash + linear
    projection + sign. The composer is cosine-similarity retrieval + bipolar
    elementwise multiplication. Pure linear algebra; nothing trained on text.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pathlib import Path

from project_x.corpus.ingestion import INGESTION_MANIFEST, ingest_corpus_dir
from project_x.corpus.mini_seed import (
    LAIN_VOICE_FRAGMENTS,
    MATH_FRAGMENTS,
    PHILOSOPHY_FRAGMENTS,
    POETRY_FRAGMENTS,
)
from project_x.experiments.encoder import CharNgramHashEncoder, cosine_bipolar


# Cycle 12 #00P13c12-01b Tier-2 corpus ingestion — at-import-time, attempt to
# load fragments from `data/corpus_raw/` if it exists. Domain-tag assignment is
# based on source-tag substring matching: poetry-flavored authors → 'poetry',
# philosophy-flavored → 'philosophy', narrative-prose → 'narrative_prose' (new
# domain tag for novels), default → 'general'. Honest framing: this is a
# rough domain-tagging heuristic; cycle-12+ extension could pre-tag at ingestion
# time per the manifest.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_INGESTED_CORPUS_DIR = _REPO_ROOT / "data" / "corpus_raw"


def _classify_domain(source_tag: str) -> str:
    """Heuristic source-tag → domain mapping for Tier-2 ingested fragments."""
    s = source_tag.lower()
    if any(kw in s for kw in ("shakespeare", "whitman", "leaves of grass", "sonnets")):
        return "poetry"
    if any(kw in s for kw in ("aurelius", "lao tzu", "tao te ching", "republic", "plato",
                              "meditations")):
        return "philosophy"
    if any(kw in s for kw in ("austen", "dickens", "shelley", "frankenstein", "carroll",
                              "alice", "tale of two cities", "pride and prejudice", "walden",
                              "thoreau")):
        return "narrative_prose"
    return "general"


@dataclass
class EmittedFragment:
    """One step of a natural-mode walk."""

    text: str
    source: str
    similarity: float
    step: int  # 0-indexed position in the walk

    def render(self) -> str:
        """Human-readable single-fragment render with provenance."""
        return f'  "{self.text}"\n    — {self.source} (sim={self.similarity:.3f})'


@dataclass
class NaturalWalkResult:
    """Output of `NaturalModeComposer.compose()`."""

    prompt: str
    domain_filter: str  # "all" / "poetry" / "philosophy" / "math" / "lain_voice"
    fragments: list[EmittedFragment]
    note: str  # honest-framing prelude

    def render(self) -> str:
        """Render the full walk with provenance trail."""
        lines = [self.note, ""]
        lines.append(f'PROMPT: "{self.prompt}"')
        lines.append(f"DOMAIN: {self.domain_filter}")
        lines.append("")
        lines.append("WALK (provenance-traced fragment retrieval):")
        for frag in self.fragments:
            lines.append(f"Step {frag.step + 1}:")
            lines.append(frag.render())
            lines.append("")
        lines.append("Honest framing — the agent did NOT generate this text. Each fragment "
                     "was retrieved by HDC cosine similarity from a hand-seeded ~100-fragment "
                     "corpus of public-domain and project-authored material; provenance cited "
                     "per fragment. v0 capability: shape proven, fluency at fragment-seam "
                     "level (no grammar repair), corpus tiny (canonical doc spec is tens of "
                     "millions of words; this is ~100).")
        return "\n".join(lines)


class NaturalModeComposer:
    """v0 natural-mode HDC walk over a hand-seeded mini-corpus.

    Loads fragments at construction time; encodes them once via
    `CharNgramHashEncoder`. `compose(prompt, ...)` runs the walk per the
    canonical doc Layer 4 § Natural mode.

    Public API:
      - `__init__()`: load corpus + encode fragments.
      - `compose(prompt, domain="all", max_fragments=5)`: run the walk.
      - `available_domains` (property): list of corpus tags.
    """

    def __init__(self, include_ingested: bool = True) -> None:
        # Collect all fragments with a domain tag for filtering.
        # (domain_tag, fragment_text, source)
        self._tagged: list[tuple[str, str, str]] = []
        for text, source in POETRY_FRAGMENTS:
            self._tagged.append(("poetry", text, source))
        for text, source in PHILOSOPHY_FRAGMENTS:
            self._tagged.append(("philosophy", text, source))
        for text, source in MATH_FRAGMENTS:
            self._tagged.append(("math", text, source))
        for text, source in LAIN_VOICE_FRAGMENTS:
            self._tagged.append(("lain_voice", text, source))
        # Cycle 12 #00P13c12-01b — Tier-2 ingested corpus from
        # `data/corpus_raw/` if present. Heuristic source-tag → domain
        # mapping via `_classify_domain`. Falls back to hand-seeded-only if
        # the directory doesn't exist or include_ingested=False.
        if include_ingested and _INGESTED_CORPUS_DIR.exists():
            for text, source in ingest_corpus_dir(
                _INGESTED_CORPUS_DIR, manifest=INGESTION_MANIFEST
            ):
                domain = _classify_domain(source)
                self._tagged.append((domain, text, source))

        # Encode all fragments once via the deterministic char-n-gram encoder.
        # No training; encode is one matrix multiply per text.
        self._encoder = CharNgramHashEncoder()
        all_texts = [t[1] for t in self._tagged]
        self._fragment_hvs = self._encoder.encode(all_texts)  # (N, D) int8 bipolar

    @property
    def available_domains(self) -> list[str]:
        # 4 original mini_seed domains + 2 new from Tier-2 ingestion
        # (narrative_prose for novels; general fallback)
        return ["all", "poetry", "philosophy", "math", "lain_voice",
                "narrative_prose", "general"]

    def _filtered_indices(self, domain: str) -> list[int]:
        """Return indices into `self._tagged` matching the domain filter."""
        if domain == "all":
            return list(range(len(self._tagged)))
        return [i for i, t in enumerate(self._tagged) if t[0] == domain]

    def compose(
        self,
        prompt: str,
        domain: str = "all",
        max_fragments: int = 5,
    ) -> NaturalWalkResult:
        """Run the natural-mode HDC walk.

        Algorithm per canonical doc Layer 4 § Natural mode:
          1. Encode prompt → context hypervector.
          2. For step in 0..max_fragments−1:
               - Compute cosine similarity from context to all UNSEEN fragments
                 in the domain filter.
               - Emit the argmax (text, source, similarity).
               - Update context: bind (elementwise bipolar multiply) with the
                 emitted fragment's hypervector. The bind creates a new context
                 near-orthogonal to both prompt AND emitted fragment, so the
                 next retrieval is "different from both" rather than just
                 "similar to the prompt." This is the load-bearing reason for
                 bind vs bundle here.
          3. Return the trail.

        Args:
            prompt: free-text query.
            domain: "all" / "poetry" / "philosophy" / "math" / "lain_voice".
            max_fragments: cap on walk length (default 5; canonical doc spec
                           leaves this hormone-modulated, v0 hand-tunes it).
        """
        if domain not in self.available_domains:
            raise ValueError(
                f"Unknown domain '{domain}'; available: {self.available_domains}"
            )

        # Encode prompt
        context_hv: np.ndarray = self._encoder.encode([prompt])[0]

        candidate_indices = set(self._filtered_indices(domain))
        emitted: list[EmittedFragment] = []

        for step in range(max_fragments):
            if not candidate_indices:
                break
            # Score all remaining candidates by cosine similarity to current context.
            best_idx = -1
            best_sim = -2.0  # cosine is in [-1, 1]; init below any real value
            for idx in candidate_indices:
                sim = cosine_bipolar(context_hv, self._fragment_hvs[idx])
                if sim > best_sim:
                    best_sim = sim
                    best_idx = idx
            if best_idx < 0:
                break
            domain_tag, text, source = self._tagged[best_idx]
            emitted.append(EmittedFragment(
                text=text,
                source=source,
                similarity=float(best_sim),
                step=step,
            ))
            # Bind context with emitted fragment hypervector to produce a
            # context that's different from both prompt AND emitted fragment.
            # Elementwise multiplication on bipolar {-1, +1} is the HDC bind
            # operator (Plate HRR / Kanerva HDC); produces a vector near-
            # orthogonal to operands. Preserves bipolar type.
            context_hv = (context_hv * self._fragment_hvs[best_idx]).astype(np.int8)
            # Remove from candidates so the same fragment isn't re-emitted.
            candidate_indices.discard(best_idx)

        note = (
            f"NATURAL-MODE WALK v0 — {max_fragments}-step HDC retrieval over a hand-seeded "
            f"mini-corpus (~{len(self._tagged)} fragments). Domain filter: {domain}. "
            f"Per canonical synthesis doc Layer 4 § Natural mode (commit a06a51a)."
        )
        return NaturalWalkResult(
            prompt=prompt,
            domain_filter=domain,
            fragments=emitted,
            note=note,
        )
