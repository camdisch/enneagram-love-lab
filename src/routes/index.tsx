import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Sparkles, Lock, Clock } from "lucide-react";

import heroCircle from "@/assets/hero-circle.jpg";
import { AdSlot } from "@/components/AdSlot";
import { Button } from "@/components/ui/button";
import { ARCHETYPES, RELATIONSHIPS, type TypeId } from "@/lib/enneagram";
import { PRODUCT } from "@/lib/product";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Who Are They Really? · Relationship Enneagram Tests" },
      {
        name: "description",
        content:
          "Take the 12-question relationship Enneagram test for your mom, dad, boyfriend, girlfriend or best friend and find out which of the 9 archetypes they really are.",
      },
      { property: "og:title", content: "Who Are They Really? · Relationship Enneagram Tests" },
      {
        property: "og:description",
        content:
          "12 questions. 9 archetypes. Decode the person you love most — then send it to them.",
      },
    ],
  }),
  component: Landing,
});

function Landing() {
  return (
    <main className="min-h-screen">
      <div className="px-4 pt-6">
        <AdSlot slot="top" />
      </div>

      <section className="relative mx-auto grid max-w-6xl items-center gap-12 px-6 py-16 md:grid-cols-[1.1fr_0.9fr] md:py-24">
        <div className="animate-rise">
          <span className="inline-flex items-center gap-2 rounded-full border border-primary/40 bg-primary/10 px-4 py-1.5 text-xs uppercase tracking-[0.28em] text-primary">
            <Sparkles className="size-3.5" /> 9 archetypes
          </span>
          <h1 className="mt-6 text-5xl leading-[1.03] md:text-7xl">
            Who are they <em className="text-gradient-gold not-italic">really</em>?
          </h1>
          <p className="mt-6 max-w-lg text-lg text-muted-foreground">
            The relationship Enneagram test that reads the people you can't stop thinking about.
            Pick a person, answer 12 uncomfortably accurate questions, and get their archetype —
            plus the exact reason they love you the way they do.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Button asChild variant="gold" size="xl">
              <a href="#tests">
                Start a test <ArrowRight />
              </a>
            </Button>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="size-4 text-primary" /> 3 minutes · no signup
            </div>
          </div>

          <dl className="mt-12 grid max-w-md grid-cols-3 gap-6 border-t border-border pt-8">
            {[
              ["412k", "tests taken"],
              ["1 in 4", "get Type 2"],
              ["87%", "send it on"],
            ].map(([k, v]) => (
              <div key={v}>
                <dt className="font-display text-2xl text-primary">{k}</dt>
                <dd className="text-xs uppercase tracking-widest text-muted-foreground">{v}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="relative animate-float-slow">
          <div
            className="absolute inset-6 rounded-full blur-3xl"
            style={{ background: "var(--gradient-gold)", opacity: 0.18 }}
          />
          <img
            src={heroCircle}
            alt="Nine glowing figures arranged in an Enneagram circle"
            width={1280}
            height={1280}
            className="relative rounded-[2rem] border border-border shadow-[var(--shadow-lift)]"
          />
        </div>
      </section>

      <section id="tests" className="mx-auto max-w-6xl scroll-mt-8 px-6 py-12">
        <h2 className="text-3xl md:text-4xl">Choose your person</h2>
        <p className="mt-3 max-w-xl text-muted-foreground">
          Same 12 questions, rewritten for each relationship. Most people run all five.
        </p>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {RELATIONSHIPS.map((r) => (
            <Link
              key={r.slug}
              to="/quiz/$relationship"
              params={{ relationship: r.slug }}
              className="group relative overflow-hidden rounded-3xl border border-border bg-card/60 p-7 transition-all hover:-translate-y-1 hover:border-primary/60 hover:shadow-[var(--shadow-glow)]"
            >
              <span className="text-3xl">{r.emoji}</span>
              <h3 className="mt-5 text-2xl">The {r.label} Test</h3>
              <p className="mt-2 text-sm text-muted-foreground">{r.hook}</p>
              <span className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-primary">
                Take it{" "}
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="text-3xl md:text-4xl">The nine archetypes</h2>
        <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(Object.keys(ARCHETYPES) as unknown as string[]).map((k) => {
            const a = ARCHETYPES[Number(k) as TypeId];
            return (
              <div
                key={a.id}
                className="rounded-2xl border border-border/70 bg-card/40 p-6 transition-colors hover:bg-card/70"
              >
                <p className="font-display text-sm tracking-[0.3em] text-primary">{a.glyph}</p>
                <h3 className="mt-3 text-xl">{a.name}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{a.blurb}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-6 pb-16">
        <div className="rounded-3xl border border-primary/30 bg-card/60 p-10 text-center">
          <Lock className="mx-auto size-6 text-primary" />
          {/* Name, price and checkout link all come from src/lib/product.ts,
              so this page and the results page can never advertise different
              things again. */}
          <h2 className="mt-5 text-3xl">{PRODUCT.name}</h2>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">{PRODUCT.description}</p>

          <div className="mt-8 flex flex-col items-center justify-center gap-4">
            {PRODUCT.isConfigured ? (
              <Button asChild variant="gold" size="lg">
                <a href={PRODUCT.stripeUrl} target="_blank" rel="noopener noreferrer">
                  {PRODUCT.ctaLabel} ({PRODUCT.price}) <ArrowRight className="size-4 ml-2" />
                </a>
              </Button>
            ) : (
              <Button variant="gold" size="lg" disabled>
                Checkout link not set
              </Button>
            )}
          </div>
        </div>
      </section>

      <div className="px-4 pb-10">
        <AdSlot slot="bottom" />
      </div>

      <footer className="border-t border-border/60 px-6 py-10 text-center text-xs text-muted-foreground">
        For entertainment and self-reflection — not a clinical assessment.
      </footer>
    </main>
  );
}
