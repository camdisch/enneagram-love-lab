/**
 * A deliberately unforgiving template engine. Mirrors
 * `enneagram_manual/templating.py`.
 *
 * Naive string interpolation fails in the two ways that matter for a product
 * you charge for: a missing key prints an empty hole, and a stray brace prints
 * raw to the customer. Both are impossible here — `render` throws instead, and
 * `auditTemplates` runs the same check statically over the whole copy bank at
 * module load, so a typo in a rarely-hit Type 5 fragment fails a build rather
 * than a buyer's download.
 */

export class TemplateError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TemplateError";
  }
}

/** Anything matching one of these in rendered output is a bug on the page. */
const RESIDUE: [string, RegExp][] = [
  ["curly placeholder", /\{[^{}]*\}/],
  ["unbalanced brace", /[{}]/],
  ["double-bracket tag", /\[\[.*?\]\]/],
  ["angle tag", /<<.*?>>/],
  ["percent format", /%\(\w+\)?[sdif]|(?<!\d)%[sd](?!\w)/],
  ["dollar template", /\$\{?[A-Za-z_]\w*\}?/],
  ["author marker", /\b(TODO|FIXME|TBD|XXX|LOREM|PLACEHOLDER)\b/i],
  ["leaked null", /\b(None|NaN|nan|undefined|null|\[object Object\])\b/],
];

const TYPOGRAPHY: [RegExp, string][] = [
  [/[ \t]*\n[ \t]*/g, " "],
  [/[ \t]{2,}/g, " "],
  [/\s+([,.;:!?])/g, "$1"],
  [/([,.;:!?])(?=[A-Za-z])/g, "$1 "],
  [/\s*--\s*/g, " — "],
  [/\.{3,}/g, "…"],
  [/\ba ([aeiouAEIOU])/g, "an $1"],
];

const APOSTROPHE = /(?<=\w)'(?=\w)/g;
const OPEN_QUOTE = /(?<![\w"])"(?=\S)/g;
const CLOSE_QUOTE = /(?<=\S)"/g;

// Substituted values are noun phrases ("your mom", "Dana") written lowercase
// because they usually land mid-sentence. When one starts a sentence the
// result reads as broken, so fix it mechanically rather than asking every
// author to remember a capitalised variant.
const SENTENCE_START = /(^|(?<=[.!?…]\s)|(?<=[“‘]))\s*([a-z])/g;

function capitaliseSentences(text: string): string {
  return text.replace(
    SENTENCE_START,
    (m: string, _lead: string, ch: string) => m.slice(0, -1) + ch.toUpperCase(),
  );
}

function typeset(text: string): string {
  let out = text;
  for (const [pattern, replacement] of TYPOGRAPHY) {
    out = out.replace(pattern, replacement);
  }
  out = out.replace(APOSTROPHE, "’");
  out = out.replace(OPEN_QUOTE, "“");
  out = out.replace(CLOSE_QUOTE, "”");
  return capitaliseSentences(out.trim());
}

const FIELD = /\{([A-Za-z_][A-Za-z0-9_]*)\}/g;

/** Every variable a template references. */
export function fieldNames(template: string): Set<string> {
  const names = new Set<string>();
  for (const match of template.matchAll(FIELD)) names.add(match[1] as string);
  return names;
}

export type Context = Record<string, string>;

/** Substitute and guarantee clean output, or throw. */
export function render(template: string, context: Context, where = "<template>"): string {
  if (typeof template !== "string") {
    throw new TemplateError(`${where}: expected a string, got ${typeof template}.`);
  }

  const required = [...fieldNames(template)];
  const missing = required.filter((n) => !(n in context)).sort();
  if (missing.length) {
    throw new TemplateError(
      `${where}: template needs [${missing}] which the context does not provide.`,
    );
  }

  const empty = required.filter((n) => context[n] == null || !String(context[n]).trim()).sort();
  if (empty.length) {
    throw new TemplateError(`${where}: context values [${empty}] are empty; would print a hole.`);
  }

  const rendered = typeset(
    template.replace(FIELD, (_m: string, name: string) => context[name] as string),
  );
  assertClean(rendered, where);
  return rendered;
}

/** Throw if text contains anything resembling unrendered markup. */
export function assertClean(text: string, where = "<text>"): void {
  for (const [label, pattern] of RESIDUE) {
    const match = pattern.exec(text);
    if (match) {
      throw new TemplateError(`${where}: ${label} "${match[0]}" survived rendering.`);
    }
  }
}

/**
 * Statically check every template in the bank against the known vocabulary.
 * Returns human-readable problems; empty means no template can reference a
 * variable that will not exist at render time, for any of the 45 combinations.
 */
export function auditTemplates(templates: [string, string][], vocabulary: Set<string>): string[] {
  const problems: string[] = [];
  for (const [where, template] of templates) {
    if (typeof template !== "string" || !template.trim()) {
      problems.push(`${where}: empty or non-string template.`);
      continue;
    }
    const unknown = [...fieldNames(template)].filter((n) => !vocabulary.has(n)).sort();
    if (unknown.length) problems.push(`${where}: references unknown variable(s) [${unknown}].`);

    // Catch residue authored into the copy itself, not produced by substitution.
    const stripped = template.replace(FIELD, "x");
    for (const [label, pattern] of RESIDUE) {
      if (label === "curly placeholder" || label === "unbalanced brace") continue;
      const match = pattern.exec(stripped);
      if (match) problems.push(`${where}: contains ${label} "${match[0]}".`);
    }
  }
  return problems;
}
