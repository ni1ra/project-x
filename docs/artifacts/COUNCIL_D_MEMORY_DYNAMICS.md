# Council D - Memory Dynamics

**Date:** 2026-05-09  
**Mode:** SINGLE-BRAIN. advisor MCP absent.  
**Question:** How should Project X handle forgetting, decay, consolidation, replay, and memory conflict once HDC moves beyond append-only demos?

---

## 0. Ground Truth

Phase 8 memory only adds.

Append-only HDC proves clean capacity behavior within bounds, but a real agent needs memory dynamics:

- not every turn should be stored equally
- stale memories should lose priority
- contradictions need revision
- important memories should survive
- sleep/replay should consolidate summaries and schemas
- provenance must remain available

The memory system must not optimize for maximum retention. It must optimize for useful recall.

---

## 1. Evidence Pack

Fetched sources:

- Complementary Learning Systems framework: neocortex learns structured generalities slowly; hippocampus rapidly encodes specific events with separated representations.
- CLS updated paper: replay can weight experience statistics by goal and has relevance to artificial intelligent agents.
- Nature Neuroscience replay paper: memory access can be prioritized by utility for future decisions.
- Phase 8 T4: finite capacity and noise cliffs are real.
- Phase 8 hostile review: "constant memory" only applies to the accumulator, not full provenance/metadata.

---

## 2. Seats

| Seat | Lens | Unique concern |
|---|---|---|
| 1 | Continual learning researcher | How does memory avoid interference? |
| 2 | Neuroscience/CLS lens | What should replay and consolidation do? |
| 3 | Database engineer | What survives outside the accumulator? |
| 4 | Product agent engineer | What should Raphael remember for the user? |
| 5 | Adjacent: librarian/archivist | How do provenance, trust, and retrieval hierarchy work? |

---

## 3. Candidate Scores

| Candidate | Score | Verdict |
|---|---:|---|
| Sparse-write importance gating + provenance store + sleep consolidation | **407** | Winner |
| Exponential decay only | 338 | Too blunt |
| LRU eviction only | 312 | Bad for rare important facts |
| Hippocampal-style replay during idle | 386 | Core Phase 10/11 addition |
| Differentiable forgetting | 344 | Interesting but premature |

Mean score: 357.4. Spread: 95.

---

## 4. Deliberation

The core mistake would be treating memory as a single accumulator.

The real architecture needs tiers:

```text
Tier 0: current prompt/context
Tier 1: working memory state
Tier 2: HDC episodic accumulator
Tier 3: metadata/provenance store
Tier 4: consolidated summaries/schemas
Tier 5: cold archive/logs
```

HDC is Tier 2. It is not the entire memory system.

Write policy matters more than raw capacity. If every minor token is written, the memory fills with noise. The controller should assign importance before write:

- user preference
- stable identity fact
- task decision
- file path
- tool result
- error mechanism
- unresolved branch
- relationship between facts

Sleep/replay should not blindly replay everything. It should prioritize:

- high-importance facts
- frequently retrieved items
- contradictions
- failed retrieval cases
- user-corrected memories
- information needed for current projects

---

## 5. Defended 400+ Idea

**Winner: sparse-write importance gating plus replay consolidation.**

Recommended write record:

```json
{
  "turn_id": 12,
  "text": "...",
  "embedding_id": "...",
  "hdc_key": "...",
  "importance": 0.0,
  "ttl": null,
  "source": "user|tool|agent",
  "confidence": 1.0,
  "supersedes": [],
  "tags": []
}
```

Recommended accumulator strategy:

- episodic HDC accumulator for recent/high-importance events
- separate fact accumulators by namespace
- negative/anti-binding experiment for correction later
- metadata store always keeps provenance

---

## 6. Consolidation Loop

Idle loop:

```text
select replay candidates
retrieve raw sources
cluster semantically
generate proposed summary/fact graph
validate against source turns
write consolidated memory
mark originals as archived or lower-priority
emit result.json
```

No summary is accepted without source turn IDs.

Replay is measured by before/after retrieval:

- recall old facts
- reduce false positives
- answer multi-hop questions
- keep contradictions visible

---

## 7. Phase Ordering

Phase 9:

- metadata/provenance store
- importance field
- no decay yet except manual namespace limits

Phase 10:

- sparse write policy
- memory dynamics benchmark
- decay/importance ablations

Phase 11:

- sleep consolidation
- replay queue
- summary validation

Phase 13+:

- utility-based replay
- task-aware memory planning

---

## 8. Risks

- Importance classifier may silently discard useful facts.
- Decay can erase rare but critical facts.
- Summaries can hallucinate.
- Consolidation can overwrite conflicting memories.
- User trust collapses if memories mutate invisibly.

Mitigation:

- Never delete raw logs by default.
- Keep supersession links.
- Cite source turns.
- Test absent-answer false positives.
- Show memory diffs in artifacts.

---

## 9. Verdict

Do not implement forgetting as deletion first.

Implement memory dynamics as:

```text
sparse writes -> provenance -> retrieval scoring -> replay consolidation -> optional decay
```

HDC gives the associative substrate. Durable metadata gives trust. Replay gives growth.

---

## 10. Implementation Pressure Test

### Write scoring

Initial importance score can be rule-based:

- `1.0`: explicit user preference or standing order
- `0.9`: project decision
- `0.8`: file path or command result
- `0.7`: error mechanism
- `0.6`: tool output summary
- `0.4`: ordinary task context
- `0.2`: casual chat
- `0.0`: filler

The score is not truth. It is a first controller heuristic.

### Retrieval scoring

Candidate score should combine:

- HDC similarity
- dense similarity if available
- recency
- importance
- source trust
- namespace match
- contradiction penalty

Do not rely on one scalar forever.

### Namespaces

Start with:

- `conversation`
- `project_x`
- `user_preferences`
- `tool_results`
- `file_paths`
- `decisions`
- `errors`

Separate accumulators reduce cleanup interference.

### Decay policy

Phase 9:

- no automatic deletion

Phase 10:

- decay retrieval priority
- do not erase raw logs

Phase 11:

- consolidate and archive

Only later:

- negative writes
- HDC unlearning
- compressed deletion

### Replay queue

Replay candidates:

- high importance
- frequently retrieved
- user-corrected
- contradictory
- old but still active
- failed retrieval target

Replay output:

- summary
- source IDs
- confidence
- supersedes links

### Evaluation pack

Memory dynamics must test:

- old preference after 1000 turns
- corrected preference
- contradictory statement
- rare file path
- repeated low-value chatter
- absent answer
- summary question

### Failure signs

If recall improves but false positives rise:

- threshold too low
- replay overgeneralized

If false positives drop but recall collapses:

- sparse-write too aggressive

If summaries answer unsupported facts:

- consolidation is hallucinating

If raw logs are missing:

- trust model is broken

### Final rule

Forgetting can hide evidence.

Lower priority first. Delete last.
