/**
 * Input normalisation and the derived profile.
 * Mirrors `enneagram_manual/models.py`.
 *
 * Contract: anything can be thrown at `buildProfile` — a truncated share link,
 * a half-filled form, an empty object — and it either returns a fully
 * populated `Profile` or throws `InputError` with a message a human can act
 * on. It never returns a half-valid object and never lets a null reach the
 * copy layer. Every repair is recorded on `profile.warnings`.
 */

import { RELATIONSHIPS, type Relationship, type RelationshipSlug, type TypeId } from "./content";
import { fixed4, fnv1a, roundHalfUp } from "./portable";

export class InputError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InputError";
  }
}

export const TYPE_IDS: readonly TypeId[] = [1, 2, 3, 4, 5, 6, 7, 8, 9];

/** Narrowing guard so a string from a URL can index RELATIONSHIPS safely. */
function isSlug(value: string): value is RelationshipSlug {
  return Object.prototype.hasOwnProperty.call(RELATIONSHIPS, value);
}
export const DEFAULT_QUESTION_COUNT = 12;

/** Below this share, a secondary is too weak to describe as a driver. */
export const SECONDARY_FLOOR = 0.12;
/** Within this, the top two are genuinely tied and the copy says so. */
export const SPLIT_MARGIN = 0.04;
/** At or above this, hedging language reads as evasive. */
export const DOMINANCE_CEILING = 0.62;

const NAME_MAX = 40;
// Unicode-aware equivalent of Python's re.UNICODE \w, so accented names survive.
const UNSAFE_NAME = /[^\p{L}\p{N}_\s'’\-.]/gu;

const ALIASES: Record<string, RelationshipSlug> = {
  mother: "mom",
  mum: "mom",
  mommy: "mom",
  ma: "mom",
  father: "dad",
  daddy: "dad",
  pa: "dad",
  bf: "boyfriend",
  husband: "boyfriend",
  partner: "boyfriend",
  gf: "girlfriend",
  wife: "girlfriend",
  bestfriend: "best-friend",
  best_friend: "best-friend",
  bff: "best-friend",
  friend: "best-friend",
};

export const DEFAULT_RELATIONSHIP = "best-friend";

export function resolveRelationship(value: unknown): [Relationship, string[]] {
  const warnings: string[] = [];
  if (value == null || (typeof value === "string" && !value.trim())) {
    warnings.push(`No relationship supplied; defaulted to '${DEFAULT_RELATIONSHIP}'.`);
    return [RELATIONSHIPS[DEFAULT_RELATIONSHIP], warnings];
  }

  const key = String(value).trim().toLowerCase().replace(/ /g, "-").replace(/_/g, "-");
  if (isSlug(key)) return [RELATIONSHIPS[key], warnings];

  const alias = ALIASES[key] ?? ALIASES[key.replace(/-/g, "")];
  if (alias) return [RELATIONSHIPS[alias], warnings];

  warnings.push(`Unknown relationship '${String(value)}'; defaulted to '${DEFAULT_RELATIONSHIP}'.`);
  return [RELATIONSHIPS[DEFAULT_RELATIONSHIP], warnings];
}

function coerceScore(raw: unknown): [number, boolean] {
  if (raw == null || typeof raw === "boolean") return [0, raw != null];
  const value = typeof raw === "number" ? raw : Number(String(raw).trim());
  if (!Number.isFinite(value)) return [0, true];
  if (value < 0) return [0, true];
  return [value, false];
}

export type ScoreMap = Record<TypeId, number>;

export function parseScores(
  raw: unknown,
  questionCount: number = DEFAULT_QUESTION_COUNT,
): [ScoreMap, string[]] {
  const warnings: string[] = [];
  const scores = {} as ScoreMap;
  for (const t of TYPE_IDS) scores[t] = 0;

  if (raw == null) return [scores, ["No scores supplied."]];

  let entries: [unknown, unknown][];

  if (typeof raw === "string") {
    const parts = raw
      .trim()
      .split(/[-,\s]+/)
      .filter((p) => p !== "");
    if (parts.length !== TYPE_IDS.length) {
      warnings.push(
        `Encoded scores had ${parts.length} values, expected ${TYPE_IDS.length}; ` +
          "missing positions treated as 0.",
      );
    }
    entries = TYPE_IDS.map((t, i) => [t, i < parts.length ? parts[i] : 0]);
  } else if (Array.isArray(raw)) {
    if (raw.length !== TYPE_IDS.length) {
      warnings.push(
        `Score sequence had ${raw.length} values, expected ${TYPE_IDS.length}; ` +
          "missing positions treated as 0.",
      );
    }
    entries = TYPE_IDS.map((t, i) => [t, i < raw.length ? raw[i] : 0]);
  } else if (typeof raw === "object") {
    entries = Object.entries(raw as Record<string, unknown>);
  } else {
    throw new InputError(`Scores must be a string, object or array, got ${typeof raw}.`);
  }

  let repaired = 0;
  for (const [key, value] of entries) {
    const typeId = Number.parseInt(String(key).trim(), 10) as TypeId;
    if (!Number.isInteger(typeId)) {
      warnings.push(`Ignored unrecognised score key '${String(key)}'.`);
      continue;
    }
    if (!(typeId in scores)) {
      warnings.push(`Ignored out-of-range type id ${typeId}.`);
      continue;
    }
    const [raw, wasRepaired] = coerceScore(value);
    let coerced = raw;
    if (wasRepaired) repaired += 1;
    if (coerced > questionCount) {
      warnings.push(
        `Type ${typeId} scored ${coerced} above the ${questionCount}-question maximum; clamped.`,
      );
      coerced = questionCount;
    }
    scores[typeId] = coerced;
  }

  if (repaired) warnings.push(`${repaired} score value(s) were unreadable and treated as 0.`);
  return [scores, warnings];
}

function cleanName(raw: unknown): [string, string[]] {
  const warnings: string[] = [];
  if (raw == null) return ["", warnings];
  // NFKC then drop non-printables, matching the Python normalisation.
  const text = String(raw)
    .normalize("NFKC")
    .trim()
    .replace(/[\p{C}]/gu, "");
  let stripped = text.replace(UNSAFE_NAME, "").trim();
  if (stripped !== text) {
    warnings.push("Subject name contained unsupported characters; they were removed.");
  }
  if (stripped.length > NAME_MAX) {
    stripped = stripped.slice(0, NAME_MAX).trimEnd();
    warnings.push(`Subject name truncated to ${NAME_MAX} characters.`);
  }
  return [stripped, warnings];
}

export type BlendMode = "pure" | "blended" | "split";
export type Confidence = "low" | "moderate" | "high";

export interface Profile {
  core: TypeId;
  secondary: TypeId;
  tertiary: TypeId;
  wing: TypeId;
  scores: ScoreMap;
  shares: ScoreMap;
  questionCount: number;
  relationship: Relationship;
  subjectName: string;
  blendMode: BlendMode;
  confidence: Confidence;
  seed: number;
  warnings: string[];
  degraded: boolean;
}

/** Display percentage. Never rounds a real share to a misleading 0 or 100. */
export function percent(profile: Profile, typeId: TypeId): number {
  const pct = (profile.shares[typeId] ?? 0) * 100;
  if (pct > 0 && pct < 1) return 1;
  if (pct > 99 && pct < 100) return 99;
  return roundHalfUp(pct);
}

export function subjectRef(profile: Profile): string {
  return profile.subjectName || profile.relationship.subject;
}

export function subjectPossessive(profile: Profile): string {
  if (!profile.subjectName) return profile.relationship.possessive;
  return profile.subjectName.endsWith("s") ? `${profile.subjectName}'` : `${profile.subjectName}'s`;
}

export function ranked(profile: Profile): [TypeId, number][] {
  return TYPE_IDS.map((t) => [t, profile.shares[t]] as [TypeId, number]).sort(
    (a, b) => b[1] - a[1] || a[0] - b[0],
  );
}

/** Adjacent type the person leans into. 9's neighbours are 8 and 1. */
function wingOf(core: TypeId, shares: ScoreMap): TypeId {
  const left = (core === 1 ? 9 : core - 1) as TypeId;
  const right = (core === 9 ? 1 : core + 1) as TypeId;
  const l = shares[left];
  const r = shares[right];
  if (r > l) return right;
  if (l > r) return left;
  return Math.min(left, right) as TypeId;
}

function seedFor(core: TypeId, secondary: TypeId, slug: string, shares: ScoreMap): number {
  const material = [
    String(core),
    String(secondary),
    slug,
    TYPE_IDS.map((t) => `${t}:${fixed4(shares[t])}`).join(","),
  ].join("|");
  return fnv1a(material);
}

export interface BuildProfileOptions {
  scores?: unknown;
  relationship?: unknown;
  subjectName?: unknown;
  questionCount?: number | null;
  /** Emit an evenly-weighted manual rather than throwing on unusable scores. */
  allowUnscored?: boolean;
}

export function buildProfile(options: BuildProfileOptions = {}): Profile {
  const warnings: string[] = [];

  let qc = DEFAULT_QUESTION_COUNT;
  if (options.questionCount != null) {
    const parsed = Number(options.questionCount);
    if (!Number.isFinite(parsed)) {
      warnings.push(`Unreadable questionCount; used ${DEFAULT_QUESTION_COUNT}.`);
    } else if (parsed <= 0) {
      warnings.push(`questionCount ${parsed} is not positive; used ${DEFAULT_QUESTION_COUNT}.`);
    } else {
      qc = Math.trunc(parsed);
    }
  }

  const [rel, relWarnings] = resolveRelationship(options.relationship);
  warnings.push(...relWarnings);

  const [parsed, scoreWarnings] = parseScores(options.scores, qc);
  warnings.push(...scoreWarnings);

  const [name, nameWarnings] = cleanName(options.subjectName);
  warnings.push(...nameWarnings);

  const total = TYPE_IDS.reduce((sum, t) => sum + parsed[t], 0);
  let degraded = false;
  const shares = {} as ScoreMap;

  if (total <= 0) {
    if (!options.allowUnscored) {
      throw new InputError(
        "Quiz result contains no usable scores. Pass allowUnscored to generate a " +
          "generic manual anyway.",
      );
    }
    degraded = true;
    warnings.push(
      "No usable scores: generated an evenly-weighted manual. This buyer's result " +
        "should be investigated.",
    );
    for (const t of TYPE_IDS) shares[t] = 1 / TYPE_IDS.length;
  } else {
    for (const t of TYPE_IDS) shares[t] = parsed[t] / total;
  }

  const order = [...TYPE_IDS].sort((a, b) => shares[b] - shares[a] || a - b);
  // The array is a permutation of nine fixed ids, so these are always present;
  // the assertions state that rather than pretending the array might be empty.
  let core = order[0] as TypeId;
  let secondary = order[1] as TypeId;
  let tertiary = order[2] as TypeId;

  if (degraded) {
    // An even split has no winner; anchor on the least opinionated archetype
    // rather than letting sort order imply precision the data lacks.
    core = 9;
    secondary = 6;
    tertiary = 3;
  }

  if (!degraded) {
    const ties = TYPE_IDS.filter((t) => t !== core && Math.abs(shares[t] - shares[core]) < 1e-9);
    if (ties.length) {
      warnings.push(
        `Type ${core} tied with ${ties.join(", ")}; resolved to the lowest type id ` +
          "for reproducibility.",
      );
    }
  }

  const gap = shares[core] - shares[secondary];
  let blendMode: BlendMode;
  if (degraded) blendMode = "pure";
  else if (gap <= SPLIT_MARGIN) blendMode = "split";
  else if (shares[secondary] < SECONDARY_FLOOR) blendMode = "pure";
  else blendMode = "blended";

  let confidence: Confidence;
  if (degraded) confidence = "low";
  else if (shares[core] >= DOMINANCE_CEILING && gap > SPLIT_MARGIN) confidence = "high";
  else if (gap <= SPLIT_MARGIN || shares[core] < 0.22) confidence = "low";
  else confidence = "moderate";

  return {
    core,
    secondary,
    tertiary,
    wing: wingOf(core, shares),
    scores: parsed,
    shares,
    questionCount: qc,
    relationship: rel,
    subjectName: name,
    blendMode,
    confidence,
    seed: seedFor(core, secondary, rel.slug, shares),
    warnings,
    degraded,
  };
}
