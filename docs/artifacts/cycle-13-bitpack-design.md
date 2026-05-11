# Cycle 13 #1 — Bitwise-Packed Binary HDC Design

**Status:** design doc; cycle-13 implementation lands the actual code per this spec.
**Date:** 2026-05-11.
**Prerequisite for:** cycle-13 #3 emergence-at-scale re-attempt on the ~22k-fragment Tier-2 corpus.
**Triggered by:** cycle-12 WSL crash (~06:22 CEST) on the 22k-fragment k-means run; 7.8 GB RAM ceiling exceeded by 500MB-2GB-of-input-vectors plus k-means inner-loop allocations.

---

## 1. The bipolar-to-binary equivalence

The HDC substrate uses **bipolar** hypervectors with values in `{-1, +1}` (stored as int8). The cosine of two bipolar D-dim vectors `a, b` is:

```
cos(a, b) = (a · b) / (||a|| · ||b||)
         = (a · b) / D                          # because ||x|| = √D for bipolar
         = (#agreements - #disagreements) / D
         = (D - 2·#disagreements) / D
```

Map bipolar `{-1, +1}` to binary `{0, 1}` via the convention `−1 → 0, +1 → 1`. Then `#disagreements between bipolar a, b` equals `popcount(binary_a XOR binary_b)`. This gives the closed-form:

```
cos(a, b) = (D - 2·popcount(binary_a XOR binary_b)) / D
```

Mathematically exact for bipolar inputs (no quality loss vs `cosine_bipolar`). Implementation needs to verify this empirically on a representative sample.

## 2. Storage compression

A bipolar int8 hypervector at D=10000 occupies **10,000 bytes** per vector. Packing 32 bits into one int32 (or 64 into one int64) compresses the same hypervector to **~313 int32 values = 1,252 bytes**. Net **~8× compression** vs int8; **~32× compression** vs the int32/float32 representations the encoder pipeline used in intermediate stages.

At cycle-12 scale (~50k-200k unique trigrams × D=10000 bipolar):
- int8 footprint: 500 MB – 2 GB
- packed int32 footprint: **62 MB – 250 MB**
- packed int64 footprint: ~62 MB – 250 MB (same; one int64 holds 64 bits same as two int32s)

Net: brings input-vector RAM from "exceeds 7.8 GB ceiling on a 7-GB-RAM VM with overhead" to "fits in 250 MB with room for k-means inner-loop assignment matrices".

## 3. Implementation surface (cycle-13 #1)

### 3.1 New module: `src/project_x/hdc_infra/bitpack.py`

Three primitives + one constant:

```
PACK_DTYPE = np.uint32     # 32 bits per packed word; uint to avoid sign-bit confusion

def pack_bipolar(hv: np.ndarray) -> np.ndarray:
    """Convert (D,) int8 bipolar (±1) → (D/32,) uint32 packed.
    Maps -1 → 0, +1 → 1; uses numpy.packbits behavior on the boolean mask hv > 0.
    Raises ValueError if D is not divisible by 32 (callers pad upstream)."""

def unpack_bipolar(packed: np.ndarray, D: int) -> np.ndarray:
    """Inverse of pack_bipolar; returns (D,) int8 bipolar (±1).
    `D` parameter required because packed shape alone underdetermines trailing bits."""

def cosine_packed(a_packed: np.ndarray, b_packed: np.ndarray, D: int) -> float:
    """Cosine between two packed bipolar hvs via the formula
    cos = (D - 2 * popcount(a XOR b)) / D.
    Uses int(bin(...).count('1')) per uint32 word, OR np.bitwise_count when available.
    Returns float in [-1.0, +1.0]; exactly equal to cosine_bipolar(unpack(a), unpack(b))."""
```

### 3.2 Integration shim — `src/project_x/experiments/encoder.py`

`CharNgramHashEncoder.encode(texts: list[str]) -> np.ndarray` currently returns `(n, D) int8 bipolar`. Add a sibling method:

```
def encode_packed(self, texts: list[str]) -> np.ndarray:
    """Same as encode() but returns (n, D/32) uint32 packed.
    For corpus-scale workflows that don't need the unpacked representation."""
```

The integration shim is opt-in: existing callers (`reasoning_agent.py` natural-mode dispatcher, `random_index_hebbian.py` query path) continue to receive int8 bipolar via `encode()`. Only emergence-at-scale and other scale-bottlenecked workflows switch to `encode_packed()`.

### 3.3 Primitive emergence opt-in — `src/project_x/corpus/primitive_emergence.py`

`_kmeans_cosine_bipolar(hvs, k, max_iters)` currently expects bipolar int8 input. Add a packed variant:

```
def _kmeans_cosine_packed(hvs_packed: np.ndarray, D: int, k: int, max_iters: int = 20) \
    -> tuple[np.ndarray, np.ndarray]:
    """K-means on packed hvs using cosine_packed for distance.
    Centroid update: bundle members in packed space (popcount-aware majority vote per bit).
    Returns (assignments: (n,), centroids_packed: (k, D/32) uint32)."""
```

The packed centroid update needs care: bundle = sign(sum of members). For packed bipolar, this becomes a per-bit majority-vote across cluster members. With `n_members = N`, the centroid's bit `i` is 1 iff at least `ceil(N/2)` members have bit `i` set. Implementable via accumulated int32 bit-count per dimension over members + threshold comparison.

`run_primitive_emergence` gains a `packed: bool = False` parameter; defaults preserve cycle-11 #06 behavior.

## 4. The empirical equivalence test (load-bearing)

The bitpack module's load-bearing test is **cosine_packed must equal cosine_bipolar on the same inputs**, mod floating-point. Test plan:

1. Generate 50 random bipolar hypervector pairs at D = 10000 (numpy random seed for reproducibility).
2. For each pair, compute `c_bipolar = cosine_bipolar(a, b)` (existing helper).
3. Pack: `a_p = pack_bipolar(a); b_p = pack_bipolar(b)`.
4. Compute `c_packed = cosine_packed(a_p, b_p, D=10000)`.
5. Assert `abs(c_bipolar - c_packed) < 1e-9` (float epsilon; the formula is exact in integer math).

Edge cases:
- `D = 32` (single packed word) — exercises the boundary
- `D = 64, 96, 128` — multi-word
- `D not divisible by 32` — must raise ValueError on pack_bipolar; documented
- all-zeros bipolar = (sign(0) = +1 convention applies; pack must preserve)
- all-ones bipolar — cosine = +1.0 trivial
- antipodal pair (a, -a) — cosine = -1.0 trivial

If any test fails, the bitpack module is broken; cycle-13 #3 emergence-at-scale stays deferred until it lands clean.

## 5. RAM math at cycle-13 scale

Cycle-13 #3 will run k-means on the ~22k-fragment Tier-2 corpus. Trigram extraction yields ~50k-200k unique trigrams depending on corpus diversity (cycle-12's 22k fragments hit ~80k trigrams empirically per the corpus pipeline output before WSL crashed).

| Representation | Per-vector size | 80k trigrams total | 200k trigrams total |
|---|---|---|---|
| Existing int8 bipolar | 10,000 bytes | 763 MB | 1.91 GB |
| Packed uint32 | 1,252 bytes | 96 MB | 239 MB |
| **Compression ratio** | **~8×** | | |

Plus k-means inner-loop: assignment array `(n,) int32` = 320 KB – 800 KB (negligible); centroid array `(k=15, D=10000) int8` or `(k=15, D/32) uint32` = 150 KB – 19 KB (both negligible). Net RAM at k-means time = ~96-239 MB for packed input + a few MB of intermediates; well under the 7.8 GB ceiling with room for OS + Python + other processes.

## 6. Cosine-via-popcount implementation notes

NumPy's `np.bitwise_count` (added in NumPy 2.0) provides vectorized popcount on uint arrays. Fallback for older NumPy: per-word `int.bit_count()` (Python 3.10+) wrapped in a vectorized loop, OR the table-based popcount Bob Jenkins style. Bench the three approaches at 80k trigrams × k=15 = 1.2M cosines per k-means iteration; pick the fastest that doesn't allocate per-call.

**Important gotcha:** popcount of `a XOR b` returns #bits-different. The cosine formula `(D - 2·popcount) / D` is only correct if `popcount` operates on the FULL D bits, not the packed word count. If `D = 10000` and we have 313 uint32 words containing 313×32 = 10,016 bits total, the last 16 bits are pad. The pack/unpack contract must pad with zeros (which are bipolar -1 by the convention), and tests must verify this. Or D must be a multiple of 32 (cleanest; document the constraint).

Recommendation: require `D % 32 == 0`. At D = 10000, that's 1 word short of a multiple; bump default D to 10240 (which is 320 × 32) OR use 9984 (312 × 32). The encoder change is minimal and the change ripples are bounded. Cycle-13 instance picks one.

## 7. Test suite pressure (advisor catch — flagged for cycle 13 attention)

Pytest at cycle-12 close shipped **596 tests in 187.79s** (~3:07). Cycle-9 close was 479 tests in 22s. That's 596/479 = 1.24× test count but 187.79/22 = 8.54× runtime — a 7× slower-per-test ratio. The slowdown is plausibly from corpus loading at import time (corpus modules iterate the data directory), audit UI hooks initializing JSONL writers, or both.

**This is a real scaling-cliff signal beyond k-means RAM.** At the current trajectory, cycle 20 has 10-minute pytest runs. Cycle 13 should:

1. **Profile** what's slow in the existing suite (`pytest --durations=20`) — identify top-10 worst offenders.
2. **Defer corpus loading** at module import; load on first encoder call only.
3. **Mock the audit log writer** in tests; use `tmp_path` fixture; avoid touching `data/audit_log/`.
4. **Add a pytest mark** like `@pytest.mark.slow` for tests that genuinely need full corpus; CI runs `not slow` by default.

Not blocking bitpack ship; flagged so cycle 13's pytest profile + corpus-lazy-load lands alongside bitpack.

## 8. Cycle-13 #1 deliverable shape

The cycle-13 instance lands:
- `src/project_x/hdc_infra/__init__.py` (new package; empty + module docstring)
- `src/project_x/hdc_infra/bitpack.py` (~120-200 lines per the surface in §3.1)
- `src/project_x/experiments/encoder.py` (gain `encode_packed` method; ~20-line addition)
- `tests/test_bitpack.py` (~150 lines; 12-20 tests covering the empirical equivalence + edge cases per §4)
- REPO_CONTROL.md row for the new `hdc_infra/` package (per co-landing rule)
- Atomic commit `feat(P13c13-01-bitpack)` + push

Expected duration: **45-75 min Raphael-time** (per advisor's honest estimate; cycle-12 close's 28-min estimate was 2× optimistic for the operation actually proposed).

Cycle-13 #1 ships BEFORE cycle-13 #3 emergence-at-scale (which depends on it). Both can ship in cycle 13's first session if lain greenlights an apotheosis window.

## 9. Honest counter-claims

1. **The popcount fast-path is hardware-dependent.** NumPy 2.0's `bitwise_count` is C-vectorized but only available on numpy ≥ 2.0; project's numpy version determines whether the fast-path is available. Cycle-13 #1 checks numpy version and degrades gracefully.
2. **Packed centroid update is more code than packed cosine.** Per-bit majority vote across cluster members requires either unpacking + bundling + repacking (defeats the RAM win) OR direct bitwise accumulation (more code, more test surface). Cycle-13 #1 must implement direct bitwise accumulation; the unpacking shortcut is a footgun documented in §3.3.
3. **Cosine equivalence is mathematically exact but floating-point order matters.** `(D - 2·popcount) / D` and `(a · b) / D` are floating-point-equal under most orderings but can differ at the last bit for very-near-orthogonal pairs. The `<1e-9` test threshold absorbs this; tighter thresholds would be brittle.
4. **The 8× compression ratio is vs int8 bipolar.** If the project ever stored hvs as int32 or float32 (rare at the current substrate level), the compression ratio is 32× or 32× respectively. Document the ratio in the bitpack module docstring against int8 specifically.

## 10. Sources + cross-references

- Cycle-10 HDC infrastructure optimization roadmap: `docs/artifacts/cycle-10-hdc-infrastructure-optimization.md` (commit `acca853`) — names bitwise-packed binary HDC as the cycle-11+ candidate; cycle 12's WSL crash promoted it to cycle-13 #1 PREREQUISITE.
- Canonical doc Layer 5: `docs/artifacts/cycle-10-semantics-architecture.md` (commit `a06a51a`) — primitive emergence via clustering; runtime constraint that motivated bitpack.
- Cycle-11 #06 primitive-emergence MVP: commit `f0abce3`; ran at ~3k trigrams (in-RAM int8) in ~85s.
- Cycle-12 WSL crash: `docs/past_work/cycles/phase_13/dev-cycle-12.md` Tension 2; RAM bound exceeded at ~22k fragments → ~80k trigrams.
- Pentti Kanerva, *Hyperdimensional Computing* (2009) §4 (binary HDC; cosine via Hamming distance is the same identity).
- Plate, *Holographic Reduced Representations* — binding + cleanup memory; bipolar↔binary mapping convention.
- Advisor consult (cycle-12 close, 2026-05-11 ~10:35 CEST) — caught the time-budget miscalculation that motivated this design-doc-before-code approach + flagged the test-suite pressure signal.

— Cycle-13 #1 instance reads this doc + cycle-12 close + canonical doc Layer 5 + canonical Layer 7, then implements per §8. Pre-commit advisor review on the bitpack module before merge.
