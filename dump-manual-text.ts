/**
 * Dump every type x relationship combination as JSON, for the cross-language
 * diff against the Python package. If these two ever disagree, the browser is
 * selling different words than CI tested.
 */
import { buildDocument, sectionText } from "../src/lib/manual/document";
import { buildProfile } from "../src/lib/manual/models";
import { ARCHETYPES, LENSES } from "../src/lib/manual/content";

const out: Record<string, unknown> = {};
for (const slug of Object.keys(LENSES).sort()) {
  for (const typeId of Object.keys(ARCHETYPES)
    .map(Number)
    .sort((a, b) => a - b)) {
    const scores: Record<number, number> = {};
    for (const t of Object.keys(ARCHETYPES).map(Number)) scores[t] = 1;
    scores[typeId] = 7;
    scores[(typeId % 9) + 1] = 3;

    const profile = buildProfile({ scores, relationship: slug });
    const doc = buildDocument(profile);
    out[`${slug}/type-${typeId}`] = {
      core: profile.core,
      secondary: profile.secondary,
      wing: profile.wing,
      blend_mode: profile.blendMode,
      confidence: profile.confidence,
      seed: profile.seed,
      sections: doc.sections.map((s) => ({ n: s.number, title: s.title, text: sectionText(s) })),
    };
  }
}
process.stdout.write(JSON.stringify(out, null, 1));
