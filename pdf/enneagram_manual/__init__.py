"""Enneagram Operator's Manual generator.

Turns a quiz result into a 24-page, print-quality PDF that has been checked
for unresolved placeholders, internal contradiction, repetition, tone and
overflow *before* it is written to disk.

Typical use::

    from enneagram_manual import generate

    report = generate(
        {"s": "1-2-6-3-1-0-4-0-1", "relationship": "mom", "name": "Diane"},
        out_path="manuals/diane.pdf",
    )
    print(report.path, report.profile.core, len(report.violations))

The copy bank is validated at import time -- a malformed template or a
missing archetype field raises here, not in front of a customer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .blending import Blender
from .content import ARCHETYPES, LENSES, VOCABULARY, iter_templates, validate_content
from .document import Document, build_document
from .errors import (
    ContentError, InputError, LayoutError, ManualError, QAFailure, TemplateError,
)
from .layout import measure_fill, render_pdf
from .models import Profile, build_profile
from .qa import Violation, check, enforce
from .templating import audit_templates

__version__ = "2.0.0"

__all__ = [
    "generate", "GenerationReport", "build_profile", "build_document", "render_pdf",
    "check", "enforce", "Profile", "Document", "Violation",
    "ManualError", "InputError", "ContentError", "TemplateError", "QAFailure",
    "LayoutError", "self_test",
]


def _validate_bank_at_import() -> None:
    """Structural + static template validation of the copy bank.

    Deliberately runs on import. The cost is a few milliseconds; the benefit
    is that no deployment can start serving a build whose copy bank has a
    typo in a rarely-hit Type 5 fragment.
    """
    validate_content()
    problems = audit_templates(iter_templates(), VOCABULARY)
    if problems:
        raise ContentError(
            "Copy bank failed template audit:\n" + "\n".join(f"  - {p}" for p in problems)
        )


_validate_bank_at_import()


@dataclass(frozen=True)
class GenerationReport:
    """What happened, in a form a caller can log or alert on."""

    path: Path
    profile: Profile
    document: Document
    violations: tuple[Violation, ...]
    #: page number -> fraction of the frame the copy occupies (see
    #: :func:`layout.measure_fill`). Anything under ~0.45 will print looking
    #: half-empty; anything at 1.0 was one line away from overflowing.
    fill: dict[int, float] = None

    @property
    def warnings(self) -> tuple[str, ...]:
        return self.profile.warnings

    @property
    def ok(self) -> bool:
        return not any(v.severity == "error" for v in self.violations)


def generate(
    result: Mapping[str, Any] | None = None,
    *,
    out_path: str | Path,
    scores: Any = None,
    relationship: Any = None,
    subject_name: Any = None,
    question_count: int | None = None,
    allow_unscored: bool = False,
    strict: bool = False,
) -> GenerationReport:
    """Build and save one manual.

    Args:
        result: The raw quiz result mapping (``s``/``scores``, ``relationship``,
            ``name``). Individual keyword arguments override it.
        allow_unscored: Produce a generic manual instead of raising when the
            scores are unusable. Appropriate for a paid download that must
            not hard-fail; the report will carry a warning.
        strict: Fail on warnings as well as errors. Use in CI.

    Raises:
        InputError: unusable input.
        QAFailure: the assembled copy did not pass the quality gate. Nothing
            is written to disk in this case.
        LayoutError: the copy did not fit the page plan.
    """
    profile = build_profile(
        result, scores=scores, relationship=relationship, subject_name=subject_name,
        question_count=question_count, allow_unscored=allow_unscored,
    )
    document = build_document(profile)
    # enforce() runs every rule, including the measured page-fill check, and
    # raises before a single byte is written.
    violations = list(enforce(document, strict=strict))
    fill = measure_fill(document)
    path = render_pdf(document, out_path)
    return GenerationReport(
        path=path, profile=profile, document=document,
        violations=tuple(violations), fill=fill,
    )


def self_test(*, strict: bool = True) -> list[str]:
    """Build every type x relationship combination in memory and QA it.

    Returns a list of failure descriptions -- empty means all 45 combinations
    produce a sellable manual. Renders nothing, so it is fast enough to run
    on every deploy.
    """
    failures: list[str] = []
    for slug in LENSES:
        for type_id in ARCHETYPES:
            scores = {t: 1 for t in ARCHETYPES}
            scores[type_id] = 7
            scores[(type_id % 9) + 1] = 3
            label = f"{slug}/type-{type_id}"
            try:
                profile = build_profile(scores=scores, relationship=slug)
                doc = build_document(profile)
                enforce(doc, strict=strict)
            except ManualError as exc:
                failures.append(f"{label}: {exc}")
    return failures
