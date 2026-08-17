type AdSlotProps = {
  slot: "top" | "bottom" | "mid-quiz";
  className?: string;
};

const LABELS: Record<AdSlotProps["slot"], string> = {
  top: "Leaderboard · 728×90",
  bottom: "Footer banner · 970×250",
  "mid-quiz": "In-content · 336×280",
};

/**
 * Google AdSense placeholder. Drop your <ins class="adsbygoogle"> unit inside
 * this wrapper (and the AdSense script into __root.tsx) when the account is live.
 */
export function AdSlot({ slot, className = "" }: AdSlotProps) {
  return (
    <div
      data-ad-slot={slot}
      className={`mx-auto flex w-full max-w-4xl items-center justify-center rounded-xl border border-dashed border-border/70 bg-card/40 px-4 py-6 text-center ${className}`}
    >
      <div className="space-y-1">
        <p className="text-[10px] uppercase tracking-[0.35em] text-muted-foreground">
          Advertisement
        </p>
        <p className="text-xs text-muted-foreground/70">
          Google AdSense placeholder — {LABELS[slot]}
        </p>
      </div>
    </div>
  );
}
