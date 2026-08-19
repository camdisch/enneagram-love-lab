"""Primitives that must behave identically in Python and TypeScript.

The manual is generated in two places now: this package (for batch runs and
CI) and a TypeScript port that runs in the buyer's browser. Both must produce
the *same words* for the same result, or the product is inconsistent and the
cross-language diff test is meaningless.

Three things in the standard library quietly differ between the two languages
and would cause that drift:

* ``random.Random`` is a Mersenne Twister; JavaScript has no equivalent.
* ``hashlib.sha256`` needs an async API in browsers.
* ``round()`` is banker's rounding in Python (``round(2.5) == 2``) and
  half-up in JavaScript (``Math.round(2.5) === 3``).

So all three are replaced here with tiny explicit implementations that are
trivial to mirror exactly. None of them need to be cryptographic or
statistically excellent -- they need to be *identical*.
"""

from __future__ import annotations

from typing import Sequence, TypeVar

T = TypeVar("T")

_UINT32 = 0xFFFFFFFF


def fnv1a(text: str) -> int:
    """32-bit FNV-1a over the UTF-8 bytes. Deterministic across languages."""
    h = 0x811C9DC5
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & _UINT32
    return h


class Rng:
    """Mulberry32 — a small, fast, fully specified PRNG.

    Chosen because it is four lines of arithmetic with no language-specific
    behaviour, so the TypeScript version is provably the same generator
    rather than approximately the same one.
    """

    def __init__(self, seed: int) -> None:
        self.state = seed & _UINT32

    def next_u32(self) -> int:
        self.state = (self.state + 0x6D2B79F5) & _UINT32
        t = self.state
        t = ((t ^ (t >> 15)) * (t | 1)) & _UINT32
        t = (t ^ (t + ((t ^ (t >> 7)) * (t | 61)) & _UINT32)) & _UINT32
        return (t ^ (t >> 14)) & _UINT32

    def next_float(self) -> float:
        return self.next_u32() / 4294967296.0

    def below(self, n: int) -> int:
        """Uniform-ish integer in [0, n). Bias is irrelevant at these sizes."""
        return self.next_u32() % n if n > 0 else 0

    def shuffle(self, items: list[T]) -> list[T]:
        """Fisher-Yates, descending, in place. Returns the same list."""
        for i in range(len(items) - 1, 0, -1):
            j = self.below(i + 1)
            items[i], items[j] = items[j], items[i]
        return items


def round_half_up(value: float) -> int:
    """Round .5 away from zero, matching JavaScript's Math.round for x >= 0.

    Python's built-in round() is half-to-even, so ``round(2.5)`` is 2 while
    ``Math.round(2.5)`` is 3. Percentages would disagree between the two
    implementations roughly one time in two hundred without this.
    """
    import math

    return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)
