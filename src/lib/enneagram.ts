export type TypeId = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9;

export type Archetype = {
  id: TypeId;
  name: string;
  title: string;
  blurb: string;
  gift: string;
  friction: string;
  glyph: string;
};

export const ARCHETYPES: Record<TypeId, Archetype> = {
  1: {
    id: 1,
    name: "The Standard-Keeper",
    title: "Type 1 · The Reformer",
    blurb:
      "They love through improvement. Order is their way of saying \"I want life to be good for you.\"",
    gift: "Unshakable integrity and follow-through.",
    friction: "Correction can land as criticism when you needed comfort.",
    glyph: "I",
  },
  2: {
    id: 2,
    name: "The Overgiver",
    title: "Type 2 · The Helper",
    blurb:
      "They read the room before they read themselves. Care arrives before you ask for it.",
    gift: "Warmth that makes people feel chosen.",
    friction: "Unspoken scorekeeping when the giving isn't returned.",
    glyph: "II",
  },
  3: {
    id: 3,
    name: "The Golden Achiever",
    title: "Type 3 · The Achiever",
    blurb:
      "Love looks like momentum. They show up polished, capable, and quietly hungry for admiration.",
    gift: "They make big things feel possible for you.",
    friction: "Image can crowd out honesty about the hard days.",
    glyph: "III",
  },
  4: {
    id: 4,
    name: "The Deep Feeler",
    title: "Type 4 · The Individualist",
    blurb:
      "Every ordinary moment has an emotional weather system. Intensity is intimacy to them.",
    gift: "They meet you in feelings nobody else names.",
    friction: "Longing for what's missing over what's already here.",
    glyph: "IV",
  },
  5: {
    id: 5,
    name: "The Quiet Observer",
    title: "Type 5 · The Investigator",
    blurb:
      "They love from a considered distance, and give you the truth instead of the performance.",
    gift: "Calm, unflappable clarity in a crisis.",
    friction: "Withdrawal reads as absence when you need presence.",
    glyph: "V",
  },
  6: {
    id: 6,
    name: "The Loyal Guardian",
    title: "Type 6 · The Loyalist",
    blurb:
      "They stress-test the future so you never get blindsided. Loyalty is the whole love language.",
    gift: "They stay. Through everything.",
    friction: "Worry leaks out as questions that feel like doubt in you.",
    glyph: "VI",
  },
  7: {
    id: 7,
    name: "The Bright Escape",
    title: "Type 7 · The Enthusiast",
    blurb:
      "They turn Tuesday into an event and heaviness into a joke, sometimes a beat too early.",
    gift: "Joy that genuinely re-energizes a room.",
    friction: "Hard conversations get rescheduled indefinitely.",
    glyph: "VII",
  },
  8: {
    id: 8,
    name: "The Fierce Protector",
    title: "Type 8 · The Challenger",
    blurb:
      "Their love is a wall between you and the world, built loudly and without apology.",
    gift: "Nobody advocates for you harder.",
    friction: "Intensity can feel like a verdict instead of a hug.",
    glyph: "VIII",
  },
  9: {
    id: 9,
    name: "The Steady Peace",
    title: "Type 9 · The Peacemaker",
    blurb:
      "Easy to be around, hard to fully find. They dissolve conflict, sometimes along with themselves.",
    gift: "A nervous system that lowers everyone else's.",
    friction: "Agreement that hides what they actually want.",
    glyph: "IX",
  },
};

export type Relationship = {
  slug: string;
  label: string;
  subject: string;
  possessive: string;
  hook: string;
  emoji: string;
};

export const RELATIONSHIPS: Relationship[] = [
  {
    slug: "mom",
    label: "Mom",
    subject: "your mom",
    possessive: "her",
    hook: "The one everybody sends to their sister first.",
    emoji: "☎️",
  },
  {
    slug: "dad",
    label: "Dad",
    subject: "your dad",
    possessive: "him",
    hook: "Decode the silences you grew up around.",
    emoji: "🪑",
  },
  {
    slug: "boyfriend",
    label: "Boyfriend",
    subject: "your boyfriend",
    possessive: "him",
    hook: "Why he goes quiet instead of loud.",
    emoji: "🔥",
  },
  {
    slug: "girlfriend",
    label: "Girlfriend",
    subject: "your girlfriend",
    possessive: "her",
    hook: "What she means when she says \"it's fine.\"",
    emoji: "🌙",
  },
  {
    slug: "best-friend",
    label: "Best Friend",
    subject: "your best friend",
    possessive: "them",
    hook: "The chaos-to-loyalty ratio, measured.",
    emoji: "🪩",
  },
];

export function getRelationship(slug: string) {
  return RELATIONSHIPS.find((r) => r.slug === slug);
}

export type Question = {
  prompt: (r: Relationship) => string;
  options: { text: string; type: TypeId }[];
};

export const QUESTIONS: Question[] = [
  {
    prompt: (r) => `You cancel plans last minute. What does ${r.subject} do?`,
    options: [
      { text: "Points out that this keeps happening.", type: 1 },
      { text: "Asks if you're okay, then offers to bring food.", type: 2 },
      { text: "Immediately proposes a better plan.", type: 7 },
      { text: "Says \"no worries\" and means about 60% of it.", type: 9 },
    ],
  },
  {
    prompt: (r) => `A stranger is rude to you in front of ${r.subject}.`,
    options: [
      { text: "They step in before you can blink.", type: 8 },
      { text: "They fix the situation and tell the story later, well.", type: 3 },
      { text: "They go still and analyze what just happened.", type: 5 },
      { text: "They defuse it so nobody escalates.", type: 9 },
    ],
  },
  {
    prompt: (r) => `How does ${r.subject} handle their own bad day?`,
    options: [
      { text: "Names the feeling in vivid, specific detail.", type: 4 },
      { text: "Stays busy so it doesn't count.", type: 3 },
      { text: "Talks through every possible worst case.", type: 6 },
      { text: "Books something fun to outrun it.", type: 7 },
    ],
  },
  {
    prompt: (r) => `What's the most ${r.subject} thing about how they show love?`,
    options: [
      { text: "Remembering the detail you mentioned once.", type: 2 },
      { text: "Showing up early, every single time.", type: 6 },
      { text: "Handling the thing you were dreading.", type: 8 },
      { text: "Doing the research you didn't ask for.", type: 5 },
    ],
  },
  {
    prompt: (r) => `You disagree openly. Where does it go?`,
    options: [
      { text: "Straight to the principle of the matter.", type: 1 },
      { text: "Loud, honest, over in ten minutes.", type: 8 },
      { text: "Quiet retreat, revisited in writing.", type: 5 },
      { text: "Nowhere. They change the subject.", type: 9 },
    ],
  },
  {
    prompt: (r) => `Their phone camera roll is mostly…`,
    options: [
      { text: "Screenshots of things to fix or plan.", type: 1 },
      { text: "Everyone else, rarely themselves.", type: 2 },
      { text: "Wins, trips, milestones.", type: 3 },
      { text: "Skies, textures, small sad beautiful things.", type: 4 },
    ],
  },
  {
    prompt: (r) => `You tell ${r.subject} big news. First reaction?`,
    options: [
      { text: "\"Okay, what's the plan?\"", type: 3 },
      { text: "\"Wait, how do you FEEL about it?\"", type: 4 },
      { text: "\"What could go wrong — just so we're ready.\"", type: 6 },
      { text: "\"We're celebrating. Tonight.\"", type: 7 },
    ],
  },
  {
    prompt: (r) => `The hardest thing to get from ${r.subject}:`,
    options: [
      { text: "An admission that they need something.", type: 8 },
      { text: "Their actual opinion, unedited.", type: 9 },
      { text: "Access to the inner room.", type: 5 },
      { text: "Rest without guilt.", type: 2 },
    ],
  },
  {
    prompt: (r) => `In a group, ${r.subject} is the one who…`,
    options: [
      { text: "Keeps the standard high.", type: 1 },
      { text: "Makes sure nobody's left out.", type: 2 },
      { text: "Runs the energy.", type: 7 },
      { text: "Watches, then says the one accurate thing.", type: 5 },
    ],
  },
  {
    prompt: (r) => `What do they fear you'll think of them?`,
    options: [
      { text: "That they're careless.", type: 1 },
      { text: "That they're a burden.", type: 2 },
      { text: "That they're unimpressive.", type: 3 },
      { text: "That they're ordinary.", type: 4 },
    ],
  },
  {
    prompt: (r) => `Under real pressure, ${r.subject}…`,
    options: [
      { text: "Goes very quiet and very logical.", type: 5 },
      { text: "Doubles down on loyalty and checklists.", type: 6 },
      { text: "Takes command whether or not it's theirs.", type: 8 },
      { text: "Numbs out and smooths over.", type: 9 },
    ],
  },
  {
    prompt: (r) => `The compliment that would actually land:`,
    options: [
      { text: "\"You always do the right thing, even when it costs you.\"", type: 1 },
      { text: "\"You made this whole thing fun.\"", type: 7 },
      { text: "\"I feel safe with you.\"", type: 6 },
      { text: "\"Nobody sees things the way you do.\"", type: 4 },
    ],
  },
];

export type Scores = Record<TypeId, number>;

export function emptyScores(): Scores {
  return { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0 };
}

export function rankScores(scores: Scores) {
  return (Object.keys(scores) as unknown as string[])
    .map((k) => ({ type: Number(k) as TypeId, score: scores[Number(k) as TypeId] }))
    .sort((a, b) => b.score - a.score || a.type - b.type);
}

const KEY = "enneagram-results";

export function saveResult(slug: string, scores: Scores) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(KEY, JSON.stringify({ slug, scores }));
}

export function loadResult(slug: string): Scores | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { slug: string; scores: Scores };
    if (parsed.slug !== slug) return null;
    return parsed.scores;
  } catch {
    return null;
  }
}
