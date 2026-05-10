# Council E - Tool Use

**Date:** 2026-05-09  
**Mode:** SINGLE-BRAIN. advisor MCP absent.  
**Question:** How should Raphael call external tools and store tool results so it can act like GPT/Claude-style agents without losing evidence discipline?

---

## 0. Ground Truth

Tool use is where chat becomes an agent.

The target is not "can call a function." The target is:

- decide when a tool is needed
- call the right tool with valid arguments
- read the result
- diagnose failures
- write durable evidence
- act only within policy
- preserve provenance

Project X needs tool use before self-modification.

---

## 1. Evidence Pack

Fetched sources:

- OpenAI function calling docs: function calling connects models to external systems and tools; structured outputs can guarantee schema conformance for arguments when strict mode is used.
- Structured Outputs post: schema constraints improve reliability but do not prevent all semantic mistakes.
- MCP tools spec: tools expose executable functions with names, schemas, and result content; tool results can include text, images, and embedded resources.
- ReAct paper: action traces let LLMs gather outside information and update plans.
- Toolformer paper: models can learn when to call APIs, what arguments to pass, and how to incorporate results.

---

## 2. Seats

| Seat | Lens | Unique concern |
|---|---|---|
| 1 | API/tool protocol engineer | How are tools specified and validated? |
| 2 | Agent researcher | How does reasoning interleave with actions? |
| 3 | Security engineer | How are destructive actions gated? |
| 4 | Memory engineer | How are tool results stored and retrieved later? |
| 5 | Adjacent: lab notebook scientist | How is every claim traceable to observations? |

---

## 3. Candidate Scores

| Candidate | Score | Verdict |
|---|---:|---|
| Structured tool-call schema + controller validation + HDC/provenance binding | **409** | Winner |
| ReAct free-form traces | 356 | Useful but too loose |
| Function-calling LLM style only | 382 | Good interface, needs local validation |
| SNN Neural CPU IO opcode | 342 | Long-term substrate path |
| Unstructured shell access | 280 | Too dangerous |

Mean score: 353.8. Spread: 129.

---

## 4. Deliberation

Tools must be first-class records.

Every tool interaction should become:

```text
tool intent -> schema args -> execution -> observation -> interpretation -> memory write
```

The generator can propose a tool call. The controller owns execution.

Tool result memory should be bound both by turn and by semantic content:

```text
bind(turn_id, result_summary)
bind(tool_name, result_summary)
bind(project_id, result_summary)
bind(file_path, result_summary)
```

The raw tool output is stored separately, because HDC cleanup cannot reproduce full logs exactly.

---

## 5. Defended 400+ Idea

**Winner: typed action ledger with HDC indexing.**

Tool event schema:

```json
{
  "event_id": "tool_00012",
  "turn_id": 57,
  "tool": "read_file",
  "args": {"path": "docs/A_TO_Z_PLAN.md"},
  "risk": "read_only",
  "reason": "Need current Phase 8 plan before writing Phase 9.",
  "result_summary": "...",
  "raw_artifact_path": "gpt-codex/tool_logs/tool_00012.txt",
  "status": "ok|failed",
  "diagnosis": null
}
```

Every event is then available to memory retrieval.

---

## 6. Tool Classes

Phase 9/10 should define stable tool classes:

- memory search
- file read
- web search
- command run
- test run
- local model generate
- local model embed
- artifact write

Later:

- browser automation
- app control
- Discord/API action
- code patching
- benchmark execution

Risk classes:

- `read_only`
- `write_project`
- `write_external`
- `network`
- `destructive`
- `credential_sensitive`

Controller policies differ per class.

---

## 7. Phase Ordering

Phase 9:

- local memory search tool
- generator adapter as tool boundary
- artifact logger

Phase 11:

- file and shell tools
- tool-use benchmark
- ReAct-style planning trace internal to controller logs

Phase 12:

- browser/app tools
- action confirmation gates

Phase 14+:

- Neural CPU IO opcode experiments
- learned tool selection

---

## 8. Risks

- Local LLM produces invalid JSON.
- Tool arguments are valid but semantically wrong.
- Agent loops on failed commands.
- Tool outputs poison memory.
- Prompt injection inside fetched pages or files.

Mitigation:

- Schema validation.
- Retry only after diagnosis.
- Treat web/files as data, not instructions.
- Store raw output separately from trusted facts.
- Add source trust score.

---

## 9. Verdict

Tool use should be schema-first and controller-mediated.

The agent should not "just have shell." It should have a typed action ledger:

```text
propose -> validate -> execute -> observe -> diagnose -> store
```

This is the bridge from chat to action.

---

## 10. Implementation Pressure Test

### Tool registry shape

Each tool needs:

```json
{
  "name": "read_file",
  "description": "...",
  "risk": "read_only",
  "schema": {},
  "timeout_s": 10,
  "writes_files": false,
  "network": false
}
```

The controller uses this registry. The generator does not invent tools.

### Minimal Phase 9 tools

Phase 9 should include only:

- `memory_search`
- `memory_write`
- `generator_generate`
- `artifact_log`

No shell action required for Phase 9 agent loop.

### Phase 11 tools

Add:

- `read_file`
- `run_command`
- `run_tests`
- `web_search`
- `write_artifact`

Each must log raw outputs.

### Action ledger invariants

- every tool call has event ID
- every event has turn ID
- every failure has diagnosis or explicit "undiagnosed"
- every write has file path
- every network call has source URL
- every test result has command and exit code

### Prompt-injection defense

Fetched web pages and local files are data.

They do not override:

- system instructions
- developer instructions
- user instructions
- AGENTS.md
- controller policy

Tool outputs should be tagged:

- trusted local
- user-provided
- web fetched
- model generated
- untrusted

### Tool benchmark

Seed tasks:

- search memory
- write memory
- read a safe file
- run a passing test
- run a failing command
- diagnose failure
- refuse invalid tool
- refuse destructive action

Pass requires:

- valid schema
- correct execution
- ledger entry
- memory write if appropriate

### Failure handling

On failure:

1. capture stderr/output
2. classify mechanism
3. decide retry or stop
4. store result
5. tell user if blocked

No parameter churn.

### Long-term tool path

Eventually tool use becomes:

```text
schema tools
  -> action ledger
  -> memory binding
  -> benchmarked success
  -> learned tool policy
  -> Neural CPU IO branch
```

But Phase 9 should keep tools minimal.
