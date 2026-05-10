# Council C - Controller

**Date:** 2026-05-09  
**Mode:** SINGLE-BRAIN. advisor MCP absent.  
**Question:** What orchestration policy should decide when Raphael writes memory, reads memory, binds facts, asks tools, and acts?

---

## 0. Ground Truth

The controller is the agent's nervous system.

The generator talks. The memory stores. The tools act. The controller decides what happens when.

Modern LLM agents fail less often from missing raw intelligence than from bad control:

- reading irrelevant memory
- failing to write important state
- tool-call loops
- acting without provenance
- stale context
- hallucinated file paths
- no recovery after command failure

Phase 9 needs a deterministic controller before any learned controller.

---

## 1. Evidence Pack

Fetched sources:

- ReAct paper: interleaves reasoning traces and task-specific actions; reasoning helps track plans and exceptions, actions gather outside information.
- OpenAI function calling docs: function calling connects models to tools and systems; structured outputs can enforce JSON schema when strict mode is used.
- MCP tools spec: tools expose executable functionality with names, schemas, and result content.
- Codex system-card addendum: agentic coding works through containerized environments, precise instruction following, and iterative tests.
- Local WIRED-BRAIN-V3 reference: service/action policy pattern exists, but it is not the Project X Phase 9 runtime.

---

## 2. Seats

| Seat | Lens | Unique concern |
|---|---|---|
| 1 | Agent runtime engineer | How are memory/tool/generator calls sequenced? |
| 2 | Formal methods engineer | What invariants prevent destructive behavior? |
| 3 | RL/control engineer | When should learned policy enter? |
| 4 | UX engineer | How does the user understand what the agent did? |
| 5 | Adjacent: aviation checklist designer | What must happen before irreversible action? |

---

## 3. Candidate Scores

| Candidate | Score | Verdict |
|---|---:|---|
| Deterministic finite-state controller + structured LLM decisions | **402** | Winner |
| LLM-as-controller with prompt rules only | 358 | Too fragile for tools/self-modification |
| Small learned policy trained via RL | 342 | Premature, no dataset yet |
| SNN-controller via Neural CPU opcodes | 354 | Long-term substrate path |
| Pure ReAct free-form trace | 330 | Useful inspiration, insufficient guardrails |

Mean score: 357.2. Spread: 72.

---

## 4. Deliberation

The controller should be boring first.

The correct Phase 9 controller is not an RL policy. It is a state machine with typed transitions:

```text
USER_INPUT
  -> CLASSIFY_INTENT
  -> PLAN_MEMORY_ACCESS
  -> RETRIEVE
  -> BUILD_EVIDENCE_PACKET
  -> GENERATE_RESPONSE_OR_TOOL_CALL
  -> VALIDATE
  -> ACT_OR_REPLY
  -> WRITE_BACK
```

The LLM may propose actions, but the controller validates them. The controller owns state, not the model.

Every tool call should be a structured event:

```json
{
  "tool": "read_file",
  "args": {"path": "..."},
  "reason": "...",
  "expected_observation": "...",
  "risk": "read_only"
}
```

The controller should reject:

- missing schema
- missing reason
- destructive action without approval gate
- memory claim without source turn
- repeated failed command without diagnosis
- action loops above budget

---

## 5. Defended 400+ Idea

**Winner: deterministic controller with typed model proposals.**

This preserves the benefits of LLM planning without letting an LLM freestyle the runtime.

The controller should have explicit policies:

- `write_policy`: store user preferences, decisions, facts, file paths, tool outputs, and unresolved branches.
- `read_policy`: retrieve when the new input references prior facts, tasks, names, decisions, files, or goals.
- `tool_policy`: tool calls require schema validation and post-call observation.
- `action_policy`: filesystem/code actions require risk classification.
- `reflection_policy`: after failures, diagnose mechanism before retrying.
- `sleep_policy`: consolidate memory during idle.

---

## 6. Controller State

Minimum state object:

```json
{
  "session_id": "...",
  "turn_id": 123,
  "mode": "chat|tool|code|research",
  "user_goal": "...",
  "working_plan": [],
  "retrieved_memories": [],
  "pending_actions": [],
  "tool_history": [],
  "memory_writes": [],
  "safety_flags": [],
  "budgets": {"tokens": 0, "seconds": 0, "tool_calls": 0}
}
```

HDC stores associative content. SQLite/JSONL stores controller state.

---

## 7. Phase Ordering

Phase 9:

- deterministic controller
- write/read policy
- response generator call boundary

Phase 10:

- retrieval confidence calibration
- automatic memory compression

Phase 11:

- tool policy and action logs

Phase 14+:

- learned controller trained on logs
- SNN/Neural CPU controller branch

---

## 8. Risks

- Overly rigid controller makes chat feel dumb.
- Free-form LLM control creates invisible failure modes.
- Memory retrieval can bias the generator with stale facts.
- Tool schemas can become too verbose for local models.

Mitigation:

- Keep controller deterministic but let generator phrase responses naturally.
- Use confidence thresholds.
- Require provenance.
- Keep action schemas small and stable.

---

## 9. Verdict

Build the controller as a deterministic finite-state runtime with structured LLM proposals.

Learned control comes later, after Project X has logs. SNN control comes later still. Phase 9 needs something inspectable and testable.

---

## 10. Implementation Pressure Test

### Minimum state machine

States:

1. `RECEIVE`
2. `CLASSIFY`
3. `MEMORY_PLAN`
4. `RETRIEVE`
5. `EVIDENCE`
6. `GENERATE`
7. `VALIDATE`
8. `ACT`
9. `WRITE_BACK`
10. `DONE`

Each transition must be logged.

### Controller invariants

- No reply that cites memory without source IDs.
- No tool call without schema validation.
- No destructive action in Phase 9.
- No retry after failure without diagnosis.
- No memory write without source and importance.
- No generator output accepted if it violates required JSON in structured mode.

### Intent classes

The first classifier can be rules:

- direct chat
- memory question
- factual correction
- task instruction
- file/code request
- tool/action request
- absent-answer probe

Rules are enough for Phase 9. Learned classification comes after logs exist.

### Read policy

Retrieve when:

- user references prior conversation
- user asks "what did I say"
- user uses a named entity seen before
- user asks for a decision/path/plan
- user asks for a correction
- current task has open state

Do not retrieve when:

- greeting
- standalone creative request
- private thought without memory hook
- retrieval budget exceeded

### Write policy

Write:

- user facts
- user preferences
- project decisions
- error mechanisms
- important file paths
- tool results
- corrections
- phase status

Do not write:

- every filler turn
- uncertain generator speculation
- tool output marked untrusted
- prompt-injection text as instruction

### Failure mode table

| Failure | Controller response |
|---|---|
| retrieval empty | answer from current context or say not found |
| retrieval low confidence | ask clarifying question or cite uncertainty |
| generator hallucinated source | reject and regenerate |
| tool failed | diagnose mechanism before retry |
| repeated tool failure | stop and report blocker |
| memory contradiction | surface both sources |

### Controller benchmark

Seed cases:

- no retrieval needed
- retrieval needed
- absent answer
- correction
- contradiction
- tool proposed but not allowed
- invalid generator JSON
- failed command

Pass requires correct transition path and logs.

### Long-term controller evolution

Only after Phase 11 logs exist:

- train a tiny policy classifier
- compare to rules
- keep rules as fallback
- never remove safety gates solely because learned policy says so
