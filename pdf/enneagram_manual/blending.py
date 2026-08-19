"""Turning a core type plus a secondary pull into one coherent voice.

The naive version of this feature concatenates two archetype descriptions
and hopes. That produces the two failure modes buyers actually notice:

1. **Contradiction.** Type 5 copy says they need distance; Type 2 copy says
   they need contact. Print both as fact and the manual is visibly wrong
   about a person the reader knows well.
2. **Repetition.** Both archetypes reach for the same stock phrases, and by
   page 14 the reader is skimming.

Both are handled structurally here rather than by author discipline.
:class:`Blender` detects conflicting claim tags and emits a *tension* line
that names the push-pull -- which is both true to how blended types actually
present and better copy than either claim alone -- and :class:`RepetitionLedger`
refuses to let a distinctive phrase appear twice in one document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .content import (
    ARCHETYPES,
    CLAIM_CONFLICTS,
    KIND_FRAMING,
    TENSION_TEMPLATES,
    Archetype,
    get_archetype,
    get_lens,
)
from .models import Profile
from .portable import Rng
from .templating import render

_WORD = re.compile(r"[a-z']+")


def _bare(name: str) -> str:
    """'The Perfector' -> 'Perfector', so copy can write 'a {core_bare}'."""
    return name[4:] if name.startswith("The ") else name

_STOPWORDS = frozenset("""
a an and are as at be been but by can cannot did do does for from get gets go goes had has
have how i if in into is it its just like made make more most much no not of on once one
only or other our out over own same she he they them their than that the then there these
things this those to too up very was way we were what when where which who why will with
without you your yours
""".split())


class RepetitionLedger:
    """Rejects distinctive phrasing that has already been used in this document.

    Works on content-word trigrams rather than raw substrings so that
    "they need to be needed" and "needing to be needed" collide, while
    ordinary connective language does not trip it.
    """

    def __init__(self, *, n: int = 3) -> None:
        self.n = n
        self._seen: dict[tuple[str, ...], str] = {}
        self.collisions: list[tuple[str, str, str]] = []

    @staticmethod
    def _content_words(text: str) -> list[str]:
        return [w for w in _WORD.findall(text.lower()) if w not in _STOPWORDS and len(w) > 2]

    def grams(self, text: str) -> set[tuple[str, ...]]:
        words = self._content_words(text)
        if len(words) < self.n:
            return set()
        return {tuple(words[i:i + self.n]) for i in range(len(words) - self.n + 1)}

    def would_collide(self, text: str) -> bool:
        return bool(self.grams(text) & set(self._seen))

    def add(self, text: str, where: str) -> None:
        """Record ``text`` and log any phrase it reuses from earlier copy."""
        for gram in self.grams(text):
            previous = self._seen.get(gram)
            if previous is not None and previous != where:
                self.collisions.append((" ".join(gram), previous, where))
            else:
                self._seen[gram] = where

    def pick(self, options: list[str], rng: Rng, where: str) -> str:
        """Choose the first non-colliding option; fall back to a random one.

        Deterministic given the same seed, so a buyer re-downloading gets a
        byte-identical file.
        """
        if not options:
            raise ValueError(f"{where}: no options to choose from.")
        shuffled = rng.shuffle(list(options))
        for option in shuffled:
            if not self.would_collide(option):
                return option
        return shuffled[0]


@dataclass
class Blend:
    """The resolved relationship between core and secondary for this profile."""

    mode: str                     # "pure" | "blended" | "split"
    core: Archetype
    secondary: Archetype
    wing: Archetype
    conflicts: tuple[frozenset[str], ...]
    #: Prose paragraphs describing the blend, already rendered.
    paragraphs: tuple[str, ...] = ()
    #: How far the scores can be trusted. Lives on the result page next to
    #: the chart it is about, not on the blend page — and keeping it off p6
    #: is what stops long archetype names overflowing that page.
    confidence_note: str = ""


# Openers for the blend section, chosen by mode so the copy never claims
# more confidence than the scores support.
_BLEND_OPENERS: dict[str, tuple[str, ...]] = {
    "pure": (
        "{subject} reads as an unusually undiluted {core_bare}. At {core_pct} percent, the "
        "core pattern is not competing with much — which makes them easier to predict "
        "than most people and harder to surprise into a different mode.",
        "There is very little noise in this result. {core_name} at {core_pct} percent, with "
        "nothing underneath it strong enough to pull in another direction. What you see "
        "with {subject} is close to the whole mechanism.",
    ),
    "blended": (
        "{subject} scores {core_name} at {core_pct} percent, running on top of an underlying {secondary_bare} "
        "at {secondary_pct}. The {core_bare} is what you meet. The {secondary_bare} is what "
        "decides how they behave once they are under pressure.",
        "The headline is {core_name} — {core_pct} percent of {subject_poss} answers — but the "
        "{secondary_bare} underneath at {secondary_pct} percent is doing more work than the "
        "numbers suggest. It is the reason they do not behave like everyone else who "
        "lands on {core_name}.",
    ),
    "split": (
        "This is a genuine split, not a clean type. {core_name} at {core_pct} percent and "
        "{secondary_name} at {secondary_pct} are close enough that neither is really in "
        "charge. That is not a flaw in the test — it is the most useful thing it found.",
        "{subject} sits almost exactly between {core_name} and {secondary_name} — {core_pct} "
        "against {secondary_pct}. People who read as inconsistent usually are not; they are "
        "running two systems that want different things and switching between them.",
    ),
}

_BLEND_BODIES: tuple[str, ...] = (
    "In practice the {core_bare} sets the goal and the {secondary_bare} sets the method. "
    "Watch any decision {subject} makes under real time pressure. What they reach for is "
    "the {core_bare} instinct. How they get there is the {secondary_bare} one — "
    "{secondary_flavour}.",
    "The layering shows up most clearly in how {subject} handles being wrong. The "
    "{core_bare} decides how much it costs them; the {secondary_bare} decides what they do "
    "about it — {secondary_flavour}.",
    "You will see the {secondary_bare} first in the small moments rather than the big ones: "
    "{secondary_flavour}. It rarely announces itself, and it is almost always the thing "
    "that explains the behaviour the {core_bare} label alone cannot.",
)

_WING_LINES: tuple[str, ...] = (
    "Their wing sits in {wing_name}, which is the accent rather than the language — it "
    "colours the delivery without changing what {subject} actually wants.",
    "The {wing_bare} wing is the flavour on top. It shapes their style far more than their "
    "motives, which is why two people with the same core can feel so different to live "
    "alongside.",
)

#: In "pure" mode there is no secondary worth describing, so the blend page
#: would otherwise run to two short paragraphs and print half-empty. The space
#: goes where it is actually useful: what an undiluted result means in practice.
_PURE_DEPTH_LINES: tuple[str, ...] = (
    "A result this concentrated is worth reading as good news. It means the rest of this "
    "manual applies to {subject} more cleanly than it would to most people — fewer "
    "exceptions, fewer moments where the pattern does not quite fit. When a page here "
    "says they will do something, they will usually do it.",
    "The practical effect of an undiluted result is consistency. {subject} will react to "
    "the same pressure the same way next month and next year. That sounds unremarkable "
    "until you count how much difficulty in any relationship comes from not knowing "
    "which version of someone you are about to get.",
    "What you lose with a result this clean is the usual escape hatch. There is no second "
    "pattern to explain away the hard parts. The friction on the next few pages is not a "
    "mood {subject} is in — it is the mechanism itself, and it is the thing to work with "
    "rather than wait out.",
)

_PURE_SECOND_LINES: tuple[str, ...] = (
    "There is a secondary pull toward {secondary_bare}, but at {secondary_pct} percent it is "
    "background rather than driver. Treat it as a footnote — if you find yourself explaining "
    "{subject} through it, you have probably over-read the number.",
    "{secondary_name} shows up faintly at {secondary_pct} percent. Real, but not load-bearing. "
    "The {core_bare} pattern will explain almost everything you need explained.",
)

_CONFIDENCE_NOTES: dict[str, str] = {
    "high": (
        "This result is unusually clear. {question_count} questions rarely concentrate this "
        "hard on one pattern, which means you can lean on what follows fairly heavily."
    ),
    "moderate": (
        "This is a solid, ordinary-strength result — clear enough to act on, with a real "
        "secondary influence you should keep in view rather than ignore."
    ),
    "low": (
        "Treat this one as a starting hypothesis rather than a verdict. The answers spread "
        "widely enough that the top pattern is a lead, not a conclusion — read it for "
        "recognition, and trust what you actually observe over what the percentages say."
    ),
}


class Blender:
    """Composes core + secondary into non-contradictory, non-repetitive prose."""

    def __init__(self, profile: Profile) -> None:
        self.profile = profile
        self.rng = Rng(profile.seed)
        self.ledger = RepetitionLedger()
        self.core = get_archetype(profile.core)
        self.secondary = get_archetype(profile.secondary)
        self.wing = get_archetype(profile.wing)
        self.lens = get_lens(profile.relationship.slug)

    # -- context ----------------------------------------------------------

    def context(self) -> dict[str, str]:
        """The full template vocabulary for this profile.

        Every value is a non-empty string, which is what lets
        :func:`templating.render` treat an empty substitution as a bug.
        """
        p = self.profile
        return {
            "subject": p.subject_ref,
            "subject_poss": p.subject_possessive,
            "relation": p.relationship.label.lower(),
            "relation_label": p.relationship.label,
            "core_name": self.core.name,
            "core_title": self.core.title,
            "secondary_name": self.secondary.name,
            "secondary_title": self.secondary.title,
            "wing_name": self.wing.name,
            "core_bare": _bare(self.core.name),
            "wing_bare": _bare(self.wing.name),
            "secondary_bare": _bare(self.secondary.name),
            "core_pull": self.core.pull,
            "secondary_pull": self.secondary.pull,
            "core_pct": str(p.percent(p.core)),
            "secondary_pct": str(p.percent(p.secondary)),
            "question_count": str(p.question_count),
            "channel": self.lens.channel,
            "stakes": self.lens.stakes,
            "ask_form": self.lens.ask_form,
            "repair_window": self.lens.repair_window,
        }

    def say(self, template: str, where: str, *, extra: dict[str, str] | None = None) -> str:
        """Render one template in this profile's context and log it for repetition."""
        ctx = self.context()
        if extra:
            ctx.update(extra)
        text = render(template, ctx, where=where)
        self.ledger.add(text, where)
        return text

    def choose(self, options: tuple[str, ...] | list[str], where: str,
               *, extra: dict[str, str] | None = None) -> str:
        """Pick a variant that has not already been used, then render it."""
        ctx = self.context()
        if extra:
            ctx.update(extra)
        rendered = [render(opt, ctx, where=f"{where}[{i}]") for i, opt in enumerate(options)]
        picked = self.ledger.pick(rendered, self.rng, where)
        self.ledger.add(picked, where)
        return picked

    # -- the blend --------------------------------------------------------

    def conflicts(self) -> tuple[frozenset[str], ...]:
        """Claim pairs where core and secondary genuinely disagree."""
        found = []
        for pair in CLAIM_CONFLICTS:
            a, b = tuple(pair)
            if (a in self.core.claims and b in self.secondary.claims) or (
                b in self.core.claims and a in self.secondary.claims
            ):
                found.append(pair)
        return tuple(sorted(found, key=lambda s: sorted(s)))

    def build(self) -> Blend:
        """Produce the blend section: opener, mechanism, tension, wing, confidence."""
        p = self.profile
        mode = p.blend_mode
        paragraphs: list[str] = [self.choose(_BLEND_OPENERS[mode], "blend.opener")]

        if mode == "pure":
            paragraphs.append(self.choose(_PURE_SECOND_LINES, "blend.pure-secondary"))
            paragraphs.append(self.choose(_PURE_DEPTH_LINES, "blend.pure-depth"))
        else:
            paragraphs.append(
                self.choose(
                    _BLEND_BODIES, "blend.body",
                    extra={"secondary_flavour": self._flavour()},
                )
            )

        conflicts = self.conflicts()
        if conflicts and mode != "pure":
            # Name the push-pull rather than asserting both sides as fact.
            paragraphs.append(self.choose(TENSION_TEMPLATES, "blend.tension"))

        wing_is_new = self.wing.type_id != p.core and (
            mode == "pure" or self.wing.type_id != p.secondary
        )
        if wing_is_new:
            paragraphs.append(self.choose(_WING_LINES, "blend.wing"))

        return Blend(
            mode=mode, core=self.core, secondary=self.secondary, wing=self.wing,
            conflicts=conflicts, paragraphs=tuple(paragraphs),
            confidence_note=self.say(_CONFIDENCE_NOTES[p.confidence], "blend.confidence"),
        )

    def _flavour(self) -> str:
        """The secondary's contribution, phrased to slot mid-sentence."""
        text = render(self.secondary.as_secondary, self.context(),
                      where=f"type-{self.secondary.type_id}.as_secondary")
        # These fragments are always spliced mid-sentence after an em dash, so
        # the leading capital that _typeset() adds has to come back off.
        return text[0].lower() + text[1:] if text[:1].isupper() else text

    # -- relationship awareness -------------------------------------------

    def kind_framing(self, type_id: int | None = None) -> str:
        """How this archetype specifically presents in this kind of bond."""
        tid = self.profile.core if type_id is None else type_id
        key = (self.profile.relationship.kind, tid)
        template = KIND_FRAMING.get(key)
        if template is None:  # pragma: no cover - validate_content() prevents this
            from .errors import ContentError
            raise ContentError(f"No KIND_FRAMING for {key}.")
        return self.say(template, f"kind-{key[0]}-{key[1]}")

    def prose(self, template: str, where: str) -> str:
        """Render authored archetype prose (gift, friction, stress_text, ...)."""
        return self.say(template, where)

    def prose_list(self, templates: tuple[str, ...], where: str) -> list[str]:
        return [self.say(t, f"{where}[{i}]") for i, t in enumerate(templates)]


def secondary_is_meaningful(profile: Profile) -> bool:
    """Whether copy is allowed to make claims about the secondary type.

    Guards every downstream section, so a 3-percent secondary never gets
    described as though it shapes the person.
    """
    return profile.blend_mode != "pure" and profile.secondary in ARCHETYPES
