"""Corpus ingestion pipeline — cycle 12 #00P13c12-01b.

Per lain 2026-05-11 catch ("you are underestimating how much and how good data
you need") + canonical synthesis doc Layer 6 § Tier-2 spec: "Domain-canonical
curated (~1M-10M words per domain): Public-domain poetry (Project Gutenberg);
... NOT GPT-generated; that would distill a transformer through the back door."

This module turns raw public-domain text files into the same `(text, source_tag)`
tuple shape that `mini_seed.py` provides hand-seeded — but at orders of magnitude
more scale. The natural-mode walk's retrieval is corpus-bound; bigger corpus +
more diverse English = better walks.

Pipeline:
  1. Read raw text file (typically Project Gutenberg dump).
  2. Strip Gutenberg header (everything before "*** START OF THE PROJECT GUTENBERG ...")
     and footer (everything after "*** END OF THE PROJECT GUTENBERG ...").
  3. Normalize whitespace (collapse runs; preserve sentence boundaries).
  4. Tokenize into sentences on `. ! ?` followed by whitespace + capital letter.
  5. Filter: length 5-50 words; not all-caps (drops chapter headers); <40% digits
     (drops page numbers); no problematic Unicode (drops bullet-list noise).
  6. Output list of (sentence_text, source_tag) tuples ready to feed
     `NaturalModeComposer` alongside hand-seeded fragments.

Honest framing:
  - Sentence tokenization is REGEX-BASED (no NLTK / spaCy / transformers). Pure
    stdlib. Occasionally splits "Mr. Darcy" mid-honorific; the filter catches
    most resulting fragments via min-length gate. Acceptable noise at v1.
  - Provenance per fragment is the source_tag tied to the source file; NOT
    per-paragraph or per-page resolution. Cycle-12+ extension: keep
    line-number / chapter metadata per sentence.
  - Public-domain only. Source files in `data/corpus_raw/` MUST be works whose
    copyright has lapsed in the US (typically pre-1928 publication) or work
    explicitly placed in the public domain. M-PROJECTX-013 / organic-thesis
    binding: NO GPT-generated text; NO copyrighted-still-in-force text.

Organic-thesis compliance: regex + stdlib only. No LLM in the pipeline. No
pretrained-tokenizer (the sentence-boundary regex is hand-rolled).
"""

from __future__ import annotations

import re
from pathlib import Path


# Gutenberg header/footer markers — Project Gutenberg uses these stable
# delimiter lines for body extraction. Patterns are intentionally lenient
# (the markers vary slightly across decades of Gutenberg releases).
_GUTENBERG_START_RE = re.compile(
    r"\*+\s*START OF (?:THE |THIS )?PROJECT GUTENBERG.*?\*+",
    re.IGNORECASE,
)
_GUTENBERG_END_RE = re.compile(
    r"\*+\s*END OF (?:THE |THIS )?PROJECT GUTENBERG.*?\*+",
    re.IGNORECASE,
)

# Sentence-boundary regex. Splits on `.!?` followed by whitespace + capital
# letter (heuristic; avoids breaking on "Mr." mid-honorific most of the time).
# Hand-rolled stdlib regex; no language-model-based tokenizer.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'])")

# Whitespace normalizer: collapse runs + trim.
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_gutenberg_boilerplate(text: str) -> str:
    """Extract body between Gutenberg START/END markers.

    Falls back to returning the whole text if markers are absent (e.g., the
    file is not from Project Gutenberg but follows the same conventions).
    """
    start_match = _GUTENBERG_START_RE.search(text)
    if start_match:
        text = text[start_match.end():]
    end_match = _GUTENBERG_END_RE.search(text)
    if end_match:
        text = text[: end_match.start()]
    return text


def _is_acceptable_fragment(sentence: str) -> bool:
    """Curation filter — high-quality, low-noise fragment selection.

    Per lain 2026-05-11 catch ("dataset must be very well curated and high
    quality, low noise. But rich and broad."), v2 filter is significantly
    stricter than v1. Goals: keep aphoristic / observational / self-contained
    declaratives; drop dialogue questions, narrative-framing-only sentences,
    chapter headers, proper-noun-heavy passages.

    Heuristics (all must pass):
      - Length: 10 ≤ word_count ≤ 50. (v1: 5 ≤ word_count ≤ 50; raised floor
        to drop short dialogue tags like "Yes, indeed.")
      - No newlines (post-normalization, multi-line = joined paragraphs).
      - Not all-caps (drops chapter headers like "CHAPTER I").
      - Digit-ratio <40% (drops page numbers / table-of-contents lines).
      - **No question marks** (drops Socratic dialogue questions which
        dominated Plato's Republic in v1; "What is the meaning of this?"
        outranked Marcus Aurelius aphorisms by 100x via mere word-overlap).
      - **No leading third-person pronoun** ("He / She / They / It said")
        (drops narrative dialogue framing without context).
      - **No common dialogue character markers** (Mr. / Mrs. / Miss / Sir /
        Lady / Doctor + period) — these almost always wrap dialogue tags.
      - **Max 3 capitalized non-first-words** — drops fragments dominated by
        proper nouns (character names, place names from novels). The remaining
        capitalized tokens are usually I / common-noun-titles.
    """
    word_count = len(sentence.split())
    if not (10 <= word_count <= 50):
        return False
    if "\n" in sentence:
        return False
    if sentence == sentence.upper() and word_count >= 2:
        return False
    digit_chars = sum(1 for c in sentence if c.isdigit())
    if digit_chars > 0.4 * len(sentence):
        return False
    # v2 cycle-12 #01b-noise-reduction filters
    if "?" in sentence:
        return False  # drops dialogue questions
    # Drop sentences starting with bare third-person pronouns (narrative framing)
    first_word = sentence.split(maxsplit=1)[0].lower().rstrip(",;:")
    if first_word in ("he", "she", "they", "it", "this"):
        return False
    # Drop fragments with common dialogue character markers
    if any(marker in sentence for marker in (
        "Mr.", "Mrs.", "Miss ", "Sir ", "Lady ", "Doctor ", "Lord ",
    )):
        return False
    # Drop proper-noun-heavy passages (>3 capitalized non-first-words)
    words = sentence.split()
    cap_count = sum(
        1 for w in words[1:]
        if w and w[0].isupper() and not w[0] in '"\''
    )
    if cap_count > 3:
        return False
    return True


def _normalize_whitespace(text: str) -> str:
    """Collapse all whitespace runs to single spaces; strip."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def ingest_text_file(
    file_path: str | Path,
    source_tag: str,
) -> list[tuple[str, str]]:
    """Ingest one text file into list of (sentence, source_tag) tuples.

    Args:
        file_path: path to raw text file (typically Project Gutenberg dump).
        source_tag: descriptor used for provenance (e.g., "Austen Pride and
                    Prejudice (Project Gutenberg #1342; public domain)").

    Returns:
        List of (sentence_text, source_tag) tuples after sentence-tokenization
        and filtering. Empty if the file produces no acceptable fragments.

    Raises:
        FileNotFoundError: if file_path doesn't exist.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"corpus file not found: {file_path}")
    raw = file_path.read_text(encoding="utf-8", errors="replace")
    body = _strip_gutenberg_boilerplate(raw)
    # Replace newline runs with spaces BEFORE sentence-splitting so that
    # multi-line paragraphs join cleanly. Then split on sentence boundaries.
    # (We still reject multi-line fragments at the filter step — but post-
    # normalization, sentences are single-line.)
    body_normalized = _WHITESPACE_RE.sub(" ", body)
    sentences = _SENTENCE_SPLIT_RE.split(body_normalized)
    fragments: list[tuple[str, str]] = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if _is_acceptable_fragment(s):
            fragments.append((s, source_tag))
    return fragments


def ingest_corpus_dir(
    corpus_dir: str | Path,
    manifest: dict[str, str] | None = None,
    per_source_cap: int = 1500,
    seed: int = 42,
) -> list[tuple[str, str]]:
    """Ingest every text file in `corpus_dir` and return combined fragments.

    Per lain 2026-05-11 ~06:00 CEST catch ("dataset must be very well curated
    and high quality, low noise. But rich and broad."): in addition to
    sentence-level quality filtering in `_is_acceptable_fragment`, this dir-
    level wrapper caps fragments per source at `per_source_cap` (default 1500).
    The cap prevents one large source (e.g., Plato Republic at 3285 fragments)
    from dominating retrieval similarity over smaller-but-aphoristic sources
    (e.g., Aurelius Meditations at 1456 fragments) by sheer count.

    Args:
        corpus_dir: directory containing raw .txt files.
        manifest: optional dict mapping filename → source_tag. If a file is in
                  the dir but not in the manifest, source_tag defaults to
                  the file stem.
        per_source_cap: max fragments per source. Sources with more fragments
                        are randomly downsampled to the cap. Default 1500.
        seed: random seed for deterministic per-source downsampling.

    Returns:
        Combined list of (sentence, source_tag) tuples from all ingested files,
        balanced per-source.
    """
    import random
    corpus_dir = Path(corpus_dir)
    if not corpus_dir.exists():
        return []
    rng = random.Random(seed)
    all_fragments: list[tuple[str, str]] = []
    manifest = manifest or {}
    for txt_path in sorted(corpus_dir.glob("*.txt")):
        tag = manifest.get(txt_path.name, txt_path.stem)
        source_frags = ingest_text_file(txt_path, source_tag=tag)
        if len(source_frags) > per_source_cap:
            # Random downsample with fixed seed (reproducibility)
            source_frags = rng.sample(source_frags, per_source_cap)
        all_fragments.extend(source_frags)
    return all_fragments


# Manifest of expected source-tags per filename for the v1 cycle-12 fetcher.
# Used by `scripts/fetch_corpus.py` to download + tag; ingestion pipeline reads
# this when wiring into the NaturalModeComposer's corpus loader.
INGESTION_MANIFEST: dict[str, str] = {
    # Cycle 12 #01b initial 10
    "pride_and_prejudice.txt":
        "Austen Pride and Prejudice (Project Gutenberg #1342; public domain)",
    "walden.txt":
        "Thoreau Walden (Project Gutenberg #205; public domain)",
    "leaves_of_grass.txt":
        "Whitman Leaves of Grass (Project Gutenberg #1322; public domain)",
    "tao_te_ching.txt":
        "Lao Tzu Tao Te Ching (Project Gutenberg #216; public domain translation)",
    "meditations_aurelius.txt":
        "Marcus Aurelius Meditations (Project Gutenberg #2680; public domain translation)",
    "republic_plato.txt":
        "Plato The Republic (Project Gutenberg #1497; public domain translation)",
    "tale_of_two_cities.txt":
        "Dickens A Tale of Two Cities (Project Gutenberg #98; public domain)",
    "frankenstein.txt":
        "Shelley Frankenstein (Project Gutenberg #84; public domain)",
    "alice_in_wonderland.txt":
        "Carroll Alice's Adventures in Wonderland (Project Gutenberg #11; public domain)",
    "shakespeare_complete_sonnets.txt":
        "Shakespeare Complete Sonnets (Project Gutenberg #1041; public domain)",
    # Cycle 12 #01c — broaden across more domains
    "nicomachean_ethics.txt":
        "Aristotle Nicomachean Ethics (Project Gutenberg #8438; public domain translation)",
    "art_of_war.txt":
        "Sun Tzu The Art of War (Project Gutenberg #132; public domain translation)",
    "bhagavad_gita.txt":
        "Bhagavad Gita (Project Gutenberg #2388; public domain translation)",
    "consolation_of_philosophy.txt":
        "Boethius Consolation of Philosophy (Project Gutenberg #14328; public domain)",
    "wealth_of_nations.txt":
        "Adam Smith Wealth of Nations (Project Gutenberg #3300; public domain)",
    "origin_of_species.txt":
        "Darwin On the Origin of Species (Project Gutenberg #1228; public domain)",
    "emerson_essays.txt":
        "Emerson Essays First Series (Project Gutenberg #2945; public domain)",
    "paradise_lost.txt":
        "Milton Paradise Lost (Project Gutenberg #20; public domain)",
    "divine_comedy.txt":
        "Dante Divine Comedy (Project Gutenberg #1004; Longfellow translation public domain)",
    "plutarchs_lives.txt":
        "Plutarch Plutarch's Lives (Project Gutenberg #14140; public domain translation)",
    "herodotus_histories.txt":
        "Herodotus The Histories (Project Gutenberg #2707; public domain translation)",
    "analects_confucius.txt":
        "Confucius The Analects (Project Gutenberg #3330; public domain translation)",
}
