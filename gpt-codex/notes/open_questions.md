# Open Questions

## Source Questions

- Need OpenAI GPT-5.5 release page as a local artifact if the 403 can be resolved through an official fetchable endpoint; the system-card PDF and Deployment Safety page are already local.
- Need Claude Opus 4.7 system-card equivalent if Anthropic publishes one separately from the release page.
- Need exact V4 CSA/HCA compression rates, top-k, layer schedule, and indexer dimensions from released inference code if public.
- Need current public status of DeepSeek V3.2, because V4 comparisons depend on that baseline.

## Mechanism Questions

- Does block-compressed top-k memory improve real next-token validation loss at tiny scale, or only long-context probes?
- Can a learned compressor be trained end-to-end without collapse into local-window dependence?
- What is the minimum long-context task that distinguishes content addressability from smoothed recurrent memory?
- Does a dual-memory system need explicit write losses, or can token loss train useful memory writes?
- Can routing/indexing be warmed up without dense attention at small scale?
- Is constrained residual mixing useful in small models, or only when depth/scale creates instability?

## Experiment Questions

- What parameter budget keeps control and candidate fair when candidate adds compressor/indexer parameters?
- Should the first experiment match total parameters or active FLOPs?
- What long-range metric is least gameable: needle retrieval, copy/association, contradiction tracking, or delayed variable binding?
- How much local-window size is required before compression effects become visible?
