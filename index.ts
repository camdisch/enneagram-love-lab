/**
 * Generate a personalised 24-page Operator's Manual in the browser.
 *
 *   import { generateManual } from "@/lib/manual";
 *   const { blob, filename } = await generateManual({ scores: "1-2-6-3-1-0-4-0-1",
 *                                                     relationship: "mom" });
 *
 * The copy bank is validated against the template vocabulary at module load,
 * so a malformed template fails the build, not a customer's download.
 */

import { VOCABULARY, ARCHETYPES, LENSES, KIND_FRAMING, TENSION_TEMPLATES } from "./content";
import { buildDocument, type ManualDocument } from "./document";
import { buildProfile, type BuildProfileOptions, type Profile } from "./models";
import { renderPdf } from "./layout";
import { enforce, type Violation } from "./qa";
import { auditTemplates } from "./templating";

export { InputError } from "./models";
export { QAFailure } from "./qa";
export type { Profile, ManualDocument, Violation };

function bankTemplates(): [string, string][] {
  const out: [string, string][] = [];
  const add = (where: string, value: string | string[]) => {
    if (Array.isArray(value)) value.forEach((v, i) => out.push([`${where}[${i}]`, v]));
    else out.push([where, value]);
  };
  for (const [id, a] of Object.entries(ARCHETYPES)) {
    const p = `type-${id}`;
    add(`${p}.one_line`, a.one_line);
    add(`${p}.core_fear`, a.core_fear);
    add(`${p}.core_desire`, a.core_desire);
    add(`${p}.core_lie`, a.core_lie);
    add(`${p}.world_view`, a.world_view);
    add(`${p}.gift`, a.gift);
    add(`${p}.friction`, a.friction);
    add(`${p}.stress_text`, a.stress_text);
    add(`${p}.growth_text`, a.growth_text);
    add(`${p}.tells`, a.tells);
    add(`${p}.deescalation`, a.deescalation);
    add(`${p}.repair`, a.repair);
    add(`${p}.repair_scripts`, a.repair_scripts);
    add(`${p}.boundary_scripts`, a.boundary_scripts);
    add(`${p}.apology_to_them`, a.apology_to_them);
    add(`${p}.their_apology`, a.their_apology);
    add(`${p}.safe`, a.safe);
    add(`${p}.never`, a.never);
    add(`${p}.starters`, a.starters);
    add(`${p}.hard_conversation`, a.hard_conversation);
    add(`${p}.daily_rhythm`, a.daily_rhythm);
    add(`${p}.mistaken_for`, a.mistaken_for);
    add(`${p}.as_secondary`, a.as_secondary);
    a.triggers.forEach((t, i) => {
      add(`${p}.triggers[${i}].name`, t.name);
      add(`${p}.triggers[${i}].looks_like`, t.looks_like);
      add(`${p}.triggers[${i}].why`, t.why);
      add(`${p}.triggers[${i}].instead`, t.instead);
    });
    for (const [k, v] of Object.entries(a.cheat)) add(`${p}.cheat.${k}`, v as string);
  }
  for (const [slug, lens] of Object.entries(LENSES)) {
    for (const [k, v] of Object.entries(lens)) {
      if (k !== "slug") add(`lens-${slug}.${k}`, v as string);
    }
  }
  for (const [key, text] of Object.entries(KIND_FRAMING)) add(`kind-${key}`, text);
  TENSION_TEMPLATES.forEach((t, i) => add(`tension[${i}]`, t));
  return out;
}

const bankProblems = auditTemplates(bankTemplates(), new Set(VOCABULARY));
if (bankProblems.length) {
  throw new Error("Copy bank failed template audit:\n" + bankProblems.join("\n"));
}

export interface GenerateOptions extends BuildProfileOptions {
  /** Fail on warnings as well as errors. Use in tests, not in production. */
  strict?: boolean;
}

export interface GenerateResult {
  blob: Blob;
  filename: string;
  profile: Profile;
  document: ManualDocument;
  violations: Violation[];
  fill: Record<number, number>;
}

export async function generateManual(options: GenerateOptions): Promise<GenerateResult> {
  const profile = buildProfile(options);
  const document = buildDocument(profile);
  const violations = enforce(document, options.strict ?? false);
  const { blob, fill } = await renderPdf(document);

  const who = (profile.subjectName || profile.relationship.label)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  const archetype = ARCHETYPES[profile.core].name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  return {
    blob,
    filename: `operators-manual-${who}-${archetype}.pdf`,
    profile,
    document,
    violations,
    fill,
  };
}

/** Trigger the browser download. Revokes the object URL on the next tick. */
export function downloadManual(result: GenerateResult): void {
  const url = URL.createObjectURL(result.blob);
  const link = window.document.createElement("a");
  link.href = url;
  link.download = result.filename;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export { buildProfile, buildDocument };
