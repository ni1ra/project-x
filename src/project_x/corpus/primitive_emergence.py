"""v0 primitive emergence — cycle 11 #00P13c11-06.

Per the canonical synthesis doc Layer 5 (`a06a51a`): "Primitives are EXTRACTED
from corpus structure via unsupervised clustering, NOT hand-built. During
corpus ingestion, n-gram-shell hypervectors are clustered in the procedural
subspace; clusters with density above threshold become primitives."

v0 implementation choices (the lightest mechanism that produces a falsifiable
empirical signal):

  - **Trigrams as n-gram shells** — extract every consecutive 3-word sequence
    from each corpus fragment. Trigrams capture local syntactic + lexical
    structure (e.g., "the more X" / "is not the" / "between two cosmic"
    patterns); their cluster centroids should surface recurring grammatical
    skeletons across the corpus.
  - **CharNgramHashEncoder** on trigram text — same encoder the rest of the
    natural-mode walk uses. Deterministic; no learning; bipolar 10k-dim hvs.
  - **K-means with cosine distance** — k=15 default. Cosine on bipolar vectors
    via the existing `cosine_bipolar` helper. Centroid update = bundle of
    cluster members (signed-sum then sign).
  - **Density threshold** — clusters with >= 5 members are surfaced as
    "discovered primitives." Below threshold = noise rejection.

Honest framing per M-PROJECTX-013:
  - The empirical question is whether the discovered clusters represent
    MEANINGFUL structural patterns (e.g., "X is Y because Z") or merely
    FREQUENCY RANKINGS of common short phrases ("of the" / "in the"). v0
    surfaces the clusters; reading them tells which.
  - K-means initialization is randomized → different runs may produce
    different clusters. Reproducibility via fixed seed (default 42).
  - This is the canonical doc Layer 5 empirical test; bootstrap fallback
    ("hand-seed ~10-20 STRUCTURAL UNIVERSALS X-is-Y / X-causes-Y / X-but-Y
    / X-then-Y") remains a cycle-11+ option if clustering insufficient.

Organic-thesis compliance: no LLM, no learning. K-means is iterative-
assignment + centroid-update on hypervector cosine-similarity. Pure linear
algebra; deterministic given seed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from project_x.corpus.mini_seed import (
    LAIN_VOICE_FRAGMENTS,
    MATH_FRAGMENTS,
    PHILOSOPHY_FRAGMENTS,
    POETRY_FRAGMENTS,
)
from project_x.experiments.encoder import CharNgramHashEncoder, cosine_bipolar


@dataclass
class DiscoveredPrimitive:
    """One discovered cluster — a "primitive" emerged from unsupervised clustering."""

    cluster_id: int
    centroid_text: str  # the trigram closest to the cluster centroid
    member_count: int
    sample_members: list[str]  # top-N most-similar-to-centroid members (n=5 default)
    avg_intra_cluster_similarity: float  # cluster cohesion metric

    def render(self) -> str:
        lines = [f"PRIMITIVE #{self.cluster_id} (members={self.member_count}, "
                 f"avg intra-cluster sim={self.avg_intra_cluster_similarity:.3f}):"]
        lines.append(f"  CENTROID: '{self.centroid_text}'")
        lines.append(f"  SAMPLE MEMBERS:")
        for s in self.sample_members:
            lines.append(f"    - '{s}'")
        return "\n".join(lines)


def _tokenize_words(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenization (preserving alphanumeric)."""
    import re
    return [t for t in re.findall(r"[a-zA-Z0-9']+", text.lower())]


def _extract_trigrams(fragments: list[tuple[str, str]]) -> list[str]:
    """Extract every consecutive 3-word trigram from each fragment.

    Returns a deduplicated list of trigrams (string form, space-joined). Dedup
    prevents one frequently-repeated trigram from dominating the clustering.
    """
    trigrams: set[str] = set()
    for text, _source in fragments:
        words = _tokenize_words(text)
        for i in range(len(words) - 2):
            trigrams.add(" ".join(words[i : i + 3]))
    return sorted(trigrams)


def _bundle_hvs(hvs: np.ndarray, indices: list[int]) -> np.ndarray:
    """HDC bundle (signed-sum-then-sign) on a subset of bipolar hypervectors."""
    if not indices:
        # Degenerate: empty cluster → return zero vector (sign convention)
        return np.ones(hvs.shape[1], dtype=np.int8)
    summed = hvs[indices].astype(np.int32).sum(axis=0)
    signed = np.sign(summed).astype(np.int8)
    # sign(0) → 0; CharNgramHashEncoder convention treats 0 as +1
    return np.where(signed == 0, 1, signed).astype(np.int8)


def _kmeans_cosine_bipolar(
    hvs: np.ndarray,
    k: int,
    max_iters: int = 30,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """K-means clustering on bipolar hypervectors with cosine distance.

    Returns (cluster_assignments, centroids):
      - cluster_assignments: shape (n_samples,), int — cluster index per sample.
      - centroids: shape (k, D), int8 bipolar — cluster centroid per cluster.

    Algorithm: random init centroid indices → assign each sample to nearest
    centroid (by max cosine) → update centroids via HDC bundle of members →
    repeat until convergence (no reassignments) or max_iters.
    """
    n_samples, D = hvs.shape
    rng = np.random.default_rng(seed)
    # Initialize: pick k random distinct sample indices as initial centroids
    init_indices = rng.choice(n_samples, size=k, replace=False)
    centroids = hvs[init_indices].copy()
    assignments = np.zeros(n_samples, dtype=np.int32)

    for iteration in range(max_iters):
        new_assignments = np.zeros(n_samples, dtype=np.int32)
        for i in range(n_samples):
            best_k = 0
            best_sim = cosine_bipolar(hvs[i], centroids[0])
            for kk in range(1, k):
                sim = cosine_bipolar(hvs[i], centroids[kk])
                if sim > best_sim:
                    best_sim = sim
                    best_k = kk
            new_assignments[i] = best_k

        if iteration > 0 and np.array_equal(new_assignments, assignments):
            assignments = new_assignments
            break
        assignments = new_assignments

        # Update centroids via HDC bundle of cluster members
        for kk in range(k):
            members = np.where(assignments == kk)[0].tolist()
            centroids[kk] = _bundle_hvs(hvs, members)

    return assignments, centroids


@dataclass
class EmergenceResult:
    """Output of `discover_primitives()`."""

    n_trigrams: int
    k: int
    seed: int
    primitives: list[DiscoveredPrimitive]
    rejected_clusters: int  # below-threshold clusters not surfaced as primitives

    def render(self) -> str:
        lines = [
            f"PRIMITIVE EMERGENCE RESULT (k={self.k}, seed={self.seed}, "
            f"trigrams={self.n_trigrams}, primitives discovered={len(self.primitives)}, "
            f"rejected below density threshold={self.rejected_clusters}):",
            "",
        ]
        for p in self.primitives:
            lines.append(p.render())
            lines.append("")
        return "\n".join(lines)


def discover_primitives(
    fragments: list[tuple[str, str]] | None = None,
    k: int = 15,
    min_density: int = 5,
    seed: int = 42,
    samples_per_primitive: int = 5,
    max_iters: int = 30,
) -> EmergenceResult:
    """V0 primitive-emergence pipeline.

    Args:
        fragments: source corpus. Defaults to the combined mini_seed corpus
                   (poetry + philosophy + math + lain_voice = ~240 fragments).
        k: number of k-means clusters. Default 15.
        min_density: minimum member count for a cluster to surface as a
                     discovered primitive (else rejected as noise).
        seed: k-means initialization seed.
        samples_per_primitive: how many top-similar members to render per cluster.

    Honest framing per M-PROJECTX-013: this v0 surfaces clusters by frequency
    and within-cluster cohesion. Whether the clusters are MEANINGFUL structural
    patterns ("X is Y because Z") or merely frequency-ranked common phrases
    ("of the" / "is the") is the empirical question. Read the rendered output
    to find out.
    """
    if fragments is None:
        fragments = (
            POETRY_FRAGMENTS + PHILOSOPHY_FRAGMENTS
            + MATH_FRAGMENTS + LAIN_VOICE_FRAGMENTS
        )

    trigrams = _extract_trigrams(fragments)
    n_trigrams = len(trigrams)
    if n_trigrams < k * min_density:
        raise ValueError(
            f"corpus too small for k={k} and min_density={min_density}: only "
            f"{n_trigrams} distinct trigrams; need ≥ {k * min_density}."
        )

    encoder = CharNgramHashEncoder()
    trigram_hvs = encoder.encode(trigrams)

    assignments, centroids = _kmeans_cosine_bipolar(trigram_hvs, k=k, seed=seed, max_iters=max_iters)

    primitives: list[DiscoveredPrimitive] = []
    rejected_clusters = 0
    for cluster_id in range(k):
        member_indices = np.where(assignments == cluster_id)[0].tolist()
        if len(member_indices) < min_density:
            rejected_clusters += 1
            continue

        # Find the trigram closest to the centroid
        best_member_idx = -1
        best_sim = -2.0
        for mi in member_indices:
            sim = cosine_bipolar(trigram_hvs[mi], centroids[cluster_id])
            if sim > best_sim:
                best_sim = sim
                best_member_idx = mi
        centroid_text = trigrams[best_member_idx]

        # Compute intra-cluster avg similarity to centroid
        sims = [cosine_bipolar(trigram_hvs[mi], centroids[cluster_id])
                for mi in member_indices]
        avg_sim = sum(sims) / len(sims)

        # Top-N most-similar members (excluding the centroid itself if distinct)
        sorted_members = sorted(
            member_indices,
            key=lambda mi: -cosine_bipolar(trigram_hvs[mi], centroids[cluster_id]),
        )
        sample_members = [trigrams[mi] for mi in sorted_members[:samples_per_primitive]]

        primitives.append(DiscoveredPrimitive(
            cluster_id=cluster_id,
            centroid_text=centroid_text,
            member_count=len(member_indices),
            sample_members=sample_members,
            avg_intra_cluster_similarity=float(avg_sim),
        ))

    # Sort discovered primitives by member count descending for readable rendering
    primitives.sort(key=lambda p: -p.member_count)
    return EmergenceResult(
        n_trigrams=n_trigrams, k=k, seed=seed,
        primitives=primitives, rejected_clusters=rejected_clusters,
    )
