import { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle, Check, Download, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { downloadManual, generateManual, type GenerateResult } from "@/lib/manual";

type Status = "idle" | "working" | "done" | "error";

interface ManualDownloadProps {
  scores: string;
  relationship: string;
  subjectName?: string | undefined;
  /** Generate as soon as the component mounts (the post-payment case). */
  auto?: boolean | undefined;
}

/**
 * Generates the 24-page manual in the buyer's browser and hands it to them.
 *
 * Everything happens client-side: no server, no email, no waiting. The
 * generator module is imported lazily inside the click handler so jsPDF and
 * the copy bank never land in the initial page bundle — visitors who never
 * buy do not pay for the download.
 */
export function ManualDownload({ scores, relationship, subjectName, auto }: ManualDownloadProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const resultRef = useRef<GenerateResult | null>(null);
  const startedRef = useRef(false);

  const run = useCallback(async () => {
    setStatus("working");
    setError(null);
    try {
      // Re-use the already-generated file if they click twice; regenerating
      // is wasted work and produces a byte-identical PDF anyway.
      const result =
        resultRef.current ??
        (await generateManual({
          scores,
          relationship,
          subjectName,
          // A buyer who has already paid must never see a hard failure over a
          // malformed score string. They get a manual; the warning is surfaced
          // in the console for you rather than to them.
          allowUnscored: true,
        }));
      resultRef.current = result;

      if (result.violations.length && import.meta.env?.DEV) {
        console.warn("[manual] QA notes:", result.violations);
      }
      if (result.profile.degraded) {
        console.warn("[manual] generated from unusable scores — investigate this sale.");
      }

      downloadManual(result);
      setStatus("done");
    } catch (err) {
      console.error("[manual] generation failed", err);
      setError(
        "Something went wrong building your manual. Your purchase is safe — " +
          "email us and we'll send it straight over.",
      );
      setStatus("error");
    }
  }, [scores, relationship, subjectName]);

  useEffect(() => {
    if (auto && !startedRef.current) {
      startedRef.current = true;
      void run();
    }
  }, [auto, run]);

  if (status === "error") {
    return (
      <div className="rounded-2xl border border-destructive/40 bg-destructive/5 p-5 text-left">
        <p className="flex items-center gap-2 text-sm font-medium text-destructive">
          <AlertCircle className="size-4 shrink-0" /> Couldn't build your manual
        </p>
        <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        <Button variant="outlineGold" className="mt-4" onClick={() => void run()}>
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div className="text-center">
      <Button variant="gold" size="xl" onClick={() => void run()} disabled={status === "working"}>
        {status === "working" ? (
          <>
            <Loader2 className="size-4 animate-spin" /> Building your manual…
          </>
        ) : status === "done" ? (
          <>
            <Check className="size-4" /> Download again
          </>
        ) : (
          <>
            <Download className="size-4" /> Download your 24-page manual
          </>
        )}
      </Button>

      {status === "done" && (
        <p className="mt-3 text-xs text-muted-foreground">
          Saved to your downloads. Page 23 is the one to screenshot.
        </p>
      )}
      {status === "working" && (
        <p className="mt-3 text-xs text-muted-foreground">
          Writing 24 pages about {subjectName || "them"} — a few seconds.
        </p>
      )}
    </div>
  );
}
