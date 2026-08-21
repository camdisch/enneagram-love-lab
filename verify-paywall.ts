/**
 * Every way in and every way past the paywall, asserted.
 *
 * Run: npx tsx scripts/verify-paywall.ts
 *
 * This imports the real decision function the /unlocked page calls — not a
 * copy of its logic — so a change to the gate that breaks a rule fails here.
 * The rule under test: nothing unlocks without BOTH a Stripe-shaped session
 * id AND a record that this browser began a checkout.
 *
 * Compiling proves nothing. Every check below stands for a way the product
 * was, or could be, given away free or withheld from someone who paid.
 */

import { decideAccess, looksLikeSession, marksBundle } from "../src/lib/accessDecision";
import type { PendingPurchase } from "../src/lib/pendingPurchase";

let passed = 0;
const failures: string[] = [];

function check(name: string, actual: unknown, expected: unknown): void {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a === e) {
    passed += 1;
    console.log(`  ✓ ${name}`);
  } else {
    failures.push(`${name}\n      expected ${e}\n      actual   ${a}`);
    console.log(`  ✗ ${name}`);
  }
}

const LIVE = "cs_live_a1B2c3D4e5F6g7H8i9J0";
const TEST = "cs_test_a1B2c3D4e5F6g7H8i9J0";

const single: PendingPurchase = {
  scores: "1-2-6-3-1-0-4-0-1",
  relationship: "mom",
  tier: "single",
  subjectName: "Diane",
  savedAt: Date.now(),
};
const bundle: PendingPurchase = { ...single, tier: "bundle" };

const outcome = (d: ReturnType<typeof decideAccess>) => d.outcome;
const tierOf = (d: ReturnType<typeof decideAccess>) => (d.outcome === "grant" ? d.tier : null);

console.log("\nSession id shape");
check("real live id accepted", looksLikeSession(LIVE), true);
check("real test id accepted", looksLikeSession(TEST), true);
check("undefined rejected", looksLikeSession(undefined), false);
check("empty string rejected", looksLikeSession(""), false);
check("bare word rejected", looksLikeSession("yes"), false);
check("plausible-looking fake rejected", looksLikeSession("cs_live_"), false);
check("wrong prefix rejected", looksLikeSession("pi_live_a1B2c3D4e5F6"), false);
check("too short rejected", looksLikeSession("cs_live_abc"), false);
check("punctuation rejected", looksLikeSession(`${LIVE}; DROP`), false);
check("leading space rejected", looksLikeSession(` ${LIVE}`), false);
check("mode must be live or test", looksLikeSession("cs_dev_a1B2c3D4e5F6g7H8"), false);

console.log("\nRefusals — nobody gets the product free");
check(
  "bare /unlocked grants nothing",
  outcome(decideAccess({ session: undefined, all: undefined, record: null })),
  "refuse",
);
check(
  "abandoned checkout (record, no session) grants nothing",
  outcome(decideAccess({ session: undefined, all: undefined, record: single })),
  "refuse",
);
check(
  "garbage session with a record grants nothing",
  outcome(decideAccess({ session: "totally-made-up", all: undefined, record: single })),
  "refuse",
);
check(
  "?all=1 alone grants nothing",
  outcome(decideAccess({ session: undefined, all: "1", record: null })),
  "refuse",
);
check(
  "?all=1 with a record but no session grants nothing",
  outcome(decideAccess({ session: undefined, all: "1", record: single })),
  "refuse",
);
check(
  "empty session string grants nothing",
  outcome(decideAccess({ session: "", all: "1", record: single })),
  "refuse",
);

console.log("\nStranded buyers — refused, but told the truth");
check(
  "valid session with no record is stranded, not refused",
  outcome(decideAccess({ session: LIVE, all: undefined, record: null })),
  "stranded",
);
check(
  "stranded never becomes a grant",
  decideAccess({ session: LIVE, all: "1", record: null }).outcome === "grant",
  false,
);
check(
  "a shared link with no local record still yields nothing",
  tierOf(decideAccess({ session: LIVE, all: "1", record: null })),
  null,
);

console.log("\nGrants — real buyers get exactly what they paid for");
check(
  "real single purchase grants",
  outcome(decideAccess({ session: LIVE, all: undefined, record: single })),
  "grant",
);
check(
  "real single purchase grants single only",
  tierOf(decideAccess({ session: LIVE, all: undefined, record: single })),
  "single",
);
check(
  "test-mode session grants (so you can test-buy)",
  tierOf(decideAccess({ session: TEST, all: undefined, record: single })),
  "single",
);
check(
  "bundle via ?all=1 grants everything",
  tierOf(decideAccess({ session: LIVE, all: "1", record: single })),
  "bundle",
);
check(
  "bundle via stored tier grants everything even if redirect drops ?all",
  tierOf(decideAccess({ session: LIVE, all: undefined, record: bundle })),
  "bundle",
);
check(
  "single purchase is never upgraded by accident",
  tierOf(decideAccess({ session: LIVE, all: "0", record: single })),
  "single",
);
check(
  "empty ?all= does not upgrade a single",
  tierOf(decideAccess({ session: LIVE, all: "", record: single })),
  "single",
);
check(
  "granted session is the one that gets recorded",
  decideAccess({ session: LIVE, all: undefined, record: single }).outcome === "grant"
    ? (decideAccess({ session: LIVE, all: undefined, record: single }) as { session: string })
        .session
    : null,
  LIVE,
);

console.log("\nRouter quirk — ?all=1 arrives as a NUMBER");
// TanStack Router parses ?all=1 as a number, which already crashed this page
// once. String(...) at the call site is what keeps these equivalent.
check("numeric 1 stringified marks bundle", marksBundle(String(1)), true);
check("numeric 0 stringified does not", marksBundle(String(0)), false);
check("undefined does not", marksBundle(undefined), false);

console.log(
  `\nchecked : ${passed + failures.length}\npassed  : ${passed}\nfailed  : ${failures.length}`,
);

if (failures.length) {
  console.error("\n✗ PAYWALL REGRESSION\n");
  for (const f of failures) console.error(`  - ${f}\n`);
  process.exit(1);
}
console.log("\n✓ the paywall grants only on real payment evidence\n");
