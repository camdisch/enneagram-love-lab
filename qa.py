"""The gate. Nothing gets saved as a PDF without passing through here.

The point of this module is that a copy bug should cost a failed test run,
not a refund and a one-star review. It runs over the assembled
:class:`~.document.Document` -- finished, blended, relationship-specific
copy -- and any ``error``-severity violation raises
:class:`~.errors.QAFailure` before a file is written.

Rules are declared as data so adding one is a two-line change, and each
carries the page and block it fired on so the message is actionable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable

from .document import (
    Bullets, Callout, Chart, Document, Glyph, KV, Numbered, Para, PullQuote,
    Script, Section, TriggerBlock, _block_text,
)
from .errors import QAFailure
from .templating import assert_clean
from .errors import TemplateError

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class Violation:
    rule: str
    severity: str
    where: str
    detail: str


# --------------------------------------------------------------------------
# Rule inputs
# --------------------------------------------------------------------------

#: Language that makes a $0.99 relationship product sound like a clinical
#: assessment, or that makes a claim we are not in a position to make.
BANNED_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(diagnos\w+|disorder|patholog\w+|psychiatric|clinical(?:ly)?)\b",
     "clinical framing — this is a relationship guide, not an assessment"),
    (r"\b(narcissist\w*|sociopath\w*|psychopath\w*|bipolar|borderline|BPD|NPD)\b",
     "armchair diagnosis of a real person"),
    (r"\b(abus\w+|manipulat(?:or|ive)|toxic person|gaslight\w*)\b",
     "labels a named individual in terms the buyer may act on unsafely"),
    (r"\b(guarantee[ds]?|100% effective|always works|never fails|cure[sd]?)\b",
     "unsupportable promise"),
    (r"\b(should probably|you must|you have to|you need to stop)\b",
     "prescriptive scolding — the register this product sells is coaching, not instruction"),
    (r"\b(delve|tapestry|multifaceted|it'?s important to note|in today'?s world|"
     r"unlock the power|navigate the complexities|ever-evolving)\b",
     "filler phrasing that reads as machine-written"),
    (r"\b(lorem ipsum|sample text|insert \w+ here)\b", "placeholder copy"),
)

#: Frames that must not appear for a given relationship kind. This is the
#: rule that stops a Type 4 romantic-intensity line from being printed in a
#: manual about somebody's mother.
RELATIONSHIP_FORBIDDEN: dict[str, tuple[tuple[str, str], ...]] = {
    "parent": (
        (r"\b(romanti\w+|dating|sexual\w*|in bed|make love|breakup|break up with|"
         r"marry (?:them|him|her)|your relationship as a couple)\b",
         "romantic/sexual framing in a parent manual"),
    ),
    "partner": (
        # Deliberately narrow: the forbidden thing is casting *the buyer* as
        # the child in this relationship. Asking a partner about their own
        # childhood is legitimate and common in the conversation starters, so
        # the pattern requires the second person to be the one who was small.
        (r"\b(as a child,? you\b|when you were (?:a )?(?:kid|child|small|little),? you\b|"
         r"you grew up (?:in|with) (?:their|this) (?:house|home)|reparent)",
         "childhood-authority framing in a partner manual"),
    ),
    "peer": (
        (r"\b(romanti\w+|sexual\w*|breakup|as a child you|reparent|"
         r"marry (?:them|him|her))\b",
         "romantic or parental framing in a friendship manual"),
    ),
}

#: Characters the PDF fonts can actually draw. The standard Type 1 fonts use
#: WinAnsi encoding, which covers Latin-1 plus a handful of typographic marks;
#: anything outside that renders as a black box on the buyer's screen, which is
#: the most visible bug this product could ship.
_WINANSI_EXTRAS = set("’‘“”—–…‚„†‡‰‹›€™š›œžŸƒˆ•")
ALLOWED_EXTRA_CHARS = _WINANSI_EXTRAS | {
    chr(c) for c in range(0xA0, 0x100) if chr(c).isprintable()
}

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")
_HEDGES = re.compile(r"\b(maybe|perhaps|possibly|sort of|kind of|arguably|it seems)\b", re.I)
_SECOND_PERSON = re.compile(r"\byou(?:r|rs|rself)?\b", re.I)
_DOUBLED_ARTICLE = re.compile(r"\b(?:the|a|an)\s+(?:The|A|An)\s+\w", re.I)
_STUTTER = re.compile(r"\b(\w+)\s+\1\b", re.I)
_LEGITIMATE_DOUBLES = frozenset({"had", "that", "no", "very"})

MAX_SENTENCE_WORDS = 45
MAX_SCRIPT_CHARS = 240
MAX_HEDGES_PER_PAGE = 2
MAX_REPETITION_COLLISIONS = 6
#: Absolute floor only. Real page fill is measured post-render, because
#: character count badly under-estimates the height of scripts and callouts.
MIN_BODY_CHARS = 320
#: Below this measured fill, a body page prints looking unfinished.
MIN_PAGE_FILL = 0.42

#: Pages where reusing a line from earlier is deliberate (the cheat sheet and
#: the close both quote the manual's key sentence back at the reader).
INTENTIONAL_REPEAT_PAGES = frozenset({19, 23, 24})


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------

def _iter_text(doc: Document) -> Iterable[tuple[str, str]]:
    """(where, text) for every authored string in the document."""
    for section in doc.sections:
        for i, block in enumerate(section.blocks):
            label = f"p{section.number}/{type(block).__name__}[{i}]"
            if isinstance(block, (Bullets, Numbered)):
                for j, item in enumerate(block.items):
                    yield f"{label}.{j}", item
            elif isinstance(block, KV):
                for key, value in block.rows:
                    yield f"{label}.{key}", value
            elif isinstance(block, (Chart, Glyph)):
                continue
            elif isinstance(block, TriggerBlock):
                for attr in ("name", "looks_like", "why", "instead"):
                    yield f"{label}.{attr}", getattr(block, attr)
            elif isinstance(block, Script):
                yield f"{label}.text", block.text
            elif isinstance(block, Callout):
                yield f"{label}.title", block.title
                yield f"{label}.text", block.text
            else:
                yield label, _block_text(block)


def rule_no_placeholders(doc: Document) -> list[Violation]:
    """Nothing that looks like unrendered markup may reach a page."""
    out = []
    for where, text in _iter_text(doc):
        try:
            assert_clean(text, where=where)
        except TemplateError as exc:
            out.append(Violation("no-placeholders", ERROR, where, str(exc)))
    return out


def rule_article_agreement(doc: Document) -> list[Violation]:
    """Catch "the The Frontrunner" / "a The Overgiver" and stuttered words.

    Archetype names carry their own definite article, so a template that
    writes "the {core_name}" doubles it. This bug shipped once during
    development; the rule exists so it cannot ship again.
    """
    out = []
    for where, text in _iter_text(doc):
        match = _DOUBLED_ARTICLE.search(text)
        if match:
            out.append(Violation("article-agreement", ERROR, where,
                                 f"doubled article: {match.group(0)!r}"))
        match = _STUTTER.search(text)
        if match and match.group(1).lower() not in _LEGITIMATE_DOUBLES:
            out.append(Violation("article-agreement", ERROR, where,
                                 f"repeated word: {match.group(0)!r}"))
    return out


def rule_no_empty(doc: Document) -> list[Violation]:
    out = []
    for where, text in _iter_text(doc):
        if not text or not text.strip():
            out.append(Violation("no-empty", ERROR, where, "empty string would render as a gap"))
        elif len(text.strip()) < 3:
            out.append(Violation("no-empty", ERROR, where, f"suspiciously short: {text!r}"))
    return out


def rule_banned_language(doc: Document) -> list[Violation]:
    out = []
    for where, text in _iter_text(doc):
        for pattern, reason in BANNED_PATTERNS:
            match = re.search(pattern, text, re.I)
            if match:
                out.append(Violation("banned-language", ERROR, where,
                                     f"{match.group(0)!r}: {reason}"))
    return out


def rule_relationship_frame(doc: Document) -> list[Violation]:
    """Copy must not use a frame that makes no sense for this relationship."""
    kind = doc.profile.relationship.kind
    out = []
    for pattern, reason in RELATIONSHIP_FORBIDDEN.get(kind, ()):
        for where, text in _iter_text(doc):
            match = re.search(pattern, text, re.I)
            if match:
                out.append(Violation("relationship-frame", ERROR, where,
                                     f"{match.group(0)!r}: {reason}"))
    return out


def rule_renderable_characters(doc: Document) -> list[Violation]:
    out = []
    for where, text in _iter_text(doc):
        bad = {
            ch for ch in text
            if ord(ch) > 126 and ch not in ALLOWED_EXTRA_CHARS
        }
        if bad:
            out.append(Violation(
                "renderable-characters", ERROR, where,
                f"characters the PDF font cannot draw: {sorted(bad)}",
            ))
    return out


def rule_sentence_length(doc: Document) -> list[Violation]:
    out = []
    for where, text in _iter_text(doc):
        for sentence in _SENTENCE_SPLIT.split(text):
            words = sentence.split()
            if len(words) > MAX_SENTENCE_WORDS:
                out.append(Violation(
                    "sentence-length", WARNING, where,
                    f"{len(words)}-word sentence (max {MAX_SENTENCE_WORDS}): "
                    f"{sentence[:70]}…",
                ))
    return out


def rule_typography(doc: Document) -> list[Violation]:
    """Prose blocks must read as finished sentences, not fragments."""
    out = []
    for section in doc.sections:
        if section.style == "cover":
            continue
        for i, block in enumerate(section.blocks):
            if not isinstance(block, (Para, Callout)):
                continue
            text = block.text if isinstance(block, Para) else block.text
            where = f"p{section.number}/{type(block).__name__}[{i}]"
            if not text[:1].isupper() and not text[:1].isdigit() and text[:1] not in "“‘":
                out.append(Violation("typography", ERROR, where,
                                     f"does not start with a capital: {text[:40]!r}"))
            if text.rstrip()[-1:] not in ".!?…”":
                out.append(Violation("typography", ERROR, where,
                                     f"does not end with terminal punctuation: …{text[-40:]!r}"))
            if "  " in text:
                out.append(Violation("typography", WARNING, where, "double space"))
    return out


def rule_scripts_are_speakable(doc: Document) -> list[Violation]:
    """A script is something the buyer says out loud. Enforce that shape."""
    out = []
    for section in doc.sections:
        for i, block in enumerate(section.blocks):
            if not isinstance(block, Script):
                continue
            where = f"p{section.number}/Script[{i}]"
            if len(block.text) > MAX_SCRIPT_CHARS:
                out.append(Violation("script-shape", ERROR, where,
                                     f"{len(block.text)} chars; nobody says this out loud "
                                     f"(max {MAX_SCRIPT_CHARS})"))
            if re.search(r"\bthey\b|\btheir\b|\bthem\b", block.text, re.I) and \
                    section.number in (15, 16, 17):
                out.append(Violation(
                    "script-shape", WARNING, where,
                    "third-person reference inside a line meant to be said to their face",
                ))
    return out


def rule_second_person(doc: Document) -> list[Violation]:
    """The manual talks to the buyer. A page that forgets that reads as generic."""
    out = []
    for section in doc.sections:
        if section.style in ("cover", "cheat"):
            continue
        if section.blocks and all(isinstance(b, TriggerBlock) for b in section.blocks):
            continue   # trigger pages describe them, not the reader
        text = doc.text_of(section)
        if not _SECOND_PERSON.search(text):
            out.append(Violation("second-person", WARNING, f"p{section.number}",
                                 "page never addresses the reader directly"))
    return out


def rule_hedging(doc: Document) -> list[Violation]:
    out = []
    for section in doc.sections:
        hedges = _HEDGES.findall(doc.text_of(section))
        if len(hedges) > MAX_HEDGES_PER_PAGE:
            out.append(Violation("hedging", WARNING, f"p{section.number}",
                                 f"{len(hedges)} hedge words: {hedges}"))
    return out


def rule_no_duplicate_sentences(doc: Document) -> list[Violation]:
    """The same sentence twice reads as a bug unless the page plan intends it."""
    seen: dict[str, int] = {}
    out = []
    for section in doc.sections:
        for sentence in _SENTENCE_SPLIT.split(doc.text_of(section)):
            key = re.sub(r"[^a-z ]", "", sentence.lower()).strip()
            if len(key.split()) < 6:
                continue
            first = seen.get(key)
            if first is None:
                seen[key] = section.number
            elif section.number not in INTENTIONAL_REPEAT_PAGES:
                out.append(Violation(
                    "duplicate-sentence", ERROR, f"p{section.number}",
                    f"repeats a sentence from p{first}: {sentence[:60]}…",
                ))
    return out


def rule_repetition(doc: Document) -> list[Violation]:
    # ".repeat" labels and the cheat sheet are deliberate callbacks: the
    # whole point of p23 is to restate the manual's key lines in one place.
    collisions = [
        c for c in doc.repetition_collisions
        if not any(marker in where for where in (c[1], c[2])
                   for marker in (".repeat", "cheat"))
    ]
    if len(collisions) > MAX_REPETITION_COLLISIONS:
        sample = "; ".join(f"{g!r} ({a} → {b})" for g, a, b in collisions[:4])
        return [Violation("repetition", WARNING, "document",
                          f"{len(collisions)} reused phrases: {sample}")]
    return []


def rule_blend_coherence(doc: Document) -> list[Violation]:
    """If core and secondary contradict, the copy must say so, not assert both."""
    if not doc.blend_conflicts or doc.profile.blend_mode == "pure":
        # A "pure" profile never asserts the secondary's claims in the first
        # place, so there is nothing to reconcile.
        return []
    blend_page = next((s for s in doc.sections if s.number == 6), None)
    if blend_page is None:  # pragma: no cover
        return [Violation("blend-coherence", ERROR, "p6", "blend page missing")]
    text = doc.text_of(blend_page).lower()
    markers = ("do not resolve", "alternate", "internal split", "swing",
               "push-pull", "when you push on one", "hold both")
    if not any(m in text for m in markers):
        return [Violation(
            "blend-coherence", ERROR, "p6",
            f"core and secondary hold conflicting claims "
            f"{[sorted(c) for c in doc.blend_conflicts]} but the copy asserts both "
            "without naming the tension",
        )]
    return []


def rule_section_budget(doc: Document) -> list[Violation]:
    out = []
    for section in doc.sections:
        length = len(doc.text_of(section))
        if length > section.budget:
            out.append(Violation(
                "section-budget", ERROR, f"p{section.number}",
                f"{length} chars over the {section.budget} budget — will overflow the page",
            ))
        elif length < MIN_BODY_CHARS and section.style == "body":
            out.append(Violation(
                "section-budget", WARNING, f"p{section.number}",
                f"only {length} chars of copy; real page fill is verified after "
                "rendering by layout.measure_fill()",
            ))
    return out


def rule_page_fill(doc: Document) -> list[Violation]:
    """Measure real wrapped height per page: catches overflow *before* saving.

    The renderer also refuses to truncate, but by then the caller has already
    committed to an output path. Failing here keeps the contract that a
    QA-passing document always renders.
    """
    from .layout import measure_fill   # imported late: layout is the heavier module

    out = []
    for page, ratio in sorted(measure_fill(doc).items()):
        style = doc.sections[page - 1].style
        if ratio > 1.0:
            out.append(Violation("page-fill", ERROR, f"p{page}",
                                 f"copy needs {ratio:.0%} of the page — it would overflow"))
        elif ratio > 0.98:
            out.append(Violation("page-fill", WARNING, f"p{page}",
                                 f"{ratio:.0%} full; almost no headroom left"))
        elif ratio < MIN_PAGE_FILL and style == "body":
            out.append(Violation("page-fill", WARNING, f"p{page}",
                                 f"copy fills only {ratio:.0%} of the page"))
    return out


def rule_title_fits(doc: Document) -> list[Violation]:
    """A page title that needs truncating reads as a rendering bug."""
    from .layout import title_overflows

    return [
        Violation("title-fits", ERROR, f"p{sec.number}",
                  f"title {sec.title!r} is too wide for the header and would be trimmed")
        for sec in doc.sections
        if sec.style != "cover" and title_overflows(sec.title)
    ]


def rule_unique_titles(doc: Document) -> list[Violation]:
    seen: dict[str, int] = {}
    out = []
    for section in doc.sections:
        key = section.title.lower()
        if key in seen and section.kicker == doc.sections[seen[key] - 1].kicker:
            out.append(Violation("unique-titles", WARNING, f"p{section.number}",
                                 f"same title and kicker as p{seen[key]}"))
        seen.setdefault(key, section.number)
    return out


def rule_degraded_input_flagged(doc: Document) -> list[Violation]:
    """A manual built from unusable scores must never be sold silently."""
    if doc.profile.degraded:
        return [Violation(
            "degraded-input", WARNING, "profile",
            "generated from unusable scores; the buyer is getting a generic manual",
        )]
    return []


RULES: tuple[Callable[[Document], list[Violation]], ...] = (
    rule_no_placeholders,
    rule_no_empty,
    rule_article_agreement,
    rule_banned_language,
    rule_relationship_frame,
    rule_renderable_characters,
    rule_typography,
    rule_scripts_are_speakable,
    rule_no_duplicate_sentences,
    rule_blend_coherence,
    rule_section_budget,
    rule_page_fill,
    rule_title_fits,
    rule_sentence_length,
    rule_second_person,
    rule_hedging,
    rule_repetition,
    rule_unique_titles,
    rule_degraded_input_flagged,
)


def check(doc: Document) -> list[Violation]:
    """Run every rule and return all violations, errors first."""
    violations: list[Violation] = []
    for rule in RULES:
        violations.extend(rule(doc))
    violations.sort(key=lambda v: (v.severity != ERROR, v.rule, v.where))
    return violations


def enforce(doc: Document, *, strict: bool = False) -> list[Violation]:
    """Raise :class:`QAFailure` if the document is not fit to sell.

    Args:
        strict: Treat warnings as errors too. Use this in CI; leave it off
            in production so a stylistic nit never blocks a paid download.

    Returns:
        The non-blocking violations, so the caller can log them.
    """
    violations = check(doc)
    blocking = [v for v in violations if v.severity == ERROR or strict]
    if blocking:
        raise QAFailure(blocking)
    return violations
