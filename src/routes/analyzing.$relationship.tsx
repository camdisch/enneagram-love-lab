import { createFileRoute, notFound, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { getRelationship } from "@/lib/enneagram";

export const Route = createFileRoute("/analyzing/$relationship")({
  loader: ({ params }) => {
    const relationship = getRelationship(params.relationship);
    if (!relationship) throw notFound();
    return { relationship };
  },
  head: ({ loaderData }) => {
    if (!loaderData) {
      return { meta: [{ title: "Unavailable" }, { name: "robots", content: "noindex" }] };
    }
    const title = `Reading ${loaderData.relationship.subject}…`;
    return {
      meta: [
        { title },
        {
          name: "description",
          content: `Scoring your answers across the nine Enneagram archetypes for ${loaderData.relationship.subject}.`,
        },
        { property: "og:title", content: title },
        {
          property: "og:description",
          content: "Your relationship archetype result is being calculated.",
        },
        { name: "robots", content: "noindex" },
      ],
    };
  },
  component: Analyzing,
});

const STEPS = [
  "Sorting 12 answers into 9 archetypes",
  "Weighing loyalty against intensity",
  "Cross-checking their stress pattern",
  "Sealing your blueprint",
];

function Analyzing() {
  const { relationship } = Route.useLoaderData();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);

  useEffect(() => {
    const stepTimer = window.setInterval(() => {
      setStep((s) => Math.min(s + 1, STEPS.length - 1));
    }, 950);
    const done = window.setTimeout(() => {
      navigate({ to: "/results/$relationship", params: { relationship: relationship.slug } });
    }, 4200);
    return () => {
      window.clearInterval(stepTimer);
      window.clearTimeout(done);
    };
  }, [navigate, relationship.slug]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <div className="relative size-40">
        <div
          className="absolute inset-0 rounded-full blur-2xl"
          style={{ background: "var(--gradient-gold)", opacity: 0.25 }}
        />
        <div className="animate-orbit absolute inset-0">
          {Array.from({ length: 9 }).map((_, i) => (
            <span
              key={i}
              className="absolute left-1/2 top-1/2 size-2 rounded-full bg-primary"
              style={{
                transform: `rotate(${i * 40}deg) translateY(-72px)`,
                opacity: 0.35 + (i % 3) * 0.25,
              }}
            />
          ))}
        </div>
        <div className="absolute inset-8 flex items-center justify-center rounded-full border border-primary/40 bg-card/60">
          <span className="font-display text-2xl text-primary">{relationship.emoji}</span>
        </div>
      </div>

      <h1 className="mt-12 text-3xl md:text-4xl">Reading {relationship.subject}</h1>
      <p key={step} className="animate-rise mt-4 h-6 text-sm text-muted-foreground">
        {STEPS[step]}…
      </p>

      <div className="mt-8 h-1 w-64 overflow-hidden rounded-full bg-secondary">
        <div
          className="animate-shimmer h-full w-full"
          style={{
            backgroundImage:
              "linear-gradient(90deg, transparent, var(--primary), transparent)",
          }}
        />
      </div>
    </main>
  );
}
