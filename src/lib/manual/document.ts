/**
 * The 24-page document, assembled as data before anything is drawn.
 * Mirrors `enneagram_manual/document.py`.
 *
 * Keeping it as a plain object graph is what makes the quality gate possible:
 * `qa.ts` inspects finished copy knowing which page and block it sits in, and
 * can block generation before a single byte of PDF exists. The page plan is
 * fixed at exactly 24 entries — changing that is a deliberate act that trips
 * this module's own assertion.
 */

import { ARCHETYPES, type Archetype, type TypeId } from "./content";
import { Blender, secondaryIsMeaningful, type Blend } from "./blending";
import { percent, ranked, type Profile } from "./models";

export const PAGE_COUNT = 24;

export type Block =
  | { kind: "para"; text: string }
  | { kind: "glyph"; text: string }
  | { kind: "bullets"; items: string[]; marker: string }
  | { kind: "numbered"; items: string[] }
  | { kind: "script"; label: string; text: string }
  | { kind: "callout"; title: string; text: string }
  | { kind: "pullquote"; text: string }
  | { kind: "kv"; rows: [string, string][] }
  | { kind: "chart"; rows: [string, number, boolean][] }
  | { kind: "trigger"; name: string; looks_like: string; why: string; instead: string };

export interface Section {
  number: number;
  kicker: string;
  title: string;
  blocks: Block[];
  style: "cover" | "body" | "cheat" | "close";
  /** Soft character budget; real overflow is measured at layout time. */
  budget: number;
}

export interface ManualDocument {
  profile: Profile;
  sections: Section[];
  blendConflicts: [string, string][];
  repetitionCollisions: [string, string, string][];
}

export function blockText(block: Block): string {
  switch (block.kind) {
    case "para":
    case "pullquote":
    case "glyph":
      return block.text;
    case "bullets":
    case "numbered":
      return block.items.join("\n");
    case "script":
      return `${block.label}\n${block.text}`;
    case "callout":
      return `${block.title}\n${block.text}`;
    case "kv":
      return block.rows.map(([k, v]) => `${k}\n${v}`).join("\n");
    case "chart":
      return block.rows.map(([label, pct]) => `${label} ${pct}%`).join("\n");
    case "trigger":
      return [block.name, block.looks_like, block.why, block.instead].join("\n");
  }
}

export function sectionText(section: Section): string {
  return section.blocks.map(blockText).join("\n");
}

export function documentText(doc: ManualDocument): string {
  return doc.sections.map(sectionText).join("\n");
}

const para = (text: string): Block => ({ kind: "para", text });
const callout = (title: string, text: string): Block => ({ kind: "callout", title, text });

function triggerBlock(
  b: Blender,
  typeId: TypeId,
  index: number,
  t: Archetype["triggers"][number],
): Block {
  const where = `type-${typeId}.triggers[${index}]`;
  return {
    kind: "trigger",
    name: b.say(t.name, `${where}.name`),
    looks_like: b.say(t.looks_like, `${where}.looks_like`),
    why: b.say(t.why, `${where}.why`),
    instead: b.say(t.instead, `${where}.instead`),
  };
}

export function buildDocument(profile: Profile): ManualDocument {
  const b = new Blender(profile);
  const core = b.core;
  const lens = b.lens;
  const sections: Section[] = [];
  const add = (s: Section) => sections.push(s);

  // -- 1. Cover ------------------------------------------------------------
  add({
    number: 1,
    style: "cover",
    kicker: `${profile.relationship.label} · Operator’s Manual`,
    title: core.name,
    budget: 1200,
    blocks: [
      { kind: "glyph", text: core.glyph },
      para(core.title),
      para(
        b.say(
          "Twenty-four pages on one specific person. Not a personality quiz result — an operating manual for {subject}, and for you.",
          "cover.lede",
        ),
      ),
      {
        kind: "kv",
        rows: [
          ["Core pattern", `${core.name} — ${percent(profile, profile.core)}%`],
          ["Secondary pull", `${b.secondary.name} — ${percent(profile, profile.secondary)}%`],
          ["Wing", b.wing.name],
          [
            "Read",
            `${(profile.confidence[0] as string).toUpperCase()}${profile.confidence.slice(1)} confidence`,
          ],
        ],
      },
    ],
  });

  // -- 2. How to use this --------------------------------------------------
  add({
    number: 2,
    style: "body",
    kicker: "Before you start",
    title: "How to use this",
    budget: 2000,
    blocks: [
      para(
        "This is not a personality report. It is an operating manual for one specific relationship, and it is written to be used mid-argument, not admired.",
      ),
      {
        kind: "numbered",
        items: [
          "Read pages 3 to 7 once, properly. That is the read, and everything else depends on it.",
          "Skip to page 23 and screenshot it. That is the page you will actually use.",
          "Come back to the trigger pages the next time something goes wrong, and find the one that matches.",
          "Use the scripts close to word-for-word the first few times. They are engineered around a specific fear, and improvising tends to remove the part that was doing the work.",
        ],
      },
      callout(
        "One honest caveat",
        "A twelve-question test is a lens, not an X-ray. Where this manual matches what you have observed for years, trust it hard. Where it does not, trust yourself — you have far more data than the quiz does.",
      ),
    ],
  });

  // -- 3. The result -------------------------------------------------------
  // Built before page 3 renders, because page 3 now carries the confidence
  // note. The blender is deterministic, so building early changes nothing.
  const blend: Blend = b.build();

  add({
    number: 3,
    style: "body",
    kicker: "The result",
    title: "What the answers actually said",
    budget: 2200,
    blocks: [
      {
        kind: "chart",
        rows: ranked(profile)
          .slice(0, 5)
          .map(
            ([t]) =>
              [ARCHETYPES[t].name, percent(profile, t), t === profile.core] as [
                string,
                number,
                boolean,
              ],
          ),
      },
      para(
        b.say(
          "Every answer {subject} would have given maps onto one of nine patterns. These are the five that came up — the top one is the engine, and the next two are the texture.",
          "result.intro",
        ),
      ),
      para(
        b.say(
          "Read those as shares of {question_count} answers rather than a score out of a hundred — so the {core_pct} percent at the top is a strong signal, not a partial one. You will recognise the top two immediately.",
          "result.method",
        ),
      ),
      callout("How far to trust this", blend.confidenceNote),
    ],
  });

  // -- 4. Who they are -----------------------------------------------------
  add({
    number: 4,
    style: "body",
    kicker: "The core",
    title: `${core.name}: who they are`,
    budget: 2700,
    blocks: [
      { kind: "pullquote", text: core.title },
      para(b.prose(core.one_line, `type-${core.type_id}.one_line`)),
      para(b.prose(core.world_view, `type-${core.type_id}.world_view`)),
      para(b.kindFraming()),
      callout(
        "What this is usually mistaken for",
        b.prose(core.mistaken_for, `type-${core.type_id}.mistaken_for`),
      ),
    ],
  });

  // -- 5. The engine -------------------------------------------------------
  add({
    number: 5,
    style: "body",
    kicker: "The core",
    title: "What is actually driving it",
    budget: 1900,
    blocks: [
      {
        kind: "kv",
        rows: [
          ["Core fear", b.prose(core.core_fear, `type-${core.type_id}.core_fear`)],
          ["Core desire", b.prose(core.core_desire, `type-${core.type_id}.core_desire`)],
        ],
      },
      callout("The sentence they live by", b.prose(core.core_lie, `type-${core.type_id}.core_lie`)),
      para(
        b.say(
          "Almost every behaviour in this manual is that sentence being defended. When {subject} does something that makes no sense to you, test it against the fear rather than against the situation — it will usually resolve immediately.",
          "engine.close",
        ),
      ),
    ],
  });

  // -- 6. The blend --------------------------------------------------------
  add({
    number: 6,
    style: "body",
    kicker: "The blend",
    title: secondaryIsMeaningful(profile)
      ? `${core.name} × ${b.secondary.name}`
      : `An undiluted ${core.name}`,
    budget: 2500,
    blocks: blend.paragraphs.map(para),
  });

  // -- 7. This relationship specifically -----------------------------------
  add({
    number: 7,
    style: "body",
    kicker: "The lens",
    title: `Why this hits harder as your ${profile.relationship.label.toLowerCase()}`,
    budget: 2400,
    blocks: [
      para(b.say(lens.stakes, `lens-${lens.slug}.stakes`)),
      para(b.say(lens.power, `lens-${lens.slug}.power`)),
      para(b.say(lens.history, `lens-${lens.slug}.history`)),
      callout("What you cannot change here", b.say(lens.limits, `lens-${lens.slug}.limits`)),
    ],
  });

  // -- 8. Their gift -------------------------------------------------------
  add({
    number: 8,
    style: "body",
    kicker: "The upside",
    title: "What you get from them",
    budget: 2100,
    blocks: [
      para(b.prose(core.gift, `type-${core.type_id}.gift`)),
      callout(
        "Say this out loud sometime",
        b.say(
          "Most people never hear the specific version of this. Naming it once, concretely, does more for {subject} than a year of general warmth.",
          "gift.callout",
        ),
      ),
      { kind: "bullets", marker: "+", items: b.proseList(core.safe, `type-${core.type_id}.safe`) },
    ],
  });

  // -- 9. The cost ---------------------------------------------------------
  add({
    number: 9,
    style: "body",
    kicker: "The cost",
    title: "Where it lands on you",
    budget: 2200,
    blocks: [
      para(b.prose(core.friction, `type-${core.type_id}.friction`)),
      para(
        b.say(
          "This is the part worth being precise about: none of it is aimed at you. It is the fear on page five, running its defence, and you happen to be standing in the room. That does not make it costless — it makes it addressable.",
          "cost.reframe",
        ),
      ),
      {
        kind: "bullets",
        marker: "×",
        items: b.proseList(core.never, `type-${core.type_id}.never`),
      },
    ],
  });

  // -- 10. Under stress ----------------------------------------------------
  add({
    number: 10,
    style: "body",
    kicker: "Under pressure",
    title: "What they look like breaking",
    budget: 1900,
    blocks: [
      para(b.prose(core.stress_text, `type-${core.type_id}.stress_text`)),
      callout(
        "The early warning",
        b.prose(core.cheat.red_flag, `type-${core.type_id}.cheat.red_flag`),
      ),
      para(
        b.say(
          "When you see this, stop asking {subject} to explain themselves. Reduce the load first — the explanation becomes available again about a day after the pressure drops, and not before.",
          "stress.action",
        ),
      ),
    ],
  });

  // -- 11. In growth -------------------------------------------------------
  add({
    number: 11,
    style: "body",
    kicker: "At their best",
    title: "What they look like thriving",
    budget: 1900,
    blocks: [
      para(b.prose(core.growth_text, `type-${core.type_id}.growth_text`)),
      callout(
        "The green flag",
        b.prose(core.cheat.green_flag, `type-${core.type_id}.cheat.green_flag`),
      ),
      para(
        b.say(
          "This is not something you can demand, and it is entirely something you can make room for. Everything from here on is about making room.",
          "growth.action",
        ),
      ),
    ],
  });

  // -- 12. The tells -------------------------------------------------------
  add({
    number: 12,
    style: "body",
    kicker: "Recognition",
    title: "How to spot it in the wild",
    budget: 2100,
    blocks: [
      para(
        b.say(
          "Four behaviours that identify this pattern faster than any question you could ask {subject} directly.",
          "tells.intro",
        ),
      ),
      {
        kind: "bullets",
        marker: "•",
        items: b.proseList(core.tells, `type-${core.type_id}.tells`),
      },
      para(
        b.wing.type_id !== core.type_id
          ? b.kindFraming(b.wing.type_id as TypeId)
          : b.say(
              "The wing sits close enough to the core here that it mostly amplifies rather than alters what you see in {subject}.",
              "tells.wing-note",
            ),
      ),
      callout(
        "Where you will notice it",
        b.say(
          "Watch for these in {channel} — that is where the pattern shows up first, before anything has gone wrong enough to talk about.",
          "tells.channel",
        ),
      ),
    ],
  });

  // -- 13-14. Triggers -----------------------------------------------------
  add({
    number: 13,
    style: "body",
    kicker: "Triggers · 1 of 2",
    title: "What detonates them",
    budget: 2400,
    blocks: [
      para(
        b.say(
          "Five reliable detonation points. For each one: what you will see, what is actually happening, and the substitution that costs you nothing.",
          "triggers.intro",
        ),
      ),
      ...core.triggers.slice(0, 2).map((t, i) => triggerBlock(b, core.type_id as TypeId, i, t)),
    ],
  });
  add({
    number: 14,
    style: "body",
    kicker: "Triggers · 2 of 2",
    title: "What detonates them",
    budget: 2700,
    blocks: core.triggers
      .slice(2, 5)
      .map((t, i) => triggerBlock(b, core.type_id as TypeId, i + 2, t)),
  });

  // -- 15. De-escalation ---------------------------------------------------
  add({
    number: 15,
    style: "body",
    kicker: "The scripts",
    title: "The three de-escalation sentences",
    budget: 2000,
    blocks: [
      para(
        b.say(
          "Each of these speaks directly to what {subject} is defending, which is why they land when a reasonable argument does not. Use them close to word-for-word the first few times.",
          "deesc.intro",
        ),
      ),
      ...b
        .proseList(core.deescalation, `type-${core.type_id}.deescalation`)
        .map((line, i): Block => ({ kind: "script", label: `Sentence ${i + 1}`, text: line })),
      para(
        b.say(
          "Say one, then stop talking. The silence afterwards is doing half the work, and filling it is the most common way people waste these.",
          "deesc.close",
        ),
      ),
    ],
  });

  // -- 16. Repair ----------------------------------------------------------
  add({
    number: 16,
    style: "body",
    kicker: "The scripts",
    title: "After a fight",
    budget: 2200,
    blocks: [
      para(b.prose(core.repair, `type-${core.type_id}.repair`)),
      para(b.say("Your realistic repair window here is {repair_window}.", "repair.window")),
      ...b
        .proseList(core.repair_scripts, `type-${core.type_id}.repair_scripts`)
        .map((line): Block => ({ kind: "script", label: "Say", text: line })),
    ],
  });

  // -- 17. Boundaries ------------------------------------------------------
  add({
    number: 17,
    style: "body",
    kicker: "The scripts",
    title: "Boundaries that do not detonate",
    budget: 2000,
    blocks: [
      para(
        b.say(
          "A boundary fails with {subject} when it reads as a verdict on them. Each of these is built as {ask_form} — same limit, no accusation attached.",
          "boundary.intro",
        ),
      ),
      ...b
        .proseList(core.boundary_scripts, `type-${core.type_id}.boundary_scripts`)
        .map((line, i): Block => ({ kind: "script", label: `Boundary ${i + 1}`, text: line })),
    ],
  });

  // -- 18. Apology, both directions ----------------------------------------
  add({
    number: 18,
    style: "body",
    kicker: "The scripts",
    title: "Apology, both directions",
    budget: 2100,
    blocks: [
      callout(
        "Apologising to them",
        b.prose(core.apology_to_them, `type-${core.type_id}.apology_to_them`),
      ),
      callout(
        "How they apologise to you",
        b.prose(core.their_apology, `type-${core.type_id}.their_apology`),
      ),
      para(
        b.say(
          "Most people in this relationship are waiting for an apology in a format the other person does not use. Recognising {subject_poss} version costs you nothing and resolves a startling amount of standing resentment.",
          "apology.close",
        ),
      ),
    ],
  });

  // -- 19. Safety and landmines --------------------------------------------
  add({
    number: 19,
    style: "body",
    kicker: "The rules",
    title: "Safe ground, and the landmines",
    budget: 2300,
    blocks: [
      callout(
        "What makes them feel safe",
        b.say("These are cheap for you and enormous for {subject}.", "safe.intro"),
      ),
      {
        kind: "bullets",
        marker: "+",
        items: b.proseList(core.safe, `type-${core.type_id}.safe.repeat`),
      },
      callout("Never", b.say("Each of these reliably costs you a week.", "never.intro")),
      {
        kind: "bullets",
        marker: "×",
        items: b.proseList(core.never, `type-${core.type_id}.never.repeat`),
      },
    ],
  });

  // -- 20. Daily rhythm ----------------------------------------------------
  add({
    number: 20,
    style: "body",
    kicker: "Day to day",
    title: "The rhythm that works",
    budget: 2000,
    blocks: [
      para(b.prose(core.daily_rhythm, `type-${core.type_id}.daily_rhythm`)),
      para(b.say(lens.leverage, `lens-${lens.slug}.leverage`)),
      callout(
        "When they go quiet",
        b.prose(core.cheat.when_quiet, `type-${core.type_id}.cheat.when_quiet`),
      ),
    ],
  });

  // -- 21. Starters --------------------------------------------------------
  add({
    number: 21,
    style: "body",
    kicker: "Day to day",
    title: "Questions that actually open them up",
    budget: 2000,
    blocks: [
      para(
        b.say(
          "Three questions built for this pattern. They work because none of them can be answered with the version {subject} has ready.",
          "starters.intro",
        ),
      ),
      ...b
        .proseList(core.starters, `type-${core.type_id}.starters`)
        .map((line, i): Block => ({ kind: "script", label: `Ask ${i + 1}`, text: line })),
      para(
        b.say(
          "Ask one. Then let the first silence run well past the point it gets uncomfortable. Rescuing it is how most people lose the honest reply.",
          "starters.close",
        ),
      ),
    ],
  });

  // -- 22. The hard conversation -------------------------------------------
  add({
    number: 22,
    style: "body",
    kicker: "The hard one",
    title: "The conversation you keep avoiding",
    budget: 2300,
    blocks: [
      para(
        b.say(
          "Four steps, in this order. The order is the mechanism — running them out of sequence with {subject} is what turns a difficult conversation into a fight.",
          "hard.intro",
        ),
      ),
      {
        kind: "numbered",
        items: b.proseList(core.hard_conversation, `type-${core.type_id}.hard_conversation`),
      },
      callout(
        "If it goes wrong anyway",
        b.prose(core.cheat.when_angry, `type-${core.type_id}.cheat.when_angry`),
      ),
    ],
  });

  // -- 23. Cheat sheet -----------------------------------------------------
  add({
    number: 23,
    style: "cheat",
    kicker: "Screenshot this",
    title: "The one-page cheat sheet",
    budget: 2200,
    blocks: [
      {
        kind: "kv",
        rows: [
          ["Say", b.prose(core.cheat.say, `type-${core.type_id}.cheat.say`)],
          ["Never say", b.prose(core.cheat.never_say, `type-${core.type_id}.cheat.never_say`)],
          [
            "When they go quiet",
            b.prose(core.cheat.when_quiet, `type-${core.type_id}.cheat.when_quiet.repeat`),
          ],
          [
            "When they are angry",
            b.prose(core.cheat.when_angry, `type-${core.type_id}.cheat.when_angry.repeat`),
          ],
          [
            "Green flag",
            b.prose(core.cheat.green_flag, `type-${core.type_id}.cheat.green_flag.repeat`),
          ],
          ["Red flag", b.prose(core.cheat.red_flag, `type-${core.type_id}.cheat.red_flag.repeat`)],
        ],
      },
      {
        kind: "pullquote",
        text: b.prose(core.cheat.one_sentence, `type-${core.type_id}.cheat.one_sentence`),
      },
    ],
  });

  // -- 24. Close -----------------------------------------------------------
  add({
    number: 24,
    style: "close",
    kicker: "Last page",
    title: "The only instruction that matters",
    budget: 1500,
    blocks: [
      para(
        b.say(
          "Pick one thing from this manual. Not five. One. Run it for two weeks with {subject} without announcing that you are running it, and watch what changes.",
          "close.instruction",
        ),
      ),
      para(
        b.say(
          "If you only take one sentence out of these 24 pages, take this one, and use it the next time it goes sideways.",
          "close.lead",
        ),
      ),
      {
        kind: "pullquote",
        text: b.prose(core.cheat.one_sentence, `type-${core.type_id}.cheat.one_sentence.repeat`),
      },
      para(
        b.say(
          "The people around {subject} are running on guesswork. You are not, any more.",
          "close.sign",
        ),
      ),
    ],
  });

  if (sections.length !== PAGE_COUNT) {
    throw new Error(`Page plan produced ${sections.length} sections, expected ${PAGE_COUNT}.`);
  }

  return {
    profile,
    sections,
    blendConflicts: blend.conflicts,
    repetitionCollisions: b.ledger.collisions,
  };
}
