#!/usr/bin/env python3
"""Fetch Project Gutenberg works into `data/corpus_raw/` — cycle 12 #00P13c12-01b.

Downloads the canonical public-domain works in `INGESTION_MANIFEST` (see
`src/project_x/corpus/ingestion.py`) and saves each as a plain-text file
in `data/corpus_raw/`. One-shot script; idempotent (skips already-downloaded
files). Stdlib only (urllib + Path); no requests / beautifulsoup.

Per canonical synthesis doc Layer 6 § Tier-2 spec: "Domain-canonical curated
(~1M-10M words per domain): Public-domain poetry (Project Gutenberg)." This
fetches Tier-2 starter corpus across poetry / philosophy / narrative-prose /
dialogue domains.

Usage:
  python3 scripts/fetch_corpus.py        # download missing files
  python3 scripts/fetch_corpus.py --force  # re-download all

Each fetched file is checked in to git (typically ~100-500KB each; total
~3-5MB) so the corpus is reproducible from a fresh clone without re-fetching.

Public-domain attribution per file:
  Pride and Prejudice (Austen, 1813)               Gutenberg #1342
  Walden (Thoreau, 1854)                           Gutenberg #205
  Leaves of Grass (Whitman, 1855)                  Gutenberg #1322
  Tao Te Ching (Lao Tzu, translation public domain) Gutenberg #216
  Meditations (Marcus Aurelius, translation pd)     Gutenberg #2680
  Republic (Plato, translation public domain)       Gutenberg #1497
  Tale of Two Cities (Dickens, 1859)               Gutenberg #98
  Frankenstein (Shelley, 1818)                     Gutenberg #84
  Alice's Adventures in Wonderland (Carroll, 1865) Gutenberg #11
  Complete Sonnets (Shakespeare, 1609)             Gutenberg #1041

NO GPT-generated text. NO copyrighted-in-force text. All sources are works
whose copyright has lapsed in the US (typically pre-1928 publication).
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path


_CORPUS_DIR = Path(__file__).resolve().parents[1] / "data" / "corpus_raw"

# Manifest: (filename, gutenberg_id)
# Primary URL: https://www.gutenberg.org/cache/epub/<id>/pg<id>.txt
# Fallback URL: https://www.gutenberg.org/files/<id>/<id>-0.txt
_GUTENBERG_FETCHES: list[tuple[str, int]] = [
    ("pride_and_prejudice.txt", 1342),
    ("walden.txt", 205),
    ("leaves_of_grass.txt", 1322),
    ("tao_te_ching.txt", 216),
    ("meditations_aurelius.txt", 2680),
    ("republic_plato.txt", 1497),
    ("tale_of_two_cities.txt", 98),
    ("frankenstein.txt", 84),
    ("alice_in_wonderland.txt", 11),
    ("shakespeare_complete_sonnets.txt", 1041),
]


def _fetch_url(url: str, timeout: int = 30) -> bytes | None:
    """Fetch URL via urllib; return bytes or None on failure."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "project-x-corpus-fetcher/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except (urllib.error.URLError, TimeoutError):
        return None


def fetch_one(filename: str, gutenberg_id: int, force: bool = False) -> bool:
    """Fetch one Gutenberg work into `data/corpus_raw/<filename>`.

    Returns True if file is present after the call (whether already-present
    or freshly downloaded); False if both primary + fallback URLs failed.
    """
    out_path = _CORPUS_DIR / filename
    if out_path.exists() and not force:
        print(f"  [skip] {filename} (already exists; {out_path.stat().st_size:,} bytes)")
        return True
    primary = f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt"
    data = _fetch_url(primary)
    if data is None:
        fallback = f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt"
        data = _fetch_url(fallback)
        if data is None:
            print(f"  [FAIL] {filename} (both URLs failed: {primary} + {fallback})")
            return False
    out_path.write_bytes(data)
    print(f"  [ok]   {filename} ({len(data):,} bytes)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--force", action="store_true", help="re-download even if files exist")
    args = parser.parse_args()

    _CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Fetching corpus into {_CORPUS_DIR}")
    successes = 0
    failures = 0
    for filename, gid in _GUTENBERG_FETCHES:
        if fetch_one(filename, gid, force=args.force):
            successes += 1
        else:
            failures += 1
    print(f"\nDone: {successes} ok, {failures} failed.")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
