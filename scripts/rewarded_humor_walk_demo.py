"""Rewarded natural-walk demo: audit ratings shift held-out retrieval.

This harness measures a strict-thesis learning loop, not a new domain rule:

1. Generate natural-mode walks for a bad humor/chat prompt and a good
   public-domain humor-style prompt.
2. Apply synthetic audit ratings through AuditLog.apply_rating(), which writes
   to HebbianBank via the real audit I/O path.
3. Reconstruct a fresh composer from the saved bank.
4. Re-rank a held-out paraphrase and require the wrong-domain math fragment to
   fall while the Alice fragment rises.

The corpus text is already in the repo's public-domain Project Gutenberg slice;
no generated prose is added here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from project_x.audit.log import AuditLog
from project_x.corpus.natural_mode import NaturalModeComposer
from project_x.experiments.encoder import cosine_bipolar
from project_x.hdc_infra import HebbianBank, blend_score


RUN_ID = "codex-2026-05-12-rewarded-humor-walk-demo"
HELD_OUT_PROMPT = "cardinality joke please"
BAD_WALK_PROMPT = "tell a joke about cardinality"
GOOD_WALK_PROMPT = "cardinality joke mad people alice cat please"
BAD_FRAGMENT_NEEDLE = "Aleph-null is the cardinality"
GOOD_FRAGMENT_NEEDLE = "we’re all mad here"


def _find_fragment(
    composer: NaturalModeComposer,
    needle: str,
) -> dict[str, str]:
    for domain, text, source in composer._tagged:
        if needle in text:
            return {"domain": domain, "text": text, "source": source}
    raise ValueError(f"fragment containing {needle!r} not found")


def _rank_fragment(
    composer: NaturalModeComposer,
    bank: HebbianBank,
    prompt: str,
    fragment_text: str,
    *,
    domain: str = "all",
    top_k: int = 5,
) -> dict[str, Any]:
    prompt_hv = composer._encoder.encode([prompt])[0]
    rows: list[tuple[float, int, str, str, str]] = []
    for idx in composer._filtered_indices(domain):
        domain_tag, text, source = composer._tagged[idx]
        cosine = cosine_bipolar(prompt_hv, composer._fragment_hvs[idx])
        score = blend_score(bank, float(cosine), prompt, text)
        rows.append((float(score), idx, domain_tag, text, source))
    rows.sort(key=lambda row: row[0], reverse=True)

    target_rank: int | None = None
    target_score: float | None = None
    target_source: str | None = None
    target_domain: str | None = None
    for rank, (score, _idx, domain_tag, text, source) in enumerate(rows, start=1):
        if text == fragment_text:
            target_rank = rank
            target_score = score
            target_source = source
            target_domain = domain_tag
            break
    if target_rank is None or target_score is None:
        raise ValueError("target fragment not found in rank table")

    top = [
        {
            "rank": rank,
            "score": score,
            "domain": domain_tag,
            "source": source,
            "text": text,
        }
        for rank, (score, _idx, domain_tag, text, source) in enumerate(
            rows[:top_k],
            start=1,
        )
    ]
    return {
        "rank": target_rank,
        "score": target_score,
        "candidate_count": len(rows),
        "domain": target_domain,
        "source": target_source,
        "top": top,
    }


def _unlink_if_present(path: Path) -> None:
    if path.exists():
        path.unlink()


def run_demo(
    *,
    output: Path | None = None,
    reject_count: int = 12,
    approve_count: int = 5,
) -> dict[str, Any]:
    if output is None:
        output = Path("/tmp/project-x-rewarded-humor-walk-demo.json")
    bank_path = output.with_suffix(".bank.pkl")
    audit_path = output.with_suffix(".walks.jsonl")
    for path in (output, bank_path, audit_path):
        _unlink_if_present(path)

    audit_log = AuditLog(audit_path, hebbian_bank_path=bank_path)
    cold_composer = NaturalModeComposer(include_ingested=True, hebbian_bank=HebbianBank())
    bad_fragment = _find_fragment(cold_composer, BAD_FRAGMENT_NEEDLE)
    good_fragment = _find_fragment(cold_composer, GOOD_FRAGMENT_NEEDLE)

    before_bad = _rank_fragment(
        cold_composer,
        HebbianBank(),
        HELD_OUT_PROMPT,
        bad_fragment["text"],
    )
    before_good = _rank_fragment(
        cold_composer,
        HebbianBank(),
        HELD_OUT_PROMPT,
        good_fragment["text"],
    )

    bad_walk = cold_composer.compose(
        BAD_WALK_PROMPT,
        domain="all",
        max_fragments=1,
        record_audit=True,
        audit_log=audit_log,
    )
    good_walk = cold_composer.compose(
        GOOD_WALK_PROMPT,
        domain="narrative_prose",
        max_fragments=1,
        record_audit=True,
        audit_log=audit_log,
    )

    if not bad_walk.fragments or bad_walk.fragments[0].text != bad_fragment["text"]:
        raise RuntimeError("bad walk did not retrieve the expected math fragment")
    if not good_walk.fragments or good_walk.fragments[0].text != good_fragment["text"]:
        raise RuntimeError("good walk did not retrieve the expected Alice fragment")

    for _ in range(reject_count):
        audit_log.apply_rating(
            bad_walk.audit_walk_id or "",
            "reject",
            "wrong-domain math retrieval for a humor/chat-like prompt",
        )
    for _ in range(approve_count):
        audit_log.apply_rating(
            good_walk.audit_walk_id or "",
            "approve",
            "better public-domain chat/humor fragment",
        )

    learned_bank = HebbianBank.load(bank_path)
    fresh_composer = NaturalModeComposer(
        include_ingested=True,
        hebbian_bank_path=bank_path,
    )
    after_bad = _rank_fragment(
        fresh_composer,
        learned_bank,
        HELD_OUT_PROMPT,
        bad_fragment["text"],
    )
    after_good = _rank_fragment(
        fresh_composer,
        learned_bank,
        HELD_OUT_PROMPT,
        good_fragment["text"],
    )

    result: dict[str, Any] = {
        "run_id": RUN_ID,
        "pass": after_good["rank"] == 1 and after_bad["rank"] > before_bad["rank"],
        "paths": {
            "output": str(output),
            "audit_log": str(audit_path),
            "hebbian_bank": str(bank_path),
        },
        "prompts": {
            "held_out": HELD_OUT_PROMPT,
            "bad_walk": BAD_WALK_PROMPT,
            "good_walk": GOOD_WALK_PROMPT,
        },
        "ratings": {
            "reject_count": reject_count,
            "approve_count": approve_count,
        },
        "walks": {
            "bad": {
                "walk_id": bad_walk.audit_walk_id,
                "domain": bad_walk.domain_filter,
                "fragments": [fragment.__dict__ for fragment in bad_walk.fragments],
            },
            "good": {
                "walk_id": good_walk.audit_walk_id,
                "domain": good_walk.domain_filter,
                "fragments": [fragment.__dict__ for fragment in good_walk.fragments],
            },
        },
        "bank": {
            "entry_count": learned_bank.entry_count(),
            "bad_lookup_on_held_out": learned_bank.lookup_for(
                HELD_OUT_PROMPT,
                bad_fragment["text"],
            ),
            "good_lookup_on_held_out": learned_bank.lookup_for(
                HELD_OUT_PROMPT,
                good_fragment["text"],
            ),
        },
        "before": {
            "bad_fragment": before_bad,
            "good_fragment": before_good,
        },
        "after": {
            "bad_fragment": after_bad,
            "good_fragment": after_good,
        },
        "movement": {
            "bad_rank": [before_bad["rank"], after_bad["rank"]],
            "good_rank": [before_good["rank"], after_good["rank"]],
            "bad_score_delta": after_bad["score"] - before_bad["score"],
            "good_score_delta": after_good["score"] - before_good["score"],
        },
        "interpretation": (
            "Synthetic ratings applied through AuditLog shifted a held-out "
            "humor/chat-like prompt away from a wrong-domain set-theory "
            "fragment and toward a public-domain Alice fragment in a fresh "
            "composer loaded from the saved Hebbian bank."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/project-x-rewarded-humor-walk-demo.json"),
    )
    parser.add_argument("--reject-count", type=int, default=12)
    parser.add_argument("--approve-count", type=int, default=5)
    args = parser.parse_args()
    result = run_demo(
        output=args.output,
        reject_count=args.reject_count,
        approve_count=args.approve_count,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
