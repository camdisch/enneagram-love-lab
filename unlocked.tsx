import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AlertCircle, ArrowRight, Check, RefreshCw } from "lucide-react";
import { z } from "zod";

import { ManualDownload } from "@/components/ManualDownload";
import { Button } from "@/components/ui/button";
import { RELATIONSHIPS } from "@/lib/enneagram";
import { grantAll, grantSingle } from "@/lib/entitlement";
import { loadPendingPurchase, type PendingPurchase } from "@/lib/pendingPurchase";
import { BUNDLE, SINGLE } from "@/lib/product";

/**
 * Where Stripe sends buyers after a completed payment.
 *
 * ⚠️ BOTH Payment Links must carry the Checkout Session id, or real buyers
 * will pay and land on the "we can't confirm this" screen:
 *
 *   single link → https://YOUR-DOMAIN/unlocked?session_id={CHECKOUT_SESSION_ID}
 *   bundle link → https://YOUR-DOMAIN/unlocked?all=1&session_id={CHECKOUT_SESSION_ID}
 *
 * Stripe substitutes {CHECKOUT_SESSION_ID} literally at redirect time.
 *
 * That token is the whole reason this page is not a free-download URL. An
 * earlier version unlocked the product for anyone who simply loaded /unlocked,
 * which meant sharing the link gave the product away. Nothing is granted now
 * without a session id that looks like Stripe issued it AND a record showing
 * this browser actually started a checkout.
 *
 * This is evidence, not proof — verifying a session really means asking
 * Stripe, which needs a server. It closes the hole that gave the product to
 * passers-by; it does not stop someone who reads the JavaScript.
 */
const searchSchema = z.object({
  s: z.union([z.string(), z.number()]).optional(),
  r: z.union([z.string(), z.number()]).optional(),
  n: z.union([z.string(), z.number()]).optional(),
  all: z.union([z.string(), z.number()]).optional(),
  session_id: z.union([z.string(), z.number()]).optional(),
});

/** Stripe Checkout Session ids look like cs_live_… or cs_test_…. */
const SESSION_ID = /^cs_(live|test)_[A-Za-z0-9]{8,}$/;

const str = (v: string | number | undefined): string | undefined =>
  v === undefined ? undefined : String(v);

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

type Status = "checking" | "granted" | "unverified";

function Unlocked() {
  const search = Route.useSearch();
  const [pending, setPending] = useState<PendingPurchase | null>(null);
  const [boughtEverything, setBoughtEverything] = useState(false);
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    const session = str(search.session_id);
    const all = str(search.all);
    const s = str(search.s);
    const r = str(search.r);
    const n = str(search.n);

    const record: PendingPurchase | null =
      s && r
        ? { scores: s, relationship: r, subjectName: n, tier: "single", savedAt: Date.now() }
        : loadPendingPurchase();

    // Two independent things must be true before anything unlocks: Stripe
    // handed back a session id, and this browser actually began a checkout.
    // Either one alone is something a passer-by could produce.
    const looksPaid = session !== undefined && SESSION_ID.test(session);
    if (!looksPaid || !record) {
      setPending(record);
      setStatus("unverified");
      return;
    }

    const isBundle = (all !== undefined && all !== "" && all !== "0") || record.tier === "bundle";
    if (isBundle) {
      grantAll(session);
    } else {
      grantSingle(record.relationship, session);
    }

    setBoughtEverything(isBundle);
    setPending(record);
    setStatus("granted");
  }, [search]);

  if (status === "checking") return null;

  // ── Could not confirm a payment ─────────────────────────────────────────
  if (status === "unverified") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center px-6 py-16 text-center">
        <div className="mx-auto w-full max-w-md">
          <AlertCircle className="mx-auto size-7 text-primary" />
          <h1 className="mt-6 text-3xl">We can't confirm a payment yet</h1>
          <p className="mt-4 text-muted-foreground">
            This page only opens after a completed checkout. If you have just paid and landed here,
            your money is safe — reply to your Stripe receipt and we'll send the PDF straight over.
          </p>

          <div className="mt-8 flex flex-col items-center gap-3">
            {SINGLE.isConfigured && (
              <Button asChild variant="gold" size="lg">
                <a href={SINGLE.stripeUrl} target="_blank" rel="noopener noreferrer">
                  {SINGLE.ctaLabel} ({SINGLE.price}) <ArrowRight className="size-4 ml-1" />
                </a>
              </Button>
            )}
            <Button asChild variant="ghost">
              <Link to="/">
                <RefreshCw className="size-4" /> Back to the tests
              </Link>
            </Button>
          </div>
        </div>
      </main>
    );
  }

  // ── Payment confirmed ───────────────────────────────────────────────────
  const current = pending?.relationship;
  const others = RELATIONSHIPS.filter((rel) => rel.slug !== current);

  return (
    <main className="min-h-screen px-6 py-16">
      <div className="mx-auto w-full max-w-lg text-center">
        <p className="text-xs uppercase tracking-[0.35em] text-muted-foreground">
          Payment complete
        </p>

        <h1 className="mt-6 text-4xl md:text-5xl">
          <span className="text-gradient-gold">Your manual is ready</span>
        </h1>
        <p className="mx-auto mt-5 max-w-md text-muted-foreground">
          Twenty-four pages, built from the answers you gave. It should start downloading on its own
          — if your browser blocked it, the button below will do it.
        </p>

        {pending && (
          <div className="mt-10">
            <ManualDownload
              auto
              scores={pending.scores}
              relationship={pending.relationship}
              subjectName={pending.subjectName}
            />
          </div>
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
             holding the thing they paid for. Best moment to sell the rest. */
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
