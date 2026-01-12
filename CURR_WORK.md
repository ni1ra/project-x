# CURR_WORK.md — Current Sprint

> Active tasks for WIRED-BRAIN
> Sprint: Week 1 - Infrastructure
> Updated: 2026-01-12

---

## Sprint Goal

**Establish measurement infrastructure** - Energy proxy, CCB scorer, OD-NDT harness, and baselines must be operational before any core implementation begins.

---

## Completed This Session

| Task | Status | Notes |
|------|--------|-------|
| Energy Instrumentation | DONE | FLOP + BytesMoved counter with budget enforcement |
| Byte Interface φ(o) | DONE | Pulled forward from Week 2 per JARVIS |
| Autoregressive Decoder | DONE | GRU(128) + 16-d byte embeddings |
| CCB Environment | DONE | Linear + Non-linear SCMs, byte output |
| CCB Scorer | DONE | DoErr computation, confounding discrimination |
| MF-1 Baseline | DONE | PPO + GRU agent with energy tracking |
| Integration Test | DONE | 2000-step training validated |

**Tests: 51/51 passing**

---

## Active Tasks

### Currently Working On

*None active - ready for next phase*

---

### Ready to Start

| Priority | Task | Est. Hours | Dependencies |
|----------|------|------------|--------------|
| P0 | Implement LN-GRU substrate (core brain) | 6h | Byte interface |
| P0 | Run hardware calibration for κ_F, κ_M | 2h | Energy proxy |
| P1 | Implement OD-NDT harness | 4h | Byte interface |
| P1 | Implement VAE encoder/decoder | 4h | LN-GRU |
| P2 | Implement MB-1 baseline (Dreamer-style) | 8h | Energy proxy |

---

## Sprint Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Tasks completed | 7 | 6 |
| Tests passing | 100% | 100% (51/51) |
| Energy proxy validated | Yes | Yes |
| CCB scorer validated | Yes | Yes |
| Byte interface working | Yes | Yes |
| MF-1 baseline operational | Yes | Yes |

---

## Files Created This Session

```
src/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── byte_interface.py      # φ(o) + AutoregressiveActionDecoder
│   └── mf1_baseline.py        # MF-1 agent + trainer
├── energy/
│   ├── __init__.py
│   └── proxy.py               # Energy tracking + budget enforcement
├── benchmarks/
│   ├── __init__.py
│   └── ccb.py                 # CCB + CCB-NL environments
└── utils/
    └── __init__.py

tests/
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_energy_proxy.py   # 11 tests
│   ├── test_byte_interface.py # 14 tests
│   └── test_ccb.py            # 17 tests
└── integration/
    ├── __init__.py
    └── test_mf1_ccb.py        # 9 tests

benchmarks/
└── rpj_v5_manifest.json       # Frozen hyperparameters

pyproject.toml                 # Project configuration
```

---

## Decisions Made This Sprint

| Decision | Rationale | Date |
|----------|-----------|------|
| Pull Byte Interface to Week 1 | JARVIS: Baselines need byte I/O before they can run | 2026-01-12 |
| Use Binomial sampling for k_r, N | Enables gradient flow through discrete decisions | 2026-01-12 |
| CCB outputs bytes not floats | Satisfies content-free interface requirement | 2026-01-12 |
| Same EnergyWrapper for all | Prevents energy proxy gaming between baseline/brain | 2026-01-12 |

---

## Blockers & Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Energy constants uncalibrated | High | Medium | Need hardware calibration before claiming "20W equivalent" |
| LN-GRU complexity | Medium | High | Follow BLUEPRINT exactly |

---

## Notes

- JARVIS scored project setup 415/420
- All Week 1 JARVIS validation criteria met:
  - EnergyWrapper correctly calculates Joules
  - CCB Environment outputs bytes
  - MF-1 Baseline trains on CCB using byte interface
  - Energy caps properly enforced

---

## Next Session Priorities

1. **LN-GRU Substrate** - The core brain architecture
2. **VAE Encoder/Decoder** - With q(z|h,o) posterior (not prior!)
3. **Hardware Calibration** - Get real κ_F, κ_M values
4. **OD-NDT Harness** - One-demo transfer protocol

---

## End of Sprint Checklist

- [x] All P0 tasks complete
- [x] Energy proxy tested on sample workload
- [x] CCB scorer produces valid DoErr
- [ ] OD-NDT harness can run single demo (NEXT)
- [x] At least one baseline operational
- [x] All tests green
- [ ] JARVIS validation ≥380 (need full implementation)
