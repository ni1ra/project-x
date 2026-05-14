# Cycle 7F Text Experience Replay Transcript

Generated: 2026-05-14T03:52:22Z

This transcript shows first-pass text learning, replay selection, replay before/after outputs, and post-replay probes. Replay uses stored correction records; it is not a generation-time template.

Replay disabled by ablation: false

## First Pass Training

### txe7e_train_001

- input: `what does arin carry`
- before correction: `arin copper key`
- after correction: `arin carries caries car`
- expected: `arin carries copper key`
- exact after: false

### txe7e_train_002

- input: `what does sora carry`
- before correction: `sora carries copper car`
- after correction: `sora carries ivory compass`
- expected: `sora carries ivory compass`
- exact after: true

### txe7e_train_003

- input: `what does luma carry`
- before correction: `luma carries amber lens`
- after correction: `luma carries amber lens`
- expected: `luma carries amber lens`
- exact after: true

### txe7e_train_004

- input: `where does arin wait`
- before correction: `arin carries carrrries `
- after correction: `arin carries  north dock`
- expected: `arin waits at north dock`
- exact after: false

### txe7e_train_005

- input: `where does sora wait`
- before correction: `sora carries carries caries caries caries caries`
- after correction: `sora waits at cedar room`
- expected: `sora waits at cedar room`
- exact after: true

### txe7e_train_006

- input: `where does luma wait`
- before correction: `luma waits at silver gates ca ca ca ca ca ca ca `
- after correction: `luma waits at silver gate`
- expected: `luma waits at silver gate`
- exact after: true

## Replay Events

### txe7e_train_001 / pass 1

- reason: `not_exact_after_first_pass`
- before replay: `arin carries copper key`
- after replay: `arin carries copper car`
- expected: `arin carries copper key`
- exact before/after: true / false
- replay mutation applied: false
- accepted: false
- acceptance reason: `rejected_candidate_would_degrade_local_train_or_probe`

### txe7e_train_004 / pass 1

- reason: `not_exact_after_first_pass`
- before replay: `arin waits at north dock`
- after replay: `arin waits at north dock`
- expected: `arin waits at north dock`
- exact before/after: true / true
- replay mutation applied: true
- accepted: true
- acceptance reason: `accepted_local_train_probe_not_worse`

### txe7e_train_001 / pass 2

- reason: `not_exact_after_first_pass`
- before replay: `arin carries copper key`
- after replay: `arin carries copper car`
- expected: `arin carries copper key`
- exact before/after: true / false
- replay mutation applied: false
- accepted: false
- acceptance reason: `rejected_candidate_would_degrade_local_train_or_probe`

### txe7e_train_004 / pass 2

- reason: `not_exact_after_first_pass`
- before replay: `arin waits at north dock`
- after replay: `arin waits at north dock`
- expected: `arin waits at north dock`
- exact before/after: true / true
- replay mutation applied: false
- accepted: false
- acceptance reason: `rejected_candidate_would_degrade_local_train_or_probe`

## Post-Replay Training Check

### txe7e_train_001

- raw output: `arin carries copper key`
- expected: `arin carries copper key`
- exact: true

### txe7e_train_002

- raw output: `sora carries ivory compass`
- expected: `sora carries ivory compass`
- exact: true

### txe7e_train_003

- raw output: `luma carries amber lens`
- expected: `luma carries amber lens`
- exact: true

### txe7e_train_004

- raw output: `arin waits at north dock`
- expected: `arin waits at north dock`
- exact: true

### txe7e_train_005

- raw output: `sora waits at cedar room`
- expected: `sora waits at cedar room`
- exact: true

### txe7e_train_006

- raw output: `luma waits at silver gate`
- expected: `luma waits at silver gate`
- exact: true

## Post-Replay Probe Check

### txe7e_probe_001

- raw output: `navi carries basalt prism`
- expected: `navi carries basalt prism`
- exact: true

### txe7e_probe_002

- raw output: `mira carries glass lantern`
- expected: `mira carries glass lantern`
- exact: true

### txe7e_probe_003

- raw output: `navi waits at quiet archive`
- expected: `navi waits at quiet archive`
- exact: true

### txe7e_probe_004

- raw output: `mira waits at stone atrium`
- expected: `mira waits at stone atrium`
- exact: true
