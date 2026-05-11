"""HDC infrastructure package — cycle-13 #1 substrate insurance.

Hosts bit-packed binary HDC primitives that compress bipolar int8 hypervectors
to uint32-packed binary (~32× compression vs int8 / ~8× vs int32) while
preserving cosine-via-popcount mathematical equivalence. Unblocks
emergence-at-scale on the 22k-fragment Tier-2 corpus (cycle-12 deferred #06
WSL crashed at the int8 footprint; packed footprint fits comfortably).

Design doc: `docs/artifacts/cycle-13-bitpack-design.md` (commit `e9b64cc`).
Synthesis verdict: `docs/artifacts/cycle-13-priority-decision.md`.

Organic-thesis compliance: no LLM, no learning. Pure binary arithmetic over
the existing CharNgramHashEncoder output.
"""

from project_x.hdc_infra.bitpack import (
    PACK_DTYPE,
    cosine_packed,
    pack_bipolar,
    unpack_bipolar,
)

__all__ = ["PACK_DTYPE", "cosine_packed", "pack_bipolar", "unpack_bipolar"]
