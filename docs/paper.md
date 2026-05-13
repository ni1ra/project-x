# Project X: How Raphael Works — A Field Guide

*For lain. Read it, argue with it, run it through NotebookLM and listen while you walk.*

---

## At a Glance

**What has been built.** Organic memory layer (HDC). A hand-rolled reasoning scaffold across fourteen problem shapes with cross-checks. The first piece of genuine learning machinery (TemporalTraceBank + hidden-rule benchmark).

**What you can verify today.**
- 679 tests pass. Mechanical benchmark audit: 48 PASS / 0 FAIL.
- Held-out hidden-rule benchmark on seed=1729: 75% pass rate (9 of 12), +75pp over random.
- Killer Milestone (memory): teach, correct, multi-hop, refuse, act — all green.

**What you CAN'T do yet.**
- No always-on chat loop. You cannot actually talk to Raphael yet.
- Math and physics capability comes from hand-coded primitives, not from learning.
- No conversational training corpus. No conversational quality rubric harness.
- Cross-seed variance on the hidden-rule benchmark is wide (~33%–83%).

**What's next.** Substrate v1 hardens the learning machinery (cross-seed reliability, non-linear scoring, scaled task packs, HebbianBank integration). In parallel, bootstrap a chat loop so chattability becomes measurable for the first time.

**The dream.** A continuous entity you can talk to whose voice has the qualities of Claude — clear, articulate, honest about uncertainty, register-aware — and whose capability comes from what it *learned*, not what was typed into a Python file. Cycle by cycle, the ratio shifts.

---

## Prologue: The Conversation

This whole thing started because you asked a question. Not "build me a chatbot." Not "make something that sounds smart." You asked: *can we build an intelligence that learns on its own, from experience, without us telling it what tools to use?*

That question is why Project X exists. Everything in this repository — every line of code, every benchmark, every test — is an attempt to answer it honestly.

This document is the story so far. Not a sales pitch. Not a research paper with tables you can skim. It is a field guide to an organism we are growing. Chapter by chapter, you see what has been built, why it was built that way, what it can actually do today, and what still needs to happen before it earns the name Raphael.

Every claim here is backed by code you can run. Every limitation is admitted upfront. The goal isn't to impress you. It's to give you a clear enough picture that you can spot where we're wrong.

---

## Chapter 1: The Shortcut Everyone Takes

Right now, every AI you can buy is basically the same architecture under the hood. Take a massive pretrained transformer — GPT, Claude, Gemini — wrap it in a retrieval system so it can look things up, and sell access. This works. It generates value. It writes emails and summarizes papers and passes the bar exam.

But the wrapper pattern has three properties that matter for what we are trying to build.

**Property 1 — the foundation is a black box.** You cannot look inside and see what it knows. When you ask "do you remember our conversation from Tuesday?" the model might say yes, but you have no way to verify that against its actual internal state. In the relevant sense, there *is* no internal state. A transformer's "memory" is just the attention pattern over its current context window. When the window slides, the memory is gone. You can bolt an external database onto the side, but the transformer itself doesn't know what is in there until you paste it back into the prompt.

**Property 2 — the persona is statistical.** The voice you hear — Claude's tone, GPT's helpfulness — is a stable pattern in how the model responds, but the stability is shallow. The right adversarial prompt can shift the persona entirely. The model doesn't have something to defend. It has a probability distribution that gets sampled.

**Property 3 — the reasoning is hidden.** When a transformer solves a math problem and shows its work, the work is text it generated. Sometimes that text faithfully traces the computation. Sometimes it is a post-hoc rationalization — the model emits a reasoning-style trace because reasoning traces appeared in its training data. From the outside, you cannot tell which is which.

For most use cases, none of this matters. The wrapper-around-a-transformer pattern delivers. But you asked for something different. You wanted a system with memory it can introspect, an identity it can defend, and reasoning it can show its work on — where the work is the actual computation, not a generated narrative.

That goal is only achievable if we do not take the shortcut.

So an early architectural choice was made: build the stack organically from the bottom up. From-scratch encoders. From-scratch reasoning primitives. No language-model wrappers at any load-bearing layer. The result is slower to build, less impressive in a five-minute demo, and harder to sell as cutting-edge AI. But the resulting system has properties the wrapper pattern doesn't.

That's the trade. The rest of this guide is how we are making it.

---

## Chapter 2: Memory as a Landscape

The first problem was memory. Before reasoning, before chat, before anything else — if Raphael was going to be your all-knowing internal computer, it had to remember things across turns without resorting to a transformer's attention pattern.

The answer is called Hyper-Dimensional Computing, or HDC. The idea is strange at first, but once it clicks, everything else makes sense.

Imagine every concept in the world has a coordinate in a very high-dimensional space — say ten thousand dimensions. Not 2D or 3D. Ten thousand. Related concepts have nearby coordinates. Unrelated concepts have coordinates that point in completely different directions.

To store a memory, you take the coordinate of the thing you want to remember and add it to a running total that represents everything Raphael knows. To retrieve, you take the coordinate of your query and ask: which part of the running total is most similar to this?

Here is the part that makes it work. In 2D or 3D, adding a thousand vectors together would create an unreadable smear. Everything would overlap and cancel out. But in ten thousand dimensions, geometry behaves differently. Random vectors are almost always pointing in nearly-perpendicular directions. When you add a thousand of them together, each one's contribution is still recoverable — because the "noise" from all the others averages out to near zero. It is counter-intuitive. But it is the mathematical bedrock of the entire system.

```
HDC retrieval (simplified):

  Query "Mary":  [+,−,+,+,−,...]  (10,240 ±1 entries)
                       │
                       │  cosine similarity
                       ▼
  Bundle of all stored facts:  [+,−,+,−,−,...]
                       │
                       ▼
  Top match: "Mary bought a car (turn 14)"
                       │
                       │  fact-graph narrows to turns about "Mary"
                       ▼
  Cited response: "From turn 14: Mary bought a car."
```

Two layers sit on top of this geometry.

**The encoder** turns text into coordinates. Pretrained transformer embeddings would violate the organic thesis, so the encoder is custom: character-n-gram hashing splits words into overlapping three-letter chunks and hashes each chunk to a random direction. "dog" and "dogs" produce nearby coordinates because they share most of their chunks. Hebbian co-occurrence tracks which words appear near each other in text and uses those statistics as a side channel. Words that show up in similar contexts get nearby coordinates even if they share no letters. Combining the two handles paraphrase queries that pure keyword matching would miss.

**The memory store** is the running total, plus a side structure called a fact-graph. The fact-graph is more traditional — for every named subject Raphael has seen, it keeps a list of which turns mentioned that subject. When you ask "what did Mary buy?", the fact-graph narrows to the turns about Mary, and the HDC accumulator ranks those turns by relevance to "buy." Two retrieval modes working together: associative for paraphrase, structural for multi-hop connections.

A third primitive called **binding** handles compositional queries. It lets Raphael store "Mary's job is engineer" as a single bundled coordinate that can be decomposed back into its parts. When you ask "what is Mary's job?", binding extracts just the role-filler part associated with Mary's identity. Structured queries without storing relational data as explicit tables.

By Phase 10, five capabilities were verified mechanically through a benchmark called the Killer Milestone:

- **Teach** — tell Raphael a new fact and retrieve it with the source citation.
- **Correct** — update a fact and have the correction override the old one.
- **Multi-hop** — chain through connections: "what did the person who bought the car also buy?"
- **Refuse** — say "I don't know" when no evidence exists, rather than making something up.
- **Act** — run a tool, capture the result, and write it back into memory as a new turn.

That last one is crucial. Raphael is not a passive database. It closes the loop between reading the world and updating its knowledge.

**Run this to see it work:**
```bash
PYTHONPATH=src python3 gpt-codex/benchmark/run_audit.py | grep memory
```

---

## Chapter 3: Learning by Living

Memory was the foundation. But memory alone is not intelligence. Intelligence is the ability to learn from experience — to try something, observe the result, and do better next time.

This is where most AI systems stop. They have memory, but they don't have *learning* in the sense of action-selection. They retrieve. They don't discover. The Terminus Learning Harness is our attempt to bridge that gap.

Here is the experiment. We show Raphael a card with some words on it — things like `focus:color` and `color:red` — and four possible actions: A, B, C, D. It has no idea which action is correct. It picks one. If it's wrong, it gets a small penalty. If it's right, it gets a reward. Over many trials, it starts to notice patterns.

The critical part: nobody programmed the rules. The code does not contain a lookup table saying "red means press A." The system only contains the *machinery for learning* — sparse tables that accumulate reward-weighted associations between features and actions. The knowledge lives in the numbers, not in the code.

```
TemporalTraceBank — three conjunction layers, one observation:

  Observation = { focus:color, color:red, distractor:smooth, distractor:loud }
  Action      = A
  Reward      = +1.0 (correct)

  Singleton updates (one feature → action):
    focus:color       → A   weight += 1.0
    color:red         → A   weight += 1.0
    distractor:smooth → A   weight += 1.0   (noise — dampens later)
    distractor:loud   → A   weight += 1.0   (noise — dampens later)

  Pair updates (two features together → action; more reliable):
    {focus:color, color:red}         → A   weight += 1.0
    {focus:color, distractor:smooth} → A   weight += 1.0   (less reliable, fewer hits)
    ...

  Triplet updates (most reliable, sparsest):
    {focus:color, color:red, distractor:smooth} → A   weight += 1.0

  Score(action | observation) = Σ over (conjunction ⊆ observation) of
                                  ( weight / update_count )
                                            ^^^^^^^^^^^^
                            average-weight scoring dampens noisy frequent features
```

Every observation is a set of feature atoms — words like `phase:probe` or `focus:shape` or `texture:smooth`. When Raphael takes an action and gets rewarded, the system strengthens the connection between every feature in that observation and the action that succeeded. It also strengthens connections between *pairs* of features and the action, and even *triplets*. This matters because a single feature like `color:red` might appear in many different contexts — sometimes as the important clue, sometimes as a distraction. The *pair* `focus:color + color:red` almost always means the same thing. The pair is a more reliable signal than either feature alone.

The innovation that made this actually work is called **average-weight scoring**. Early versions simply added up all the feature weights, which meant frequent but noisy features could overwhelm rare but reliable ones. Average-weight scoring divides each feature's total weight by how many times it has been updated. A feature that appears in a hundred contexts with mixed results gets dampened. A feature that appears in three contexts with consistent results gets amplified. Simple trick, complete behavior change.

The benchmark has forty-eight tasks. Thirty-six are training tasks — Raphael explores them, makes mistakes, learns from rewards. Twelve are held-out tasks — same underlying rules, different combinations of features Raphael has never seen before. After training on seed=1729, Raphael solves nine of the twelve held-out tasks correctly. Seventy-five percent — far from perfect, but dramatically better than random guessing, which would get essentially zero.

The three failures are honest. In each case, the random distractor features created a correlation the linear model couldn't fully disambiguate. We know exactly why it fails, which means we know what to build next: a non-linear gating mechanism that can suppress distracting features when a stronger signal is present. That is the substrate v1 work.

But the harness already proves the core claim. **The system learned which action to take by trying, failing, and improving — not by being told the rules.** That is the first time Project X has demonstrated genuine action-learning from experience.

**Run this to see it work:**
```bash
PYTHONPATH=src python3 scripts/terminus_learning_harness_demo.py --mode test
```

---

## Chapter 4: Training Wheels

While the learning machinery is maturing, Raphael still needs to solve problems today. That is where the reasoning substrate comes in — a collection of hand-rolled mathematical and physical primitives that produce structured derivations.

The word "hand-rolled" needs context. These primitives are not the final intelligence. They are **scaffolding** — training wheels that let us evaluate the agent's outputs while the learning substrate develops. The long-term goal, as you put it, is that Raphael should learn the quadratic formula from worked examples and audit signal, not find it hard-coded in a Python file. Until the learning substrate reaches that level, the hand-coded primitives serve as gold-standard oracles — the learned model's outputs are compared against them to measure progress.

Here is what a primitive looks like in practice. You ask Raphael to solve `3x² − 14x − 5 = 0`. Internally, a substrate function takes the three coefficients and returns a Lemma — a structured object with a claim, a chain of derivation steps, and a final answer.

Step 1: compute the discriminant. Step 2: take its square root. Step 3: apply the quadratic formula. Each step has a justification in plain English. The final answer is `[−1/3, 5]`.

But the Lemma also contains something stronger: an **invariant check**. A separate computation, using a completely different algorithm, verifies the same result.

```
The invariant pattern:

  Problem:  3x² − 14x − 5 = 0
                  │
                  ▼
  Primary path:   discriminant → √ → quadratic formula → roots [−1/3, 5]
                  │
                  ▼
  Independent check (Vieta's formulas):
                  sum   = −1/3 + 5 = 14/3   should equal  −b/a = −(−14)/3 = 14/3   ✓
                  prod  = −1/3 × 5 = −5/3   should equal  c/a  = −5/3              ✓
                  │
                  ▼
  Lemma certified — return roots [−1/3, 5]
```

This pattern repeats across every primitive. Residue theorem integrals are cross-checked with Simpson's numerical quadrature. Definite integrals are cross-checked with Riemann sums. Exponential solutions to differential equations are cross-checked with Taylor series expansions. The 3×3 determinant is computed via Laplace cofactor expansion and independently verified with Sarrus' rule.

Every answer comes with a derivation, and every derivation includes at least one cross-check from a different mathematical path. That is the substrate's contract.

The scaffold currently covers: quadratics, 2×2 eigenvalues, 3×3 determinants, residue theorem integrals, polynomial definite integrals, first-order ODEs, integration by parts, u-substitution, free-fall kinematics, simple and large-angle pendulum periods, relativistic momentum, projectile motion, relativistic Doppler shift, bounded Diophantine enumeration. Each is implemented using only Python's standard math library — no sympy, no scipy, no shortcuts.

There is also a category of problems at the unsolved frontier — Collatz, Goldbach, twin primes, the Mertens bound. The trap here is obvious: if Raphael iterates Collatz for the first thousand integers and they all reach one, the headline could read "AI verifies Collatz conjecture." That would be an overclaim. The conjecture is open. No one has proved it. What Raphael can do is say, honestly: "verified for [1, 1000]." The framing is baked into the substrate at every level — the claim, the justification, the audit status all carry the same constraint. **The architecture is designed to make overclaim hard.**

---

## Chapter 5: How Raphael Reads the World

With memory and reasoning in place, the next question is: how do they connect? When you give Raphael a math problem in English, how does the right primitive get invoked?

A dispatcher does this work — a pattern-matching system that reads the prompt, recognizes which problem shape it resembles, extracts the parameters, and routes to the corresponding substrate function. It is regex-based and keyword-gated, not powered by a language model. Brittle in some ways — unusual phrasing can cause a mismatch — but failures are loud and honest. When no pattern matches, Raphael returns a structured refusal: "I don't recognize this problem shape." No confabulation. No attempt to force an answer.

The dispatcher currently handles fourteen problem shapes. Each has multiple recognition gates to prevent misrouting. If you phrase a quadratic in a way the regex does not catch — say, using a unicode superscript instead of ASCII — the dispatcher fails. The most common patterns are fortified against typography variations, but comprehensive parser robustness across all shapes is still on the roadmap.

The cost of this choice is clear: less flexibility than an LLM-powered parser. The benefit is equally clear: when it fails, you know exactly why. There is no quiet misrouting where the wrong tool is applied to the right problem and produces a plausible-looking wrong answer.

**Important caveat.** The dispatcher is scaffold, not architecture. Per the MANIFESTO, routing decisions must EMERGE from learned experience over time, not from regex patterns. The dispatcher is what runs today; the learning substrate will eventually replace it. When `TemporalTraceBank` learned to pick action A from `focus:color + color:red`, it solved a miniature version of the same problem. Scaling that mechanism is how routing eventually moves from regex to learned policy.

---

## Chapter 6: The Architecture of Honesty

How do we know what Raphael can actually do, as opposed to what we hope it can do? This is the third leg of the architecture, alongside memory and reasoning. Project X has more anti-self-deception machinery than capability machinery, by design.

### The benchmark has two kinds of entries

**Mechanical-ground-truth entries** have definite answers — a specific number, vector, or set. Solve this quadratic. Compute this integral. These entries carry an auto-grade block with the expected answer and a tolerance for floating-point comparison. The harness verifies them automatically.

**Rubric-pending entries** have subjective answers — write a haiku, analyze a philosophical question, defend a persona under pressure. These entries CANNOT carry a self-score from the agent, because the system that generates the answer cannot be trusted to grade it fairly. They carry a pointer to a rubric document, and the grade comes from external review. This is the **split-grading firewall**: the architecture refuses to grade itself on subjective work.

The firewall is enforced mechanically. A grep across all benchmark files looking for `self_score` fields will fail the build if it finds one. Not a guideline. A gate.

### The invariant cross-checks

Every math and physics primitive returns a Lemma carrying its own independent verification path (Chapter 4). If the primary path has a bug, the invariant catches it. If both paths agree, the answer is reported. If they disagree, the Lemma is flagged. The architecture prefers "I don't know" over a wrong answer with confidence.

### The refusal patterns

When the dispatcher does not recognize a problem, Raphael returns a structured refusal naming what it did not understand. When the memory has no evidence for a query, it returns "I don't know" with the empty result cited as evidence. When a domain is rubric-pending, the output never carries a confidence score. These three refusal patterns close the major confabulation vectors.

### What could still fool us — honest by domain

- **Math and physics.** The invariant could agree with the primary path because both share the same bug. Mitigation: algorithmically-independent methods (discriminant vs. Vieta, residue vs. Simpson). Not bulletproof. A determined adversary could construct a problem where both paths fail the same way.
- **Memory.** The HDC bundle is fuzzy. Two facts that share many features could produce a confused retrieval. Mitigation: fact-graph structural lookup. Still possible the wrong turn surfaces with high confidence.
- **Learning.** The hidden-rule benchmark is small (48 tasks). Cross-seed variance is wide (~33%–83%). The 75% number is one seed. A bigger benchmark and a cross-seed sweep are exactly what v1 attacks.
- **Chattability.** No chat loop runs yet, so no probe has run. The dream is unmeasured, which means *we currently have no way to falsify claims about it*. The next cycle fixes this.

The audit harness replays every mechanical entry against the live agent on every commit. As of this writing, forty-eight auto-graded entries pass with zero failures. Breakdown: twenty-two mathematics, fifteen memory, eleven physics. The subjective entries — poetry, philosophy, persona — remain rubric-pending, awaiting external grades.

**Run this to verify:**
```bash
PYTHONPATH=src python3 gpt-codex/benchmark/run_audit.py
```

---

## Chapter 7: What Raphael Can Do Right Now

Concrete examples to ground all of this.

| You ask | Raphael does | Where it lives |
|---|---|---|
| Solve `3x² − 14x − 5 = 0` | Returns `[−1/3, 5]` with three-step derivation and Vieta cross-check | `solve_quadratic` |
| Eigenvalues of `[[2,1],[1,2]]` | Returns `[1, 3]` with characteristic polynomial, trace, determinant verified | `eigenvalues_2x2` |
| Determinant of a 3×3 | Cofactor expansion + Sarrus cross-check | `determinant_3x3` |
| Evaluate an integral via residue theorem | Identifies pole, computes residue, applies theorem, numerical cross-check | `residue_theorem` |
| Solve a first-order ODE at a target point | Separates variables, integrates, applies initial condition | `solve_ode` |
| Memory question after teaching a fact | Retrieves the fact with the turn ID cited as source | `SemanticHDCMemory.query` |
| Something it does not know | Honest refusal, no confabulation | structured refusal |
| Learn a hidden rule from feedback | After 36 training trials, solves 9 of 12 held-out cards on seed=1729 | hidden-rule benchmark |

**What you CAN'T do yet.**

- Talk to Raphael in conversation. No chat loop exists. The next cycle bootstraps one.
- Ask it about anything outside the fourteen problem shapes the dispatcher recognizes. Anything else returns a structured refusal.
- Trust the math and physics answers as "learned." They are scaffold. Honest at the answer level — but the capability is hand-coded, not earned.

---

## Chapter 8: The Dream — Speaking Like Claude

Here is what has not been built yet: a continuous entity you can actually talk to.

You named the dream on 2026-05-13: *"a truly chattable, talkable entity. that can speak like you, claude."* The Terminus in the MANIFESTO already names "Always-on chattability" as a required criterion. This chapter decomposes what that means and how we will know we got there.

**What does "speak like Claude" actually mean?** Not "use Claude's API behind the scenes" — that violates the thesis. The qualities split into two halves: the *defensive* qualities (don't fail like a bad chatbot) and the *generative* qualities (what actually makes Claude's voice feel like Claude's).

**Defensive qualities:**

- **Clarity.** Says one thing well rather than three things vaguely.
- **Calibrated uncertainty.** "I don't know" when no evidence exists. Not weasel words. Not hallucination.
- **Register-awareness.** Technical question gets a technical answer; casual question gets a warm casual one.
- **Reasoning on demand.** Visible chain-of-thought when asked, not when not asked.
- **Persona stability.** Adversarial probes do not flip the voice.
- **Clean refusal.** Out-of-scope or harmful requests get a brief calibrated decline, not a moralizing essay.

**Generative qualities (the hard ones — without these the agent passes a bad-chatbot test while still sounding nothing like Claude):**

- **Clarifying-question reflex.** Given an ambiguous prompt, asks ONE targeted clarifying question rather than guessing.
- **Concrete-example reflex.** When explaining a concept, reaches for an analogy or specific example rather than abstract definitions.

These eight properties become the measurable rubric — eight pass/fail tests any chat probe can score. Today's baseline is 0/8 because no chat loop exists to test against. **The dream has not moved until at least one generative criterion is passing.**

**How we get there.**

1. **Bootstrap the chat loop.** Local REPL first; then a **standalone Discord-bot process** for the "always-on" property — its own Python script running `discord.py` against the Discord REST API, NOT a Claude-Code-session wrapper. (The MANIFESTO § Identity Discipline makes this distinction binding: Project X Raphael speaks; Claude Code Raphael only writes and tests the code.) Both layers wired to the existing `ReasoningAgent` + `SemanticHDCMemory` + template generator. No new templates. No LLM smuggled in via a tool call. Just a pipe from prompt to substrate to response.
2. **Run a 10-prompt probe.** Ten prompts covering all eight criteria, with 2-3 hitting the generative ones (clarifying-question, concrete-example). Save the transcripts. Score honestly — passing tests + 1-line evidence per test.
3. **Label what is learned vs. scaffold.** The first chat loop will be ~95% template, ~5% learned (the substrate picks fragments via HDC retrieval). That is honest. The verdict says so explicitly.
4. **Build the corpus.** Without conversational training data, no learned generator can emerge. The probe transcripts are the seed; v2 scales the corpus.
5. **Train the generator.** Eventually, response composition migrates from template-stitching to substrate-emergent generation, the way `TemporalTraceBank` made action-selection emergent.

**The integrity rule.** Every cycle's verdict reports the chattability score (N of 8) AND the learned-vs-template ratio. If the score goes up but the ratio does not shift toward learned, we are gaming the rubric. **The number that matters most is not the rubric — it is the trajectory of the ratio.**

**A note on parallel tracks.** Substrate v1 (TemporalTraceBank improvements) and chat-loop v1 (REPL + Discord bot + template generator) are largely *parallel* this cycle, not sequential. The substrate work hardens action-learning on the hidden-rule benchmark; the chat loop wires existing components into a conversation. They converge in v2/v3, when `TemporalTraceBank` becomes a response-selection mechanism inside the chat loop — but that's later work. Be honest about this in the verdict. The substrate is not "carrying the chat loop on its back" yet.

---

## Chapter 9: From Here to the Terminus

This is the trajectory ahead.

**The memory layer works.** HDC binding, bundling, retrieval, fact-graph navigation, and incremental write are all verified and load-bearing.

**The reasoning scaffold works.** Fourteen problem shapes with structured derivations and algorithmically-independent cross-checks. Every answer is auditable.

**The learning machinery works at v0.** The first genuine action-learning from rewarded experience. Three failure modes are identified and v1 attacks them.

**The honesty architecture works.** Refusals instead of confabulations. External grading instead of self-grading. Scope boundaries instead of overclaim.

**What is left.**

| Capability | Today | What is needed |
|---|---|---|
| Hidden-rule action-learning | 75% on seed=1729; ~33%–83% across seeds | v1: cross-seed sweep, non-linear scoring, scaled task packs, HebbianBank wire |
| Always-on chat loop | none | Discord-bot bootstrap; 10-prompt probe; six-criteria rubric |
| Math and physics from learning | 0% learned | Conversational + worked-example corpora; learned generator; scaffold retirement |
| Persona consistency under load | unmeasured | Adversarial probe added to chat-loop tests |
| Million-turn coherence | unmeasured | Long-horizon eval pack; designed after chat loop ships |

**The migration plan.** Each scaffold piece gets retired the same way:

1. The learned model trains alongside it.
2. The audit harness reports both outputs.
3. When the learned model matches or beats the scaffold on held-out tasks across multiple seeds, the scaffold moves to `legacy/` as a historical control.
4. The learned model becomes the primary path. The audit invariants stay.

The math primitives are first in line. The dispatcher is next. The template generator goes last, after the conversational corpus is large enough and the learned generator is good enough to take over. **None of these get thrown away** — they become the gold-standard against which the learned model is judged, forever.

Beyond that: learned tool selection, learned algorithms, learned reasoning strategy, learned persona and composition. Each layer earns its place by being load-bearing for the next. None are throwaways.

**There is no should — there is the vector, and those of us carried along it.** This is what you chose to do with the ride.

---

## Glossary

- **HDC** (Hyper-Dimensional Computing) — representation scheme using 10,000+ dimensional bipolar vectors where related concepts have similar coordinates.
- **VSA** (Vector Symbolic Architecture) — synonym for HDC in the literature.
- **Bipolar vector** — vector whose entries are ±1; cheap to store, robust to noise.
- **Bundling** — adding vectors together to form a superposition. Encodes "and" semantics.
- **Binding** — multiplying vectors element-wise to form a compositional key-value pair. Encodes "X has value Y" semantics.
- **Fact-graph** — auxiliary structure mapping named subjects to the turns that mention them. Provides structural retrieval alongside HDC associative retrieval.
- **Hebbian co-occurrence** — encoder side-channel that strengthens coordinate similarity between words appearing in similar contexts.
- **K-rollout** — exploration mechanism that samples K candidate continuations and picks the one with the highest audit signal.
- **Lemma** — structured object returned by substrate functions: claim + derivation steps + cross-check + final answer.
- **Invariant check** — independent computation, using a different algorithm, that verifies a primary derivation's result.
- **Dispatcher** — regex-based router that maps prompts to substrate functions. Brittle but loud-failing. Will be replaced by learned policy.
- **TemporalTraceBank** — the learning substrate's first piece. Accumulates reward-weighted associations between feature conjunctions (singleton, pair, triplet) and actions.
- **Average-weight scoring** — TemporalTraceBank's anti-noise mechanism. Divides each conjunction's total weight by update count so frequent-but-noisy features get dampened.
- **Eight chattability criteria** — six defensive (multi-turn coherence, honest uncertainty, register-shift, reasoning on demand, persona stability, clean refusal) and two generative (clarifying-question reflex, concrete-example reflex). The seed rubric for "speaks like Claude."
- **Learned-vs-hand-coded ratio** — every cycle reports the fraction of agent capability that comes from the learned model vs. from hand-coded primitives. The integrity number.
- **Scaffold** — hand-coded primitives that bridge the gap until the learned model matches them. Stay in the repo as gold-standard oracles.
- **The Terminus** — the project's exit condition: super-human across math, poetry, philosophy, physics; perfect memory; persona consistency + humor; always-on chattability; sandboxed action-taking.

---

## How to Verify Every Claim

```bash
# Full test suite (~679 tests pass)
PYTHONPATH=src python3 -m pytest -q

# Mechanical benchmark audit (48 / 48)
PYTHONPATH=src python3 gpt-codex/benchmark/run_audit.py

# Hidden-rule learning demo (75% held-out on seed=1729)
PYTHONPATH=src python3 scripts/terminus_learning_harness_demo.py --mode test

# Learning substrate unit tests
PYTHONPATH=src python3 -m pytest tests/test_temporal_trace_bank.py tests/test_hidden_rule_actions.py -q
```

If any of these claims does not replicate, the paper is wrong. Tell us.

---

*Last updated: 2026-05-13. The Project X repository at `/home/nira/Research/projext-x` is the source of truth.*
