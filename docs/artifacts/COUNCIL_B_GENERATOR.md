# Council B - Generator

**Date:** 2026-05-09  
**Mode:** SINGLE-BRAIN. advisor MCP absent.  
**Question:** What should turn HDC-retrieved context plus current user intent into natural language and tool/action proposals?

---

## 0. Ground Truth

HDC does not generate text.

Phase 8 built a memory primitive. The chattable Raphael endpoint requires a generator that can:

- understand user messages
- condition on retrieved evidence
- produce fluent text
- produce structured tool calls
- refuse impossible claims
- degrade gracefully when memory retrieval is uncertain

No SNN generator in the local codebase currently provides this. project_synapse is a controller/substrate research line, not a ready chat decoder.

---

## 1. Evidence Pack

Fetched sources:

- Qwen2.5-7B-Instruct card: 7.61B params, 28 layers, GQA, 128K-token context, stronger coding/math/structured output claims, quantizations available for local runtimes.
- Mistral 7B model card: 7B open weights, 32k context, Apache 2.0, but older v0.3 is marked replaced by Ministral 3 8B.
- llama.cpp GGUF guide: local GGUF models can run through CLI or server, with CUDA build support.
- OpenAI function calling/Structured Outputs docs: modern agent action surfaces depend on structured tool calls and schema adherence.
- Local hardware council: 13.9 GB VRAM cap makes quantized 7B-8B the default first target.

---

## 2. Seats

| Seat | Lens | Unique concern |
|---|---|---|
| 1 | Local LLM engineer | What runs well on the hardware now? |
| 2 | Language modeling researcher | What generator architecture is plausible beyond transformers? |
| 3 | Agent UX engineer | What response quality is needed for a JARVIS-like loop? |
| 4 | Substrate researcher | How does SNN generation enter without blocking? |
| 5 | Adjacent: dialogue writer | Does the agent maintain identity and conversational continuity? |

---

## 3. Candidate Scores

| Candidate | Score | Verdict |
|---|---:|---|
| Local Q4/Q5 7B-8B LLM as generator/decoder | **405** | Winner |
| Local 13B Q4 as optional stronger mode | 372 | Useful but memory-risky |
| project_synapse evolved-SNN generator | 344 | Vision-aligned, not ready |
| World-model + autoregressive token decoder from scratch | 318 | Too expensive for near-term |
| Pure template generator | 300 | Test harness only |

Mean score: 347.8. Spread: 105.

---

## 4. Deliberation

The generator should be borrowed, not invented, in Phase 9.

This is not a retreat from the no-cap vision. It is division of labor.

The local LLM is the speech motor cortex. It handles language, formatting, and tool-call proposal. HDC handles memory. The controller handles policy. SNN/Neural CPU handles long-term substrate research.

The first generator should be a local GGUF model, preferably Qwen2.5-7B-Instruct or a newer 7B/8B successor if installed locally. Qwen's documented structured output and coding/math improvements make it a better first candidate than older Mistral 7B. Llama 3 8B remains a strong fallback depending on local license/access and available GGUF quant.

The generator must not be asked to remember everything. It receives:

```text
system identity
current user message
compact working state
retrieved evidence packet with source IDs
available actions schema
```

The generator should not see the raw entire memory store.

---

## 5. Defended 400+ Idea

**Winner: local 7B-class LLM as a replaceable decoder behind an API boundary.**

The model should be swappable:

```text
GeneratorClient.generate(prompt, schema=None) -> text_or_json
```

Initial backends:

- `llama.cpp` server
- offline mock/template backend for tests
- optional cloud frontier backend for evaluation only, clearly labeled

Do not fine-tune yet. Do not train a decoder from scratch. Do not make SNN generation the blocking path.

---

## 6. Interface Contract

The generator receives:

```json
{
  "identity": "Raphael",
  "user_message": "...",
  "retrieved_evidence": [
    {"turn_id": 47, "text": "...", "score": 0.82}
  ],
  "controller_state": {"mode": "chat"},
  "allowed_tools": [...]
}
```

The generator returns either:

```json
{"type": "reply", "text": "...", "used_turn_ids": [47]}
```

or:

```json
{"type": "tool_call", "tool": "search_memory", "args": {...}, "reason": "..."}
```

The controller validates.

---

## 7. Phase Ordering

Phase 9:

- mock generator
- optional llama.cpp generator adapter
- evidence-conditioned answer benchmark

Phase 11:

- structured tool-call generation
- action schemas

Phase 13:

- multi-model routing
- branch-and-rank deliberation

Phase 15+:

- substrate-native generator experiments
- SNN/token decoder research

---

## 8. Risks

- Local 7B may be too weak for complex reasoning.
- Long context settings can break VRAM budget.
- Quantization can hurt instruction following.
- Generator may over-trust retrieved noise.

Mitigation:

- Keep evidence small and high precision.
- Add "I do not know" behavior when retrieval confidence is low.
- Benchmark with held-out memory questions.
- Use cloud frontier models only as labeled evaluator or bootstrap assistant, not as claimed local capability.

---

## 9. Verdict

Use a local quantized 7B-8B LLM as the generator now.

The ideal stack is hybrid:

```text
HDC memory gives evidence.
Controller gives policy.
Local LLM gives language/action proposals.
SNN substrate evolves underneath.
```

Do not make Project X invent natural language generation before it has a working agent loop.

---

## 10. Implementation Pressure Test

### Generator interface

The generator should be replaceable:

```python
class GeneratorClient:
    def generate(self, request: dict) -> dict:
        ...
```

Backends:

- `MockGenerator`
- `LlamaCppGenerator`
- optional `CloudEvaluatorGenerator`

Mock generator is mandatory for tests.

### Prompt packet

The generator receives:

- identity
- user message
- retrieved evidence
- controller mode
- allowed response schema
- uncertainty instructions

It does not receive:

- entire memory archive
- raw tool credentials
- unrestricted system state
- hidden benchmark labels

### Required response forms

Reply:

```json
{
  "type": "reply",
  "text": "...",
  "used_turn_ids": [1, 7]
}
```

Tool call:

```json
{
  "type": "tool_call",
  "tool": "search_memory",
  "args": {},
  "reason": "..."
}
```

Uncertain:

```json
{
  "type": "reply",
  "text": "I do not have that in memory.",
  "used_turn_ids": []
}
```

### Model selection gates

Qwen-like local model is preferred if:

- GGUF exists locally
- Q4/Q5 fits with KV cache
- JSON behavior is stable enough
- tokens/sec is acceptable

Mini model or mock remains acceptable if:

- Phase 9 is benchmarking memory, not prose quality

### Evaluation questions

The generator is not judged by vibes.

Judge:

- did it use only provided evidence?
- did it cite source turns?
- did it abstain when evidence absent?
- did it format JSON when requested?
- did it avoid inventing tool results?

### Failure modes

If generator ignores evidence:

- tighten prompt
- reduce evidence length
- use schema
- fallback to mock for benchmark

If generator invents sources:

- controller rejects
- regenerate with source constraints

If local model is too weak:

- keep generator mocked for Phase 9
- do not downgrade memory benchmark

### Long-term generator path

Phase 9:

- mock/local optional

Phase 11:

- reliable tool proposals

Phase 13:

- branch generation

Phase 15+:

- substrate-native decoder research

### Critical separation

Do not confuse:

- generator quality
- memory retrieval quality
- controller policy quality

Benchmark them separately.
