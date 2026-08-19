/**
 * What the buyer has paid for.
 *
 * Two tiers, so this tracks two shapes of ownership:
 *   - a SINGLE purchase unlocks exactly that relationship
 *   - the COLLECTION unlocks all five, including tests not taken yet
 *
 * Nothing is ever revoked, so a returning visitor gets back what they paid for.
 *
 * ── How much this actually protects ────────────────────────────────────────
 * Access is granted only when the page can see evidence of a completed Stripe
 * Checkout Session (see routes/unlocked.tsx). That closes the hole that
 * mattered: simply visiting /unlocked used to hand over the product, which
 * made a public URL into a free download for anyone who found or shared it.
 *
 * It is still not cryptographic proof. Verifying a session id genuinely means
 * asking Stripe, and asking Stripe means a server. Someone who reads this
 * JavaScript can still forge a grant. The trade is deliberate at $0.99–$2.99
 * with no backend to run — but if you are paying for traffic, the server-side
 * check is the upgrade, and the generator in src/lib/manual runs unchanged in
 * Node when you want it.
 */

/**
 * Storage key is versioned. Bumping it invalidates every grant issued by an
 * older, more permissive build — including the ones handed out by simply
 * loading /unlocked. Bump it again any time the granting rules tighten.
 */
const KEY = "ell:access:v2";

interface AccessRecord {
  /** True once the five-manual collection has been bought. */
  all: boolean;
  /** Relationship slugs bought individually. */
  singles: string[];
  /** Stripe Checkout Session ids that produced these grants, for support. */
  sessions: string[];
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
      sessions: Array.isArray(parsed.sessions)
        ? parsed.sessions.filter((s) => typeof s === "string")
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

function blank(): AccessRecord {
  return { all: false, singles: [], sessions: [], grantedAt: Date.now() };
}

/** Unlock one relationship — what a single purchase buys. */
export function grantSingle(slug: string, session: string): void {
  const current = read() ?? blank();
  if (!current.singles.includes(slug)) current.singles.push(slug);
  if (!current.sessions.includes(session)) current.sessions.push(session);
  write(current);
}

/** Unlock every relationship — what the collection buys. */
export function grantAll(session: string): void {
  const current = read() ?? blank();
  current.all = true;
  if (!current.sessions.includes(session)) current.sessions.push(session);
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
