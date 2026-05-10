# Kill Criteria

Global gates:

- No architecture is allowed to pass because it sounds frontier-adjacent.
- A candidate must beat or match a simple transformer control under identical data, tokens, steps, batch, optimizer, and hardware limits.
- Any reported gain must include at least one normal LM metric and one targeted long-context/memory metric.
- If implementation exceeds the 180-second test-mode budget, it must be cut down before being considered viable.

Primary experiment kill criteria:

- Validation loss is more than 3% worse than control after matched steps.
- Long-association probe improves less than 10% relative while validation loss is worse.
- Memory/read budget is not lower than control.
- Selector entropy collapses to pure recency or uniform random and does not recover.
- Training produces repeated NaN/loss spikes in short mode.
- Code requires custom CUDA or heavy dependencies for the first falsification.

Promotion criteria:

- Equal or better validation loss, or a small validation loss regression offset by strong memory metric gain.
- Clear loss/byte Pareto improvement.
- Reproducible in at least two seeds in short mode.
- Failure mode is diagnosable from logged artifacts.
