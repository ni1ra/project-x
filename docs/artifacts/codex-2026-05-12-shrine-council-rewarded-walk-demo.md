# Codex 2026-05-12 - Shrine Council Rewarded Walk Demo

**Run ID:** `codex-2026-05-12-rewarded-humor-walk-demo`  
**Scope:** brainstorm + implement the next impressive learned-behavior demo under the strict-strict thesis.

## Shrine Council Research

The council was used as a design pressure test, not as authority. Each seat maps to public work relevant to Project X's current substrate:

| Seat | Researched anchor | Implication for Project X |
|---|---|---|
| Sutton / Barto reinforcement learning | MIT Press describes RL as learning to maximize reward while interacting with an uncertain environment. Source: https://mitpress.mit.edu/9780262039246/reinforcement-learning/ | Do not mutate the bank directly in the demo. Route ratings through the environment-facing audit log, then reload the learned state. |
| Silver / Hassabis AlphaGo Zero | Nature's AlphaGo Zero paper frames tabula-rasa improvement from reinforcement learning without human data beyond game rules. Source: https://www.nature.com/articles/nature24270 | The impressive shape is before/after behavior on held-out prompts from reward, not hand-authored routing. |
| Kanerva HDC | Kanerva's HDC tutorial frames high-dimensional random vectors as distributed representations manipulated by algebraic operations. Source: https://philpapers.org/rec/KANHCA-2 | Keep the mechanism inside HDC/Hebbian scoring and atom overlap; do not add a new semantic parser. |
| Hawkins / Numenta cortical columns | Numenta's Thousand Brains summary emphasizes many partial models voting rather than one monolithic hierarchy. Source: https://www.numenta.com/blog/2019/01/16/the-thousand-brains-theory-of-intelligence/ | Prefer multiple neutral prompt atoms and fragment evidence over one brittle exact string key. |
| Lehman / Stanley novelty search | The UCF abstract for novelty search warns that fixed objectives can misdirect search and that novelty can outperform objective chasing in deceptive domains. Source: https://stars.library.ucf.edu/facultybib2010/1530/ | Do not optimize only "math benchmark green." Use chat/humor retrieval as a different behavioral niche. |
| Hinton / fast weights | NeurIPS/Google summaries of fast weights motivate state that changes faster than long-term weights and stores recent context. Sources: https://papers.neurips.cc/paper/6057-using-fast-weights-to-attend-to-the-recent-past and https://research.google/pubs/using-fast-weights-to-attend-to-the-recent-past/ | Treat the Hebbian bank as a fast reward memory over recent rated walks, not a permanent authored domain table. |

## Council Verdict

The winning direction was **a rewarded natural-walk replay over an existing public-domain corpus slice**:

1. Generate a bad natural-mode walk for a humor/chat-like prompt that retrieves a wrong-domain set-theory fragment.
2. Generate a good natural-mode walk that retrieves a public-domain Alice fragment.
3. Apply synthetic audit ratings through `AuditLog.apply_rating`, not by direct `HebbianBank.update`.
4. Reload a fresh composer from the saved bank.
5. Re-run a held-out paraphrase and require rank movement.

Rejected alternatives:

- Add more corpus first: useful but not immediately measured unless ratings consume it.
- Add another dispatcher rule: violates the strict-strict thesis.
- Add per-domain scorer weights: too close to cycle-14 A2/A3's rejected hand-coded policy shape.

## Change

Added `scripts/rewarded_humor_walk_demo.py`.

The script uses the existing Project Gutenberg corpus already on disk. It adds no generated prose and no new domain route. It writes three artifacts beside the requested output path:

- result JSON
- audit-log JSONL
- saved Hebbian bank pickle

## Measured Result

Command:

```bash
PYTHONPATH=src python3 scripts/rewarded_humor_walk_demo.py --output /tmp/project-x-rewarded-humor-walk-demo.json
```

Result: `pass=true`.

Held-out prompt: `cardinality joke please`  
Rated bad prompt: `tell a joke about cardinality`  
Rated good prompt: `cardinality joke mad people alice cat please`

Before ratings:

- wrong-domain math fragment rank: `1 / 22052`
- Alice fragment rank: `1948 / 22052`

After synthetic audit ratings through the real audit path and a fresh composer reload:

- wrong-domain math fragment rank: `21996 / 22052`
- Alice fragment rank: `1 / 22052`
- bank entries: `24`
- held-out bad lookup: `-0.7999999999999999`
- held-out good lookup: `0.6666666666666666`

Artifacts:

- `/tmp/project-x-rewarded-humor-walk-demo.json`
- `/tmp/project-x-rewarded-humor-walk-demo.walks.jsonl`
- `/tmp/project-x-rewarded-humor-walk-demo.bank.pkl`

## Interpretation

This is closer to the manifesto target than a cleaner scaffold because the behavior change is learned from ratings over data:

- The bad fragment is punished because it was rated as a bad retrieval.
- The good fragment is promoted because it was rated as a better retrieval.
- The held-out prompt was not the same as the rated bad prompt.
- The post-rating run uses a fresh composer loaded from persisted bank state.

This still is not broad intelligence. It is one controlled demonstration that reward/data can redirect natural retrieval away from a wrong-domain math fragment and toward a more appropriate public-domain chat/humor fragment.

## Remaining Gaps

- Synthetic ratings are still builder-provided; real lain/auditor rating cadence is needed.
- The composer still retrieves fragments rather than generating fluent original text.
- The prompt atom overlap is lexical, not semantic enough for distant paraphrases.
- The good target is public-domain narrative prose, not a dedicated humor/chat corpus.

## Verification

```bash
PYTHONPATH=src python3 -m py_compile scripts/rewarded_humor_walk_demo.py
```

Result: exit `0`.

```bash
PYTHONPATH=src python3 -m pytest tests/test_hebbian_bank.py tests/test_audit_log_v1.py -q
```

Result: `35 passed`.

```bash
PYTHONPATH=src python3 gpt-codex/benchmark/run_audit.py
```

Result: `48 PASS / 0 FAIL`; rubric-pending skipped: `30`.
