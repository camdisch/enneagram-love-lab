import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ArrowRight, Check, RefreshCw } from "lucide-react";
import { z } from "zod";

import { ManualDownload } from "@/components/ManualDownload";
import { Button } from "@/components/ui/button";
import { RELATIONSHIPS } from "@/lib/enneagram";
import { grantAll, grantSingle } from "@/lib/entitlement";
import { loadPendingPurchase, type PendingPurchase } from "@/lib/pendingPurchase";
import { BUNDLE } from "@/lib/product";

/**
 * Where Stripe sends buyers after payment.
 *
 * Set BOTH Payment Links' "After payment" redirect:
 *   single link → https://YOUR-DOMAIN/unlocked
 *   bundle link → https://YOUR-DOMAIN/unlocked?all=1
 *
 * The quiz result travels via localStorage (written just before they left for
 * Stripe) rather than the URL, because a Payment Link redirect is a fixed URL
 * and cannot carry their scores. That stored record also says which button
 * they clicked, so the right tier unlocks even if `?all=1` is missing — the
 * query param is a second, independent signal rather than the only one.
 */
/**
 * TanStack Router infers types from the raw query string, so `?all=1` arrives
 * as the NUMBER 1, not the string "1". A plain z.string() rejects it and the
 * whole page throws before the buyer sees their download. Accept either and
 * normalise, so a hand-typed or Stripe-generated URL can never break delivery.
 */
const flexibleParam = z
  .union([z.string(), z.number()])
  .optional()
  .transform((value) => (value === undefined ? undefined : String(value)));

const searchSchema = z.object({
  s: flexibleParam,
  r: flexibleParam,
  n: flexibleParam,
  all: flexibleParam,
});

export const Route = createFileRoute("/unlocked")({
  validateSearch: searchSchema,
  head: () => ({
    meta: [
      { title: "Your manual is ready" },
      // A post-purchase page should never appear in search results.
      { name: "robots", content: "noindex, nofollow" },
    ],
  }),
  component: Unlocked,
});

function Unlocked() {
  const { s, r, n, all } = Route.useSearch();
  const [pending, setPending] = useState<PendingPurchase | null>(null);
  const [boughtEverything, setBoughtEverything] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Query params win when present, so a re-download link works even from a
    // different browser than the one that took the quiz.
    const record: PendingPurchase | null =
      s && r
        ? { scores: s, relationship: r, subjectName: n, tier: "single", savedAt: Date.now() }
        : loadPendingPurchase();

    // Landing here means Stripe accepted the payment. Unlock either the one
    // manual they bought or all five — whichever they actually paid for.
    const isBundle = (all !== undefined && all !== "" && all !== "0") || record?.tier === "bundle";
    if (isBundle) {
      grantAll();
    } else if (record) {
      grantSingle(record.relationship);
    }

    setBoughtEverything(isBundle);
    setPending(record);
    setReady(true);
  }, [s, r, n, all]);

  if (!ready) return null;

  const current = pending?.relationship;
  const others = RELATIONSHIPS.filter((rel) => rel.slug !== current);

  return (
    <main className="min-h-screen px-6 py-16">
      <div className="mx-auto w-full max-w-lg text-center">
        <p className="text-xs uppercase tracking-[0.35em] text-muted-foreground">
          Payment complete
        </p>

        {pending ? (
          <>
            <h1 className="mt-6 text-4xl md:text-5xl">
              <span className="text-gradient-gold">Your manual is ready</span>
            </h1>
            <p className="mx-auto mt-5 max-w-md text-muted-foreground">
              Twenty-four pages, built from the answers you gave. It should start downloading on its
              own — if your browser blocked it, the button below will do it.
            </p>

            <div className="mt-10">
              <ManualDownload
                auto
                scores={pending.scores}
                relationship={pending.relationship}
                subjectName={pending.subjectName}
              />
            </div>
          </>
        ) : (
          <>
            <h1 className="mt-6 text-4xl md:text-5xl">
              <span className="text-gradient-gold">You're unlocked</span>
            </h1>
            <p className="mx-auto mt-5 max-w-md text-muted-foreground">
              Your payment went through. We just can't tell which result to build — results live in
              the browser that took the quiz, so if you paid on a different device, take the test
              below and the manual will appear at the end of it.
            </p>
          </>
        )}

        {boughtEverything ? (
          /* Collection buyer: the four they have not tested yet are the whole
             point of what they just bought, so put them front and centre. */
          <div className="mt-14 border-t border-border pt-8">
            <p className="flex items-center justify-center gap-2 text-sm text-primary">
              <Check className="size-4" /> All five manuals are unlocked on this device
            </p>
            <p className="mt-3 text-sm text-muted-foreground">
              Take any of these and its manual is yours at the end — no second payment.
            </p>

            <div className="mt-6 grid gap-2 text-left sm:grid-cols-2">
              {others.map((rel) => (
                <Button key={rel.slug} asChild variant="outlineGold" className="justify-start">
                  <Link to="/quiz/$relationship" params={{ relationship: rel.slug }}>
                    <span className="mr-2">{rel.emoji}</span> The {rel.label} Test
                    <ArrowRight className="size-4 ml-auto" />
                  </Link>
                </Button>
              ))}
            </div>
          </div>
        ) : (
          /* Single buyer: they have just proved they will pay, and they are
             holding the thing they paid for. This is the best moment on the
             whole site to offer the other four. */
          BUNDLE.isConfigured && (
            <div className="mt-14 rounded-2xl border border-primary/30 bg-card/50 p-6">
              <p className="text-sm text-foreground/90">
                There are four other people you can decode.
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                {BUNDLE.description} One payment, and every test you take from now on ends with its
                own manual.
              </p>
              <Button asChild variant="gold" size="lg" className="mt-5">
                <a href={BUNDLE.stripeUrl} target="_blank" rel="noopener noreferrer">
                  {BUNDLE.ctaLabel} — {BUNDLE.price} <ArrowRight className="size-4 ml-1" />
                </a>
              </Button>
            </div>
          )
        )}

        <div className="mt-10">
          <Button asChild variant="ghost" size="lg">
            <Link to="/">
              <RefreshCw className="size-4" /> Back to the start
            </Link>
          </Button>
        </div>

        <p className="mt-8 text-xs text-muted-foreground">
          Stuck? Reply to your Stripe receipt and we'll send the PDF over directly.
        </p>
      </div>
    </main>
  );
}
