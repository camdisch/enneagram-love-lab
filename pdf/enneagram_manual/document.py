"""Assembling the 24-page document as data, before anything is drawn.

Keeping the document as a plain object graph (rather than emitting PDF
primitives as we go) is what makes the quality gate possible: :mod:`.qa`
inspects finished copy with full knowledge of which page and which block it
sits in, and can block the save *before* a single byte is written.

The page plan is fixed at exactly 24 entries. Adding or removing a page is a
deliberate act that fails :func:`build_document`'s own assertion, not
something that happens by accident when someone tweaks a section.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .blending import Blender, secondary_is_meaningful
from .errors import LayoutError
from .models import Profile

PAGE_COUNT = 24


# --------------------------------------------------------------------------
# Blocks
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Para:
    text: str


@dataclass(frozen=True)
class Bullets:
    items: tuple[str, ...]
    marker: str = "•"


@dataclass(frozen=True)
class Numbered:
    items: tuple[str, ...]


@dataclass(frozen=True)
class Script:
    """A word-for-word line the buyer is meant to actually say."""

    label: str
    text: str


@dataclass(frozen=True)
class Callout:
    title: str
    text: str


@dataclass(frozen=True)
class PullQuote:
    text: str


@dataclass(frozen=True)
class KV:
    rows: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Chart:
    """Horizontal bars for the top-N type shares."""

    rows: tuple[tuple[str, int, bool], ...]   # (label, percent, is_core)


@dataclass(frozen=True)
class TriggerBlock:
    name: str
    looks_like: str
    why: str
    instead: str


@dataclass(frozen=True)
class Glyph:
    """A decorative type numeral. Exempt from the prose rules in :mod:`.qa`."""

    text: str


Block = (Para | Bullets | Numbered | Script | Callout | PullQuote | KV | Chart
         | TriggerBlock | Glyph)


@dataclass(frozen=True)
class Section:
    """One page of the manual."""

    number: int
    kicker: str
    title: str
    blocks: tuple[Block, ...]
    style: str = "body"          # "cover" | "body" | "cheat" | "close"
    #: Soft character budget. QA warns above it, layout enforces the hard
    #: limit by measuring actual frame overflow.
    budget: int = 2400


@dataclass(frozen=True)
class Document:
    profile: Profile
    sections: tuple[Section, ...]
    blend_conflicts: tuple[frozenset[str], ...]
    repetition_collisions: tuple[tuple[str, str, str], ...]

    def text_of(self, section: Section) -> str:
        return "\n".join(_block_text(b) for b in section.blocks)

    @property
    def all_text(self) -> str:
        return "\n".join(self.text_of(s) for s in self.sections)


def _block_text(block: Block) -> str:
    if isinstance(block, Para):
        return block.text
    if isinstance(block, (Bullets, Numbered)):
        return "\n".join(block.items)
    if isinstance(block, Script):
        return f"{block.label}\n{block.text}"
    if isinstance(block, Callout):
        return f"{block.title}\n{block.text}"
    if isinstance(block, PullQuote):
        return block.text
    if isinstance(block, Glyph):
        return block.text
    if isinstance(block, KV):
        return "\n".join(f"{k}\n{v}" for k, v in block.rows)
    if isinstance(block, Chart):
        return "\n".join(f"{label} {pct}%" for label, pct, _ in block.rows)
    if isinstance(block, TriggerBlock):
        return "\n".join([block.name, block.looks_like, block.why, block.instead])
    raise LayoutError(f"Unknown block type {type(block).__name__}.")


# --------------------------------------------------------------------------
# The page plan
# --------------------------------------------------------------------------

def build_document(profile: Profile) -> Document:
    """Compose the full 24-page document for one profile.

    Raises:
        LayoutError: if the page plan does not produce exactly 24 sections.
    """
    b = Blender(profile)
    core = b.core
    lens = b.lens
    sections: list[Section] = []

    def add(section: Section) -> None:
        sections.append(section)

    # -- 1. Cover ---------------------------------------------------------
    add(Section(
        number=1, style="cover", kicker=f"{profile.relationship.label} · Operator’s Manual",
        title=core.name,
        blocks=(
            Glyph(core.glyph),
            Para(core.title),
            Para(b.say(
                "Twenty-four pages on one specific person. Not a personality quiz result — "
                "an operating manual for {subject}, and for you.",
                "cover.lede",
            )),
            KV(rows=(
                ("Core pattern", f"{core.name} — {profile.percent(profile.core)}%"),
                ("Secondary pull",
                 f"{b.secondary.name} — {profile.percent(profile.secondary)}%"),
                ("Wing", b.wing.name),
                ("Read", profile.confidence.capitalize() + " confidence"),
            )),
        ),
        budget=1200,
    ))

    # -- 2. How to use this ----------------------------------------------
    add(Section(
        number=2, kicker="Before you start", title="How to use this",
        blocks=(
            Para(
                "This is not a personality report. It is an operating manual for one "
                "specific relationship, and it is written to be used mid-argument, not "
                "admired."
            ),
            Numbered(items=(
                "Read pages 3 to 7 once, properly. That is the read, and everything "
                "else depends on it.",
                "Skip to page 23 and screenshot it. That is the page you will actually use.",
                "Come back to the trigger pages the next time something goes wrong, and "
                "find the one that matches.",
                "Use the scripts close to word-for-word the first few times. They are "
                "engineered around a specific fear, and improvising tends to remove the "
                "part that was doing the work.",
            )),
            Callout(
                title="One honest caveat",
                text=(
                    "A twelve-question test is a lens, not an X-ray. Where this manual "
                    "matches what you have observed for years, trust it hard. Where it "
                    "does not, trust yourself — you have far more data than the quiz does."
                ),
            ),
        ),
        budget=2000,
    ))

    # -- 3. The result ----------------------------------------------------
    blend = b.build()
    ranked = profile.ranked()[:5]
    add(Section(
        number=3, kicker="The result", title="What the answers actually said",
        blocks=(
            Chart(rows=tuple(
                (b_arch_name(t), profile.percent(t), t == profile.core)
                for t, _ in ranked
            )),
            Para(b.say(
                "Every answer {subject} would have given maps onto one of nine patterns. "
                "These are the five that came up — the top one is the engine, and the "
                "next two are the texture.",
                "result.intro",
            )),
            Para(b.say(
                "Read those as shares of {question_count} answers rather than a score out of a "
                "hundred — so the {core_pct} percent at the top is a strong signal, not a "
                "partial one. You will recognise the top two immediately.",
                "result.method",
            )),
            Callout(title="How far to trust this", text=blend.confidence_note),
        ),
        budget=2200,
    ))

    # -- 4. Who they are --------------------------------------------------
    add(Section(
        number=4, kicker="The core", title=f"{core.name}: who they are",
        blocks=(
            PullQuote(core.title),
            Para(b.prose(core.one_line, f"type-{core.type_id}.one_line")),
            Para(b.prose(core.world_view, f"type-{core.type_id}.world_view")),
            Para(b.kind_framing()),
            Callout(
                title="What this is usually mistaken for",
                text=b.prose(core.mistaken_for, f"type-{core.type_id}.mistaken_for"),
            ),
        ),
        budget=2700,
    ))

    # -- 5. The engine ----------------------------------------------------
    add(Section(
        number=5, kicker="The core", title="What is actually driving it",
        blocks=(
            KV(rows=(
                ("Core fear", b.prose(core.core_fear, f"type-{core.type_id}.core_fear")),
                ("Core desire", b.prose(core.core_desire, f"type-{core.type_id}.core_desire")),
            )),
            Callout(
                title="The sentence they live by",
                text=b.prose(core.core_lie, f"type-{core.type_id}.core_lie"),
            ),
            Para(b.say(
                "Almost every behaviour in this manual is that sentence being defended. "
                "When {subject} does something that makes no sense to you, test it against "
                "the fear rather than against the situation — it will usually resolve "
                "immediately.",
                "engine.close",
            )),
        ),
        budget=1900,
    ))

    # -- 6. The blend -----------------------------------------------------
    add(Section(
        number=6, kicker="The blend",
        title=(f"{core.name} × {b.secondary.name}"
               if secondary_is_meaningful(profile) else f"An undiluted {core.name}"),
        blocks=tuple(Para(p) for p in blend.paragraphs),
        budget=2500,
    ))

    # -- 7. This relationship specifically --------------------------------
    add(Section(
        number=7, kicker="The lens", title=f"Why this hits harder as your {profile.relationship.label.lower()}",
        blocks=(
            Para(b.say(lens.stakes, f"lens-{lens.slug}.stakes")),
            Para(b.say(lens.power, f"lens-{lens.slug}.power")),
            Para(b.say(lens.history, f"lens-{lens.slug}.history")),
            Callout(title="What you cannot change here",
                    text=b.say(lens.limits, f"lens-{lens.slug}.limits")),
        ),
        budget=2400,
    ))

    # -- 8. Their gift ----------------------------------------------------
    add(Section(
        number=8, kicker="The upside", title="What you get from them",
        blocks=(
            Para(b.prose(core.gift, f"type-{core.type_id}.gift")),
            Callout(
                title="Say this out loud sometime",
                text=b.say(
                    "Most people never hear the specific version of this. Naming it once, "
                    "concretely, does more for {subject} than a year of general warmth.",
                    "gift.callout",
                ),
            ),
            Bullets(items=tuple(b.prose_list(core.safe, f"type-{core.type_id}.safe")),
                    marker="+"),
        ),
        budget=2100,
    ))

    # -- 9. The cost ------------------------------------------------------
    add(Section(
        number=9, kicker="The cost", title="Where it lands on you",
        blocks=(
            Para(b.prose(core.friction, f"type-{core.type_id}.friction")),
            Para(b.say(
                "This is the part worth being precise about: none of it is aimed at you. "
                "It is the fear on page five, running its defence, and you happen to be "
                "standing in the room. That does not make it costless — it makes it "
                "addressable.",
                "cost.reframe",
            )),
            Bullets(items=tuple(b.prose_list(core.never, f"type-{core.type_id}.never")),
                    marker="×"),
        ),
        budget=2200,
    ))

    # -- 10. Under stress -------------------------------------------------
    stress = b.rng  # noqa: F841 - keeps rng advancement deterministic across builds
    add(Section(
        number=10, kicker="Under pressure", title="What they look like breaking",
        blocks=(
            Para(b.prose(core.stress_text, f"type-{core.type_id}.stress_text")),
            Callout(
                title="The early warning",
                text=b.prose(core.cheat.red_flag, f"type-{core.type_id}.cheat.red_flag"),
            ),
            Para(b.say(
                "When you see this, stop asking {subject} to explain themselves. Reduce "
                "the load first — the explanation becomes available again about a day "
                "after the pressure drops, and not before.",
                "stress.action",
            )),
        ),
        budget=1900,
    ))

    # -- 11. In growth ----------------------------------------------------
    add(Section(
        number=11, kicker="At their best", title="What they look like thriving",
        blocks=(
            Para(b.prose(core.growth_text, f"type-{core.type_id}.growth_text")),
            Callout(
                title="The green flag",
                text=b.prose(core.cheat.green_flag, f"type-{core.type_id}.cheat.green_flag"),
            ),
            Para(b.say(
                "This is not something you can demand, and it is entirely something you can "
                "make room for. Everything from here on is about making room.",
                "growth.action",
            )),
        ),
        budget=1900,
    ))

    # -- 12. The tells ----------------------------------------------------
    add(Section(
        number=12, kicker="Recognition", title="How to spot it in the wild",
        blocks=(
            Para(b.say(
                "Four behaviours that identify this pattern faster than any question you "
                "could ask {subject} directly.",
                "tells.intro",
            )),
            Bullets(items=tuple(b.prose_list(core.tells, f"type-{core.type_id}.tells"))),
            Para(b.kind_framing(b.wing.type_id) if b.wing.type_id != core.type_id
                 else b.say("The wing sits close enough to the core here that it mostly "
                            "amplifies rather than alters what you see in {subject}.",
                            "tells.wing-note")),
            Callout(
                title="Where you will notice it",
                text=b.say(
                    "Watch for these in {channel} — that is where the pattern shows up "
                    "first, before anything has gone wrong enough to talk about.",
                    "tells.channel",
                ),
            ),
        ),
        budget=2100,
    ))

    # -- 13-14. Triggers --------------------------------------------------
    triggers = core.triggers
    add(Section(
        number=13, kicker="Triggers · 1 of 2", title="What detonates them",
        blocks=(
            Para(b.say(
                "Five reliable detonation points. For each one: what you will see, what is "
                "actually happening, and the substitution that costs you nothing.",
                "triggers.intro",
            )),
            *[_trigger_block(b, core.type_id, i, t) for i, t in enumerate(triggers[:2])],
        ),
        budget=2400,
    ))
    add(Section(
        number=14, kicker="Triggers · 2 of 2", title="What detonates them",
        blocks=tuple(
            _trigger_block(b, core.type_id, i + 2, t) for i, t in enumerate(triggers[2:5])
        ),
        budget=2700,
    ))

    # -- 15. De-escalation ------------------------------------------------
    add(Section(
        number=15, kicker="The scripts", title="The three de-escalation sentences",
        blocks=(
            Para(b.say(
                "Each of these speaks directly to what {subject} is defending, which is "
                "why they land when a reasonable argument does not. Use them close to "
                "word-for-word the first few times.",
                "deesc.intro",
            )),
            *[Script(label=f"Sentence {i + 1}", text=line)
              for i, line in enumerate(b.prose_list(core.deescalation,
                                                    f"type-{core.type_id}.deescalation"))],
            Para(b.say(
                "Say one, then stop talking. The silence afterwards is doing half the "
                "work, and filling it is the most common way people waste these.",
                "deesc.close",
            )),
        ),
        budget=2000,
    ))

    # -- 16. Repair -------------------------------------------------------
    add(Section(
        number=16, kicker="The scripts", title="After a fight",
        blocks=(
            Para(b.prose(core.repair, f"type-{core.type_id}.repair")),
            Para(b.say(
                "Your realistic repair window here is {repair_window}.",
                "repair.window",
            )),
            *[Script(label="Say", text=line)
              for line in b.prose_list(core.repair_scripts,
                                       f"type-{core.type_id}.repair_scripts")],
        ),
        budget=2200,
    ))

    # -- 17. Boundaries ---------------------------------------------------
    add(Section(
        number=17, kicker="The scripts", title="Boundaries that do not detonate",
        blocks=(
            Para(b.say(
                "A boundary fails with {subject} when it reads as a verdict on them. Each "
                "of these is built as {ask_form} — same limit, no accusation attached.",
                "boundary.intro",
            )),
            *[Script(label=f"Boundary {i + 1}", text=line)
              for i, line in enumerate(b.prose_list(core.boundary_scripts,
                                                    f"type-{core.type_id}.boundary_scripts"))],
        ),
        budget=2000,
    ))

    # -- 18. Apology, both directions -------------------------------------
    add(Section(
        number=18, kicker="The scripts", title="Apology, both directions",
        blocks=(
            Callout(title="Apologising to them",
                    text=b.prose(core.apology_to_them,
                                 f"type-{core.type_id}.apology_to_them")),
            Callout(title="How they apologise to you",
                    text=b.prose(core.their_apology, f"type-{core.type_id}.their_apology")),
            Para(b.say(
                "Most people in this relationship are waiting for an apology in a format "
                "the other person does not use. Recognising {subject_poss} version costs "
                "you nothing and resolves a startling amount of standing resentment.",
                "apology.close",
            )),
        ),
        budget=2100,
    ))

    # -- 19. Safety and landmines -----------------------------------------
    add(Section(
        number=19, kicker="The rules", title="Safe ground, and the landmines",
        blocks=(
            Callout(title="What makes them feel safe",
                    text=b.say("These are cheap for you and enormous for {subject}.",
                               "safe.intro")),
            Bullets(items=tuple(b.prose_list(core.safe, f"type-{core.type_id}.safe.repeat")),
                    marker="+"),
            Callout(title="Never",
                    text=b.say("Each of these reliably costs you a week.", "never.intro")),
            Bullets(items=tuple(b.prose_list(core.never, f"type-{core.type_id}.never.repeat")),
                    marker="×"),
        ),
        budget=2300,
    ))

    # -- 20. Daily rhythm -------------------------------------------------
    add(Section(
        number=20, kicker="Day to day", title="The rhythm that works",
        blocks=(
            Para(b.prose(core.daily_rhythm, f"type-{core.type_id}.daily_rhythm")),
            Para(b.say(lens.leverage, f"lens-{lens.slug}.leverage")),
            Callout(
                title="When they go quiet",
                text=b.prose(core.cheat.when_quiet, f"type-{core.type_id}.cheat.when_quiet"),
            ),
        ),
        budget=2000,
    ))

    # -- 21. Starters -----------------------------------------------------
    add(Section(
        number=21, kicker="Day to day", title="Questions that actually open them up",
        blocks=(
            Para(b.say(
                "Three questions built for this pattern. They work because none of them can "
                "be answered with the version {subject} has ready.",
                "starters.intro",
            )),
            *[Script(label=f"Ask {i + 1}", text=line)
              for i, line in enumerate(b.prose_list(core.starters,
                                                    f"type-{core.type_id}.starters"))],
            Para(b.say(
                "Ask one. Then let the first silence run well past the point it gets "
                "uncomfortable. Rescuing it is how most people lose the honest reply.",
                "starters.close",
            )),
        ),
        budget=2000,
    ))

    # -- 22. The hard conversation ----------------------------------------
    add(Section(
        number=22, kicker="The hard one", title="The conversation you keep avoiding",
        blocks=(
            Para(b.say(
                "Four steps, in this order. The order is the mechanism — running them out "
                "of sequence with {subject} is what turns a difficult conversation into a "
                "fight.",
                "hard.intro",
            )),
            Numbered(items=tuple(b.prose_list(core.hard_conversation,
                                              f"type-{core.type_id}.hard_conversation"))),
            Callout(
                title="If it goes wrong anyway",
                text=b.prose(core.cheat.when_angry, f"type-{core.type_id}.cheat.when_angry"),
            ),
        ),
        budget=2300,
    ))

    # -- 23. Cheat sheet --------------------------------------------------
    add(Section(
        number=23, style="cheat", kicker="Screenshot this", title="The one-page cheat sheet",
        blocks=(
            KV(rows=(
                ("Say", b.prose(core.cheat.say, f"type-{core.type_id}.cheat.say")),
                ("Never say", b.prose(core.cheat.never_say,
                                      f"type-{core.type_id}.cheat.never_say")),
                ("When they go quiet", b.prose(core.cheat.when_quiet,
                                               f"type-{core.type_id}.cheat.when_quiet.repeat")),
                ("When they are angry", b.prose(core.cheat.when_angry,
                                                f"type-{core.type_id}.cheat.when_angry.repeat")),
                ("Green flag", b.prose(core.cheat.green_flag,
                                       f"type-{core.type_id}.cheat.green_flag.repeat")),
                ("Red flag", b.prose(core.cheat.red_flag,
                                     f"type-{core.type_id}.cheat.red_flag.repeat")),
            )),
            PullQuote(b.prose(core.cheat.one_sentence,
                              f"type-{core.type_id}.cheat.one_sentence")),
        ),
        budget=2200,
    ))

    # -- 24. Close --------------------------------------------------------
    add(Section(
        number=24, style="close", kicker="Last page", title="The only instruction that matters",
        blocks=(
            Para(b.say(
                "Pick one thing from this manual. Not five. One. Run it for two weeks with "
                "{subject} without announcing that you are running it, and watch what "
                "changes.",
                "close.instruction",
            )),
            Para(b.say(
                "If you only take one sentence out of these 24 pages, take this one, and use "
                "it the next time it goes sideways.",
                "close.lead",
            )),
            PullQuote(b.prose(core.cheat.one_sentence,
                              f"type-{core.type_id}.cheat.one_sentence.repeat")),
            Para(b.say(
                "The people around {subject} are running on guesswork. You are not, "
                "any more.",
                "close.sign",
            )),
        ),
        budget=1500,
    ))

    if len(sections) != PAGE_COUNT:
        raise LayoutError(
            f"Page plan produced {len(sections)} sections, expected exactly {PAGE_COUNT}."
        )
    numbers = [s.number for s in sections]
    if numbers != list(range(1, PAGE_COUNT + 1)):
        raise LayoutError(f"Section numbers are not 1..{PAGE_COUNT}: {numbers}.")

    return Document(
        profile=profile,
        sections=tuple(sections),
        blend_conflicts=blend.conflicts,
        repetition_collisions=tuple(b.ledger.collisions),
    )


def _trigger_block(b: Blender, type_id: int, index: int, trigger) -> TriggerBlock:
    where = f"type-{type_id}.triggers[{index}]"
    return TriggerBlock(
        name=b.say(trigger.name, f"{where}.name"),
        looks_like=b.say(trigger.looks_like, f"{where}.looks_like"),
        why=b.say(trigger.why, f"{where}.why"),
        instead=b.say(trigger.instead, f"{where}.instead"),
    )


def b_arch_name(type_id: int) -> str:
    from .content import get_archetype
    return get_archetype(type_id).name
