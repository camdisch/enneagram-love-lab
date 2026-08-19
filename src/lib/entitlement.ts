/**
 * Who has paid, and what that unlocks.
 *
 * The product is the collection: one $3.33 purchase unlocks the manual for
 * every relationship, not just the one they had tested when they bought. That
 * is the only version of "all five" that can actually work — each manual is
 * generated from that relationship's own quiz answers, and a buyer has taken
 * exactly one test at the moment they pay. So the purchase grants standing
 * access, and each further test they take produces its manual for free.
 *
 * This is an honour-system unlock, deliberately. A flag in localStorage is not
 * a security boundary: anyone who reads the site's JavaScript can set it. At
 * $3.33 the conversion win from instant, serverless delivery is worth far more
 * than the leakage. If that ever stops being true, move generation behind a
 * server that verifies the Stripe session — the generator in src/lib/manual
 * runs unchanged in Node.
 */

const KEY = "ell:collection-access";

interface Access {
  grantedAt: number;
  /** Stripe's checkout session id when it came back on the redirect. */
  reference?: string | undefined;
}

export function grantAccess(reference?: string): void {
  if (typeof window === "undefined") return;
  try {
    const existing = readAccess();
    // Keep the original purchase date if they come back through /unlocked again.
    const payload: Access = {
      grantedAt: existing?.grantedAt ?? Date.now(),
      reference: reference ?? existing?.reference,
    };
    window.localStorage.setItem(KEY, JSON.stringify(payload));
  } catch {
    // Private browsing or a full quota. The download on this page still works;
    // only the "come back later" convenience is lost, so never throw here.
  }
}

function readAccess(): Access | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Access>;
    return typeof parsed?.grantedAt === "number"
      ? { grantedAt: parsed.grantedAt, reference: parsed.reference }
      : null;
  } catch {
    return null;
  }
}

/** True once the collection has been bought in this browser. */
export function hasAccess(): boolean {
  return readAccess() !== null;
}
