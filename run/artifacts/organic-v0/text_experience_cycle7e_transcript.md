# Cycle 7E Text Experience Transcript

Generated: 2026-05-14T03:44:49Z

This transcript preserves raw organic-v0 output before correction, after correction, and on held-out probes. Empty output is written as `<empty>`. The correction text is training feedback, not a generation-time answer template.

Learning disabled by ablation: false

## Training Records

### txe7e_train_001

- input: `what does arin carry`
- before correction: `arin copper key`
- correction: `arin carries copper key`
- after correction: `arin carries caries car`
- exact before/after: false / false

### txe7e_train_002

- input: `what does sora carry`
- before correction: `sora carries copper car`
- correction: `sora carries ivory compass`
- after correction: `sora carries ivory compass`
- exact before/after: false / true

### txe7e_train_003

- input: `what does luma carry`
- before correction: `luma carries amber lens`
- correction: `luma carries amber lens`
- after correction: `luma carries amber lens`
- exact before/after: true / true

### txe7e_train_004

- input: `where does arin wait`
- before correction: `arin carries carrrries `
- correction: `arin waits at north dock`
- after correction: `arin carries  north dock`
- exact before/after: false / false

### txe7e_train_005

- input: `where does sora wait`
- before correction: `sora carries carries caries caries caries caries`
- correction: `sora waits at cedar room`
- after correction: `sora waits at cedar room`
- exact before/after: false / true

### txe7e_train_006

- input: `where does luma wait`
- before correction: `luma waits at silver gates ca ca ca ca ca ca ca `
- correction: `luma waits at silver gate`
- after correction: `luma waits at silver gate`
- exact before/after: false / true

## Probe Records

### txe7e_probe_001

- input: `what does navi carry`
- raw output: `navi carries basalt prism`
- expected after oracle scoring: `navi carries basalt prism`
- exact: true

### txe7e_probe_002

- input: `what does mira carry`
- raw output: `mira carries glass lantern`
- expected after oracle scoring: `mira carries glass lantern`
- exact: true

### txe7e_probe_003

- input: `where does navi wait`
- raw output: `navi waits at quiet archive`
- expected after oracle scoring: `navi waits at quiet archive`
- exact: true

### txe7e_probe_004

- input: `where does mira wait`
- raw output: `mira waits at stone atrium`
- expected after oracle scoring: `mira waits at stone atrium`
- exact: true
