"""HDC infrastructure package.

Cycle-13 #1 substrate insurance: bit-packed binary HDC primitives that
compress bipolar int8 hypervectors to uint32-packed binary (~32× compression
vs int8 / ~8× vs int32) while preserving cosine-via-popcount mathematical
equivalence. Unblocks emergence-at-scale on the 22k-fragment Tier-2 corpus
(cycle-12 deferred #06 WSL crashed at the int8 footprint; packed footprint
fits comfortably).
Design doc: `docs/artifacts/cycle-13-bitpack-design.md` (commit `e9b64cc`).

Cycle-14 #08a: HebbianBank — substrate-wide reward-driven co-occurrence
storage. The substrate's first write path from rated experience. Strict-
strict-thesis fit per `docs/artifacts/cycle-14-priority-decision.md`.

Organic-thesis compliance: no LLM, no pretrained transformer derivatives.
Pure binary arithmetic + Hebbian co-occurrence over the CharNgramHashEncoder
substrate.
"""

from project_x.hdc_infra.bitpack import (
    PACK_DTYPE,
    cosine_packed,
    pack_bipolar,
    unpack_bipolar,
)
from project_x.hdc_infra.hebbian import HebbianBank

__all__ = [
    "PACK_DTYPE",
    "cosine_packed",
    "pack_bipolar",
    "unpack_bipolar",
    "HebbianBank",
]
