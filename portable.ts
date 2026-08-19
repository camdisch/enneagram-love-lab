/**
 * Primitives that must behave identically here and in the Python package.
 *
 * The manual is generated in two places: this browser port, and the Python
 * package under `pdf/` used for batch runs and CI. Both must produce the same
 * words for the same quiz result. Three standard-library behaviours differ
 * between the languages and would cause silent drift:
 *
 *   - Python's `random.Random` is a Mersenne Twister; JS has no equivalent.
 *   - `hashlib.sha256` needs an async API in browsers.
 *   - `round()` is half-to-even in Python, half-up in JS.
 *
 * All three are replaced with explicit implementations small enough to be
 * provably the same in both languages. Mirrors `enneagram_manual/portable.py`.
 */

const UINT32 = 0xffffffff;

/** 32-bit FNV-1a over UTF-8 bytes. */
export function fnv1a(text: string): number {
  let h = 0x811c9dc5;
  const bytes = new TextEncoder().encode(text);
  for (const byte of bytes) {
    h ^= byte;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

/** Mulberry32. Small, fast, fully specified — so the port is exact. */
export class Rng {
  private state: number;

  constructor(seed: number) {
    this.state = seed >>> 0;
  }

  nextU32(): number {
    this.state = (this.state + 0x6d2b79f5) >>> 0;
    let t = this.state;
    t = Math.imul(t ^ (t >>> 15), t | 1) >>> 0;
    t = (t ^ (t + (Math.imul(t ^ (t >>> 7), t | 61) >>> 0))) >>> 0;
    return (t ^ (t >>> 14)) >>> 0;
  }

  below(n: number): number {
    return n > 0 ? this.nextU32() % n : 0;
  }

  /** Fisher-Yates, descending, in place. */
  shuffle<T>(items: T[]): T[] {
    for (let i = items.length - 1; i > 0; i--) {
      const j = this.below(i + 1);
      // Both indices are < items.length, so the reads are always defined.
      const a = items[i] as T;
      const b = items[j] as T;
      items[i] = b;
      items[j] = a;
    }
    return items;
  }
}

/** Round .5 away from zero — Python's round() would go to even. */
export function roundHalfUp(value: number): number {
  return value >= 0 ? Math.floor(value + 0.5) : Math.ceil(value - 0.5);
}

/** Python's `"%.4f" % x`, which JS toFixed matches for our range. */
export function fixed4(value: number): string {
  return value.toFixed(4);
}
