/**
 * The two things you sell, in one place.
 *
 * TIER 1 — the single manual, $0.99. This is the offer. It is what the whole
 * funnel is built to convert: cheap enough to be an impulse, specific enough
 * to feel personal.
 *
 * TIER 2 — the collection, offered *underneath* tier 1 as an upgrade for
 * people who want more than one person decoded. It never replaces the $0.99
 * option and never appears above it.
 *
 * Everything on the site reads from here, so the landing page and the results
 * page can never advertise different names or prices again — which is the bug
 * that started all of this.
 */

/**
 * ⚠️ THE PRICES BELOW MUST MATCH WHAT STRIPE ACTUALLY CHARGES.
 *
 * This file controls what the buyer *reads*. Stripe controls what the buyer is
 * *charged*. Nothing here can change a Stripe price — if the two disagree,
 * someone reads one number, gets billed another, and you eat a refund and a
 * chargeback. Change the price on the Payment Link in Stripe first, then
 * change the matching string here.
 */

export const SINGLE = {
  name: "The Operator's Manual",
  /** Short form for buttons and running text. */
  shortName: "Operator's Manual",
  description:
    "Your free result names their archetype. The manual is the 24-page PDF that tells you what to actually do with it — their triggers, their repair language, and the sentence that ends most of your fights.",
  price: "$0.99",
  /**
   * Shown struck through beside the price. Empty string hides it.
   *
   * Deliberately empty: $2.99 is now the bundle's real price, so anchoring the
   * single against it put "$0.99 was $2.99" directly above "all five — $2.99"
   * and made the bundle look like a crossed-out old price. Put a number back
   * here only if it is one that cannot be confused with the bundle.
   */
  compareAtPrice: "",
  ctaLabel: "Unlock the Operator's Manual",
  /** Charges $0.99. Verified against the link that was live on the results page. */
  stripeUrl: "https://buy.stripe.com/bJe3cv0YH1qN2hy95Kdby01",
  get isConfigured(): boolean {
    return this.stripeUrl.startsWith("https://");
  },
} as const;

export const BUNDLE = {
  name: "The Complete Collection",
  description: "All five manuals — mom, dad, boyfriend, girlfriend, best friend.",
  /**
   * ⚠️ Must match the Stripe price on the link below. This string is only what
   * the buyer READS; Stripe decides what they are CHARGED.
   */
  price: "$2.99",
  ctaLabel: "Or unlock all five",
  // The $2.99 link. Replaced the old $3.33 one (…dby02) on 19 Aug.
  stripeUrl: "https://buy.stripe.com/14A9ATfTB8Tf8FW5Tydby03",
  get isConfigured(): boolean {
    return this.stripeUrl.startsWith("https://");
  },
} as const;

/**
 * Kept as an alias so anything still importing PRODUCT gets the headline
 * offer rather than breaking. New code should use SINGLE or BUNDLE directly.
 */
export const PRODUCT = SINGLE;

/**
 * Where Stripe returns the buyer after payment.
 *
 * REQUIRED SETUP — nothing is delivered until this is set on BOTH links:
 * Stripe → Payment Links → the link → Edit → "After payment" →
 * "Don't show confirmation page" → "Redirect customers to your website":
 *
 *     single link  →  https://YOUR-DOMAIN/unlocked?session_id={CHECKOUT_SESSION_ID}
 *     bundle link  →  https://YOUR-DOMAIN/unlocked?all=1&session_id={CHECKOUT_SESSION_ID}
 *
 * The session id is REQUIRED, not optional. Without it the page cannot tell a
 * buyer from a passer-by, so it refuses to unlock anything and a real customer
 * sees "we can't confirm a payment yet".
 *
 * The `?all=1` is a belt-and-braces signal. The site also records which button
 * was clicked before the buyer left, so the right thing unlocks even if the
 * redirect is misconfigured — but setting both makes it correct either way.
 */
export const AFTER_PAYMENT_PATH = "/unlocked?session_id={CHECKOUT_SESSION_ID}";
export const AFTER_PAYMENT_PATH_BUNDLE = "/unlocked?all=1&session_id={CHECKOUT_SESSION_ID}";
