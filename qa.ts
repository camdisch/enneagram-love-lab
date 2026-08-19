/**
 * The quality gate. Mirrors `enneagram_manual/qa.py`.
 *
 * Runs over the assembled document — finished, blended, relationship-specific
 * copy — and any error-severity violation aborts generation before a PDF
 * exists. Every rule here fired on a real bug during development.
 */

import { blockText, sectionText, type Block, type ManualDocument } from "./document";

export const ERROR = "error";
export const WARNING = "warning";

export interface Violation {
  rule: string;
  severity: "error" | "warning";
  where: string;
  detail: string;
}

export class QAFailure extends Error {
  constructor(readonly violations: Violation[]) {
    super(
      `${violations.length} QA violation(s) blocked generation:\n` +
        violations.map((v) => `  - [${v.severity}] ${v.rule} @ ${v.where}: ${v.detail}`).join("\n"),
    );
    this.name = "QAFailure";
  }
}

const BANNED: [RegExp, string][] = [
  [
    /\b(diagnos\w+|disorder|patholog\w+|psychiatric|clinically?)\b/i,
    "clinical framing — this is a relationship guide, not an assessment",
  ],
  [
    /\b(narcissist\w*|sociopath\w*|psychopath\w*|bipolar|borderline|BPD|NPD)\b/i,
    "armchair diagnosis of a real person",
  ],
  [
    /\b(abus\w+|manipulat(?:or|ive)|toxic person|gaslight\w*)\b/i,
    "labels a named individual in terms the buyer may act on unsafely",
  ],
  [
    /\b(guarantee[ds]?|100% effective|always works|never fails|cure[sd]?)\b/i,
    "unsupportable promise",
  ],
  [
    /\b(should probably|you must|you have to|you need to stop)\b/i,
    "prescriptive scolding — this product coaches, it does not instruct",
  ],
  [
    /\b(delve|tapestry|multifaceted|it'?s important to note|in today'?s world|unlock the power|navigate the complexities|ever-evolving)\b/i,
    "filler phrasing that reads as machine-written",
  ],
  [/\b(lorem ipsum|sample text|insert \w+ here)\b/i, "placeholder copy"],
];

const RELATIONSHIP_FORBIDDEN: Record<string, [RegExp, string][]> = {
  parent: [
    [
      /\b(romanti\w+|dating|sexual\w*|in bed|make love|breakup|break up with|marry (?:them|him|her)|your relationship as a couple)\b/i,
      "romantic/sexual framing in a parent manual",
    ],
  ],
  partner: [
    // Deliberately narrow: the forbidden thing is casting the *buyer* as the
    // child. Asking a partner about their own childhood is legitimate.
    [
      /\b(as a child,? you\b|when you were (?:a )?(?:kid|child|small|little),? you\b|you grew up (?:in|with) (?:their|this) (?:house|home)|reparent)/i,
      "childhood-authority framing in a partner manual",
    ],
  ],
  peer: [
    [
      /\b(romanti\w+|sexual\w*|breakup|as a child you|reparent|marry (?:them|him|her))\b/i,
      "romantic or parental framing in a friendship manual",
    ],
  ],
};

const SENTENCE_SPLIT = /(?<=[.!?…])\s+/;
const HEDGES = /\b(maybe|perhaps|possibly|sort of|kind of|arguably|it seems)\b/gi;
const SECOND_PERSON = /\byou(?:r|rs|rself)?\b/i;
const DOUBLED_ARTICLE = /\b(?:the|a|an)\s+(?:The|A|An)\s+\w/i;
const STUTTER = /\b(\w+)\s+\1\b/i;
const LEGITIMATE_DOUBLES = new Set(["had", "that", "no", "very"]);

const MAX_SENTENCE_WORDS = 45;
const MAX_SCRIPT_CHARS = 240;
const MAX_HEDGES_PER_PAGE = 2;
const MAX_REPETITION_COLLISIONS = 6;
const MIN_BODY_CHARS = 320;

/** Pages where quoting an earlier line back at the reader is deliberate. */
const INTENTIONAL_REPEAT_PAGES = new Set([19, 23, 24]);

/** Everything the standard PDF fonts can draw. Anything else prints as a box. */
const ALLOWED_EXTRA = new Set("’‘“”—–…‚„†‡‰‹›€™š›œžŸƒˆ•×÷");
for (let c = 0xa0; c < 0x100; c++) ALLOWED_EXTRA.add(String.fromCharCode(c));

function* iterText(doc: ManualDocument): Generator<[string, string]> {
  for (const section of doc.sections) {
    for (let i = 0; i < section.blocks.length; i++) {
      const block = section.blocks[i] as Block;
      const label = `p${section.number}/${block.kind}[${i}]`;
      switch (block.kind) {
        case "chart":
        case "glyph":
          continue;
        case "bullets":
        case "numbered":
          for (let j = 0; j < block.items.length; j++) {
            yield [`${label}.${j}`, block.items[j] as string];
          }
          break;
        case "kv":
          for (const [k, v] of block.rows) yield [`${label}.${k}`, v];
          break;
        case "trigger":
          yield [`${label}.name`, block.name];
          yield [`${label}.looks_like`, block.looks_like];
          yield [`${label}.why`, block.why];
          yield [`${label}.instead`, block.instead];
          break;
        case "script":
          yield [`${label}.text`, block.text];
          break;
        case "callout":
          yield [`${label}.title`, block.title];
          yield [`${label}.text`, block.text];
          break;
        default:
          yield [label, blockText(block)];
      }
    }
  }
}

type Rule = (doc: ManualDocument) => Violation[];

const v = (
  rule: string,
  severity: "error" | "warning",
  where: string,
  detail: string,
): Violation => ({ rule, severity, where, detail });

const ruleNoEmpty: Rule = (doc) => {
  const out: Violation[] = [];
  for (const [where, text] of iterText(doc)) {
    if (!text || !text.trim())
      out.push(v("no-empty", ERROR, where, "empty string renders as a gap"));
    else if (text.trim().length < 3)
      out.push(v("no-empty", ERROR, where, `suspiciously short: ${text}`));
  }
  return out;
};

const ruleArticleAgreement: Rule = (doc) => {
  const out: Violation[] = [];
  for (const [where, text] of iterText(doc)) {
    const doubled = DOUBLED_ARTICLE.exec(text);
    if (doubled) out.push(v("article-agreement", ERROR, where, `doubled article: "${doubled[0]}"`));
    const stutter = STUTTER.exec(text);
    if (stutter && !LEGITIMATE_DOUBLES.has((stutter[1] as string).toLowerCase())) {
      out.push(v("article-agreement", ERROR, where, `repeated word: "${stutter[0]}"`));
    }
  }
  return out;
};

const ruleBannedLanguage: Rule = (doc) => {
  const out: Violation[] = [];
  for (const [where, text] of iterText(doc)) {
    for (const [pattern, reason] of BANNED) {
      const m = pattern.exec(text);
      if (m) out.push(v("banned-language", ERROR, where, `"${m[0]}": ${reason}`));
    }
  }
  return out;
};

const ruleRelationshipFrame: Rule = (doc) => {
  const out: Violation[] = [];
  for (const [pattern, reason] of RELATIONSHIP_FORBIDDEN[doc.profile.relationship.kind] ?? []) {
    for (const [where, text] of iterText(doc)) {
      const m = pattern.exec(text);
      if (m) out.push(v("relationship-frame", ERROR, where, `"${m[0]}": ${reason}`));
    }
  }
  return out;
};

const ruleRenderableCharacters: Rule = (doc) => {
  const out: Violation[] = [];
  for (const [where, text] of iterText(doc)) {
    const bad = [
      ...new Set([...text].filter((ch) => ch.charCodeAt(0) > 126 && !ALLOWED_EXTRA.has(ch))),
    ];
    if (bad.length) {
      out.push(v("renderable-characters", ERROR, where, `font cannot draw: ${bad.join(" ")}`));
    }
  }
  return out;
};

const ruleTypography: Rule = (doc) => {
  const out: Violation[] = [];
  for (const section of doc.sections) {
    if (section.style === "cover") continue;
    section.blocks.forEach((block, i) => {
      if (block.kind !== "para" && block.kind !== "callout") return;
      const text = block.text;
      const where = `p${section.number}/${block.kind}[${i}]`;
      const first = text[0] ?? "";
      if (first !== first.toUpperCase() && !/\d/.test(first) && !"“‘".includes(first)) {
        out.push(
          v("typography", ERROR, where, `does not start with a capital: ${text.slice(0, 40)}`),
        );
      }
      if (!".!?…”".includes(text.trimEnd().slice(-1))) {
        out.push(v("typography", ERROR, where, `no terminal punctuation: ${text.slice(-40)}`));
      }
    });
  }
  return out;
};

const ruleScriptsSpeakable: Rule = (doc) => {
  const out: Violation[] = [];
  for (const section of doc.sections) {
    section.blocks.forEach((block, i) => {
      if (block.kind !== "script") return;
      if (block.text.length > MAX_SCRIPT_CHARS) {
        out.push(
          v(
            "script-shape",
            ERROR,
            `p${section.number}/script[${i}]`,
            `${block.text.length} chars; nobody says this out loud`,
          ),
        );
      }
    });
  }
  return out;
};

const ruleNoDuplicateSentences: Rule = (doc) => {
  const seen = new Map<string, number>();
  const out: Violation[] = [];
  for (const section of doc.sections) {
    for (const sentence of sectionText(section).split(SENTENCE_SPLIT)) {
      const key = sentence
        .toLowerCase()
        .replace(/[^a-z ]/g, "")
        .trim();
      if (key.split(/\s+/).filter(Boolean).length < 6) continue;
      const first = seen.get(key);
      if (first === undefined) seen.set(key, section.number);
      else if (!INTENTIONAL_REPEAT_PAGES.has(section.number)) {
        out.push(
          v(
            "duplicate-sentence",
            ERROR,
            `p${section.number}`,
            `repeats a sentence from p${first}: ${sentence.slice(0, 60)}`,
          ),
        );
      }
    }
  }
  return out;
};

const ruleBlendCoherence: Rule = (doc) => {
  if (!doc.blendConflicts.length || doc.profile.blendMode === "pure") return [];
  const page = doc.sections.find((s) => s.number === 6);
  if (!page) return [v("blend-coherence", ERROR, "p6", "blend page missing")];
  const text = sectionText(page).toLowerCase();
  const markers = [
    "do not resolve",
    "alternate",
    "internal split",
    "swing",
    "push-pull",
    "when you push on one",
    "hold both",
  ];
  if (!markers.some((m) => text.includes(m))) {
    return [
      v(
        "blend-coherence",
        ERROR,
        "p6",
        "core and secondary hold conflicting claims but the copy asserts both without naming the tension",
      ),
    ];
  }
  return [];
};

const ruleSectionBudget: Rule = (doc) => {
  const out: Violation[] = [];
  for (const section of doc.sections) {
    const length = sectionText(section).length;
    if (length > section.budget) {
      out.push(
        v(
          "section-budget",
          ERROR,
          `p${section.number}`,
          `${length} chars over the ${section.budget} budget`,
        ),
      );
    } else if (length < MIN_BODY_CHARS && section.style === "body") {
      out.push(v("section-budget", WARNING, `p${section.number}`, `only ${length} chars of copy`));
    }
  }
  return out;
};

const ruleSentenceLength: Rule = (doc) => {
  const out: Violation[] = [];
  for (const [where, text] of iterText(doc)) {
    for (const sentence of text.split(SENTENCE_SPLIT)) {
      const words = sentence.split(/\s+/).filter(Boolean).length;
      if (words > MAX_SENTENCE_WORDS) {
        out.push(v("sentence-length", WARNING, where, `${words}-word sentence`));
      }
    }
  }
  return out;
};

const ruleSecondPerson: Rule = (doc) => {
  const out: Violation[] = [];
  for (const section of doc.sections) {
    if (section.style === "cover" || section.style === "cheat") continue;
    if (section.blocks.length && section.blocks.every((b) => b.kind === "trigger")) continue;
    if (!SECOND_PERSON.test(sectionText(section))) {
      out.push(
        v("second-person", WARNING, `p${section.number}`, "page never addresses the reader"),
      );
    }
  }
  return out;
};

const ruleHedging: Rule = (doc) => {
  const out: Violation[] = [];
  for (const section of doc.sections) {
    const hedges = sectionText(section).match(HEDGES) ?? [];
    if (hedges.length > MAX_HEDGES_PER_PAGE) {
      out.push(v("hedging", WARNING, `p${section.number}`, `${hedges.length} hedge words`));
    }
  }
  return out;
};

const ruleRepetition: Rule = (doc) => {
  const collisions = doc.repetitionCollisions.filter(
    ([, a, b]) => ![a, b].some((w) => w.includes(".repeat") || w.includes("cheat")),
  );
  if (collisions.length > MAX_REPETITION_COLLISIONS) {
    return [v("repetition", WARNING, "document", `${collisions.length} reused phrases`)];
  }
  return [];
};

const ruleDegradedInput: Rule = (doc) =>
  doc.profile.degraded
    ? [
        v(
          "degraded-input",
          WARNING,
          "profile",
          "generated from unusable scores; this buyer is getting a generic manual",
        ),
      ]
    : [];

export const RULES: Rule[] = [
  ruleNoEmpty,
  ruleArticleAgreement,
  ruleBannedLanguage,
  ruleRelationshipFrame,
  ruleRenderableCharacters,
  ruleTypography,
  ruleScriptsSpeakable,
  ruleNoDuplicateSentences,
  ruleBlendCoherence,
  ruleSectionBudget,
  ruleSentenceLength,
  ruleSecondPerson,
  ruleHedging,
  ruleRepetition,
  ruleDegradedInput,
];

export function check(doc: ManualDocument): Violation[] {
  const violations = RULES.flatMap((rule) => rule(doc));
  violations.sort(
    (a, b) =>
      Number(a.severity !== ERROR) - Number(b.severity !== ERROR) ||
      a.rule.localeCompare(b.rule) ||
      a.where.localeCompare(b.where),
  );
  return violations;
}

/** Throw if the document is not fit to sell. Returns non-blocking warnings. */
export function enforce(doc: ManualDocument, strict = false): Violation[] {
  const violations = check(doc);
  const blocking = violations.filter((x) => x.severity === ERROR || strict);
  if (blocking.length) throw new QAFailure(blocking);
  return violations;
}
