import { createFileRoute, notFound, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  QUESTIONS,
  emptyScores,
  getRelationship,
  saveResult,
  type Scores,
  type TypeId,
} from "@/lib/enneagram";

export const Route = createFileRoute("/quiz/$relationship")({
  loader: ({ params }) => {
    const relationship = getRelationship(params.relationship);
    if (!relationship) throw notFound();
    return { relationship };
  },
  head: ({ loaderData }) => {
    if (!loaderData) {
      return {
        meta: [{ title: "Test unavailable" }, { name: "robots", content: "noindex" }],
      };
    }
    const label = loaderData.relationship.label;
    const title = `The ${label} Enneagram Test · 12 questions`;
    const description = `Answer 12 questions about ${loaderData.relationship.subject} and find out which of the 9 Enneagram archetypes they are.`;
    return {
      meta: [
        { title },
        { name: "description", content: description },
        { property: "og:title", content: title },
        { property: "og:description", content: description },
      ],
    };
  },
  component: Quiz,
});

function Quiz() {
  const { relationship } = Route.useLoaderData();
  const navigate = useNavigate();
  const [index, setIndex] = useState(0);
  const [scores, setScores] = useState<Scores>(() => emptyScores());
  const [history, setHistory] = useState<TypeId[]>([]);

  const question = QUESTIONS[index]!;
  const progress = (index / QUESTIONS.length) * 100;

  function choose(type: TypeId) {
    const next: Scores = { ...scores, [type]: scores[type] + 1 };
    setScores(next);
    setHistory((h) => [...h, type]);

    if (index + 1 >= QUESTIONS.length) {
      saveResult(relationship.slug, next);
      navigate({ to: "/analyzing/$relationship", params: { relationship: relationship.slug } });
    } else {
      setIndex(index + 1);
    }
  }

  function back() {
    if (index === 0) {
      navigate({ to: "/" });
      return;
    }
    const last = history[history.length - 1]!;
    setScores((s) => ({ ...s, [last]: Math.max(0, s[last] - 1) }));
    setHistory((h) => h.slice(0, -1));
    setIndex(index - 1);
  }

  return (
    <main className="min-h-screen px-6 py-10">
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="sm" onClick={back}>
            <ArrowLeft /> Back
          </Button>
          <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            {relationship.label} test
          </p>
        </div>

        <div className="mt-6 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${Math.max(progress, 4)}%`, backgroundImage: "var(--gradient-gold)" }}
          />
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          Question {index + 1} of {QUESTIONS.length}
        </p>

        <div key={index} className="animate-rise mt-10">
          <h1 className="text-3xl leading-snug md:text-4xl">{question.prompt(relationship)}</h1>
          <div className="mt-8 space-y-3">
            {question.options.map((o) => (
              <Button key={o.text} variant="quiz" onClick={() => choose(o.type)}>
                {o.text}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
