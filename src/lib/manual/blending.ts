/**
 * Core + secondary composed into one coherent voice.
 * Mirrors `enneagram_manual/blending.py`.
 *
 * Concatenating two archetype descriptions produces the two failure modes
 * buyers actually notice: contradiction (Type 5 "needs distance" printed
 * alongside Type 2 "needs contact") and repetition. Both are handled
 * structurally — conflicting claim tags trigger a tension paragraph that names
 * the push-pull, and a repetition ledger refuses phrasing already used.
 */

import {
  ARCHETYPES,
  CLAIM_CONFLICTS,
  KIND_FRAMING,
  LENSES,
  TENSION_TEMPLATES,
  type Archetype,
  type RelationshipLens,
  type RelationshipSlug,
  type TypeId,
} from "./content";
import { percent, subjectPossessive, subjectRef, type BlendMode, type Profile } from "./models";
import { Rng } from "./portable";
import { render, type Context } from "./templating";

const WORD = /[a-z']+/g;

const STOPWORDS = new Set(
  `a an and are as at be been but by can cannot did do does for from get gets go goes had has
   have how i if in into is it its just like made make more most much no not of on once one
   only or other our out over own same she he they them their than that the then there these
   things this those to too up very was way we were what when where which who why will with
   without you your yours`.split(/\s+/),
);

/** "The Perfector" -> "Perfector", so copy can write "a {core_bare}". */
function bare(name: string): string {
  return name.startsWith("The ") ? name.slice(4) : name;
}

/**
 * Rejects distinctive phrasing already used in this document. Works on
 * content-word trigrams, so "they need to be needed" and "needing to be
 * needed" collide while ordinary connective language does not.
 */
export class RepetitionLedger {
  private seen = new Map<string, string>();
  readonly collisions: [string, string, string][] = [];

  constructor(private readonly n = 3) {}

  private contentWords(text: string): string[] {
    return (text.toLowerCase().match(WORD) ?? []).filter((w) => !STOPWORDS.has(w) && w.length > 2);
  }

  grams(text: string): string[] {
    const words = this.contentWords(text);
    if (words.length < this.n) return [];
    const out = new Set<string>();
    for (let i = 0; i <= words.length - this.n; i++) {
      out.add(words.slice(i, i + this.n).join(" "));
    }
    return [...out];
  }

  wouldCollide(text: string): boolean {
    return this.grams(text).some((g) => this.seen.has(g));
  }

  add(text: string, where: string): void {
    for (const gram of this.grams(text)) {
      const previous = this.seen.get(gram);
      if (previous !== undefined && previous !== where) {
        this.collisions.push([gram, previous, where]);
      } else {
        this.seen.set(gram, where);
      }
    }
  }

  pick(options: string[], rng: Rng, where: string): string {
    if (!options.length) throw new Error(`${where}: no options to choose from.`);
    const shuffled = rng.shuffle([...options]);
    for (const option of shuffled) {
      if (!this.wouldCollide(option)) return option;
    }
    // options is non-empty (checked above), so index 0 always exists.
    return shuffled[0] as string;
  }
}

const BLEND_OPENERS: Record<BlendMode, string[]> = {
  pure: [
    "{subject} reads as an unusually undiluted {core_bare}. At {core_pct} percent, the core pattern is not competing with much — which makes them easier to predict than most people and harder to surprise into a different mode.",
    "There is very little noise in this result. {core_name} at {core_pct} percent, with nothing underneath it strong enough to pull in another direction. What you see with {subject} is close to the whole mechanism.",
  ],
  blended: [
    "{subject} scores {core_name} at {core_pct} percent, running on top of an underlying {secondary_bare} at {secondary_pct}. The {core_bare} is what you meet. The {secondary_bare} is what decides how they behave once they are under pressure.",
    "The headline is {core_name} — {core_pct} percent of {subject_poss} answers — but the {secondary_bare} underneath at {secondary_pct} percent is doing more work than the numbers suggest. It is the reason they do not behave like everyone else who lands on {core_name}.",
  ],
  split: [
    "This is a genuine split, not a clean type. {core_name} at {core_pct} percent and {secondary_name} at {secondary_pct} are close enough that neither is really in charge. That is not a flaw in the test — it is the most useful thing it found.",
    "{subject} sits almost exactly between {core_name} and {secondary_name} — {core_pct} against {secondary_pct}. People who read as inconsistent usually are not; they are running two systems that want different things and switching between them.",
  ],
};

const BLEND_BODIES = [
  "In practice the {core_bare} sets the goal and the {secondary_bare} sets the method. Watch any decision {subject} makes under real time pressure. What they reach for is the {core_bare} instinct. How they get there is the {secondary_bare} one — {secondary_flavour}.",
  "The layering shows up most clearly in how {subject} handles being wrong. The {core_bare} decides how much it costs them; the {secondary_bare} decides what they do about it — {secondary_flavour}.",
  "You will see the {secondary_bare} first in the small moments rather than the big ones: {secondary_flavour}. It rarely announces itself, and it is almost always the thing that explains the behaviour the {core_bare} label alone cannot.",
];

const WING_LINES = [
  "Their wing sits in {wing_name}, which is the accent rather than the language — it colours the delivery without changing what {subject} actually wants.",
  "The {wing_bare} wing is the flavour on top. It shapes their style far more than their motives, which is why two people with the same core can feel so different to live alongside.",
];

const PURE_SECOND_LINES = [
  "There is a secondary pull toward {secondary_bare}, but at {secondary_pct} percent it is background rather than driver. Treat it as a footnote — if you find yourself explaining {subject} through it, you have probably over-read the number.",
  "{secondary_name} shows up faintly at {secondary_pct} percent. Real, but not load-bearing. The {core_bare} pattern will explain almost everything you need explained.",
];

const CONFIDENCE_NOTES: Record<string, string> = {
  high: "This result is unusually clear. {question_count} questions rarely concentrate this hard on one pattern, which means you can lean on what follows fairly heavily.",
  moderate:
    "This is a solid, ordinary-strength result — clear enough to act on, with a real secondary influence you should keep in view rather than ignore.",
  low: "Treat this one as a starting hypothesis rather than a verdict. The answers spread widely enough that the top pattern is a lead, not a conclusion — read it for recognition, and trust what you actually observe over what the percentages say.",
};

export interface Blend {
  mode: BlendMode;
  conflicts: [string, string][];
  paragraphs: string[];
  /**
   * How far the scores can be trusted. Lives on the result page next to the
   * chart it describes — and keeping it off page 6 is what stops the longer
   * archetype names overflowing the blend page.
   */
  confidenceNote: string;
}

export class Blender {
  readonly rng: Rng;
  readonly ledger = new RepetitionLedger();
  readonly core: Archetype;
  readonly secondary: Archetype;
  readonly wing: Archetype;
  readonly lens: RelationshipLens;

  constructor(readonly profile: Profile) {
    this.rng = new Rng(profile.seed);
    this.core = ARCHETYPES[profile.core];
    this.secondary = ARCHETYPES[profile.secondary];
    this.wing = ARCHETYPES[profile.wing];
    this.lens = LENSES[profile.relationship.slug as RelationshipSlug];
  }

  /** Full template vocabulary. Every value is a non-empty string by construction. */
  context(): Context {
    const p = this.profile;
    return {
      subject: subjectRef(p),
      subject_poss: subjectPossessive(p),
      relation: p.relationship.label.toLowerCase(),
      relation_label: p.relationship.label,
      core_name: this.core.name,
      core_title: this.core.title,
      secondary_name: this.secondary.name,
      secondary_title: this.secondary.title,
      wing_name: this.wing.name,
      core_bare: bare(this.core.name),
      secondary_bare: bare(this.secondary.name),
      wing_bare: bare(this.wing.name),
      core_pull: this.core.pull,
      secondary_pull: this.secondary.pull,
      core_pct: String(percent(p, p.core)),
      secondary_pct: String(percent(p, p.secondary)),
      question_count: String(p.questionCount),
      channel: this.lens.channel,
      stakes: this.lens.stakes,
      ask_form: this.lens.ask_form,
      repair_window: this.lens.repair_window,
    };
  }

  say(template: string, where: string, extra?: Context): string {
    const ctx = extra ? { ...this.context(), ...extra } : this.context();
    const text = render(template, ctx, where);
    this.ledger.add(text, where);
    return text;
  }

  choose(options: string[], where: string, extra?: Context): string {
    const ctx = extra ? { ...this.context(), ...extra } : this.context();
    const rendered = options.map((opt, i) => render(opt, ctx, `${where}[${i}]`));
    const picked = this.ledger.pick(rendered, this.rng, where);
    this.ledger.add(picked, where);
    return picked;
  }

  /** Claim pairs where core and secondary genuinely disagree. */
  conflicts(): [string, string][] {
    const coreClaims = new Set(this.core.claims);
    const secondaryClaims = new Set(this.secondary.claims);
    return CLAIM_CONFLICTS.filter(
      ([a, b]) =>
        (coreClaims.has(a) && secondaryClaims.has(b)) ||
        (coreClaims.has(b) && secondaryClaims.has(a)),
    );
  }

  private flavour(): string {
    const text = render(
      this.secondary.as_secondary,
      this.context(),
      `type-${this.secondary.type_id}.as_secondary`,
    );
    // Always spliced mid-sentence after an em dash, so the leading capital
    // that typeset() adds has to come back off.
    return /^[A-Z]/.test(text) ? (text[0] as string).toLowerCase() + text.slice(1) : text;
  }

  build(): Blend {
    const p = this.profile;
    const mode = p.blendMode;
    const paragraphs: string[] = [this.choose(BLEND_OPENERS[mode], "blend.opener")];

    if (mode === "pure") {
      paragraphs.push(this.choose(PURE_SECOND_LINES, "blend.pure-secondary"));
    } else {
      paragraphs.push(
        this.choose(BLEND_BODIES, "blend.body", { secondary_flavour: this.flavour() }),
      );
    }

    const conflicts = this.conflicts();
    if (conflicts.length && mode !== "pure") {
      // Name the push-pull rather than asserting both sides as fact.
      paragraphs.push(this.choose(TENSION_TEMPLATES, "blend.tension"));
    }

    if (this.wing.type_id !== p.core && this.wing.type_id !== p.secondary) {
      paragraphs.push(this.choose(WING_LINES, "blend.wing"));
    }

    return {
      mode,
      conflicts,
      paragraphs,
      confidenceNote: this.say(CONFIDENCE_NOTES[p.confidence] as string, "blend.confidence"),
    };
  }

  kindFraming(typeId?: TypeId): string {
    const tid = typeId ?? this.profile.core;
    const key = `${this.profile.relationship.kind}:${tid}`;
    const template = KIND_FRAMING[key];
    if (!template) throw new Error(`No KIND_FRAMING for ${key}.`);
    return this.say(template, `kind-${this.profile.relationship.kind}-${tid}`);
  }

  prose(template: string, where: string): string {
    return this.say(template, where);
  }

  proseList(templates: string[], where: string): string[] {
    return templates.map((t, i) => this.say(t, `${where}[${i}]`));
  }
}

/** Whether copy may make claims about the secondary type at all. */
export function secondaryIsMeaningful(profile: Profile): boolean {
  return profile.blendMode !== "pure";
}
