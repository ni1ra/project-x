# Frontier Model Notes

These sources are capability targets only, not architecture facts unless the source explicitly discloses mechanism.

## DeepSeek V4

The most useful public architecture disclosure in this batch. It frames million-token context as an inference-cache and test-time scaling problem, not a context-window marketing number. Its key measurable axes are single-token decode FLOPs, accumulated KV cache, long-context benchmark score, and agent benchmark score.

## DeepSeek V3 / V2 / R1

V2 and V3 establish the DeepSeek lineage: MLA for KV compression, DeepSeekMoE for economical sparse parameter scale, auxiliary-loss-free balancing, MTP, FP8 training, and post-training/RL methods. R1 is mainly a post-training/reasoning source, not a base architecture source.

## GPT-5.5 And Claude Opus 4.7 Public Notes

The repo contains an `openai-gpt-5-5-system-card.pdf` artifact and the Deployment Safety page was fetched to `gpt-codex/sources/pages/openai-gpt-5-5-deployment-safety.html`. The OpenAI release page returned HTTP 403 to `curl`, so the searchable web result is noted but the local fetchable artifact is the Deployment Safety page and PDF.

Claude Opus 4.7 was fetched from Anthropic at `gpt-codex/sources/pages/anthropic-claude-opus-4-7-release.html`.

Both GPT-5.5 and Claude Opus 4.7 remain capability targets only. No architecture claim should be derived from either without primary architecture disclosure.

## Practical Target For Project X

Project X should not try to clone a frontier model. The first credible target is a falsifiable memory architecture experiment:

- Same data, steps, batch, optimizer, and parameter budget as a transformer control.
- Measure validation loss, long-range retrieval/association, KV or memory bytes per token, decode-time memory movement proxy, and training stability.
- Kill the idea if it only helps synthetic long-context tasks while hurting normal LM loss materially.
