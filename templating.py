"""A deliberately unforgiving template engine.

``str.format`` fails silently in the two ways that matter for a product you
charge money for: a key you forgot to pass raises only at the moment of
rendering (so it ships if that branch is rare), and a stray brace prints
raw to the customer. This module removes both possibilities:

* :func:`render` raises on a missing key, an unexpected key, an empty value,
  and on *any* placeholder-looking residue left in the output.
* :func:`audit_templates` runs the same check **statically** over the whole
  copy bank at import time, so a typo in a rarely-hit Type 5 fragment fails
  the test suite instead of a buyer's PDF.

Typography is normalised here too, for the same reason: it is the last place
every string passes through before it becomes a page.
"""

from __future__ import annotations

import re
import string
from typing import Any, Iterable, Mapping

from .errors import TemplateError

_FORMATTER = string.Formatter()

#: Anything in the rendered output matching one of these is, by definition,
#: a bug that reached the page. Checked after substitution, so it catches
#: unbalanced braces and foreign template syntax pasted in from elsewhere.
_RESIDUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("curly placeholder", re.compile(r"\{[^{}]*\}")),
    ("unbalanced brace", re.compile(r"[{}]")),
    ("double-bracket tag", re.compile(r"\[\[.*?\]\]")),
    ("angle tag", re.compile(r"<<.*?>>")),
    ("percent format", re.compile(r"%\((?:\w+)\)?[sdif]|(?<!\d)%[sd](?!\w)")),
    ("dollar template", re.compile(r"\$\{?[A-Za-z_]\w*\}?")),
    ("author marker", re.compile(r"\b(TODO|FIXME|TBD|XXX|LOREM|PLACEHOLDER)\b", re.I)),
    ("leaked null", re.compile(r"\b(None|NaN|nan|undefined|null|\[object Object\])\b")),
)

_TYPOGRAPHY: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"[ \t]*\n[ \t]*"), " "),        # copy is authored as prose, not lines
    (re.compile(r"[ \t]{2,}"), " "),
    (re.compile(r"\s+([,.;:!?])"), r"\1"),       # no space before punctuation
    (re.compile(r"([,.;:!?])(?=[A-Za-z])"), r"\1 "),
    (re.compile(r"\s*--\s*"), " — "),        # spaced em dash, house style
    (re.compile(r"\.{3,}"), "…"),
    (re.compile(r"\ba ([aeiouAEIOU])"), r"an \1"),
)

_APOSTROPHE = re.compile(r"(?<=\w)'(?=\w)")
_OPEN_QUOTE = re.compile(r'(?<![\w"])"(?=\S)')
_CLOSE_QUOTE = re.compile(r'(?<=\S)"')

# Substituted values are noun phrases ("your mom", "Dana") that are written
# lowercase because they usually appear mid-sentence. When one lands at the
# start of a sentence the result is "your mom does not need you to grovel",
# which looks broken. Rather than asking every author to remember a
# {Subject} variant, fix it mechanically at the last step.
_SENTENCE_START = re.compile(r"(^|(?<=[.!?…]\s)|(?<=[“‘]))\s*([a-z])")


def _capitalise_sentences(text: str) -> str:
    return _SENTENCE_START.sub(lambda m: m.group(0)[:-1] + m.group(2).upper(), text)


def _typeset(text: str) -> str:
    """Normalise whitespace, punctuation and casing to print-quality output."""
    for pattern, replacement in _TYPOGRAPHY:
        text = pattern.sub(replacement, text)
    text = _APOSTROPHE.sub("’", text)
    text = _OPEN_QUOTE.sub("“", text)
    text = _CLOSE_QUOTE.sub("”", text)
    return _capitalise_sentences(text.strip())


def field_names(template: str) -> set[str]:
    """Every top-level variable a template references.

    Raises:
        TemplateError: if the template itself is malformed.
    """
    try:
        parsed = list(_FORMATTER.parse(template))
    except ValueError as exc:
        raise TemplateError(f"Malformed template {template[:60]!r}: {exc}") from exc
    names: set[str] = set()
    for _literal, field, _spec, _conv in parsed:
        if field is None:
            continue
        if field == "":
            raise TemplateError(
                f"Positional placeholder '{{}}' in {template[:60]!r}; use a named one."
            )
        names.add(field.split(".")[0].split("[")[0])
    return names


def render(template: str, context: Mapping[str, Any], *, where: str = "<template>",
           allow_unused: bool = True) -> str:
    """Substitute ``context`` into ``template`` and guarantee clean output.

    Args:
        where: A human-readable location used in error messages, e.g.
            ``"type-3.triggers[2].why"``. Worth passing -- it is the
            difference between a 5-second fix and a grep.
        allow_unused: Context normally carries the full profile vocabulary,
            most of which any single template ignores. Set False for
            fragments where an unused key signals a mistake.

    Raises:
        TemplateError: on a missing key, an empty substitution, leftover
            placeholder syntax, or (when ``allow_unused`` is False) an
            unused context key.
    """
    if not isinstance(template, str):
        raise TemplateError(f"{where}: expected a string, got {type(template).__name__}.")

    required = field_names(template)
    missing = sorted(required - set(context))
    if missing:
        raise TemplateError(
            f"{where}: template needs {missing} which the context does not provide. "
            f"Available: {sorted(context)[:12]}{'…' if len(context) > 12 else ''}"
        )

    empty = sorted(
        name for name in required
        if context[name] is None or (isinstance(context[name], str) and not context[name].strip())
    )
    if empty:
        raise TemplateError(f"{where}: context values {empty} are empty; would print a hole.")

    if not allow_unused:
        unused = sorted(set(context) - required)
        if unused:
            raise TemplateError(f"{where}: context keys {unused} are unused.")

    try:
        rendered = _FORMATTER.vformat(template, (), dict(context))
    except (KeyError, IndexError, AttributeError) as exc:
        raise TemplateError(f"{where}: substitution failed ({exc!r}).") from exc

    rendered = _typeset(rendered)
    assert_clean(rendered, where=where)
    return rendered


def assert_clean(text: str, *, where: str = "<text>") -> None:
    """Fail if ``text`` contains anything that looks like unrendered markup.

    Split out from :func:`render` so it can also be run over copy that was
    assembled by concatenation rather than substitution.
    """
    for label, pattern in _RESIDUE_PATTERNS:
        match = pattern.search(text)
        if match:
            snippet = text[max(0, match.start() - 30):match.end() + 30]
            raise TemplateError(
                f"{where}: {label} {match.group(0)!r} survived rendering — …{snippet}…"
            )


def audit_templates(templates: Iterable[tuple[str, str]], vocabulary: set[str]) -> list[str]:
    """Statically check every template in the copy bank against the vocabulary.

    Returns a list of human-readable problems. An empty list means no
    template in the bank can reference a variable that will not exist at
    render time -- regardless of which of the 45 type/relationship
    combinations a buyer lands on.
    """
    problems: list[str] = []
    for where, template in templates:
        if not isinstance(template, str):
            problems.append(f"{where}: not a string ({type(template).__name__}).")
            continue
        if not template.strip():
            problems.append(f"{where}: empty template.")
            continue
        try:
            names = field_names(template)
        except TemplateError as exc:
            problems.append(str(exc))
            continue
        unknown = sorted(names - vocabulary)
        if unknown:
            problems.append(f"{where}: references unknown variable(s) {unknown}.")
        # Catch literal residue authored *into* the copy (not from substitution).
        stripped = _FORMATTER.vformat(
            template, (), {name: "x" for name in names}
        ) if names else template
        for label, pattern in _RESIDUE_PATTERNS:
            if label in ("curly placeholder", "unbalanced brace"):
                continue  # legitimately present pre-render
            match = pattern.search(stripped)
            if match:
                problems.append(f"{where}: contains {label} {match.group(0)!r}.")
    return problems
