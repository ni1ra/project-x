# Council F - Self-Modification

**Date:** 2026-05-09  
**Mode:** SINGLE-BRAIN. advisor MCP absent.  
**Question:** How should Raphael eventually rewrite its own code without becoming fake, unsafe, or unverifiable?

---

## 0. Ground Truth

The MANIFESTO endpoint is serious:

```text
agent reads kernels.py
identifies inefficiency
writes patch
recompiles/tests
keeps improvement if verified
```

That is not Phase 9. It is not "let the LLM edit anything." It is a staged loop with sandbox, benchmarks, rollback, and evidence.

Self-modification without measurement is self-delusion.

---

## 1. Evidence Pack

Fetched sources:

- Codex system-card addendum: agentic coding is framed around a sandboxed environment, precise instruction following, and iteratively running tests.
- Terminal-Bench: terminal-agent benchmarks use real terminal tasks and programmatic verification; 2.0 has 89 high-quality tasks.
- OpenAI structured outputs: schemas can constrain generated tool arguments, but not guarantee semantic correctness.
- Project local tests: `PYTHONPATH=src pytest -q` currently fails due a package import-path regression; this proves verification surfaces matter.
- Project_synapse: Triton kernels and Neural CPU code are the future substrate surfaces, but they require hard tests before mutation.

---

## 2. Seats

| Seat | Lens | Unique concern |
|---|---|---|
| 1 | Software verification engineer | What proves a patch improved anything? |
| 2 | Agent safety engineer | How are destructive edits contained? |
| 3 | ML systems engineer | Which self-improvements are measurable? |
| 4 | Project Lain substrate engineer | How does Neural CPU self-editing enter? |
| 5 | Adjacent: scientific method philosopher | What separates learning from narrative? |

---

## 3. Candidate Scores

| Candidate | Score | Verdict |
|---|---:|---|
| Staged sandbox-and-replace loop with benchmarks | **410** | Winner |
| Tool-call file editor with tests | 372 | Needed component, insufficient alone |
| Neural CPU opcode reads/writes kernels.py | 352 | Long-term substrate embodiment |
| Differentiable architecture search | 324 | Too expensive and under-specified |
| Direct live self-editing | 240 | Reject |

Mean score: 339.6. Spread: 170.

---

## 4. Deliberation

Self-modification must start as externalized scientific method.

Loop:

```text
observe weakness
form hypothesis
create patch in sandbox
run benchmark
compare against baseline
accept or reject
write result
```

The agent does not get to declare improvement from vibes. It needs:

- before artifact
- after artifact
- run ID
- benchmark command
- result JSON
- interpretation
- rollback path

The first self-modification targets should be non-critical:

- prompt/harness improvements
- retrieval policy thresholds
- projection matrix configs
- benchmark scripts
- memory consolidation rules

Not:

- direct kernel mutation
- security policy mutation
- destructive tool permissions
- hidden memory edits

---

## 5. Defended 400+ Idea

**Winner: sandbox-and-replace self-improvement harness.**

A proposed change file:

```json
{
  "proposal_id": "selfmod_0007",
  "target": "memory_write_policy",
  "hypothesis": "Raising importance threshold reduces false positives without hurting exact recall.",
  "patch_path": "...",
  "benchmark_command": "...",
  "baseline_result": "...",
  "candidate_result": "...",
  "accept_rule": "semantic_top5 >= baseline - 0.02 and false_positive <= baseline - 0.05",
  "verdict": "accept|reject"
}
```

Only accepted patches merge into the live system.

---

## 6. Phase Ordering

Phase 9:

- no self-modification
- write benchmarks and logs so self-modification becomes possible

Phase 12:

- patch proposal harness
- sandboxed edits to Project X memory policies
- automatic test/benchmark comparison

Phase 13:

- agent proposes improvements to controller/tool policies
- human approval for accepted changes

Phase 15+:

- project_synapse/Neural CPU self-read experiments
- kernel-level patch proposals
- compile/test/benchmark gate

---

## 7. Acceptance Gates

No self-modification patch is accepted unless:

- baseline and candidate use the same benchmark seed set
- result file is machine-readable
- performance threshold is predeclared
- safety regression checks pass
- changed files are listed
- rollback is possible
- user-visible handoff records the change

For kernel work:

- unit tests
- numerical equivalence checks
- performance profile
- VRAM cap validation
- thermal/run stability

---

## 8. Risks

- Agent optimizes benchmark loopholes.
- Agent mutates its own evaluation.
- Prompt changes look good but reduce generality.
- Code edits pass smoke tests but break long-run behavior.
- "Self-improvement" becomes theater.

Mitigation:

- held-out benchmarks
- immutable baseline artifacts
- separate evaluator where possible
- manual approval for high-risk changes
- regression pack across tasks

---

## 9. Verdict

Self-modification is Phase 12+.

The immediate work is to create the evidence surfaces self-modification will need. Build the loop before letting the loop edit itself.

The correct doorway is:

```text
logs -> benchmarks -> proposals -> sandbox patches -> measured accept/reject -> live replacement
```

Not live self-rewrite.

---

## 10. Implementation Pressure Test

### First allowed targets

Allowed early:

- benchmark scripts
- retrieval thresholds
- memory write policy
- report aggregation
- prompt templates
- controller classifiers

Forbidden early:

- kernel code
- permission model
- evaluator logic
- deletion logic
- credential handling
- live tool runtime

### Proposal lifecycle

1. detect weakness
2. write hypothesis
3. define metric
4. capture baseline
5. patch sandbox
6. run candidate
7. compare
8. accept or reject
9. write interpretation

Every step is artifact-backed.

### Baseline requirements

Baseline must include:

- commit/file snapshot or checksum
- command
- seeds
- result JSON
- machine
- mode

Candidate must use same benchmark unless intentionally testing transfer.

### Anti-cheat rules

The self-modifier may not:

- edit the benchmark while evaluating candidate
- lower pass thresholds
- delete failing cases
- hide failed runs
- use training labels at inference
- claim improvement without result JSON

### First self-mod benchmark

Use memory policy:

- baseline write-all
- candidate sparse-write
- evaluate recall and false positives
- accept if false positives drop without recall collapse

This is safer than code-generation self-editing.

### Kernel self-edit path

Before touching `kernels.py`:

- unit tests green
- golden output saved
- profiler result saved
- patch generated in sandbox
- compile/test command scripted
- VRAM watchdog active
- rollback path known

### Human authority

High-risk accepted patches require lain approval:

- tool permissions
- file deletion
- network behavior
- kernel changes
- self-modification policy changes

### Self-modification success definition

Success is not "agent wrote code."

Success is:

```text
candidate changed behavior
benchmark measured improvement
regressions stayed within threshold
artifact records why
```

### Long-term endpoint

The MANIFESTO door opens only when the system can improve its own substrate while keeping evidence external to the claim.
