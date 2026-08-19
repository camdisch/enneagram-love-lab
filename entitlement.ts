/**
 * What the buyer has paid for.
 *
 * Two tiers, so this has to track two shapes of ownership:
 *
 *   - buying a SINGLE manual unlocks exactly that relationship
 *   - buying the COLLECTION unlocks all five, including tests not taken yet
 *
 * Someone who buys the Mom manual and later upgrades keeps both records; the
 * collection flag simply wins. Nothing is ever revoked, so a repeat visitor
 * always gets back what they paid for.
 *
 * This is an honour-system unlock, deliberately. A flag in localStorage is not
 * a security boundary — anyone who reads the site's JavaScript can set it. At
 * a dollar, the conversion win from instant serverless delivery is worth far
 * more than the leakage. If that ever stops being true, move generation behind
 * a server that verifies the Stripe session; the generator in src/lib/manual
 * runs unchanged in Node.
 */

const KEY = "ell:access";

interface AccessRecord {
  /** True once the five-manual collection has been bought. */
  all: boolean;
  /** Relationship slugs bought individually. */
  singles: string[];
  grantedAt: number;
}

function read(): AccessRecord | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<AccessRecord>;
    return {
      all: parsed.all === true,
      singles: Array.isArray(parsed.singles)
        ? parsed.singles.filter((s) => typeof s === "string")
        : [],
      grantedAt: typeof parsed.grantedAt === "number" ? parsed.grantedAt : Date.now(),
    };
  } catch {
    return null;
  }
}

function write(record: AccessRecord): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(record));
  } catch {
    // Private browsing or a full quota. The download on the current page still
    // works; only the "come back later" convenience is lost, so never throw.
  }
}

/** Unlock one relationship — what a $0.99 purchase buys. */
export function grantSingle(slug: string): void {
  const current = read() ?? { all: false, singles: [], grantedAt: Date.now() };
  if (!current.singles.includes(slug)) current.singles.push(slug);
  write(current);
}

/** Unlock every relationship — what the collection buys. */
export function grantAll(): void {
  const current = read() ?? { all: false, singles: [], grantedAt: Date.now() };
  current.all = true;
  write(current);
}

/** Whether this specific manual has been paid for. */
export function hasAccessTo(slug: string): boolean {
  const record = read();
  return record !== null && (record.all || record.singles.includes(slug));
}

/** Whether the full collection has been bought (hides the upsell). */
export function hasCollection(): boolean {
  return read()?.all === true;
}

/** Slugs unlocked individually, for the "you own these" list. */
export function ownedSingles(): string[] {
  return read()?.singles ?? [];
}
