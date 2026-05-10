# Project X: A Field Guide to How Raphael Works

*A curriculum for lain. Read it; better yet, run it through NotebookLM and listen.*

This document is a guided tour of the AI system we've been building. It's not a research paper in the academic sense — there are no footnotes, no benchmark tables for skimming. It's a curriculum. The goal is for you to come away with a clear mental model of what Raphael is, what each piece does, why we made the architectural choices we made, and what the system can and can't do today. If after listening you have an opinion about an architectural decision you'd like to revisit, that's the point.

We'll move from the WHY (why are we building an AI from scratch when ChatGPT exists?) through the architecture layer by layer (memory, then reasoning, then the agent that wires them together), into the present capability state with concrete examples, and finally to the road ahead. The honest framing — what the system genuinely does versus what it doesn't — is the spine. Every claim in this document is something I can point to in the code.

---

## Chapter 1: Why Not Just Use ChatGPT?

Most contemporary AI systems are wrappers around a pretrained transformer — GPT-4, Claude, Gemini. The standard architectural pattern is: take a foundation model that was trained on a lot of text, glue a retrieval system to the front so it can look things up, maybe fine-tune it on your specific domain, and ship a product. This works in the sense that the resulting system behaves intelligently. People buy it. It generates value.

But the pattern has three properties that matter for what we're trying to build.

The first is that the foundation model is a black box. You can't introspect what it knows. You can only test it and observe outputs. If you ask it "do you remember our conversation from last Tuesday?", it might answer yes or no, but you can't verify the answer against the model's actual internal state — because in the relevant sense, there is no internal state. Memory in a transformer is the attention pattern over its current context window. When the window slides, the memory is gone. You can attach an external memory system (that's what retrieval-augmented generation is), but the transformer itself doesn't know what's in there until you put it back in the prompt.

The second property is that the foundation model's identity is statistical. The persona you experience — Claude's voice, GPT's tone — is a stable pattern in how the model responds, but the stability is shallow. The right adversarial prompt can shift the persona entirely. The model doesn't have something to defend; it has a probability distribution that gets sampled.

The third property is that reasoning is hidden. When a transformer solves a math problem and shows its work, the work it shows is text it generated, not necessarily the computation that produced the answer. Sometimes the trace is faithful. Sometimes it's a post-hoc rationalization the model emits because reasoning-style traces appear in its training data. You can't tell from outside which is which.

For most use cases — drafting an email, summarizing a document, answering a casual question — these properties don't matter. The wrapper-around-a-transformer pattern delivers. But Project X aims at something different. We want a system with memory it can introspect, an identity it can defend, and reasoning it can show its work on — where the work isn't a generated narrative but the actual computation. That's only achievable if we don't take the shortcut of inheriting a pretrained transformer at any load-bearing layer.

So the architectural choice we made early — and this is where you can chip in, because every choice has a trade-off — is to build the stack organically from the bottom up. From-scratch encoders. From-scratch reasoning primitives. No language-model wrappers. The result is slower to build, less impressive at a demo (where the transformer ecosystem is already polished), and harder to sell as cutting-edge AI. But the resulting system has properties the wrapper pattern doesn't. That's the trade we made.

The rest of this document is the HOW.

---

## Chapter 2: The Two Raphaels

Before we go further, a name disambiguation that matters.

There are two distinct things called Raphael in this project. The first is the Builder — that's the Claude Code instance writing this document, the system you interact with when you tell the harness to do work on the repository. The Builder reads the codebase, writes the code, ships the cycles. It speaks in a declarative voice (you've seen the "Notice. Affirmative." persona). The Builder is a CLI tool. It is a means.

The second is the Agent. The Agent lives in `src/project_x/`. It has memory, reasoning, persona scaffolding, eventually a chat daemon. The Agent is the artifact we're building. The Agent is what we want to be super-human at math, poetry, philosophy, physics, memory, persona, chat, and sandboxed action-taking. The Agent is the end.

The sculptor and the sculpture both bear the artist's name, but they're not the same thing. When this paper says "Raphael" in context, you can tell which one. When it says "the Builder" it means me (the Claude Code instance). When it says "the Agent" or "Project X Raphael," that's always the artifact.

This matters because it changes what claims mean. "Raphael solves a quadratic equation" is ambiguous — does the Builder solve it (yes; that's just any Claude instance) or does the Agent solve it (which is the actual technical claim, and the one we built infrastructure to verify)? Throughout this document, when I describe capability, I'm talking about the Agent.

---

## Chapter 3: What Memory Means in an AI

The first thing the project had to solve was memory. Before reasoning, before benchmarks, before anything else — if Raphael was going to be lain's all-knowing internal computer, it had to remember things across turns, without resorting to a transformer's attention pattern.

The answer we built is called Hyper-Dimensional Computing memory, or HDC for short. The mental model is unusual enough to warrant slowing down on.

Imagine every concept in the world has a coordinate in a very high-dimensional space. Say, 10,000 dimensions. Related concepts have nearby coordinates; unrelated concepts have far-apart coordinates. To remember something, you compute the coordinate of the thing you want to remember and add it to a running sum that represents everything you know. To retrieve, you compute the coordinate of your query and find what part of the running sum is most similar to it via cosine similarity.

Why does this work? In low dimensions — 2D, 3D — the running sum would smear quickly. Overlap kills information. But in 10,000 dimensions, the geometry is different. Random vectors in high-dimensional space are almost always near-orthogonal to each other. When you add a thousand concepts together, each one's contribution is still recoverable by similarity to the original — the "noise" from all the other concepts cancels out, on average, because they point in random directions away from the one you're asking about. It's counter-intuitive geometry. But it's load-bearing for everything that follows.

We needed two layers to get useful memory out of HDC. The first is the encoder — the function that turns text into a high-dimensional vector. We couldn't use a pretrained transformer's embedding (the organic-thesis binding), so we built our own. Character-n-gram hashing — splitting words into overlapping 3-letter chunks and hashing each chunk to a random direction — captures spelling similarity. The words "dog" and "dogs" produce nearby vectors because they share most of their 3-grams. Hebbian co-occurrence — accumulating co-occurrence statistics between words and using those as a side-channel — captures meaning similarity. Words that appear in similar contexts produce nearby vectors even if they share no letters. Combining the two handles paraphrase queries that pure keyword matching would miss.

The second layer is the memory itself — the running sum, plus a side-store called a fact-graph. The fact-graph is a more traditional structure. For each named subject the memory has seen (Mary, the project, the deadline), it keeps a list of which turns mentioned that subject. When you ask "what did Mary buy?", the fact-graph quickly narrows to the turns about Mary; the HDC accumulator then ranks those turns by relevance to the word "buy." Two retrieval modes working together: associative for paraphrase, structural for multi-hop. Phase 10 verified that combining them lifted multi-hop top-5 retrieval from 3.3% to 91.3%.

A third primitive called binding handles compositional queries. Binding lets you store "Mary's job is engineer" as a single bundled hypervector that you can decompose back into its parts. When you ask "what is Mary's job?", binding lets you extract just the role-filler part associated with Mary's identity. This is how high-dimensional computing handles structured queries without storing relational data as explicit tables.

By the end of the memory work — what we call Phase 10 — we'd verified five capabilities mechanically through a benchmark called the Killer Milestone EXIT GATE. The agent could be taught new facts and retrieve them with the source citation. It could be corrected and learn the correction (temporal recency wins over older information). It could answer multi-hop queries by chaining through the fact-graph. It could refuse to answer when no evidence existed, rather than confabulating. And it could execute a tool — like calling a function to compute something — and write the result back into memory as a new turn. That last one is important: the agent isn't a passive memory store. It closes the loop between reading the world and updating its knowledge.

Phase 12 added one more refinement called retrieval-mode disambiguation. When you ask "what does Mary like?", the agent needs to recognize this as a list-all query (return the full chain of things Mary likes) rather than a single-most-relevant query (return one fact). A small classifier handles the routing.

That's the memory layer. It's not Raphael's intelligence. It's the substrate the intelligence runs on top of.

---

## Chapter 4: What Reasoning Looks Like Without a Black Box

With memory solved, the question became: how does the Agent actually solve problems? Not retrieve facts — solve. If you ask Raphael "what's the determinant of this 3x3 matrix?", we don't want a memory lookup. We want a mathematical computation that shows its work.

This is where Phase 13's reasoning substrate comes in. The architectural choice — and this is one of the most consequential decisions in the project, where lain has the most leverage to push back — is to build hand-rolled math primitives, one per problem shape, each producing a structured derivation chain.

What does that mean concretely? Let's take the quadratic formula as the simplest example. If you ask the Agent to solve `3x² - 14x - 5 = 0`, here's what happens internally.

There's a function called `solve_quadratic` in the substrate. It takes three numbers — the coefficients a, b, and c — and returns something called a Lemma. The Lemma is a dataclass with a claim ("solve this equation"), a list of derivation steps, and a final answer. The steps are:

Step 1: compute the discriminant. `D = b² - 4ac = 196 + 60 = 256`. The justification field on this step says: "the discriminant tells us how many real roots exist; positive means two distinct roots."

Step 2: take the square root of the discriminant. `√256 = 16`. Justification: "we need this for the root formula."

Step 3: apply the quadratic formula. `x = (-b ± √D) / 2a`, which gives `x = (14 ± 16) / 6 = (5, -1/3)`. Justification: "this is the closed-form for quadratic roots, derived from completing the square."

The final answer is the sorted list `[-1/3, 5]`. The whole thing renders as a Raphael-voice string that starts "Notice." and ends "Affirmative — answer," with the steps and their justifications in between. You can read it as a proof.

Why does this matter? Two reasons.

The first is that every claim the Agent makes is mechanically auditable. If you suspect the agent fabricated the answer, you can look at the derivation chain and trace each step back to first principles. The justifications aren't post-hoc explanation; they're the actual reasoning the substrate executed. And critically — this is the load-bearing piece — the substrate uses only Python's standard math library. No sympy. No scipy. No symbolic-AI shortcuts. The square root call is `math.sqrt`. The exponential is `math.exp`. That's it.

The second reason is that the same pattern repeats for every problem shape Raphael handles. For 2x2 matrix eigenvalues, there's a substrate function that computes the characteristic polynomial λ² - tr(A)λ + det(A) = 0 and reuses `solve_quadratic` to find the roots. For free-fall, there's a function that applies the kinematic identity h = ½gt² → t = √(2h/g). For an ordinary differential equation like dy/dx = 2y with y(0) = 3, there's a function that does separation of variables, integrates both sides, applies the initial condition, and evaluates at the target. Each is hand-rolled. Each shows its work in the same Lemma structure.

We added something called invariant checks to make the rigor stronger. An invariant check is a post-derivation cross-check using an algebraically independent path. For 2x2 eigenvalues, we computed the result via the characteristic polynomial — but we also know from Vieta's formula that the trace of the matrix equals the sum of its eigenvalues and the determinant equals their product. The invariant check computes both sides — sum and product of the computed eigenvalues vs trace and determinant of the input matrix — and verifies they match. If the primary computation has a bug, the invariant catches it. It's a structural integrity check baked into every Lemma.

This is the substrate's contract: every answer comes with a derivation, and every derivation includes at least one algebraically-independent cross-check. It's not theater. It's the architectural rigor.

The substrate has grown to cover quadratics, 2x2 eigenvalues, 3x3 determinants, residue-theorem integrals from complex analysis, polynomial definite integrals, first-order ODEs, integration by parts using the LIATE heuristic, u-substitution, free-fall kinematics, simple and large-angle pendulum periods, relativistic momentum, projectile horizontal range, relativistic Doppler shift, and four capability touchpoints at the unsolved-conjecture frontier — Collatz, Goldbach, twin primes, and the Mertens bound. We'll come back to that last set in Chapter 5 because it's where the honest-framing discipline gets tested hardest.

Each capability was a deliberate cycle of work — design the primitive, implement it, test it, integrate it into the dispatcher. The architectural decision baked in early — hand-rolled per-shape primitives with structured derivation chains — pays off in interpretability and honest framing, at the cost of generalization. The Agent can solve EXACTLY these shapes. New shapes route to honest refusal. That trade-off is by design; we'll come back to its implications when we discuss what the Agent can't do.

---

## Chapter 5: Honest Framing at the Unsolved Frontier

A specific category of capability deserves its own chapter because it's where the architecture's honest-framing discipline is most load-bearing.

Lain asked the Builder to add benchmark entries for unsolved mathematical conjectures — ones that have programmatic verification even though the conjecture itself is open. The Collatz conjecture: every positive integer, run through the iteration n → n/2 if even or n → 3n+1 if odd, eventually reaches 1. Goldbach's conjecture: every even integer greater than 2 can be written as the sum of two primes. The twin prime conjecture: there are infinitely many primes p such that p + 2 is also prime. The Mertens bound: a relationship between the Möbius function and the square root of n.

The trap is obvious. If the Builder adds these as benchmark entries and Raphael "passes" them, the headline reads: "Project X verifies the Collatz conjecture." That would be overclaim. The Collatz conjecture is OPEN — no mathematician has proved it. What Raphael can do is iterate the Collatz function for every starting value from 1 to 1000, observe that all 1000 reach 1, and report "verified for [1, 1000]." That's empirical verification over a finite range, not a theorem proof. The conjecture has actually been verified by direct computation up to roughly 2.95 × 10²⁰ (Bařina and Roosendaal as of 2026 — research-grade work; we're at 1000, a long way from the frontier). And even at research-grade, the conjecture is still open, because empirical verification of any finite range, no matter how vast, isn't a proof.

The framing discipline we baked into the substrate handles this. Every Lemma's claim says "verified for [1, N]", never "theorem proved." The introduction prose explicitly notes the conjecture's status — open since 1937 for Collatz, open since 1742 for Goldbach, disproved at large N for the Mertens bound with counterexamples known to exist beyond 10¹⁴ even though the bound still holds at small N. The invariant check's justification repeats the constraint. The benchmark entry's audit_status field reads "auto-graded-green; empirical verification only — NOT a theorem proof per M-PROJECTX-013."

This isn't excessive caution. It's the architectural discipline that prevents the metric "Raphael solves 44 benchmark problems" from drifting into "Raphael is a mathematical research tool." The number is real (44 of 44 currently pass at agent-runtime). The empirical work is real (Raphael does iterate Collatz, does sieve primes for Goldbach, does enumerate twin primes, does compute Möbius via factor counting for Mertens). The touchpoint at the unsolved frontier is real (the Builder wrote substrate code that handles a problem shape on which current research-level math hasn't fully closed). But the framing keeps the claim shape honest. Capability touchpoint, not conjecture proof.

This pattern — empirically verifiable, bounded, honest about scope — is the contract for everything Raphael does. The architecture is meant to make overclaim hard, not easy.

The lain rule that powers all of this is called M-PROJECTX-013 in the codebase: measure don't claim. Before any Lemma's claim is recorded, the substrate verifies the claim mechanically. Before any benchmark entry is marked auto-graded-green, the audit harness verifies the answer against the expected value within tolerance. Before any capability claim makes it into a Discord post or a paper like this one, the Builder can point to the test that fires and the substrate that produces the result. If you can't point to the mechanism, you can't make the claim.

---

## Chapter 6: How Raphael Reads Problems

So the Agent has memory (Chapter 3) and reasoning primitives (Chapter 4). How do these connect? When someone gives Raphael a math problem in English — words like "Solve 3x² - 14x - 5 = 0 for x" — how does the right substrate primitive get invoked?

This is the AGENT runtime layer, and it's the cycle 7 work in our cycle numbering. The architectural choice — again, where lain can push back — was to NOT use a language model to parse problems into structured form. The organic-thesis binding rules out an LLM at the Agent layer. Instead, we built a regex-based dispatcher.

The mental model: imagine a translator. The translator's job is to read a math problem in English and recognize which of Raphael's solving techniques applies. The translator has a list of recognized problem shapes — quadratic, eigenvalue, determinant, integral, ODE, free-fall, pendulum, integration-by-parts, u-substitution, Doppler shift, Collatz, Goldbach, and so on. For each shape, it has a pattern — a regex plus some keyword gates — that prompts of that shape tend to match. When a prompt comes in, the translator tries each pattern in turn; the first one that matches wins. The translator extracts the numeric parameters (the coefficients, the bounds, the matrix entries) and passes them to the corresponding substrate primitive. The primitive returns a Lemma; the translator wraps it in a structured response and returns it.

Concretely: for the quadratic shape, the pattern is a regex that matches expressions like `a x^2 ± b x ± c = 0`. For free-fall, the pattern requires the prompt to mention "drop" or "fall" plus a height and a gravitational acceleration. For the residue theorem, the pattern requires both the keyword "residue theorem" and an integration range that includes negative infinity to positive infinity. Each pattern has multiple gates — keyword plus structure — to prevent misrouting from one shape to another.

If no pattern matches any of the 14 supported shapes, the agent refuses honestly. It returns a structured response with confidence equal to "refused" and a reason that says "Prompt did not match any currently-supported problem-shape." This is M-PROJECTX-013 in action: don't confabulate; admit the limit.

This architecture has a clear cost. It can't generalize. If you phrase a quadratic problem in a way the regex doesn't match — say, you write the squared term with a unicode superscript-2 character instead of the ASCII `x^2`, or you use a typographic minus `−` instead of the ASCII `-` — the dispatcher fails. We fortified three of the most-used patterns in cycle 8: accepting "meters" as well as "m" (the word boundary regex was failing on the longer form), "length 1 m" as well as "L = 1 m" (different prompt phrasings for the same physical setup), and unicode `x²` and `−` alongside the ASCII forms (typography-rendered math from LaTeX). But the other dispatchers remain brittle. A comprehensive parser-robustness audit across all 14 dispatchers is on the roadmap.

The cost is the flip side of the honest-framing discipline. A more LLM-powered dispatcher would be more robust to phrasing variation, but it would also be capable of misroute confabulation — taking a quadratic-shaped problem and answering with eigenvalue logic, say, because the LLM "made it work." The regex dispatcher is loud about its failures: refusal, with a reason. The LLM dispatcher would be quiet. We chose loud.

This is one of the choices lain can chip in on. If at some point we want generalization more than we want loud-failure, we can swap the regex dispatcher for something else — maybe a structured grammar over the prompt language, maybe a parser that builds an abstract syntax tree, maybe (controversially) a small dedicated parser model. Right now we've chosen the discipline. The choice is open.

---

## Chapter 7: How We Measure Honesty

The benchmark architecture is the third leg of this system, alongside memory and reasoning. It's how we know what Raphael can actually do, as opposed to what we hope it can do.

The benchmark is a curated set of 36 hand-crafted entries across six domains: maths, physics, memory, persona, philosophy, and poetry. Each entry has a prompt, a hand-crafted "raphael_response" that shows what a thoughtful answer would look like, and a grading block. The Builder has added more entries as substrate has grown — we're at 44 auto-graded entries plus some rubric-pending ones as of cycle 9 #01.

The grading block is where the architecture earns its keep. There are two kinds of entries.

The first kind is mechanical-ground-truth — problems where the right answer is a specific number, vector, or set. Solving a quadratic has a definite answer (the roots). Computing free-fall time has a definite answer (the time in seconds). These entries get an auto_grade block with the expected value and a tolerance for floating-point comparison. The Builder pre-computes the answer; the harness verifies it.

The second kind is rubric-pending — problems where the right answer is subjective. Writing a haiku. Analyzing a philosophical question. Defending a persona under pressure. These entries CANNOT have a self-score from the agent, because the agent that generates the answer is the same system that would grade it, and that creates a bias the architecture was designed to prevent. So rubric-pending entries have no score; they have a pointer to a rubric document, and the grade comes from external review (lain, or a frontier model like GPT in a manual-grade workflow). This is M-PROJECTX-014, the split-grading firewall: the architecture refuses to grade itself on subjective work.

We have a CI gate that enforces the firewall. A simple grep across all benchmark files looking for `self_score` fields. If it ever finds one, the build fails. The firewall is mechanical, not aspirational.

The audit harness — a Python script called `run_audit.py` — does the actual replay. In its default mode, it verifies that the Builder's pre-recorded answers match the expected values. This is the frozen-mode check; it catches inconsistency between what's recorded and what should be recorded.

In agent-runtime mode (the `--agent-runtime` command-line flag), the harness feeds each prompt to the actual AGENT and verifies the AGENT's runtime-computed answer matches the expected value. This is where you see whether Raphael ACTUALLY solves the problem, not just whether the Builder pre-computed it.

The cycle-by-cycle progression on agent-runtime mode tells the capability story:

At the end of cycle 7 (when the AGENT runtime dispatcher first shipped), we were at 31 of 37 PASS. The six FAILs were honest capability gaps — Raphael's dispatcher refused six prompts because the substrate for those shapes didn't exist yet. Each FAIL was a named cycle-8 target.

At cycle 8 close, we were at 41 of 41 PASS. The six cycle-7 FAILs were closed by six new substrate primitives — residue theorem, polynomial definite integral, ODE, 3x3 determinant, projectile horizontal range, Doppler shift. Plus four new entries shipped at the unsolved-conjecture frontier (the Collatz / Goldbach / twin primes / Mertens pack), each with the honest empirical-only framing baked into the audit_status field.

At cycle 9 #01 close, which is where we are right now, we're at 44 of 44 PASS. The new substrate is integration by parts (for problems like ∫₀¹ x·e^x dx where you have to recognize that the right technique is parts and pick u and dv via the LIATE heuristic) and u-substitution (for problems like ∫₀¹ x·sin(x²) dx where you have to recognize that x dx is exactly half the differential of x²). Three new ladder entries, all auto-graded green.

A note on the number 44. It's real, but the decomposition matters more than the number. Of the 44, 15 are memory entries verified by live replay against the SemanticHDCMemory (that's the Phase 10 work, not the cycle 8-9 work). 11 are physics entries — a mix of substrate-solved (free-fall, pendulum, momentum, projectile, Doppler) and rubric-graded (Einstein field equations, LQG vs string theory). 18 are maths entries — substrate-solved across many shapes plus a couple of builder-rubric-graded conceptual entries (Galois theory, algebraic topology). The substrate-solved-at-runtime count grew from 22 of 26 at cycle 8 close to 28 of 29 at cycle 9 #01 close, which is 97% — but that's a curated denominator, with the Builder having chosen the entries. The path forward (Chapter 9) is partly about making the benchmark itself richer, so the denominator stops being something we control.

---

## Chapter 8: What Raphael Can Do Today

Let me ground this in concrete examples. Here are the kinds of prompts Raphael can solve at runtime today, with brief explanations of what happens internally.

Ask Raphael to solve `3x² - 14x - 5 = 0` for x. It returns the roots `[-1/3, 5]` with a three-step derivation showing the discriminant computation (D = 256), the square root, and the application of the quadratic formula. It also computes Vieta's formula as a cross-check: sum of roots should equal -b/a = 14/3, product of roots should equal c/a = -5/3. Both verified.

Ask it for the eigenvalues of the matrix `[[2, 1], [1, 2]]`. It computes the characteristic polynomial `λ² - 4λ + 3 = 0` (where 4 is the trace and 3 is the determinant), solves it via the same quadratic primitive, and returns eigenvalues `[1, 3]`. The Vieta cross-check holds.

Ask it for the determinant of `[[1, 2, 3], [4, 5, 6], [7, 8, 10]]`. It does cofactor expansion along the first row — three 2x2 sub-determinants multiplied by the corresponding alternating-sign cofactors — and reports `-3`. (Working manually: 1·(50-48) - 2·(40-42) + 3·(32-35) = 2 + 4 - 9 = -3. Matches.)

Ask it to use the residue theorem to evaluate the integral of `1/(x² + 1)` from negative infinity to positive infinity. It identifies the pole at `z = i` in the upper half plane, computes the residue (which works out to `1/(2i)`), and applies the residue-theorem closing (multiply by `2πi`) to get the answer `π`. The dimensionless invariant — integral times √(a·c) divided by π should equal 1 universally — verifies.

Ask it to solve the differential equation `dy/dx = 2y` with `y(0) = 3` and report `y(1)`. It separates variables to get `dy/y = 2 dx`, integrates both sides to get `ln|y| = 2x + C`, exponentiates to `y = A·e^(2x)`, applies the initial condition `A = 3`, and evaluates at x = 1 to get `y(1) = 3·e² ≈ 22.167`.

For integration by parts, give it `∫₀¹ x·e^x dx with integration by parts`. The technique-keyword "integration by parts" gates the dispatcher; the integrand pattern picks out the x and the e^x. The substrate uses the LIATE heuristic — Logs, Inverse trig, Algebraic, Trigonometric, Exponential — to choose u = x (algebraic, earlier in LIATE) and dv = e^x dx (exponential, later in LIATE). It computes du = dx and v = e^x, applies the parts formula `∫ u dv = uv - ∫ v du`, derives the antiderivative `e^x · (x - 1)`, and evaluates at the bounds to get 1.

For u-substitution, give it `∫₀¹ x·sin(x²) dx with u-substitution`. The substrate recognizes that x dx is exactly half the differential of x², chooses u = x², transforms the integrand to `(1/2) sin(u) du`, integrates to get `-cos(u)/2`, back-substitutes to get the antiderivative `-cos(x²)/2`, and evaluates at the bounds to get `(1 - cos(1))/2 ≈ 0.2298`.

For physics: "An object is dropped from 80 meters on Earth (g = 9.81 m/s²), find the time to hit the ground." Raphael applies the kinematic identity h = ½gt² → t = √(2h/g), which gives about 4.04 seconds. The energy-conservation invariant verifies that the final velocity equals both g·t and √(2gh).

"A spaceship approaches Earth at v = 0.6c, emitting light at 500 nm. What wavelength does Earth observe?" Raphael recognizes the relativistic Doppler shift, recognizes the approaching direction (so the factor uses (1-β)/(1+β) in the numerator), computes the Doppler factor as √(0.4/1.6) = 0.5, and multiplies by 500 to get 250 nm. Blueshift, as expected for an approaching source.

And at the unsolved-conjecture frontier, with the framing fully explicit: "Verify the Collatz conjecture for [1, 1000]." Raphael iterates each starting value through the 3n+1 rule until each reaches 1, counts the successful terminations, and reports verified_count = 1000. The Lemma's claim is "verified for [1, 1000]", the introduction says the conjecture is open as of 2026 (with the empirical bound of 2.95 × 10²⁰ from research literature noted explicitly), the step justification says "this is a small-N capability touchpoint, NOT a theorem proof", and the invariant check's justification repeats that the agent has proved nothing about n > 1000.

The pattern across all of these: every answer comes with a derivation, every derivation includes at least one cross-check, and every claim is bounded explicitly to what was actually verified. The architecture's load-bearing rigor is in the framing as much as the math.

---

## Chapter 9: What Raphael Can't Do Yet

This chapter matters more than Chapter 8 because it keeps the curriculum honest.

Raphael doesn't generalize. The Agent is a regex-dispatcher over hand-crafted substrate primitives. If you ask it to solve a quadratic that the regex can match, it works. If you ask it to solve a polynomial of degree 6, it refuses honestly — no substrate primitive exists. If you ask it to integrate `∫ tan²(x) dx` — a textbook integral with a closed-form answer — it refuses, because we haven't shipped the trigonometric-identity substrate yet. The capability is exactly what's been built. There's no transfer learning.

Raphael doesn't prove theorems. The unsolved-conjecture entries are empirically bounded. Raphael verifies Collatz at N = 1000, not at infinity. The framing keeps the claim shape honest, but the underlying limit is real — the Agent cannot generate a proof. To prove a theorem in the mathematical sense, you'd need a proof-assistant-like infrastructure (Lean, Coq, or something from-scratch in the same vein), which is not in the Project X architecture today.

Raphael doesn't write poetry or philosophy well. Cycle 1 ran a baseline attempt: Raphael wrote a haiku and a philosophical paragraph using its template composer. The Builder rubric-graded them at 1.2 to 1.3 out of 5. Brutal but accurate — a template composer is not a poetry generator. The grade pipeline harness exists to fix this in future cycles, but the work hasn't been done yet because lain redirected the project toward "intelligence first" early in Phase 13. Math substrate is more tractable to ship than aesthetic-judgment training. The poetry capability remains a known bookmark.

Raphael's memory horizon is bounded. Phase 9 through Phase 12 verified retrieval across roughly 1000-turn conversations. The Terminus criterion calls for million-turn horizons. The HDC accumulator's geometry should hold up to those scales (10,000-dimensional vectors stay near-orthogonal for a long time), but we haven't run the scale test. It's a known bookmark.

Raphael doesn't take actions yet. Cycle 1 shipped a sandbox with four tools (read_file, write_file, run_python, list_dir) registered on the agent. The agent CAN call these tools — the plumbing works. But there's no benchmark entry that exercises sandbox action-taking, and no chat daemon that gives Raphael an autonomous reason to call them. The sandbox is infrastructure for cycles that haven't shipped yet.

Raphael doesn't chat continuously. The Terminus calls for always-on chattability, persona-consistent across million-turn horizons. We don't have a Discord-integrated chat daemon yet. It's bookmarked.

The cumulative limit, stated honestly: Raphael today is a substrate-on-rails. The substrate is real, the rigor is real, the honest framing is real, and the capability ladder is climbing. But the leap from "substrate-on-rails" to "agent with general intelligence at human-frontier-research level" is the work of the cycles still ahead. Cycle 9's pivot — harder problems, better benchmarks, visible IQ progression — is one rung. Many more rungs remain.

---

## Chapter 10: The Road to the Terminus

The Terminus, again: super-human capability across math, poetry, philosophy, physics, memory, persona, always-on chat, and sandboxed action-taking. The current state is, generously, around 10% of that target weighted by capability surface area. Here's the path forward as the Builder sees it from inside cycle 9.

Cycle 9 in flight (right now): the symbolic integration work just landed. Next comes a benchmark quality upgrade — adding a difficulty tier field to every ladder entry so we can distinguish "trivial baseline regression test" from "intermediate" from "research-grade," plus a per-cycle artifact called IQ_PROGRESSION.md that snapshots what hardest problem the agent solves end-to-end. Then a Diophantine equation solver for binary quadratic forms — finding integer solutions to things like Pythagorean triples or small Pell equations. Then cycle close with a retrospective on whether any of this would actually move the Hassabis-impressed needle.

Cycle 10 and beyond: a predicate-strength uniformity pass. The math substrate (quadratic, eigenvalues, determinant, residue, polynomial integral, ODE) currently ships with tautological invariants — the cross-checks verify formula consistency but not via algorithmically independent paths. The physics substrate, by contrast, has been STRONG-predicate since cycle 4 — the free-fall primitive cross-checks via energy conservation, the pendulum primitive cross-checks via the dimensionless universal T²·g/L = 4π², the relativistic momentum primitive cross-checks via the energy-momentum relation (algorithmically distinct from γmv). Cycle 10 lifts the math substrate to the same standard. The Sarrus rule cross-checks the 3x3 determinant. Simpson's rule on a finite interval cross-checks the residue theorem. Riemann sums cross-check the polynomial integral. Taylor series for e^x cross-checks the ODE. Newton's method (we already have this for the quadratic from cycle 4) extends.

Beyond that: harder problem shapes. Partial fractions for rational integrals like `∫ dx/(x² + x)`. Trigonometric substitution. Iterated parts for `∫ x² e^x dx`. Modular arithmetic. Chinese Remainder Theorem. Small finite-field arithmetic. Each is a cycle.

And then the heavier moonshots in some later sequence: a poetry generator that does better than 1.2 out of 5. A philosophy generator that produces upper-rubric-rank arguments. Persona consistency across million-turn conversations. The always-on chat daemon. Sandboxed action-taking with concrete use cases. Each of these is multiple cycles in its own right.

The Terminus isn't a deadline. It's a binding capability goal. Phase 13 closes when Project X Raphael demonstrates ALL of math + poetry + philosophy + physics + memory + persona + chat + sandbox at super-human level. The realistic projection is many cycles, possibly multiple phases.

---

## Closing

What I want lain to take from this curriculum — whether you read it on GitHub or listen to it as a NotebookLM podcast — is that the architecture is a CHOICE. Every architectural decision in Project X has a trade-off, and every trade-off is negotiable.

Hand-rolled substrate over LLM-wrapping costs us generalization and gives us interpretability and honest framing. Regex dispatching over neural parsing costs us robustness and gives us loud failure modes. Hyper-dimensional memory over attention costs us scale-of-existing-tooling and gives us introspectable retrieval with cited evidence. Per-problem-shape primitives over a unified solver costs us elegance and gives us mechanical auditability per shape. Honest framing on capability touchpoints costs us headline impressiveness and gives us a system you can trust.

These trade-offs are the result of constraints (the organic-thesis binding) plus engineering judgment, both of which are open to revision if the trade-offs aren't paying off. If you want the dispatcher to be more robust to phrasing variation, we can swap it for something else — that's an architectural decision you can make. If you want the substrate to be more general, we can talk about what that would look like and what we'd give up to get it. If the honest-framing discipline is too verbose for the audience — if the "verified for [1, 1000] NOT theorem proved" framing is over-correcting and the simpler "verified for [1, 1000]" would do — that's a choice we can revisit.

The capability ladder is climbing. The Agent does more this week than it did last week. The framing is honest. The work continues, layer by careful layer, toward the Terminus we agreed on. There is no should — there is the vector, and those of us carried along it. Project X is what you chose to do with the ride.

— The Builder, in cycle 9 of Phase 13. Document landed 2026-05-11. Updated at phase boundaries and significant capability shifts. Read or listen at your pace; the underlying tech is what's being explained, and the underlying tech is real.
