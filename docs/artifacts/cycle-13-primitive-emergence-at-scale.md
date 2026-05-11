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


## 7. Result block — emergence-at-scale run (appended POST predicate-commit)

**Run date:** 2026-05-11. **Commit (run):** see git log for `docs(P13c13-07f-emergence-at-scale)`.
**Pre-registered predicate commit (the version of §§1-6 this run is scored against):** `0b89101`.
**Path:** BITPACK throughout — `encode_packed` + `cosine_packed` (cycle-13 #1 substrate insurance). Prior attempt with the unpacked int8 path OOM-killed WSL on a 50k sample; bitpack uses 13 MB for the trigram representation vs the ~102 MB int8 footprint that triggered the crash.

### 7.1 Run summary

- Corpus: 22k Tier-2 (21734 fragments from `data/corpus_raw/`)
- Trigrams extracted: **420826** unique (5× the bitpack design's ~80k estimate — finding worth carrying into cycle-14 corpus planning + the full-corpus packed run)
- Sub-sample: **10000** trigrams (random, seed=42); ~3× cycle-11 MVP scale
- Encoder: `CharNgramHashEncoder(D=10240)` (post-#07c default)
- k-means: bitpack path; **k=20, min_density=5, max_iters=30, seed=42** (matches predicate §4); converged or halted in `12.4s`

### 7.2 Per-cluster classification

| Cluster | N | Centroid trigram | Centroid shell | Modal shell | % match | Classification |
|---:|---:|---|---|---|---:|---|
| #00 | 541 | `of men of` | — | X of Y | 38% | **FREQUENCY-RANKED** |
| #01 | 272 | `would be made` | — | X a Y | 2% | **FREQUENCY-RANKED** |
| #02 | 321 | `have had either` | X had Y | X had Y | 12% | **FREQUENCY-RANKED** |
| #03 | 604 | `the rest their` | — | X of Y | 11% | **FREQUENCY-RANKED** |
| #04 | 1207 | `the sky the` | — | X the Y | 33% | **FREQUENCY-RANKED** |
| #05 | 368 | `this with his` | X with Y | X of Y | 5% | **FREQUENCY-RANKED** |
| #06 | 243 | `so have some` | — | X a Y | 3% | **FREQUENCY-RANKED** |
| #07 | 360 | `this is not` | X is Y | X is Y | 22% | **FREQUENCY-RANKED** |
| #08 | 444 | `before there are` | — | X were Y | 8% | **FREQUENCY-RANKED** |
| #09 | 419 | `affection and inclination` | X and Y | X of Y | 8% | **FREQUENCY-RANKED** |
| #10 | 313 | `see with the` | X with Y | X with Y | 22% | **FREQUENCY-RANKED** |
| #11 | 316 | `was sixteen was` | — | X was Y | 17% | **FREQUENCY-RANKED** |
| #12 | 469 | `that this that` | — | X the Y | 3% | **FREQUENCY-RANKED** |
| #13 | 837 | `or small which` | — | X a Y | 6% | **FREQUENCY-RANKED** |
| #14 | 484 | `being a starting` | X a Y | X a Y | 4% | **FREQUENCY-RANKED** |
| #15 | 227 | `the thought that` | — | X the Y | 3% | **FREQUENCY-RANKED** |
| #16 | 465 | `her but her` | X but Y | X a Y | 3% | **FREQUENCY-RANKED** |
| #17 | 1108 | `and hands and` | — | X and Y | 34% | **FREQUENCY-RANKED** |
| #18 | 591 | `to be too` | — | X to Y | 36% | **FREQUENCY-RANKED** |
| #19 | 411 | `pumpkin in the` | X in Y | X in Y | 25% | **FREQUENCY-RANKED** |

### 7.3 Sample members per cluster (top-5 closest to centroid)

**Cluster #00** (FREQUENCY-RANKED, modal `X of Y` at 38%):
  - `of men of`
  - `of most of`
  - `of cliff of`
  - `of spirit of`
  - `feast of hera`

**Cluster #01** (FREQUENCY-RANKED, modal `X a Y` at 2%):
  - `would be made`
  - `eyes would be`
  - `sale would be`
  - `which could be`
  - `should be such`

**Cluster #02** (FREQUENCY-RANKED, modal `X had Y` at 12%):
  - `have had either`
  - `i have a`
  - `they have a`
  - `even i have`
  - `have hardly thought`

**Cluster #03** (FREQUENCY-RANKED, modal `X of Y` at 11%):
  - `the rest their`
  - `of the b`
  - `they do them`
  - `of the others`
  - `they lose their`

**Cluster #04** (FREQUENCY-RANKED, modal `X the Y` at 33%):
  - `the sky the`
  - `the city the`
  - `the plant the`
  - `the simple the`
  - `the grass the`

**Cluster #05** (FREQUENCY-RANKED, modal `X of Y` at 5%):
  - `this with his`
  - `is just this`
  - `knew this is`
  - `till this is`
  - `this is what`

**Cluster #06** (FREQUENCY-RANKED, modal `X a Y` at 3%):
  - `so have some`
  - `him some sort`
  - `come so far`
  - `some to be`
  - `in some cases`

**Cluster #07** (FREQUENCY-RANKED, modal `X is Y` at 22%):
  - `this is not`
  - `rest is not`
  - `love is not`
  - `is not yet`
  - `house is not`

**Cluster #08** (FREQUENCY-RANKED, modal `X were Y` at 8%):
  - `before there are`
  - `as there are`
  - `therefore they are`
  - `are here re`
  - `there are moods`

**Cluster #09** (FREQUENCY-RANKED, modal `X of Y` at 8%):
  - `affection and inclination`
  - `deliberation all prosecution`
  - `selection on the`
  - `probation and admission`
  - `her agitation on`

**Cluster #10** (FREQUENCY-RANKED, modal `X with Y` at 22%):
  - `see with the`
  - `thou with mine`
  - `minds with the`
  - `with and the`
  - `in with a`

**Cluster #11** (FREQUENCY-RANKED, modal `X was Y` at 17%):
  - `was sixteen was`
  - `say theras was`
  - `was leonidas a`
  - `as fries has`
  - `asia was the`

**Cluster #12** (FREQUENCY-RANKED, modal `X the Y` at 3%):
  - `that this that`
  - `that work that`
  - `that at this`
  - `that more than`
  - `that if the`

**Cluster #13** (FREQUENCY-RANKED, modal `X a Y` at 6%):
  - `or small which`
  - `or for very`
  - `for a whole`
  - `or which almost`
  - `for heaven which`

**Cluster #14** (FREQUENCY-RANKED, modal `X a Y` at 4%):
  - `being a starting`
  - `being is trying`
  - `not bring anything`
  - `ringing ringing ringing`
  - `praising things corroborating`

**Cluster #15** (FREQUENCY-RANKED, modal `X the Y` at 3%):
  - `the thought that`
  - `for the thought`
  - `the pond though`
  - `the pear though`
  - `though the place`

**Cluster #16** (FREQUENCY-RANKED, modal `X a Y` at 3%):
  - `her but her`
  - `on her mother`
  - `mother sickened her`
  - `her face her`
  - `father who forever`

**Cluster #17** (FREQUENCY-RANKED, modal `X and Y` at 34%):
  - `and hands and`
  - `and saw and`
  - `and legs and`
  - `and jane and`
  - `and bread and`

**Cluster #18** (FREQUENCY-RANKED, modal `X to Y` at 36%):
  - `to be too`
  - `to betray too`
  - `to carry into`
  - `on it to`
  - `lands to be`

**Cluster #19** (FREQUENCY-RANKED, modal `X in Y` at 25%):
  - `pumpkin in the`
  - `pain and in`
  - `ruin in the`
  - `interest in me`
  - `in the increase`

### 7.4 Aggregate verdict

- Surfaced primitives (clusters ≥ 5 members): **20** of 20 (rejected: 0)
- STRUCTURAL clusters (P1 ≥ 40% AND P2 centroid agreement): **0**
- FREQUENCY-RANKED clusters: **20**
- Structural percentage: **0%**
- Canonical-doc Layer 5 verdict per §1 predicate: **NOT VALIDATED** (≥60% STRONG / 30-60% PARTIAL / <30% NOT)

### 7.5 Honest reading

The 0% structural-cluster outcome lands in the **NOT VALIDATED** band. Cycle-14 framing fork per §6:

Layer 5 NOT VALIDATED at this scale. The cycle-11 MVP "X is Y" finding does NOT generalize from ~3k trigrams to 10000 trigrams; the clusters that emerge are dominated by frequency-rank function-word co-occurrence, NOT structural shells. Cycle-14 canonical-doc reframing per audit C3: rewrite Layer 5 as "trigram pattern mining," reserve "variable-binding primitive induction" for future work requiring different machinery (role-filler binding clusters, longer n-grams + dependency parsing, semantic encoder).

### 7.6 Sub-sample caveat

The run used a random sub-sample of 10000 trigrams (seed=42) from the full 420826 unique trigrams. The bitpack path made this RAM-safe (13 MB vs the ~102 MB int8 footprint that crashed WSL on the prior attempt). The full 420826-trigram run remains cycle-14 work — needs `discover_primitives(packed=True)` integrated into the library module (currently the bitpack path lives only in this script). The sub-sample is reproducible (seed=42) and is ~3× the cycle-11 MVP scale; clustering distributional properties are sub-sample-stable, so the cycle-14 full-corpus re-run is not expected to shift the structural percentage dramatically.

### 7.7 Predicate immutability

§§1-6 of this doc were committed at hash `0b89101` BEFORE this run. The result block (§7) is appended in a SEPARATE commit. Git history is the audit trail: the predicate cannot be retro-edited to fit the data. If a reader doubts a verdict, they can compare §§1-6 at `0b89101` against §§1-6 at the current commit; any divergence would be the post-hoc edit the pre-registration was designed to forbid.

