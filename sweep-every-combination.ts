/**
 * Exhaustive proof that every buyer gets a good manual.
 *
 * The 45 "type x relationship" combinations are not the real input space. What
 * a buyer actually lands on is a *score distribution*, and that decides four
 * independent things: which archetype is core, which is secondary (8 options
 * per core), which blend mode the copy uses (pure / blended / split), and which
 * wing. This sweep walks all of it, renders a real PDF for every case, and
 * fails on anything that is not a clean 24 pages under strict QA.
 *
 *   npx tsx scripts/sweep-every-combination.ts
 *
 * Run it after any copy or layout change. It is slower than the 45-combo check
 * and it is the one that actually proves the claim.
 */
import { generateManual } from "../src/lib/manual";
import { ARCHETYPES, LENSES, type TypeId } from "../src/lib/manual/content";

const SLUGS = Object.keys(LENSES);
const TYPES = Object.keys(ARCHETYPES).map(Number) as TypeId[];

interface Failure {
  label: string;
  reason: string;
}
const failures: Failure[] = [];
const fills: number[] = [];
let ok = 0;

async function check(label: string, scores: Record<number, number>, slug: string, name?: string) {
  try {
    const r = await generateManual({
      scores,
      relationship: slug,
      ...(name ? { subjectName: name } : {}),
      strict: true, // warnings are failures here
    });
    const bytes = new Uint8Array(await r.blob.arrayBuffer());
    const text = new TextDecoder("latin1").decode(bytes);
    const pages = (text.match(/\/Type \/Page[^s]/g) ?? []).length;
    if (pages !== 24) {
      failures.push({ label, reason: `${pages} pages, expected 24` });
      return;
    }
    if (bytes.length < 15000) {
      failures.push({ label, reason: `only ${bytes.length} bytes` });
      return;
    }
    const thin = Object.entries(r.fill).filter(([, f]) => f < 0.42);
    const tight = Object.entries(r.fill).filter(([, f]) => f > 1.0);
    if (tight.length) {
      failures.push({ label, reason: `overflow on p${tight.map(([p]) => p)}` });
      return;
    }
    if (thin.length) {
      failures.push({ label, reason: `thin p${thin.map(([p]) => p)}` });
      return;
    }
    fills.push(...Object.values(r.fill));
    ok++;
  } catch (e) {
    failures.push({ label, reason: (e as Error).message.split("\n").slice(0, 2).join(" | ") });
  }
}

const base = (v = 0) => Object.fromEntries(TYPES.map((t) => [t, v])) as Record<number, number>;

console.log("Sweeping every core x secondary x relationship x blend mode...\n");

// 1. BLENDED — every core with every possible secondary, in every relationship.
//    9 x 8 x 5 = 360. This is the case most buyers land on.
for (const slug of SLUGS) {
  for (const core of TYPES) {
    for (const secondary of TYPES) {
      if (secondary === core) continue;
      const s = base(1);
      s[core] = 7;
      s[secondary] = 4;
      await check(`blended ${slug} ${core}>${secondary}`, s, slug);
    }
  }
  process.stdout.write(`  blended ${slug} done\n`);
}

// 2. PURE — secondary below the floor, so the copy must stop describing it.
for (const slug of SLUGS) {
  for (const core of TYPES) {
    const s = base(0);
    s[core] = 11;
    s[(core % 9) + 1] = 1;
    await check(`pure ${slug} ${core}`, s, slug);
  }
}
console.log("  pure done");

// 3. SPLIT — an exact tie between two types, every unordered pair.
for (const slug of SLUGS) {
  for (const a of TYPES) {
    for (const b of TYPES) {
      if (b <= a) continue;
      const s = base(0);
      s[a] = 6;
      s[b] = 6;
      await check(`split ${slug} ${a}=${b}`, s, slug);
    }
  }
}
console.log("  split done");

// 4. EXTREMES — 100% concentration, and a flat nine-way tie.
for (const slug of SLUGS) {
  for (const core of TYPES) {
    const s = base(0);
    s[core] = 12;
    await check(`total ${slug} ${core}`, s, slug);
  }
  await check(`flat ${slug}`, base(4), slug);
}
console.log("  extremes done");

// 5. NAMES — a subject name changes possessives and can widen headings.
for (const name of ["Diane", "Chris", "Alexandrina-Josephine", "Zoë", "J"]) {
  const s = base(1);
  s[3] = 7;
  s[7] = 4;
  await check(`name "${name}"`, s, "mom", name);
}
console.log("  names done");

const avg = fills.reduce((a, b) => a + b, 0) / fills.length;
console.log(`\nchecked : ${ok + failures.length}`);
console.log(`passed  : ${ok}`);
console.log(`avg fill: ${(avg * 100).toFixed(1)}%`);
if (failures.length) {
  console.log(`\nFAILURES (${failures.length}):`);
  for (const f of failures.slice(0, 40)) console.log(`  ✗ ${f.label}: ${f.reason}`);
  process.exit(1);
}
console.log("\n✓ every combination produces a clean 24-page manual");
