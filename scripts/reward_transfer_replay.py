"""Reward-transfer replay harness for the HebbianBank.

Measures whether a rating on one prompt shape changes retrieval score/rank for
a held-out paraphrase. This is a small deterministic harness for the 2026-05-12
Codex pass: exact prompt ratings should keep full strength, while overlapping
token/bigram atoms should transfer fractional reward to paraphrases.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from project_x.corpus.natural_mode import NaturalModeComposer
from project_x.experiments.encoder import cosine_bipolar
from project_x.hdc_infra import HebbianBank, blend_score


DEFAULT_RATED_PROMPT = "Tell me a joke about entropy"
DEFAULT_HELD_OUT_PROMPT = "Write a joke about entropy please"
DEFAULT_TARGET_FRAGMENT = (
    "Aleph-null is the cardinality of the natural numbers; aleph-one is the "
    "cardinality of the reals; the continuum hypothesis asks if there is a "
    "cardinal strictly between."
)


def _rank_fragment(
    composer: NaturalModeComposer,
    bank: HebbianBank,
    prompt: str,
    domain: str,
    target_fragment: str,
) -> dict[str, Any]:
    prompt_hv = composer._encoder.encode([prompt])[0]
    rows: list[tuple[float, int, str]] = []
    for idx in composer._filtered_indices(domain):
        text = composer._tagged[idx][1]
        cosine = cosine_bipolar(prompt_hv, composer._fragment_hvs[idx])
        score = blend_score(bank, cosine, prompt, text)
        rows.append((float(score), idx, text))
    rows.sort(key=lambda row: row[0], reverse=True)
    for rank, (score, idx, text) in enumerate(rows, start=1):
        if text == target_fragment:
            return {
                "rank": rank,
                "score": score,
                "candidate_count": len(rows),
                "source": composer._tagged[idx][2],
            }
    raise ValueError("target fragment not found in selected domain")


def run_replay(
    *,
    rated_prompt: str = DEFAULT_RATED_PROMPT,
    held_out_prompt: str = DEFAULT_HELD_OUT_PROMPT,
    target_fragment: str = DEFAULT_TARGET_FRAGMENT,
    domain: str = "math",
    reject_count: int = 5,
    filler_count: int = 120,
) -> dict[str, Any]:
    composer = NaturalModeComposer(include_ingested=False, hebbian_bank=HebbianBank())
    empty_bank = HebbianBank()
    before = _rank_fragment(composer, empty_bank, held_out_prompt, domain, target_fragment)

    bank = HebbianBank()
    for _ in range(reject_count):
        bank.update(rated_prompt, [target_fragment], rating=1.0)
    for i in range(filler_count):
        bank.update(f"filler prompt {i}", [f"filler fragment {i}"], rating=5.0)

    after = _rank_fragment(composer, bank, held_out_prompt, domain, target_fragment)
    exact_lookup = bank.lookup_for(rated_prompt, target_fragment)
    transferred_lookup = bank.lookup_for(held_out_prompt, target_fragment)

    return {
        "rated_prompt": rated_prompt,
        "held_out_prompt": held_out_prompt,
        "domain": domain,
        "target_fragment": target_fragment,
        "reject_count": reject_count,
        "filler_count": filler_count,
        "bank_entry_count": bank.entry_count(),
        "exact_lookup": exact_lookup,
        "transferred_lookup": transferred_lookup,
        "before": before,
        "after": after,
        "rank_delta": after["rank"] - before["rank"],
        "score_delta": after["score"] - before["score"],
        "pass": transferred_lookup < 0.0 and after["rank"] > before["rank"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON result path.")
    parser.add_argument("--domain", default="math")
    parser.add_argument("--reject-count", type=int, default=5)
    parser.add_argument("--filler-count", type=int, default=120)
    args = parser.parse_args()

    result = run_replay(
        domain=args.domain,
        reject_count=args.reject_count,
        filler_count=args.filler_count,
    )
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
