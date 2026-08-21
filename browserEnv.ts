/**
 * What kind of browser the buyer is actually in.
 *
 * This matters because almost all of the traffic to this site arrives from a
 * social app, and a social app does not open links in the user's browser. It
 * opens them in an embedded WebView it controls. Two things break there:
 *
 *  1. On iOS every in-app browser is WKWebView, which does not honour the
 *     `download` attribute on an anchor pointing at a `blob:` URL. The tap
 *     does nothing at all — no error, no file. WebKit bug 216918, still open.
 *
 *  2. WebView storage is isolated from the real browser's storage. Anything
 *     written to localStorage inside Instagram is invisible in Safari, which
 *     is why the checkout round trip must never leave the context it started
 *     in (see the same-tab navigation in results.$relationship.tsx).
 *
 * Detection is a user-agent sniff, which is normally a bad idea. It is the
 * right call here because there is no feature test for "the download
 * attribute will silently do nothing" — the failure is silent by definition,
 * so it cannot be probed. Everything gated on this is a *fallback offered in
 * addition to* the normal path, never a removal of it, so a wrong guess costs
 * the buyer an extra visible option rather than the product.
 */

/** Instagram, Facebook, Messenger, TikTok, Snapchat, LINE, Pinterest. */
const IN_APP_TOKENS =
  /(Instagram|FBAN|FBAV|FB_IAB|FBIOS|musical_ly|BytedanceWebview|TikTok|Snapchat|Line\/|Pinterest)/i;

function ua(): string {
  if (typeof navigator === "undefined") return "";
  return navigator.userAgent || "";
}

/** iOS, including iPadOS pretending to be a Mac. */
export function isIOS(): boolean {
  const s = ua();
  if (/iPhone|iPod/i.test(s)) return true;
  // iPadOS 13+ reports a desktop Safari UA; the touch point count gives it away.
  if (/iPad/i.test(s)) return true;
  return (
    /Macintosh/i.test(s) && typeof navigator !== "undefined" && (navigator.maxTouchPoints ?? 0) > 1
  );
}

/**
 * True when the page is inside a social app's embedded browser.
 *
 * Beyond the named tokens, two shape checks catch the quieter ones: Android
 * WebViews carry a `; wv)` marker, and an iPhone UA that is missing its
 * `Safari/` token is not real Safari.
 */
export function isInAppBrowser(): boolean {
  const s = ua();
  if (!s) return false;
  if (IN_APP_TOKENS.test(s)) return true;
  if (/Android/i.test(s) && /;\s*wv\)/i.test(s)) return true;
  if (/iPhone|iPod|iPad/i.test(s) && !/Safari\//i.test(s) && /AppleWebKit/i.test(s)) return true;
  return false;
}

/**
 * Whether `<a download href="blob:…">` can be trusted to produce a file.
 *
 * WKWebView ignores it entirely. Real iOS Safari honours it, but only from
 * inside a genuine touch handler — a programmatic click fired on page load is
 * dropped without a word, which is why nothing here ever auto-downloads.
 */
export function blobDownloadIsReliable(): boolean {
  return !isInAppBrowser();
}

/** Best-effort name of the wrapping app, for writing instructions the buyer can follow. */
export function inAppBrowserName(): string | null {
  const s = ua();
  if (/Instagram/i.test(s)) return "Instagram";
  if (/musical_ly|BytedanceWebview|TikTok/i.test(s)) return "TikTok";
  if (/FBAN|FBAV|FB_IAB|FBIOS/i.test(s)) return "Facebook";
  if (/Snapchat/i.test(s)) return "Snapchat";
  if (/Pinterest/i.test(s)) return "Pinterest";
  if (/Line\//i.test(s)) return "LINE";
  return isInAppBrowser() ? "this app" : null;
}
