"""Emit the copy bank as TypeScript.

Hand-retyping 1,400 lines of authored copy into another language is how you
introduce errors you will never find. This generates it instead, straight
from the validated Python objects, so the TypeScript build is exact by
construction. Re-run it any time the copy changes.

    python export_content.py > ../port/src/lib/manual/content.ts
"""

from __future__ import annotations

import dataclasses
import json
import sys

from enneagram_manual.content import (
    ARCHETYPES, CLAIM_CONFLICTS, KIND_FRAMING, LENSES, TENSION_TEMPLATES,
    VOCABULARY, validate_content,
)
from enneagram_manual.models import RELATIONSHIPS

validate_content()   # never export a bank that would not pass its own checks


def js(value, indent: int = 0) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def archetype_dict(a) -> dict:
    d = dataclasses.asdict(a)
    d["claims"] = sorted(a.claims)
    d["triggers"] = [dataclasses.asdict(t) for t in a.triggers]
    d["cheat"] = dataclasses.asdict(a.cheat)
    for key in ("tells", "deescalation", "repair_scripts", "boundary_scripts",
                "safe", "never", "starters", "hard_conversation"):
        d[key] = list(getattr(a, key))
    return d


HEADER = '''/**
 * The copy bank — nine archetypes, five relationship lenses, and the rules
 * that let them combine without contradicting each other.
 *
 * GENERATED FILE — do not edit by hand.
 * Source of truth is the Python package under `pdf/enneagram_manual/content.py`.
 * Regenerate with:  python export_content.py > src/lib/manual/content.ts
 *
 * Generating rather than retyping is deliberate: this is ~1,400 lines of
 * authored copy, and a hand-port would introduce silent transcription errors
 * that no test would catch.
 */

export interface Trigger {
  name: string;
  looks_like: string;
  why: string;
  instead: string;
}

export interface CheatSheet {
  say: string;
  never_say: string;
  when_quiet: string;
  when_angry: string;
  green_flag: string;
  red_flag: string;
  one_sentence: string;
}

export interface Archetype {
  type_id: number;
  name: string;
  title: string;
  glyph: string;
  one_line: string;
  core_fear: string;
  core_desire: string;
  core_lie: string;
  world_view: string;
  gift: string;
  friction: string;
  stress_to: number;
  stress_text: string;
  growth_to: number;
  growth_text: string;
  tells: string[];
  triggers: Trigger[];
  deescalation: string[];
  repair: string;
  repair_scripts: string[];
  boundary_scripts: string[];
  apology_to_them: string;
  their_apology: string;
  safe: string[];
  never: string[];
  starters: string[];
  hard_conversation: string[];
  daily_rhythm: string;
  mistaken_for: string;
  cheat: CheatSheet;
  as_secondary: string;
  pull: string;
  claims: string[];
}

export interface RelationshipLens {
  slug: string;
  stakes: string;
  power: string;
  channel: string;
  ask_form: string;
  repair_window: string;
  history: string;
  limits: string;
  leverage: string;
}

export interface Relationship {
  slug: string;
  label: string;
  subject: string;
  possessive: string;
  short: string;
  kind: "parent" | "partner" | "peer";
  forbidden_frames: string[];
}
'''


def main() -> None:
    out = [HEADER]

    out.append("export const ARCHETYPES: Record<number, Archetype> = " +
               js({k: archetype_dict(v) for k, v in sorted(ARCHETYPES.items())}) + ";\n")

    out.append("export const LENSES: Record<string, RelationshipLens> = " +
               js({k: dataclasses.asdict(v) for k, v in LENSES.items()}) + ";\n")

    out.append("export const RELATIONSHIPS: Record<string, Relationship> = " +
               js({k: {**dataclasses.asdict(v),
                       "forbidden_frames": list(v.forbidden_frames)}
                   for k, v in RELATIONSHIPS.items()}) + ";\n")

    out.append("/** kind + type id -> how this archetype presents in that bond. */\n"
               "export const KIND_FRAMING: Record<string, string> = " +
               js({f"{kind}:{tid}": text for (kind, tid), text in sorted(KIND_FRAMING.items())})
               + ";\n")

    out.append("export const TENSION_TEMPLATES: string[] = " + js(list(TENSION_TEMPLATES)) + ";\n")

    out.append("/** Behavioural claims that cannot both be asserted about one person. */\n"
               "export const CLAIM_CONFLICTS: [string, string][] = " +
               js([sorted(pair) for pair in sorted(CLAIM_CONFLICTS, key=lambda p: sorted(p))])
               + ";\n")

    out.append("export const VOCABULARY: string[] = " + js(sorted(VOCABULARY)) + ";\n")

    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
