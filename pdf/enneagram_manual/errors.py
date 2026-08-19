"""Exception hierarchy.

Every failure mode in this package is one of these. The CLI maps them to
distinct exit codes so a caller (a Stripe webhook handler, a cron job, a
retry wrapper) can tell "the buyer sent garbage" apart from "our copy bank
has a hole in it" without parsing strings.
"""

from __future__ import annotations


class ManualError(Exception):
    """Base class for every error this package raises."""


class InputError(ManualError):
    """The supplied quiz result could not be coerced into a valid profile.

    Raised only for input that is unusable even after defaulting. Anything
    recoverable (missing scores, out-of-range values, unknown relationship)
    is repaired and recorded on ``Profile.warnings`` instead.
    """


class ContentError(ManualError):
    """The copy bank is missing or malformed for a requested combination.

    This is always a bug in our content, never the buyer's fault.
    """


class TemplateError(ManualError):
    """A template referenced a variable that does not exist, or vice versa."""


class QAFailure(ManualError):
    """The assembled copy failed a pre-save quality gate.

    Carries the structured list of violations so callers can log them.
    """

    def __init__(self, violations):
        self.violations = list(violations)
        detail = "\n".join(f"  - [{v.severity}] {v.rule} @ {v.where}: {v.detail}" for v in self.violations)
        super().__init__(f"{len(self.violations)} QA violation(s) blocked the save:\n{detail}")


class LayoutError(ManualError):
    """The rendered document did not match its structural contract."""
