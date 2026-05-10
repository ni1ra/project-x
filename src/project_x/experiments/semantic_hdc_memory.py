"""
semantic_hdc_memory.py — Phase 9 Layer 3.

Wraps the cycle-4 ensemble encoder in a proper memory class with:
  - write(turn_id, text, fact_keys=[], **metadata) — encode + store
  - retrieve(query, k=5) — encoded query → top-k turn_ids by ensemble cosine
  - retrieve_with_baselines(query, k=5) — same + keyword overlap baseline
  - retrieve_multi_hop(query, k=5) — decompose query on "and"/"both"/"or",
                                     run sub-retrievals, union top-k
  - persist / load to/from JSONL (provenance store)

Uses EnsembleMemory pattern: holds TWO encoders (floor + Hebbian) + alpha,
combines their cosine matrices at retrieve time per cycle-4 winning design
(α=0.5 → paraphrase 51.7%, exact 62%, contradiction 30%).

Keyword baseline: simple Jaccard token overlap. Required by lain
(A_TO_Z_PLAN §3 acceptance: HDC must beat keyword baseline on paraphrase).

Author: Raphael
Phase: 9 — semantic_hdc_memory_agent (Cycle 5, Layer 3 — organic stack)
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from project_x.experiments.encoder import (
    CharNgramHashEncoder,
    cosine_matrix_bipolar,
)
from project_x.experiments.random_index_hebbian import (
    RandomIndexHebbianEncoder,
    tokenize,
)
from project_x.experiments.hdc_substrate import bind, superpose


# =============================================================================
# Phase 10 P3 — subject extraction helpers (no corpus-coupled hardcoded names)
# =============================================================================

# fact_keys conventional kinds that name a subject in the value half.
# Phase 10 P3 (#00c-1) baseline: pref/dec/file. Phase 10 #00g adds 'tool' so
# tool-written turns get clean fact_graph keying for retrieval after run_tool.
_FACT_KEY_KINDS = frozenset({"pref", "dec", "file", "tool"})

# Capitalized tokens that are usually not subjects — sentence-start words +
# pronouns + auxiliaries. Subject extraction strips these. This list is
# domain-neutral; do NOT add corpus-specific names here.
_CAPITALIZED_STOPWORDS = frozenset({
    "What", "Where", "Who", "Why", "When", "How", "Which",
    "The", "A", "An", "This", "That", "These", "Those",
    "I", "We", "You", "He", "She", "They", "It",
    "Is", "Are", "Was", "Were", "Be", "Been", "Being",
    "Do", "Does", "Did", "Have", "Has", "Had",
    "Can", "Could", "Will", "Would", "Should", "May", "Might",
    "Yes", "No", "OK", "Sure", "Actually", "Update",
})

_CAPITALIZED_TOKEN = re.compile(r"\b([A-Z][A-Za-z0-9_-]*)\b")


def _subjects_from_fact_keys(fact_keys: list[str]) -> list[str]:
    """Parse fact_keys like 'pref:Alice' / 'dec:subsystem-317' / 'file:controller'."""
    out = []
    for fk in fact_keys:
        if ":" in fk:
            kind, val = fk.split(":", 1)
            if kind in _FACT_KEY_KINDS:
                out.append(val)
    return out


def _subjects_from_text(text: str) -> list[str]:
    """Subject extraction from assertion-shaped text. First non-stopword
    capitalized token only.

    Phase 11 P2 (#00P11b) — was: ALL capitalized non-stopword tokens. The
    bug: for an assertion like "Alice now prefers Rust.", the OLD logic
    returned ["Alice", "Rust"] and `_extract_subjects_for_record` populated
    `fact_graph["Rust"]` with Alice's turn. A later structural-retrieval
    query like "Who uses Rust?" would then extract "Rust" as a known subject
    and surface Alice's turn at top-1 — wrong attribution. The FIX is
    first-token-only: in a Phase 9-shape declarative assertion, the subject
    is the sentence-initial proper noun; subsequent capitalized tokens are
    objects, tools, or values — NOT subjects. This is a record-side
    extraction fallback that only fires when `fact_keys` is empty (the
    `agent.process` write path is the canonical caller). Query-side
    extraction uses fact_graph-key substring match (`_extract_query_subjects`)
    and is unaffected; multi-subject queries like "What do Alice and Bob
    prefer?" still match BOTH Alice and Bob via that path.
    """
    for m in _CAPITALIZED_TOKEN.findall(text):
        if m not in _CAPITALIZED_STOPWORDS:
            return [m]
    return []


# =============================================================================
# Keyword baseline — simple Jaccard token overlap retrieval
# =============================================================================


class KeywordBaseline:
    """Lexical overlap retrieval: Jaccard token similarity. Honest baseline
    for HDC ensemble per A_TO_Z_PLAN §3 (HDC must beat keyword baseline on
    semantic paraphrase queries to justify the ML-free organic encoder)."""

    def __init__(self):
        self._turn_token_sets: list[set[str]] = []

    def fit(self, turn_texts: list[str]) -> None:
        self._turn_token_sets = [set(tokenize(t)) for t in turn_texts]

    def retrieve_top_k(self, query: str, k: int = 5) -> list[tuple[int, float]]:
        q_set = set(tokenize(query))
        if not q_set:
            return []
        sims = []
        for ti, tset in enumerate(self._turn_token_sets):
            if not tset:
                sims.append((ti, 0.0))
                continue
            inter = len(q_set & tset)
            union = len(q_set | tset)
            sims.append((ti, inter / union if union > 0 else 0.0))
        sims.sort(key=lambda iv: -iv[1])
        return sims[:k]


# =============================================================================
# SemanticHDCMemory — ensemble + multi-hop decomposition
# =============================================================================


@dataclass
class TurnRecord:
    turn_id: int
    text: str
    fact_keys: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class SemanticHDCMemory:
    """Memory built on the cycle-4 ensemble (CharNgram floor + RIHV-with-neg-sampling).

    Holds two encoders + alpha. Both encoders see all written texts; at retrieve
    time, cosine matrices are blended `alpha * floor + (1-alpha) * hebbian`.
    α=0.5 is the cycle-4 winner.
    """

    D: int = 10000
    alpha: float = 0.5                # 0=pure hebbian, 1=pure floor; 0.5 = cycle-4 winner
    negative_samples: int = 5
    seed: int = 1337

    # Internal:
    _floor: CharNgramHashEncoder = field(init=False, repr=False)
    _hebbian: RandomIndexHebbianEncoder = field(init=False, repr=False)
    _baseline: KeywordBaseline = field(init=False, repr=False)
    _records: list[TurnRecord] = field(default_factory=list, init=False, repr=False)
    _turn_texts: list[str] = field(default_factory=list, init=False, repr=False)
    _floor_turn_vecs: np.ndarray | None = field(default=None, init=False, repr=False)
    _heb_turn_vecs: np.ndarray | None = field(default=None, init=False, repr=False)
    _is_built: bool = field(default=False, init=False, repr=False)
    # Phase 10 P3: fact graph (subject -> turn_ids, recency-sorted descending).
    _fact_graph: dict[str, list[int]] = field(default_factory=dict, init=False, repr=False)
    # Phase 10 P3 (#00c-2): HDC role-filler binding bank.
    # `_subject_atoms[s]` = floor-encoded bipolar vec for subject string `s`.
    # `_subject_bound_accum[s]` = int32 accumulator (sum of bind(turn_vec, atom_s)
    #     across all turns where subject s appeared) — kept uncleaned so additional
    #     turns can extend the superposition without sign-clip drift.
    # `_subject_bound_bank[s]` = sign-cleaned bipolar superposition of the accum;
    #     unbinding it with atom_s recovers the (noisy) sum of those turn vecs —
    #     the Plate-style "what was said about subject s" pseudo-vec.
    _subject_atoms: dict[str, np.ndarray] = field(default_factory=dict, init=False, repr=False)
    _subject_bound_accum: dict[str, np.ndarray] = field(default_factory=dict, init=False, repr=False)
    _subject_bound_bank: dict[str, np.ndarray] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._floor = CharNgramHashEncoder(D=self.D, feature_dim=4096, n=3, seed=self.seed)
        self._hebbian = RandomIndexHebbianEncoder(
            D=self.D, n_active=10, window=3, subsample_threshold=1e-3,
            negative_samples=self.negative_samples, seed=self.seed,
        )
        self._baseline = KeywordBaseline()

    # --- Building memory --------------------------------------------------

    def write_batch(
        self, records: list[TurnRecord]
    ) -> None:
        """Bulk-write all turns. Single fit() over the corpus, then encode."""
        self._records = list(records)
        self._turn_texts = [r.text for r in records]
        # Fit Hebbian (needs full corpus for vocab + co-occurrence)
        self._hebbian.fit(self._turn_texts)
        # Fit baseline
        self._baseline.fit(self._turn_texts)
        # Encode all turns once
        self._floor_turn_vecs = self._floor.encode(self._turn_texts)
        self._heb_turn_vecs = self._hebbian.encode(self._turn_texts)
        # Phase 10 P3: build fact graph (subject -> turn_ids, recency-sorted)
        self._fact_graph = self._build_fact_graph(self._records)
        # Phase 10 P3 (#00c-2): build HDC role-filler binding bank.
        self._build_binding_bank(self._records)
        self._is_built = True

    def _extract_subjects_for_record(self, r: TurnRecord) -> list[str]:
        """fact_keys preferred (project-specific reliable signal); capitalized-token fallback."""
        from_keys = _subjects_from_fact_keys(r.fact_keys)
        if from_keys:
            return from_keys
        return _subjects_from_text(r.text)

    def _build_fact_graph(self, records: list[TurnRecord]) -> dict[str, list[int]]:
        graph: dict[str, list[int]] = {}
        for r in records:
            for s in self._extract_subjects_for_record(r):
                graph.setdefault(s, []).append(r.turn_id)
        # Recency-sort each subject's turn_ids descending so [0] is the most-recent turn.
        for s in graph:
            graph[s].sort(reverse=True)
        return graph

    # --- Phase 10 P3 (#00c-2): HDC role-filler binding -------------------

    def _atom_for(self, subject: str) -> np.ndarray:
        """Return (and lazily build) the floor-encoded bipolar atom for `subject`.

        Atoms are stable across calls — same subject string always produces the
        same atom — because CharNgramHashEncoder is deterministic.
        """
        if subject not in self._subject_atoms:
            self._subject_atoms[subject] = self._floor.encode([subject])[0]
        return self._subject_atoms[subject]

    def _add_to_binding_bank(self, subject: str, turn_vec: np.ndarray) -> None:
        """Add `bind(turn_vec, atom_subject)` to the accumulator, then refresh
        the sign-cleaned bipolar bank for `subject`. Idempotent across multiple
        calls for the same (subject, turn_vec) pair only by accident — callers
        are responsible for not double-adding the same turn."""
        atom = self._atom_for(subject)
        bound = bind(turn_vec, atom).astype(np.int32)
        if subject not in self._subject_bound_accum:
            self._subject_bound_accum[subject] = bound.copy()
        else:
            self._subject_bound_accum[subject] += bound
        accum = self._subject_bound_accum[subject]
        # Sign cleanup: 0 → +1 by HDC convention (rare at high D).
        self._subject_bound_bank[subject] = np.where(
            accum == 0, 1, np.sign(accum)
        ).astype(np.int8)

    def _build_binding_bank(self, records: list[TurnRecord]) -> None:
        """Populate atoms + bound bank for all records in batch. Uses
        `_floor_turn_vecs` rows as the turn-side bind operand. Phase 9's
        floor encoder gives a stable bipolar vec per turn text; binding it
        with the subject atom encodes the role-filler triple structurally."""
        for r in records:
            tv = self._floor_turn_vecs[r.turn_id]
            for s in self._extract_subjects_for_record(r):
                self._add_to_binding_bank(s, tv)

    def unbind_subject_pseudo_vec(self, subject: str) -> np.ndarray | None:
        """Plate-style structural retrieval — unbind subject atom from the per-
        subject bound bank. Returns a (noisy) approximation of the superposition
        of all turn vecs that mentioned `subject`. None if the subject has no
        bound bank (never seen). Cosine-comparing this pseudo-vec to candidate
        turn vecs ranks turns by "how much the subject said about each."
        """
        if subject not in self._subject_bound_bank:
            return None
        return bind(self._subject_bound_bank[subject], self._atom_for(subject))

    # --- Retrieval --------------------------------------------------------

    def _ensemble_cosines(self, query: str) -> np.ndarray:
        if not self._is_built:
            raise RuntimeError("call write_batch(...) before retrieve(...)")
        f_q = self._floor.encode([query])
        h_q = self._hebbian.encode([query])
        f_cos = cosine_matrix_bipolar(f_q, self._floor_turn_vecs)[0]
        h_cos = cosine_matrix_bipolar(h_q, self._heb_turn_vecs)[0]
        return self.alpha * f_cos + (1.0 - self.alpha) * h_cos

    def _per_encoder_cosines(self, query: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return (floor_cos, hebbian_cos, ensemble_cos) per-turn arrays.

        Phase 10 P5 (#00b): exposes per-encoder cosines so the absent-answer
        ensemble-disagreement gating can compare CharNgram floor top-1 turn_id
        against RIHV-Hebbian top-1 turn_id (disagreement → low confidence →
        likely absent).
        """
        if not self._is_built:
            raise RuntimeError("call write_batch(...) before retrieve(...)")
        f_q = self._floor.encode([query])
        h_q = self._hebbian.encode([query])
        f_cos = cosine_matrix_bipolar(f_q, self._floor_turn_vecs)[0]
        h_cos = cosine_matrix_bipolar(h_q, self._heb_turn_vecs)[0]
        ensemble = self.alpha * f_cos + (1.0 - self.alpha) * h_cos
        return f_cos, h_cos, ensemble

    def retrieve(self, query: str, k: int = 5) -> list[tuple[int, float, TurnRecord]]:
        """Top-k turn_ids by ensemble cosine. Returns list of (turn_id, cos, record)."""
        cosines = self._ensemble_cosines(query)
        topk = np.argsort(-cosines)[:k]
        return [(int(idx), float(cosines[idx]), self._records[int(idx)]) for idx in topk]

    # --- Phase 10 P4: incremental write + replay consolidation ----------

    def write_one(self, record: TurnRecord) -> None:
        """Append a single TurnRecord to memory without batch rebuild.

        Encodes the new text via both encoders (CharNgram is stateless;
        Hebbian uses existing trained vectors with unseen-word fallback for
        novel tokens — see `random_index_hebbian.py` _word_hash_seed flow).
        Refreshes fact_graph (subjects extracted from fact_keys + capitalized-
        token fallback) and Jaccard baseline incrementally. Replay-consolidate
        on a cadence (caller's responsibility) for the Hebbian "sleep pass"
        that re-fits trained vectors against the accumulator.
        """
        if not self._is_built:
            raise RuntimeError("call write_batch(...) before write_one(...)")
        self._records.append(record)
        self._turn_texts.append(record.text)
        # Stateless / incremental-safe encoders.
        new_floor = self._floor.encode([record.text])  # (1, D)
        new_heb = self._hebbian.encode([record.text])  # (1, D); unseen-word fallback handles novel tokens
        self._floor_turn_vecs = np.concatenate([self._floor_turn_vecs, new_floor], axis=0)
        self._heb_turn_vecs = np.concatenate([self._heb_turn_vecs, new_heb], axis=0)
        # Jaccard baseline: append new token set
        self._baseline._turn_token_sets.append(set(tokenize(record.text)))
        # Fact graph: prepend turn_id (most-recent first; recency-sorted desc invariant).
        # Binding bank: extend the per-subject bound accumulator with the new bind.
        new_floor_vec = self._floor_turn_vecs[record.turn_id]
        for s in self._extract_subjects_for_record(record):
            self._fact_graph.setdefault(s, []).insert(0, record.turn_id)
            self._add_to_binding_bank(s, new_floor_vec)

    def replay_consolidate(self) -> None:
        """Hebbian "sleep pass": re-fit Hebbian on the full current corpus and
        re-encode every turn. Run periodically after a batch of `write_one`s
        so trained vectors absorb the new co-occurrence signal. This is the
        consolidation half of Council Idea #4 (Incremental Hebbian Replay)."""
        if not self._is_built:
            return
        # Re-fit Hebbian on the full current corpus (includes incrementally-written turns).
        self._hebbian.fit(self._turn_texts)
        # Re-encode all turns with refreshed Hebbian; floor vecs unchanged (stateless).
        self._heb_turn_vecs = self._hebbian.encode(self._turn_texts)
        # Baseline refit (cheap; just rebuilds token sets).
        self._baseline.fit(self._turn_texts)

    # --- Phase 10 P3: structural retrieval via fact graph ----------------

    def _extract_query_subjects(self, query: str) -> list[str]:
        """Find fact_graph keys that occur as substrings of the query.

        Case-insensitive substring match against the fact_graph keys. This catches
        subjects regardless of capitalization or spacing — `subsystem-317` (lowercase
        decision topic) and `the database` (multi-word topic with article) and
        `Alice` (proper noun) all extract uniformly. The capitalized-token regex
        in `_subjects_from_text` is kept as a record-side fallback for corpora
        without fact_keys (e.g., the killer-milestone test corpus uses raw turns).
        """
        if not self._fact_graph:
            return []
        q_lower = query.lower()
        return [k for k in self._fact_graph if k.lower() in q_lower]

    def _structural_cosines(self, query: str, binding_weight: float = 0.0) -> np.ndarray:
        """Ensemble cosines, with structural override for queries naming known subjects.

        Behavior:
          1. Extract subjects via substring match against fact_graph keys.
          2. If none → return pure ensemble cosines (back-compat: absent_answer queries
             with phantom subjects fall through to existing cosine path).
          3. If known subjects → restrict candidate set to fact_graph[s] ∪ ...; the
             most-recent turn per subject is given a strict-dominance boost
             (max_in_subject + 1.0) so it ranks ABOVE every other candidate from
             that subject regardless of base-cosine variance. Other candidates carry
             their base cosine; non-candidates are zeroed (excluded from top-k unless
             no known-subject candidates exist).
          4. binding_weight > 0 blends in the Plate-style unbind cosine:
             score(t) = base[t] + binding_weight * cosine(unbind_subject_pseudo_vec(s), floor_turn_vec[t]).
             This wires #00c-2's binding mechanism into the hot retrieval path so
             the hybrid claim has empirical data behind it. Default 0.0 preserves
             the Phase 10 P3 (#00c-1) winner.

        The strict-dominance boost is what makes contradiction LATEST-wins work at
        scale. For multi-subject queries, each subject's most-recent gets the same
        shape boost, so both surface in top-2.
        """
        base = self._ensemble_cosines(query)
        qs = self._extract_query_subjects(query)
        if not qs:
            return base

        out = np.zeros_like(base)
        for s in qs:
            candidates = self._fact_graph[s]
            if not candidates:
                continue
            # Optional binding signal: cosine of unbind(bank_s, atom_s) vs each turn vec.
            # Bind/unbind in bipolar HDC produces a (noisy) superposition of all turn
            # vecs that mentioned s — cosine to a particular turn approximates "did s
            # speak in this turn" with the structural binding as evidence.
            bind_sims = None
            if binding_weight > 0:
                pseudo = self.unbind_subject_pseudo_vec(s)
                if pseudo is not None:
                    bind_sims = cosine_matrix_bipolar(
                        pseudo.reshape(1, -1), self._floor_turn_vecs
                    )[0]

            max_in_subject = float("-inf")
            for tid in candidates:
                score = base[tid]
                if bind_sims is not None:
                    score = score + binding_weight * float(bind_sims[tid])
                if score > out[tid]:
                    out[tid] = score
                if score > max_in_subject:
                    max_in_subject = score
            out[candidates[0]] = max_in_subject + 1.0
        return out

    def retrieve_structural(
        self, query: str, k: int = 5
    ) -> list[tuple[int, float, TurnRecord]]:
        """Structural retrieval — fact-graph candidate set + ensemble cosine + recency boost.

        Equivalent to retrieve() when the query has no known subjects (no boost).
        Recommended path for question-answering: handles single-subject (paraphrase,
        contradiction), multi-subject (multi-hop), and unknown-subject (absent_answer
        falls through to pure cosine) queries uniformly.
        """
        cos = self._structural_cosines(query)
        topk = np.argsort(-cos)[:k]
        return [(int(idx), float(cos[idx]), self._records[int(idx)]) for idx in topk]

    # --- Multi-hop attack -------------------------------------------------

    _SPLIT_PATTERN = re.compile(r"\s+(?:and|both|or|plus|with)\s+", re.IGNORECASE)

    def retrieve_multi_hop(self, query: str, k: int = 5) -> list[tuple[int, float, TurnRecord]]:
        """Decompose query on 'and'/'both'/'or', run sub-retrievals, union top-k.

        Phase 10 P3 (#00c-1): if query mentions known subjects, prefer structural
        retrieval (fact-graph candidate set + ensemble cosine + recency boost) — it
        subsumes the lexical decomposition path and handles cases where surface-form
        splitting fails (e.g., subjects without 'and' separators). Falls back to
        the legacy lexical decomposition when no known subjects are extracted.
        """
        if self._extract_query_subjects(query):
            return self.retrieve_structural(query, k)

        # Legacy lexical decomposition fallback (Phase 9 path).
        parts = self._SPLIT_PATTERN.split(query)
        if len(parts) < 2:
            return self.retrieve(query, k)
        # Heuristic: assume "What do X and Y prefer?" → "What does X prefer?" + "What does Y prefer?"
        # Strategy: drop verbs in plural ("do") and rebuild per-subject.
        # Simpler still: just retrieve for each part as-is.
        all_topk: dict[int, float] = {}
        for part in parts:
            sub_query = part.strip(" ?.")
            # Reconstruct a question-shape if missing
            if "?" not in sub_query and "what" not in sub_query.lower():
                sub_query = f"What does {sub_query}?"
            cosines = self._ensemble_cosines(sub_query)
            sub_topk = np.argsort(-cosines)[:k]
            for idx in sub_topk:
                ix = int(idx)
                cos = float(cosines[ix])
                if ix not in all_topk or cos > all_topk[ix]:
                    all_topk[ix] = cos
        # Sort by max cosine across sub-queries, keep top-k
        merged = sorted(all_topk.items(), key=lambda iv: -iv[1])[:k]
        return [(idx, cos, self._records[idx]) for idx, cos in merged]

    # --- Side-by-side with keyword baseline -------------------------------

    def retrieve_with_baselines(
        self, query: str, k: int = 5
    ) -> dict:
        """Returns {ensemble: [...], keyword: [...], floor_only: [...], hebbian_only: [...]}."""
        if not self._is_built:
            raise RuntimeError("call write_batch(...) before retrieve_with_baselines(...)")
        ensemble_top = self.retrieve(query, k)
        keyword_top = self._baseline.retrieve_top_k(query, k)
        f_q = self._floor.encode([query])
        h_q = self._hebbian.encode([query])
        f_cos = cosine_matrix_bipolar(f_q, self._floor_turn_vecs)[0]
        h_cos = cosine_matrix_bipolar(h_q, self._heb_turn_vecs)[0]
        f_topk = np.argsort(-f_cos)[:k]
        h_topk = np.argsort(-h_cos)[:k]
        return {
            "ensemble": [(int(i), c, self._records[i]) for i, c, _ in ensemble_top],
            "keyword": [(int(i), c, self._records[i]) for i, c in keyword_top],
            "floor_only": [(int(i), float(f_cos[i]), self._records[int(i)]) for i in f_topk],
            "hebbian_only": [(int(i), float(h_cos[i]), self._records[int(i)]) for i in h_topk],
        }

    # --- Provenance persistence ------------------------------------------

    def save_provenance(self, path: Path) -> None:
        """JSONL — one TurnRecord per line."""
        with path.open("w", encoding="utf-8") as f:
            for r in self._records:
                f.write(json.dumps({
                    "turn_id": r.turn_id,
                    "text": r.text,
                    "fact_keys": r.fact_keys,
                    "metadata": r.metadata,
                }) + "\n")


# =============================================================================
# Benchmark — top-1 + top-5 across all query types + baselines + multi-hop
# =============================================================================


def evaluate(
    queries: list[dict],
    cosines_per_query: list[np.ndarray],
    k_values: tuple[int, ...] = (1, 5),
) -> dict:
    """top-k accuracy across query types. cosines_per_query[qi] is shape (n_turns,)."""
    bucket: dict[str, dict] = {}
    expected_cos: list[float] = []
    absent_top1_cos: list[float] = []
    for qi, q in enumerate(queries):
        qtype = q["type"]
        sims = cosines_per_query[qi]
        sorted_idx = np.argsort(-sims)
        expected_ids = q["expected_turn_ids"]
        b = bucket.setdefault(qtype, {f"top{k}_correct": 0 for k in k_values})
        b.setdefault("n", 0)
        if expected_ids:
            b["n"] += 1
            for k in k_values:
                topk = set(int(i) for i in sorted_idx[:k])
                if any(eid in topk for eid in expected_ids):
                    b[f"top{k}_correct"] += 1
            expected_cos.append(float(sims[expected_ids[0]]))
        else:
            absent_top1_cos.append(float(sims[int(sorted_idx[0])]))
    out = {}
    for qtype, b in bucket.items():
        if b["n"] > 0:
            for k in k_values:
                out[f"{qtype}_top{k}"] = round(b[f"top{k}_correct"] / b["n"], 4)
        else:
            for k in k_values:
                out[f"{qtype}_top{k}"] = None
    if expected_cos and absent_top1_cos:
        out["signal_gap"] = round(
            float(np.mean(expected_cos) - np.mean(absent_top1_cos)), 4
        )
    return out


def evaluate_keyword(
    queries: list[dict],
    baseline: KeywordBaseline,
    k_values: tuple[int, ...] = (1, 5),
) -> dict:
    bucket: dict[str, dict] = {}
    for q in queries:
        qtype = q["type"]
        topk_max = max(k_values)
        topk = baseline.retrieve_top_k(q["text"], topk_max)
        topk_ids = [i for i, _ in topk]
        expected_ids = q["expected_turn_ids"]
        b = bucket.setdefault(qtype, {f"top{k}_correct": 0 for k in k_values})
        b.setdefault("n", 0)
        if expected_ids:
            b["n"] += 1
            for k in k_values:
                if any(eid in topk_ids[:k] for eid in expected_ids):
                    b[f"top{k}_correct"] += 1
    out = {}
    for qtype, b in bucket.items():
        if b["n"] > 0:
            for k in k_values:
                out[f"{qtype}_top{k}"] = round(b[f"top{k}_correct"] / b["n"], 4)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=str,
                        default="gpt-codex/runs/phase9_dataset_full")
    parser.add_argument("--out", type=str,
                        default="gpt-codex/runs/phase9_memory")
    parser.add_argument("--D", type=int, default=10000)
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--negative-samples", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1337)
    args = parser.parse_args()

    dataset_dir = Path(args.dataset)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with (dataset_dir / "conversation.jsonl").open() as f:
        turns = [json.loads(line) for line in f]
    with (dataset_dir / "queries.jsonl").open() as f:
        queries = [json.loads(line) for line in f]

    records = [
        TurnRecord(
            turn_id=t["turn_id"], text=t["text"],
            fact_keys=t.get("fact_keys", []),
            metadata={k: v for k, v in t.items() if k not in ("turn_id", "text", "fact_keys")},
        )
        for t in turns
    ]

    mem = SemanticHDCMemory(
        D=args.D, alpha=args.alpha,
        negative_samples=args.negative_samples, seed=args.seed,
    )

    t0 = time.time()
    mem.write_batch(records)
    write_wall = time.time() - t0

    # Compute ensemble cosines per query (Phase 9 baseline track)
    t1 = time.time()
    ensemble_cos = [mem._ensemble_cosines(q["text"]) for q in queries]
    ensemble_wall = time.time() - t1

    # Phase 10 P3: structural cosines per query (fact-graph + recency boost).
    # Falls through to ensemble for queries with no known subjects.
    t1b = time.time()
    structural_cos = [mem._structural_cosines(q["text"]) for q in queries]
    structural_wall = time.time() - t1b
    # Phase 10 P3 (#00c-2): structural cosines + binding-blend variant.
    # binding_weight=0.5 wires unbind_subject_pseudo_vec into the hot path so the
    # corpse-spec hybrid retrieval (per-subject atom unbinding + structural ranking)
    # has measured empirical comparison vs the fact-graph-only baseline.
    t1c = time.time()
    structural_with_binding_cos = [
        mem._structural_cosines(q["text"], binding_weight=0.5) for q in queries
    ]
    structural_with_binding_wall = time.time() - t1c

    # For multi_hop, run multi-hop decomposition for those queries only
    t2 = time.time()
    multi_hop_cos_overrides: list[np.ndarray | None] = [None] * len(queries)
    for qi, q in enumerate(queries):
        if q["type"] == "multi_hop":
            # Build a synthetic cosine vector: use multi-hop retrieval to set top-k
            # to high values, all others to 0 (for top-k evaluation purposes)
            mh_top = mem.retrieve_multi_hop(q["text"], k=5)
            v = np.zeros(len(records), dtype=np.float32)
            for idx, cos, _ in mh_top:
                v[idx] = cos
            multi_hop_cos_overrides[qi] = v
    multi_hop_wall = time.time() - t2

    # Combined cosines: standard ensemble for non-multi-hop, decomp for multi-hop
    combined_cos = [
        multi_hop_cos_overrides[qi] if multi_hop_cos_overrides[qi] is not None else ensemble_cos[qi]
        for qi in range(len(queries))
    ]

    # Evaluations
    eval_ensemble = evaluate(queries, ensemble_cos, k_values=(1, 5))
    eval_with_mh = evaluate(queries, combined_cos, k_values=(1, 5))
    eval_structural = evaluate(queries, structural_cos, k_values=(1, 5))
    eval_structural_with_binding = evaluate(queries, structural_with_binding_cos, k_values=(1, 5))
    eval_keyword = evaluate_keyword(queries, mem._baseline, k_values=(1, 5))

    # Per-query baseline samples
    samples = []
    for qi in [0, 1, 2, 30, 60, 120, 150, 195]:
        if qi >= len(queries):
            continue
        q = queries[qi]
        bl = mem.retrieve_with_baselines(q["text"], k=3)
        samples.append({
            "query_id": q["query_id"],
            "type": q["type"],
            "text": q["text"],
            "expected_turn_ids": q["expected_turn_ids"],
            "ensemble_top3": [(i, round(c, 3), r.text[:60]) for i, c, r in bl["ensemble"]],
            "keyword_top3": [(i, round(c, 3), r.text[:60]) for i, c, r in bl["keyword"]],
        })

    result = {
        "run_id": f"phase9_memory_seed{args.seed}_alpha{args.alpha}_neg{args.negative_samples}",
        "config": {
            "D": args.D,
            "alpha": args.alpha,
            "negative_samples": args.negative_samples,
            "seed": args.seed,
            "n_turns": len(turns),
            "n_queries": len(queries),
        },
        "metrics": {
            "write_wall_seconds": round(write_wall, 4),
            "ensemble_query_wall_seconds": round(ensemble_wall, 4),
            "structural_query_wall_seconds": round(structural_wall, 4),
            "structural_with_binding_wall_seconds": round(structural_with_binding_wall, 4),
            "multi_hop_decomp_wall_seconds": round(multi_hop_wall, 4),
            "ensemble_only": eval_ensemble,
            "with_multi_hop_decomposition": eval_with_mh,
            "with_structural": eval_structural,
            "with_structural_and_binding": eval_structural_with_binding,
            "keyword_baseline": eval_keyword,
        },
        "samples": samples,
        "notes": [
            "ensemble_only: standard ensemble cosines for ALL query types.",
            "with_multi_hop_decomposition: ensemble for non-multi-hop, query-decomposition union-top-5 for multi-hop.",
            "keyword_baseline: simple Jaccard token overlap — must lose to ensemble on paraphrase to justify HDC.",
        ],
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2))

    # Print summary
    def _row(label, e):
        return (
            f"  {label:30s}  exact1={e.get('exact_turn_lookup_top1', 'NA'):>6} "
            f"exact5={e.get('exact_turn_lookup_top5', 'NA'):>6}  "
            f"para1={e.get('semantic_paraphrase_top1', 'NA'):>6} "
            f"para5={e.get('semantic_paraphrase_top5', 'NA'):>6}  "
            f"contra1={e.get('contradiction_top1', 'NA'):>6} "
            f"mh1={e.get('multi_hop_top1', 'NA'):>6} "
            f"mh5={e.get('multi_hop_top5', 'NA'):>6}"
        )
    print(f"SemanticHDCMemory  D={args.D}  alpha={args.alpha}  neg={args.negative_samples}  seed={args.seed}")
    print(f"  write/ensemble/structural/multi_hop wall: "
          f"{write_wall:.3f}s / {ensemble_wall:.3f}s / {structural_wall:.3f}s / {multi_hop_wall:.3f}s")
    print(_row("ensemble (no multi-hop)", eval_ensemble))
    print(_row("ensemble + multi-hop decomp", eval_with_mh))
    print(_row("structural (P3 fact-graph)", eval_structural))
    print(_row("keyword baseline (Jaccard)", eval_keyword))
    print(f"  signal_gap (ensemble): {eval_ensemble.get('signal_gap', 'NA')}")
    print(f"  signal_gap (structural): {eval_structural.get('signal_gap', 'NA')}")
    print(f"  wrote {out_dir / 'result.json'}")


if __name__ == "__main__":
    main()
