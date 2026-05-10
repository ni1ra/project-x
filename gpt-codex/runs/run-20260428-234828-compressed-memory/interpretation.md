# Run Interpretation

Run ID: `run-20260428-234828-compressed-memory`

Mode: `test`  
Device: CPU  
Result: `gpt-codex/runs/run-20260428-234828-compressed-memory/result.json`

## Outcome

The dual-rate compressed-memory candidate passed the initial mechanical gate:

- Validation loss regression: `0.0000355575`, effectively tied with control in this tiny run.
- Estimated memory improvement: `0.4375`.
- Candidate selector entropy: `1.0693`, so top-k selection did not collapse immediately.
- Selected block age: `3.2059`, so selection was not purely the most recent block.

## What Did Not Improve

Delayed-association accuracy was `0.0` for both control and candidate. Six training steps are enough for smoke validation but not enough to claim long-range association learning.

## Next Experiment

Make the probe stronger and more learnable in short mode:

- Add a dedicated delayed-association evaluation loss on the final token, not only argmax accuracy.
- Increase short-mode steps modestly while keeping under 180 seconds.
- Run two seeds and require the candidate to keep memory-byte advantage while improving the targeted probe.

Follow-up runs completed:

- `run-20260428-234939-compressed-memory-seed-1337`
- `run-20260428-234941-compressed-memory-seed-2026`

Both preserved the memory-byte advantage and non-collapsed selector entropy. Delayed-association loss slightly favored the candidate, but delayed-association accuracy remained tied and weak.
