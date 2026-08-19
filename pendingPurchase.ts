/**
 * Carries the quiz result across the trip to Stripe and back.
 *
 * The buyer leaves your site for Stripe's checkout and returns to a fixed
 * redirect URL that cannot carry their result in it. sessionStorage does not
 * reliably survive that round trip (some browsers treat the return as a new
 * session, and mobile Safari may discard it entirely), so the result is
 * written to localStorage before they leave and read back when they return.
 *
 * Deliberately not a security boundary: this is an honour-system unlock on a
 * $0.99 impulse product, where instant delivery is worth far more than
 * airtight enforcement. Anyone determined enough to read your JavaScript can
 * generate a manual without paying. If that ever becomes a real problem, the
 * fix is to move generation behind a server that checks the Stripe session —
 * the engine in src/lib/manual runs unchanged in Node.
 */

import type { Scores } from "./enneagram";

const KEY = "ell:pending-purchase";
const MAX_AGE_MS = 1000 * 60 * 60 * 24 * 7; // a week is generous for a checkout

export type PurchaseTier = "single" | "bundle";

export interface PendingPurchase {
  scores: string;
  relationship: string;
  /**
   * Which button they clicked. Both Stripe links redirect to the same page,
   * so this is how /unlocked knows whether to unlock one manual or all five.
   */
  tier: PurchaseTier;
  /**
   * Explicitly `| undefined` rather than just optional: the repo runs with
   * exactOptionalPropertyTypes, under which an optional property may be
   * omitted but not assigned undefined.
   */
  subjectName?: string | undefined;
  savedAt: number;
}

export function savePendingPurchase(input: Omit<PendingPurchase, "savedAt">): void {
  if (typeof window === "undefined") return;
  try {
    const payload: PendingPurchase = { ...input, savedAt: Date.now() };
    window.localStorage.setItem(KEY, JSON.stringify(payload));
  } catch {
    // Private browsing or a full quota — never block the buyer over this.
    // They can still re-run the quiz from the results link.
  }
}

export function loadPendingPurchase(): PendingPurchase | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<PendingPurchase>;
    if (!parsed || typeof parsed.scores !== "string" || typeof parsed.relationship !== "string") {
      return null;
    }
    if (typeof parsed.savedAt === "number" && Date.now() - parsed.savedAt > MAX_AGE_MS) {
      return null;
    }
    return {
      scores: parsed.scores,
      relationship: parsed.relationship,
      // Anything written before the two-tier split, or by a tampered-with
      // storage entry, is treated as the cheaper purchase.
      tier: parsed.tier === "bundle" ? "bundle" : "single",
      subjectName: typeof parsed.subjectName === "string" ? parsed.subjectName : undefined,
      savedAt: parsed.savedAt ?? Date.now(),
    };
  } catch {
    return null;
  }
}

export function clearPendingPurchase(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* nothing useful to do */
  }
}

/**
 * Pack a Scores map into the compact "1-2-0-3-1-0-4-0-1" form the manual
 * generator reads. Order is types 1..9, always nine values, so a missing or
 * zero score never shifts the others.
 */
export function encodeScores(scores: Scores): string {
  return [1, 2, 3, 4, 5, 6, 7, 8, 9].map((t) => scores[t as keyof Scores] ?? 0).join("-");
}
