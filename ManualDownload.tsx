import { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle, Check, Download, ExternalLink, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { blobDownloadIsReliable, inAppBrowserName, isIOS } from "@/lib/browserEnv";
import { downloadManual, generateManual, type GenerateResult } from "@/lib/manual";

type Status = "idle" | "working" | "ready" | "saved" | "error";

interface ManualDownloadProps {
  scores: string;
  relationship: string;
  subjectName?: string | undefined;
  /**
   * Build the PDF as soon as the component mounts, so the file is ready in
   * memory before the buyer reaches for it.
   *
   * This does NOT save the file. Saving has to happen inside a real tap: iOS
   * silently ignores a programmatic click on a blob: URL fired during page
   * load, so the previous auto-save looked fine in desktop testing and
   * delivered nothing at all on an iPhone.
   */
  auto?: boolean | undefined;
}

/**
 * Builds the 24-page manual in the buyer's browser and gets it onto their device.
 *
 * Everything is client-side: no server, no email, no waiting. The generator is
 * imported lazily so jsPDF and the copy bank never land in the initial bundle.
 *
 * ── Why this is more than one button ───────────────────────────────────────
 * Most buyers arrive from a social app, inside that app's embedded browser.
 * On iOS those are WKWebView, which ignores `<a download>` pointing at a blob:
 * URL — the tap does nothing whatsoever. One download button is therefore a
 * silent failure for a large share of paying customers, so there are three
 * paths to the same file:
 *
 *   1. Anchor download — the normal one, correct on desktop and Android.
 *   2. Open the PDF in a tab — iOS renders it in its own viewer, whose share
 *      sheet has "Save to Files". This works inside WebViews.
 *   3. An inline <iframe> as the last resort, so the buyer can at least read
 *      and screenshot what they paid for without leaving the page.
 *
 * The buyer is shown whichever is most likely to work first and can always
 * reach the others. Nobody who has paid should end up with nothing.
 */
export function ManualDownload({ scores, relationship, subjectName, auto }: ManualDownloadProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [showInline, setShowInline] = useState(false);
  const resultRef = useRef<GenerateResult | null>(null);
  const startedRef = useRef(false);

  const appName = inAppBrowserName();
  const preferOpenInTab = !blobDownloadIsReliable();

  /** Build the PDF (idempotent — a second call reuses the first result). */
  const build = useCallback(async (): Promise<GenerateResult> => {
    if (resultRef.current) return resultRef.current;
    const result = await generateManual({
      scores,
      relationship,
      subjectName,
      // Someone who has already paid must never hit a hard failure over a
      // malformed score string. They get a manual; the warning goes to the
      // console for you rather than to them.
      allowUnscored: true,
    });
    resultRef.current = result;
    if (result.violations.length && import.meta.env?.DEV) {
      console.warn("[manual] QA notes:", result.violations);
    }
    if (result.profile.degraded) {
      console.warn("[manual] generated from unusable scores — investigate this sale.");
    }
    return result;
  }, [scores, relationship, subjectName]);

  /** Pre-build on mount so the tap that follows is instant. Never saves. */
  useEffect(() => {
    if (!auto || startedRef.current) return;
    startedRef.current = true;
    setStatus("working");
    build()
      .then((result) => {
        setObjectUrl(URL.createObjectURL(result.blob));
        setStatus("ready");
      })
      .catch((err: unknown) => {
        console.error("[manual] generation failed", err);
        setError(
          "Something went wrong building your manual. Your purchase is safe — " +
            "reply to your Stripe receipt and we'll send it straight over.",
        );
        setStatus("error");
      });
  }, [auto, build]);

  // The object URL outlives individual clicks, so it is revoked only when the
  // component unmounts. Revoking eagerly is what breaks "download again".
  useEffect(() => {
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [objectUrl]);

  /** Save to the device. Only ever called from a real tap. */
  const save = useCallback(async () => {
    setStatus((s) => (s === "ready" || s === "saved" ? s : "working"));
    setError(null);
    try {
      const result = await build();
      if (!objectUrl) setObjectUrl(URL.createObjectURL(result.blob));
      downloadManual(result);
      setStatus("saved");
    } catch (err) {
      console.error("[manual] generation failed", err);
      setError(
        "Something went wrong building your manual. Your purchase is safe — " +
          "reply to your Stripe receipt and we'll send it straight over.",
      );
      setStatus("error");
    }
  }, [build, objectUrl]);

  /** Open the PDF in its own tab — the path that works inside WebViews. */
  const openInTab = useCallback(async () => {
    setError(null);
    try {
      const result = await build();
      const url = objectUrl ?? URL.createObjectURL(result.blob);
      if (!objectUrl) setObjectUrl(url);
      const opened = window.open(url, "_blank");
      if (!opened) {
        // Blocked — some WebViews refuse window.open outright. Render it in
        // the page instead so they still get to read it.
        setShowInline(true);
      }
      setStatus("saved");
    } catch (err) {
      console.error("[manual] open failed", err);
      setShowInline(true);
    }
  }, [build, objectUrl]);

  if (status === "error") {
    return (
      <div className="rounded-2xl border border-destructive/40 bg-destructive/5 p-5 text-left">
        <p className="flex items-center gap-2 text-sm font-medium text-destructive">
          <AlertCircle className="size-4 shrink-0" /> Couldn't build your manual
        </p>
        <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        <Button variant="outlineGold" className="mt-4" onClick={() => void save()}>
          Try again
        </Button>
      </div>
    );
  }

  const busy = status === "working";

  return (
    <div className="text-center">
      {/* Primary action. Inside a social app the tab-opener goes first,
          because there the download button is a button that does nothing. */}
      {preferOpenInTab ? (
        <Button variant="gold" size="xl" onClick={() => void openInTab()} disabled={busy}>
          {busy ? (
            <>
              <Loader2 className="size-4 animate-spin" /> Building your manual…
            </>
          ) : (
            <>
              <ExternalLink className="size-4" /> Open your 24-page manual
            </>
          )}
        </Button>
      ) : (
        <Button variant="gold" size="xl" onClick={() => void save()} disabled={busy}>
          {busy ? (
            <>
              <Loader2 className="size-4 animate-spin" /> Building your manual…
            </>
          ) : status === "saved" ? (
            <>
              <Check className="size-4" /> Download again
            </>
          ) : (
            <>
              <Download className="size-4" /> Download your 24-page manual
            </>
          )}
        </Button>
      )}

      {busy && (
        <p className="mt-3 text-xs text-muted-foreground">
          Writing 24 pages about {subjectName || "them"} — a few seconds.
        </p>
      )}

      {/* Save instructions differ per platform, and they are the difference
          between a buyer keeping the file and losing it. */}
      {preferOpenInTab ? (
        <p className="mx-auto mt-4 max-w-sm text-xs leading-relaxed text-muted-foreground">
          {appName ? `You're inside ${appName}'s browser. ` : ""}
          Your manual opens as a PDF — tap the share icon and choose{" "}
          <span className="text-foreground/80">{isIOS() ? "Save to Files" : "Download"}</span> to
          keep it. Save it now; access is tied to this browser.
        </p>
      ) : (
        status === "saved" && (
          <p className="mt-3 text-xs text-muted-foreground">
            Saved to your downloads. Page 23 is the one to screenshot.
          </p>
        )
      )}

      {/* Secondary escape hatches, always reachable once something exists. */}
      {status !== "idle" && !busy && (
        <div className="mt-4 flex flex-wrap items-center justify-center gap-3 text-xs">
          {preferOpenInTab ? (
            <button
              type="button"
              onClick={() => void save()}
              className="text-muted-foreground underline underline-offset-4 hover:text-foreground"
            >
              Try a direct download instead
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void openInTab()}
              className="text-muted-foreground underline underline-offset-4 hover:text-foreground"
            >
              Open it in a tab instead
            </button>
          )}
          <button
            type="button"
            onClick={() => setShowInline((v) => !v)}
            className="text-muted-foreground underline underline-offset-4 hover:text-foreground"
          >
            {showInline ? "Hide preview" : "Read it here"}
          </button>
        </div>
      )}

      {/* Last resort: render it in the page, so nobody who paid leaves empty-handed. */}
      {showInline && objectUrl && (
        <div className="mt-6 overflow-hidden rounded-2xl border border-border">
          <iframe
            src={objectUrl}
            title="Your Operator's Manual"
            className="h-[70vh] w-full bg-white"
          />
        </div>
      )}
    </div>
  );
}
