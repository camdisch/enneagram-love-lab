/**
 * The paywall, as one pure function.
 *
 * This is the single place that decides whether a visitor gets the product.
 * It lived inside the /unlocked component, which meant the most
 * money-sensitive branch in the codebase could only be exercised by clicking
 * through a real browser — so in practice it was never exercised at all. It is
 * a plain function now: no React, no storage, no DOM. Everything it needs is
 * an argument, so every path can be asserted in CI (scripts/verify-paywall.ts).
 *
 * ── The rule ───────────────────────────────────────────────────────────────
 * Two independent things must BOTH be true before anything unlocks:
 *
 *   1. Stripe handed back something shaped like a Checkout Session id.
 *   2. This browser holds a record showing it actually began a checkout.
 *
 * Either alone is something a passer-by could produce: a shared link carries
 * a session id, and anyone can click a buy button and abandon it. Requiring
 * both is what stopped /unlocked from being a free download URL.
 *
 * ── What this is not ───────────────────────────────────────────────────────
 * This is evidence, not verification. Really verifying a session means asking
 * Stripe, and asking Stripe means a server. Someone who reads this JavaScript
 * can still forge a grant. That trade is deliberate at $0.99 with no backend:
 * it stops passers-by and shared links, which is the leak that was actually
 * happening. If it ever stops being a fair trade, the upgrade is a Node
 * service running the same generator behind a real session check.
 */

import type { PendingPurchase } from "./pendingPurchase";

/** Stripe Checkout Session ids look like cs_live_… or cs_test_…. */
export const SESSION_ID_PATTERN = /^cs_(live|test)_[A-Za-z0-9]{8,}$/;

export interface AccessInput {
  /** `session_id` from the URL, if any. */
  session: string | undefined;
  /** The `all` search param, if any — Stripe's bundle marker. */
  all: string | undefined;
  /** What this browser recorded before leaving for Stripe. */
  record: PendingPurchase | null;
}

export type AccessDecision =
  | { outcome: "grant"; tier: "single" | "bundle"; session: string; record: PendingPurchase }
  /** Valid-looking session, but no record — almost certainly a real buyer. */
  | { outcome: "stranded" }
  /** No acceptable payment evidence. Show the wall. */
  | { outcome: "refuse" };

/** Whether a string is shaped like a Stripe Checkout Session id. */
export function looksLikeSession(session: string | undefined): boolean {
  return typeof session === "string" && SESSION_ID_PATTERN.test(session);
}

/**
 * Whether the `all` param marks this as a bundle purchase.
 *
 * TanStack Router parses `?all=1` as a NUMBER, so this must tolerate both.
 * Absent, empty and "0" all mean "not a bundle"; anything else means bundle.
 */
export function marksBundle(all: string | undefined): boolean {
  return all !== undefined && all !== "" && all !== "0";
}

export function decideAccess({ session, all, record }: AccessInput): AccessDecision {
  const paid = looksLikeSession(session);

  if (!paid || !record) {
    // A session id with no record is the signature of a buyer whose checkout
    // crossed a storage boundary, not of a stranger — a stranger has no
    // session id at all. Nothing is granted either way; only the wording of
    // the screen changes, so this distinction can never leak the product.
    return paid && !record ? { outcome: "stranded" } : { outcome: "refuse" };
  }

  const tier = marksBundle(all) || record.tier === "bundle" ? "bundle" : "single";
  // `paid` narrowed session to a string, but TypeScript cannot see through the
  // helper, so assert what the guard already proved.
  return { outcome: "grant", tier, session: session as string, record };
}
