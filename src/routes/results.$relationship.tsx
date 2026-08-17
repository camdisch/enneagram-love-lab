import { createFileRoute, notFound, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Check, Lock, RefreshCw, Share2, FileText } from "lucide-react";
import { toast } from "sonner";

import { AdSlot } from "@/components/AdSlot";
import { Button } from "@/components/ui/button";
import {
  ARCHETYPES,
  QUESTIONS,
  getRelationship,
  loadResult,
  rankScores,
  type Scores,
} from "@/lib/enneagram";

export const Route = createFileRoute("/results/$relationship")({
  loader: ({ params }) => {
    const relationship = getRelationship(params.relationship);
    if (!relationship) throw notFound();
    return { relationship };
  },
  head: ({ loaderData }) => {
    if (!loaderData) {
      return { meta: [{ title: "Result unavailable" }, { name: "robots", content: "noindex" }] };
    }
    const title = `Your ${loaderData.relationship.label} result · Relationship Enneagram`;
    const description = `The archetype behind ${loaderData.relationship.subject} — their gift, their friction, and what unlocks in the Premium Relationship Blueprint.`;
    return {
      meta: [
        { title },
        { name: "description", content: description },
        { property: "og:title", content: title },
        { property: "og:description", content: description },
      ],
    };
  },
  component: Results,
});

function Results() {
  const { relationship } = Route.useLoaderData();
  const [scores, setScores] = useState<Scores | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setScores(loadResult(relationship.slug));
    setReady(true);
  }, [relationship.slug]);

  if (ready && !scores) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
        <h1 className="text-3xl">This result has expired</h1>
        <p className="mt-3 max-w-sm text-muted-foreground">
          Results live in this browser session only. Retake the {relationship.label} test to see it
          again.
        </p>
        <Button asChild variant="gold" size="lg" className="mt-8">
          <Link to="/quiz/$relationship" params={{ relationship: relationship.slug }}>
            Retake the test
          </Link>
        </Button>
      </main>
    );
  }

  const ranked = scores ? rankScores(scores) : [];
  const primary = ranked[0] ? ARCHETYPES[ranked[0].type] : null;
  const wings = ranked.slice(1, 3).map((r) => ARCHETYPES[r.type]);
  const total = QUESTIONS.length;

  function share() {
    const url = typeof window !== "undefined" ? window.location.origin : "";
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(`I found out ${relationship.subject}'s Enneagram archetype: ${primary?.name}. Try it: ${url}`);
      toast.success("Copied — go ruin someone's evening");
    }
  }

  return (
    <main className="min-h-screen px-6 py-10">
      <div className="mx-auto max-w-3xl">
        <AdSlot slot="top" />

        {primary && (
          <>
            <section className="animate-rise mt-12 text-center">
              <p className="text-xs uppercase tracking-[0.35em] text-muted-foreground">
                {relationship.label} result
              </p>
              <p className="mt-8 font-display text-5xl text-primary">{primary.glyph}</p>
              <h1 className="mt-4 text-4xl md:text-5xl">
                <span className="text-gradient-gold">{primary.name}</span>
              </h1>
              <p className="mt-2 text-sm uppercase tracking-[0.2em] text-muted-foreground">
                {primary.title}
              </p>
              <p className="mx-auto mt-8 max-w-xl text-lg text-muted-foreground">{primary.blurb}</p>
            </section>

            <section className="mt-10 grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-border bg-card/60 p-6">
                <h2 className="text-lg">Their gift</h2>
                <p className="mt-2 text-sm text-muted-foreground">{primary.gift}</p>
              </div>
              <div className="rounded-2xl border border-border bg-card/60 p-6">
                <h2 className="text-lg">Where it costs you</h2>
                <p className="mt-2 text-sm text-muted-foreground">{primary.friction}</p>
              </div>
            </section>

            <section className="mt-10">
              <h2 className="text-xl">Your free breakdown</h2>
              <div className="mt-4 space-y-3">
                {ranked.slice(0, 3).map((r, i) => {
                  const a = ARCHETYPES[r.type];
                  return (
                    <div key={r.type} className="flex items-center gap-4">
                      <span className="w-40 shrink-0 truncate text-sm text-foreground/80">
                        {i === 0 ? a.name : "•••••••••••"}
                      </span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-secondary">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${(r.score / total) * 100}%`,
                            backgroundImage: "var(--gradient-gold)",
                            opacity: i === 0 ? 1 : 0.45,
                          }}
                        />
                      </div>
                      <span className="w-10 text-right text-xs text-muted-foreground">
                        {Math.round((r.score / total) * 100)}%
                      </span>
                    </div>
                  );
                })}
              </div>
              <div className="relative mt-6 overflow-hidden rounded-2xl border border-border/70 bg-card/40 p-6">
                <div className="select-none blur-sm" aria-hidden>
                  <p className="text-sm text-muted-foreground">
                    {wings.map((w) => w.name).join(" · ")} — their secondary pull shapes how they
                    apologise, how they withdraw, and what they need on the worst day of the year.
                  </p>
                </div>
                <div className="mt-4 flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-primary">
                  <Lock className="size-3.5" /> Locked in the Blueprint
                </div>
              </div>
            </section>

            <section className="mt-12 rounded-3xl border border-primary/40 bg-card/70 p-8 shadow-[var(--shadow-glow)] md:p-10">
              <p className="text-xs uppercase tracking-[0.3em] text-primary">Unlock everything</p>
              <h2 className="mt-4 text-3xl">The Premium Relationship Blueprint</h2>
              <p className="mt-3 text-muted-foreground">
                A 24-page personalised PDF built from this exact result — written for you and{" "}
                {relationship.subject}, delivered instantly.
              </p>
              <ul className="mt-6 space-y-3 text-sm">
                {[
                  `Full 9-type profile with ${primary.name} wings and stress lines`,
                  `The three sentences that calm ${relationship.possessive} down fastest`,
                  "Their conflict pattern, decoded turn by turn",
                  "Birthday, apology and boundary scripts you can copy",
                  "A one-page cheat sheet for your phone",
                ].map((f) => (
                  <li key={f} className="flex gap-3">
                    <Check className="mt-0.5 size-4 shrink-0 text-primary" />
                    <span className="text-muted-foreground">{f}</span>
                  </li>
                ))}
              </ul>

              <div className="mt-8 flex flex-wrap items-end justify-between gap-4 border-t border-border pt-6">
                <div>
                  <p className="font-display text-4xl">
                    $2.99{" "}
                    <span className="align-middle text-base text-muted-foreground line-through">
                      $7.99
                    </span>
                  </p>
                  <p className="text-xs text-muted-foreground">One-time · instant PDF download</p>
                </div>
                <Button
                  variant="gold"
                  size="xl"
                  onClick={() =>
                    toast("Stripe Checkout placeholder", {
                      description: "Connect payments to enable real checkout for the Blueprint.",
                    })
                  }
                >
                  <FileText /> Unlock the Blueprint
                </Button>
              </div>
            </section>

            <section className="mt-10 flex flex-wrap justify-center gap-3">
              <Button variant="outlineGold" size="lg" onClick={share}>
                <Share2 /> Share your result
              </Button>
              <Button asChild variant="ghost" size="lg">
                <Link to="/">
                  <RefreshCw /> Test someone else
                </Link>
              </Button>
            </section>
          </>
        )}

        <div className="mt-12">
          <AdSlot slot="bottom" />
        </div>
      </div>
    </main>
  );
}
