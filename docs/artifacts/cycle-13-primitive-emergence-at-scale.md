# Cycle 13 — Primitive Emergence at Scale (pre-registered predicate + result)

**Pre-registration commit:** committed BEFORE the emergence run per audit D3 (`docs/artifacts/cycle-13-external-audit.md`). Without pre-registration the verdict is interpretive — author + audience interpret the output favorably or unfavorably depending on what they wanted to find. The predicate locks the test on disk before the data exists.

**Pairs with:** `docs/artifacts/cycle-13-bitpack-design.md` (substrate); `docs/artifacts/cycle-13-priority-decision.md` (synthesis §7 row 6); `docs/artifacts/cycle-13-external-audit.md` (audit D3 pre-registration mandate); cycle-11 #06 MVP primitive-emergence (the small-corpus run on ~3k trigrams that surfaced "X is Y" copula shells at k=15).

---

## 1. The pre-registered predicate

The test:

> A cluster discovered by `run_primitive_emergence(packed=True)` on the 22k-fragment Tier-2 corpus's ~80k unique trigrams is classified **STRUCTURAL** if BOTH of the following hold:
>
> **(P1) Shell-consistency:** at least **40% of cluster-member trigrams** parse against the SAME shell from the pre-registered shell list (§2 below). Cluster shell = the modal parseable shell across members; if no single shell exceeds 40%, the cluster fails P1.
>
> **(P2) Centroid agreement:** the **cluster centroid trigram** (the trigram closest to the cluster centroid hypervector) parses against the same shell identified in P1. If the centroid trigram does not parse against any shell, or parses against a different shell than the modal-member shell, the cluster fails P2.
>
> A cluster that PASSES BOTH P1 AND P2 is STRUCTURAL.
>
> A cluster that FAILS either P1 or P2 is **FREQUENCY-RANKED** — its member trigrams share no consistent syntactic shell beyond high-frequency surface-coincidence (e.g., "of the" / "in the" / "to the" sharing the bigram "the" but no deeper pattern).
>
> The cycle-13 verdict on canonical-doc Layer 5 ("primitives are EXTRACTED from corpus structure via unsupervised clustering") is **VALIDATED** if and only if **≥ 30% of surfaced primitives** (clusters above `min_density=5`) classify as STRUCTURAL.

Below 30%: the Layer 5 claim is **NOT VALIDATED at scale** — the cycle-11 MVP "X is Y" finding does not generalize from ~3k trigrams to ~80k trigrams, and the Layer 5 framing requires honest reframing in cycle 14 (per audit C3: "trigram pattern mining" rather than "variable-binding primitive induction").

Between 30% and 60%: Layer 5 is **PARTIALLY VALIDATED** — structural clusters DO emerge but coexist with frequency-rank clusters; the framing needs nuance.

Above 60%: Layer 5 is **STRONGLY VALIDATED at scale** — structural shells emerge robustly from unsupervised clustering on the production corpus.

## 2. Pre-registered shell list

Each shell is a syntactic SKELETON with variable slots (X, Y) where any noun, pronoun, or noun-phrase fragment can fit. A trigram parses against a shell if its three tokens fit the shell's slot-pattern positionally. The shells were chosen from the cycle-11 MVP findings (canonical "X is Y" + "X and Y" + "X gives Y" survivors) PLUS additional shells that frontier-grammar reference grammars would predict as productive in English public-domain literary corpora.

| Shell | Parse rule | Example trigrams (cycle-11 MVP or anticipated) |
|---|---|---|
| `X is Y` | token[1] == "is" | "it is a", "this is my", "he is a", "2 is a" |
| `X and Y` | token[1] == "and" | "stars and stones", "you and me", "good and bad" |
| `X but Y` | token[1] == "but" | "small but real", "old but free" |
| `X or Y` | token[1] == "or" | "discovered or invented", "true or false" |
| `X with Y` | token[1] == "with" | "girl with hair", "tree with roots" |
| `X of Y` | token[1] == "of" | "meaning of life", "shape of space" |
| `X to Y` | token[1] == "to" | "free to be", "ready to fall" |
| `X in Y` | token[1] == "in" | "still in the", "warm in winter" |
| `X for Y` | token[1] == "for" | "wait for spring", "asks for time" |
| `X the Y` | token[1] == "the" | "by the river", "in the deep" |
| `X a Y` | token[1] == "a" | "had a dream", "wear a hat" |
| `X has Y` | token[1] == "has" | "he has lost", "time has come" |
| `X had Y` | token[1] == "had" | "she had seen", "we had hoped" |
| `X was Y` | token[1] == "was" | "she was lost", "it was true" |
| `X were Y` | token[1] == "were" | "they were tired", "we were one" |
| `X gives Y` | token[1] == "gives" | "translation gives conservation" (cycle-11 finding) |
| `X because Y` | token[1] == "because" | "left because true", "broke because cold" |
| `X then Y` | token[1] == "then" | "fall then rise", "speak then listen" |
| `X if Y` | token[1] == "if" | "stay if needed", "go if free" |

Total: 19 shells. The shells privileged are copula (`is`/`was`/`were`/`has`/`had`), coordination (`and`/`but`/`or`), prepositional (`of`/`with`/`for`/`in`/`to`), function-word stoppers (`the`/`a`), and the rarer structural verbs (`gives`/`because`/`then`/`if`).

**Caveat:** trigrams like "is a man" parse against `X is Y` (token[1] == "is") even though semantically the relation is "man IS the noun being modified." The predicate is positional, not semantic — a strength when the question is "do trigrams cluster by syntactic shape?" (yes if the trigram's middle token consistently lands on a structural marker), a weakness when the question is "do trigrams encode logical relations?" (which would require deeper parsing). Cycle-14+ work would extend to longer n-grams + dependency parsing.

## 3. The frequency-rank null hypothesis

If clustering on the 22k-corpus produces clusters whose members are ranked by FREQUENCY rather than SHAPE — e.g., a cluster dominated by "of the" / "to the" / "in the" / "and the" / "by the" / "for the" — then the cluster fails P1 because no single shell achieves 40% (members split across `X the Y`-suffix and various prepositions). This is the canonical pattern that exposes "primitive emergence" as "frequency ranking" — the failure mode the predicate is specifically designed to catch.

The cycle-11 MVP at k=15 on ~3k trigrams reported primitive #10 with members `{'it is a', '2 is a', 'this is my', 'he is a'}` — all 4 parse against `X is Y` (token[1] == "is"). At ≥ 40% threshold a 4-member cluster with 4 of 4 matches would PASS P1 (100% > 40%). The MVP's centroid trigram was reportedly "it is a" — which also parses against `X is Y`. PASSES P2. So the cycle-11 MVP cluster #10 is STRUCTURAL by this predicate. The cycle-13 emergence-at-scale test: do the OTHER 14 cycle-13 clusters classify the same way at ~80k trigrams? Or does the structural pattern only emerge in the small-corpus regime?

## 4. Methodology (pre-registered)

1. Run `discover_primitives(fragments=Tier-2-corpus, k=20, min_density=5, seed=42)` on the 22k-fragment Tier-2 corpus.
2. Confirm trigram extraction count is approximately within the expected range (`30k-100k` unique trigrams; cycle-12 estimate was ~50k-200k, cycle-13 bitpack design used ~80k).
3. For each surfaced primitive (cluster with ≥ 5 members):
   - Parse each member trigram against the shell list. Record the modal shell + the percentage of members matching it.
   - Parse the centroid trigram against the shell list. Record whether it matches the modal-member shell.
   - Classify the cluster as STRUCTURAL (P1 AND P2 pass) or FREQUENCY-RANKED (either P1 or P2 fail).
4. Compute the structural-cluster percentage = N_structural / N_surfaced.
5. Report verdict per §1 criteria (VALIDATED / PARTIALLY VALIDATED / NOT VALIDATED).

## 5. Why this predicate is honest

- **Pre-registered before data exists.** The verdict isn't a post-hoc story.
- **Falsifiable.** Frequency-rank clusters DON'T pass; structural-shell clusters DO. Both outcomes are observable.
- **Threshold-explicit.** 40% intra-cluster shell-consistency + centroid agreement + 30% structural-clusters-of-surfaced. Not "many" / "most" / "some" — numbers.
- **Shell list pre-published.** The 19 shells are listed BEFORE the data is seen. The author cannot retro-pick shells to match observed clusters.
- **Anticipated failure mode named.** §3's frequency-rank null is the OBVIOUS failure mode the predicate is hardest against.
- **Three-band verdict.** Strong, partial, none — refuses the binary trap.

## 6. Layer-5 reframing branches

The cycle-14+ reframing fork:
- **NOT VALIDATED (<30%):** canonical-doc Layer 5 honest reframe to "trigram pattern mining" (audit C3). Layer 5 stops claiming "variable-binding primitive induction" until different machinery (role-filler binding clusters, longer-n-gram + dependency parse, semantic-encoder) is shipped.
- **PARTIALLY VALIDATED (30-60%):** Layer 5 keeps the framing AS APPLIED to the structural-cluster subset; doc explicitly carries the structural-cluster percentage as the falsifiability anchor.
- **STRONGLY VALIDATED (>60%):** Layer 5 framing survives. Cycle-14 can build atop primitive emergence with calibrated confidence.

---

## 7. Result block (TO BE APPENDED AFTER THE RUN — RESERVED)

*This section is INTENTIONALLY EMPTY at predicate commit. Cycle-13 #07f-run will append the result data + classification table + verdict. Predicate authority is the version-controlled state at the commit hash this doc is written under.*

---

*Single-line takeaway: cycle-13 #07f-pre commits the test (this doc), cycle-13 #07f-run runs the experiment and appends the verdict (next commit). The predicate constrains the verdict; the verdict constrains cycle-14 Layer-5 framing.*
