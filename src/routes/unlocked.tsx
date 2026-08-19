import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ArrowRight, Check, RefreshCw } from "lucide-react";
import { z } from "zod";

import { ManualDownload } from "@/components/ManualDownload";
import { Button } from "@/components/ui/button";
import { RELATIONSHIPS } from "@/lib/enneagram";
import { grantAccess } from "@/lib/entitlement";
import { loadPendingPurchase, type PendingPurchase } from "@/lib/pendingPurchase";

/**
 * Where Stripe sends buyers after payment.
 *
 * Point the Payment Link's "After payment" setting at
 * https://YOUR-DOMAIN/unlocked and the manual generates and downloads the
 * moment they land, with no server involved.
 *
 * The quiz result travels via localStorage (written just before they left for
 * Stripe) rather than the URL, because a Payment Link redirect is a fixed URL
 * and cannot carry their scores. As a fallback the route also accepts `s`,
 * `r` and `n` query params, so a direct re-download link can be handed to
 * anyone who gets stuck.
 */
const searchSchema = z.object({
  s: z.string().optional(),
  r: z.string().optional(),
  n: z.string().optional(),
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
  const { s, r, n } = Route.useSearch();
  const [pending, setPending] = useState<PendingPurchase | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Landing here means Stripe accepted the payment, so the collection is
    // unlocked for every relationship from now on — not just this one.
    grantAccess();

    // Query params win when present, so a re-download link works even from a
    // different browser than the one that took the quiz.
    if (s && r) {
      setPending({ scores: s, relationship: r, subjectName: n, savedAt: Date.now() });
    } else {
      setPending(loadPendingPurchase());
    }
    setReady(true);
  }, [s, r, n]);

  if (!ready) return null;

  const current = pending?.relationship;
  const remaining = RELATIONSHIPS.filter((rel) => rel.slug !== current);

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
              Your payment went through and all five manuals are yours. We just can't tell which
              result to build — results live in the browser that took the quiz, so if you paid on a
              different device, take a test below and the manual will appear at the end of it.
            </p>
          </>
        )}

        {/* The collection is the product, so the four they have not tested yet
            are the most valuable thing on this page — they are already paid for. */}
        <div className="mt-14 border-t border-border pt-8 text-left">
          <p className="flex items-center justify-center gap-2 text-center text-sm text-primary">
            <Check className="size-4" /> All five manuals are unlocked on this device
          </p>
          <p className="mt-3 text-center text-sm text-muted-foreground">
            Take any of these and its manual is yours at the end — no second payment.
          </p>

          <div className="mt-6 grid gap-2 sm:grid-cols-2">
            {remaining.map((rel) => (
              <Button key={rel.slug} asChild variant="outlineGold" className="justify-start">
                <Link to="/quiz/$relationship" params={{ relationship: rel.slug }}>
                  <span className="mr-2">{rel.emoji}</span> The {rel.label} Test
                  <ArrowRight className="size-4 ml-auto" />
                </Link>
              </Button>
            ))}
          </div>
        </div>

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
