/**
 * Single source of truth for the paid product.
 *
 * Before this file existed, the landing page sold a "$2.99 Premium
 * Relationship Blueprint" and the results page sold a "$0.99 Operator's
 * Manual" — two names, two prices, two different Stripe links, one product.
 * A visitor who reads one price and meets another at checkout hesitates, and
 * hesitation at $3 is a lost sale. Every surface reads from here now, so the
 * two can never drift apart again.
 *
 * The product is the COLLECTION: one payment unlocks the manual for all five
 * relationships. See src/lib/entitlement.ts for why it has to work that way.
 */

export const PRODUCT = {
  name: "The Operator's Manual Collection",
  /** Used where a single manual is the subject rather than the bundle. */
  manualName: "Operator's Manual",
  /** Buy-button label. Written out so no template has to glue words together. */
  ctaLabel: "Unlock all five manuals",
  description:
    "Your free result names their archetype. The manual is the 24-page PDF that tells you what to actually do with it — their triggers, their repair language, and the sentence that ends most of your fights. One payment unlocks it for all five people you can test.",
  price: "$3.33",
  /** Shown struck through beside the price. Empty string hides it. */
  compareAtPrice: "",
  stripeUrl: "https://buy.stripe.com/4gM6oHdLt7Pb3lC2Hmdby02",

  /** Guards every buy button, so an unset link can never render as a dead one. */
  get isConfigured(): boolean {
    return this.stripeUrl.startsWith("https://");
  },
} as const;

/**
 * Where Stripe returns the buyer after a successful payment.
 *
 * REQUIRED SETUP — nothing is delivered until this is done:
 * Stripe → Payment Links → your link → Edit → "After payment" →
 * "Don't show confirmation page" → "Redirect customers to your website" →
 *
 *     https://YOUR-DOMAIN/unlocked
 *
 * The quiz result is written to localStorage before the buyer leaves for
 * Stripe, so /unlocked can rebuild it and generate the PDF in their browser
 * the moment they land back — no server, no email, no wait.
 */
export const AFTER_PAYMENT_PATH = "/unlocked";
