"""Input normalisation and the derived profile.

The contract for this module: **anything** can be thrown at
:func:`build_profile` -- a dict from a Stripe webhook, a share-link query
param, a half-filled form, an empty object -- and it either returns a fully
populated, internally consistent :class:`Profile`, or raises
:class:`~.errors.InputError` with a message a human can act on. It never
returns a half-valid object, and it never lets a ``None`` reach the copy
layer.

Every repair it performs is recorded on ``Profile.warnings`` so the caller
can log or alert on silently-degraded output instead of finding out from a
refund request.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .errors import InputError

TYPE_IDS: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 9)

#: Questions on the live quiz. Used to convert raw counts into percentages.
DEFAULT_QUESTION_COUNT = 12

#: Below this share of the total, a secondary type is too weak to blend --
#: the manual speaks about the core type alone rather than inventing a
#: nuance the quiz did not actually measure.
SECONDARY_FLOOR = 0.12

#: If the top two types are within this fraction of each other, the person
#: is genuinely split and the copy says so instead of pretending to a
#: confidence the data does not support.
SPLIT_MARGIN = 0.04

#: Anything at or above this share is a near-total concentration; copy that
#: hedges ("they lean toward...") reads as evasive at that level.
DOMINANCE_CEILING = 0.62

_NAME_MAX = 40
_SAFE_NAME = re.compile(r"[^\w\s'’\-.]", re.UNICODE)


# --------------------------------------------------------------------------
# Relationships
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Relationship:
    """One of the five quiz verticals, with the grammar the copy needs.

    ``subject`` / ``possessive`` / ``object_`` exist so no template ever has
    to hard-code "your mom" -- the same sentence renders correctly for a
    girlfriend or a best friend.
    """

    slug: str
    label: str
    subject: str          # "your mom"
    possessive: str       # "your mom's"
    short: str            # "she", used sparingly; see `pronoun_policy`
    kind: str             # "parent" | "partner" | "peer"
    #: Frames that must never appear for this relationship. Enforced by QA,
    #: not just by author discipline -- see qa.RELATIONSHIP_FORBIDDEN.
    forbidden_frames: tuple[str, ...] = ()


RELATIONSHIPS: dict[str, Relationship] = {
    "mom": Relationship(
        slug="mom", label="Mom", subject="your mom", possessive="your mom's",
        short="she", kind="parent",
        forbidden_frames=("romantic", "dating", "breakup", "sexual"),
    ),
    "dad": Relationship(
        slug="dad", label="Dad", subject="your dad", possessive="your dad's",
        short="he", kind="parent",
        forbidden_frames=("romantic", "dating", "breakup", "sexual"),
    ),
    "boyfriend": Relationship(
        slug="boyfriend", label="Boyfriend", subject="your boyfriend",
        possessive="your boyfriend's", short="he", kind="partner",
        forbidden_frames=("parental", "childhood-authority"),
    ),
    "girlfriend": Relationship(
        slug="girlfriend", label="Girlfriend", subject="your girlfriend",
        possessive="your girlfriend's", short="she", kind="partner",
        forbidden_frames=("parental", "childhood-authority"),
    ),
    "best-friend": Relationship(
        slug="best-friend", label="Best Friend", subject="your best friend",
        possessive="your best friend's", short="they", kind="peer",
        forbidden_frames=("romantic", "dating", "parental", "sexual"),
    ),
}

#: Slugs people actually type or that older share links used.
_RELATIONSHIP_ALIASES = {
    "mother": "mom", "mum": "mom", "mommy": "mom", "ma": "mom",
    "father": "dad", "daddy": "dad", "pa": "dad",
    "bf": "boyfriend", "husband": "boyfriend", "partner": "boyfriend",
    "gf": "girlfriend", "wife": "girlfriend",
    "bestfriend": "best-friend", "best_friend": "best-friend",
    "bff": "best-friend", "friend": "best-friend",
}

DEFAULT_RELATIONSHIP = "best-friend"


def resolve_relationship(value: Any) -> tuple[Relationship, list[str]]:
    """Coerce any relationship-ish value into a real :class:`Relationship`.

    Returns the relationship plus any warnings generated on the way. Falls
    back to the most neutral vertical (best friend) rather than failing --
    a buyer who already paid should get a readable manual even if the slug
    in the webhook was mangled.
    """
    warnings: list[str] = []
    if value is None or (isinstance(value, str) and not value.strip()):
        warnings.append(
            f"No relationship supplied; defaulted to '{DEFAULT_RELATIONSHIP}'."
        )
        return RELATIONSHIPS[DEFAULT_RELATIONSHIP], warnings

    key = str(value).strip().lower().replace(" ", "-").replace("_", "-")
    if key in RELATIONSHIPS:
        return RELATIONSHIPS[key], warnings

    unhyphenated = key.replace("-", "")
    alias = _RELATIONSHIP_ALIASES.get(key) or _RELATIONSHIP_ALIASES.get(unhyphenated)
    if alias:
        return RELATIONSHIPS[alias], warnings

    warnings.append(
        f"Unknown relationship {value!r}; defaulted to '{DEFAULT_RELATIONSHIP}'."
    )
    return RELATIONSHIPS[DEFAULT_RELATIONSHIP], warnings


# --------------------------------------------------------------------------
# Scores
# --------------------------------------------------------------------------

def _coerce_score(raw: Any) -> tuple[float, bool]:
    """Turn anything into a finite, non-negative float. Flags if it repaired."""
    if raw is None or isinstance(raw, bool):
        return 0.0, raw is not None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0, True
    if math.isnan(value) or math.isinf(value):
        return 0.0, True
    if value < 0:
        return 0.0, True
    return value, False


def parse_scores(raw: Any, *, question_count: int = DEFAULT_QUESTION_COUNT
                 ) -> tuple[dict[int, float], list[str]]:
    """Normalise scores from any of the shapes the site produces.

    Accepts the compact share-link string (``"1-2-0-3-1-0-4-0-1"``), a dict
    keyed by int or str, or a 9-item sequence. Missing types become 0 rather
    than raising, and every repair is reported.
    """
    warnings: list[str] = []
    scores: dict[int, float] = {t: 0.0 for t in TYPE_IDS}

    if raw is None:
        return scores, ["No scores supplied."]

    if isinstance(raw, str):
        parts = [p for p in re.split(r"[-,\s]+", raw.strip()) if p != ""]
        if len(parts) != len(TYPE_IDS):
            warnings.append(
                f"Encoded scores had {len(parts)} values, expected {len(TYPE_IDS)}; "
                "missing positions treated as 0."
            )
        raw = {t: (parts[i] if i < len(parts) else 0) for i, t in enumerate(TYPE_IDS)}

    if isinstance(raw, Mapping):
        items: Iterable[tuple[Any, Any]] = raw.items()
    elif isinstance(raw, Sequence):
        if len(raw) != len(TYPE_IDS):
            warnings.append(
                f"Score sequence had {len(raw)} values, expected {len(TYPE_IDS)}; "
                "missing positions treated as 0."
            )
        items = [(t, raw[i] if i < len(raw) else 0) for i, t in enumerate(TYPE_IDS)]
    else:
        raise InputError(f"Scores must be a string, mapping or sequence, got {type(raw).__name__}.")

    repaired = 0
    for key, value in items:
        try:
            type_id = int(str(key).strip())
        except (TypeError, ValueError):
            warnings.append(f"Ignored unrecognised score key {key!r}.")
            continue
        if type_id not in scores:
            warnings.append(f"Ignored out-of-range type id {type_id}.")
            continue
        coerced, was_repaired = _coerce_score(value)
        if was_repaired:
            repaired += 1
        if coerced > question_count:
            warnings.append(
                f"Type {type_id} scored {coerced:g} above the {question_count}-question "
                "maximum; clamped."
            )
            coerced = float(question_count)
        scores[type_id] = coerced

    if repaired:
        warnings.append(f"{repaired} score value(s) were unreadable and treated as 0.")
    return scores, warnings


def _clean_name(raw: Any) -> tuple[str, list[str]]:
    """Sanitise a buyer-supplied subject name for safe, sane rendering."""
    warnings: list[str] = []
    if raw is None:
        return "", warnings
    text = unicodedata.normalize("NFKC", str(raw)).strip()
    text = "".join(ch for ch in text if ch.isprintable())
    stripped = _SAFE_NAME.sub("", text).strip()
    if stripped != text:
        warnings.append("Subject name contained unsupported characters; they were removed.")
    if len(stripped) > _NAME_MAX:
        stripped = stripped[:_NAME_MAX].rstrip()
        warnings.append(f"Subject name truncated to {_NAME_MAX} characters.")
    return stripped, warnings


# --------------------------------------------------------------------------
# Profile
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Profile:
    """A validated, fully-derived quiz result. The only input the copy sees.

    Every field is non-optional and already in its final form, so no
    downstream module needs a ``None`` check or a fallback branch.
    """

    core: int
    secondary: int
    tertiary: int
    wing: int
    scores: dict[int, float]
    shares: dict[int, float]           # 0.0-1.0, sums to 1.0 (or all-equal if no data)
    question_count: int
    relationship: Relationship
    subject_name: str                  # "" when the buyer did not give one
    blend_mode: str                    # "pure" | "blended" | "split"
    confidence: str                    # "low" | "moderate" | "high"
    seed: int
    warnings: tuple[str, ...] = ()
    degraded: bool = False             # True when scores were unusable

    # -- convenience -------------------------------------------------------

    @property
    def core_share(self) -> float:
        return self.shares[self.core]

    @property
    def secondary_share(self) -> float:
        return self.shares[self.secondary]

    def percent(self, type_id: int) -> int:
        """Display percentage. Rounds, but never to a misleading 0 or 100."""
        pct = self.shares.get(type_id, 0.0) * 100
        if 0 < pct < 1:
            return 1
        if 99 < pct < 100:
            return 99
        return int(round(pct))

    @property
    def subject_ref(self) -> str:
        """What the copy calls them: their name if given, else the relation."""
        return self.subject_name or self.relationship.subject

    @property
    def subject_possessive(self) -> str:
        if not self.subject_name:
            return self.relationship.possessive
        return f"{self.subject_name}'s" if not self.subject_name.endswith("s") else f"{self.subject_name}'"

    def ranked(self) -> list[tuple[int, float]]:
        """Types ordered by score desc, then by type id asc for stability."""
        return sorted(self.shares.items(), key=lambda kv: (-kv[1], kv[0]))


def _wing_of(core: int, shares: Mapping[int, float]) -> int:
    """The adjacent type the person leans into, per standard Enneagram wings.

    Types sit on a circle, so 9's neighbours are 8 and 1. Ties resolve to the
    lower type id so the same result always produces the same manual.
    """
    left = 9 if core == 1 else core - 1
    right = 1 if core == 9 else core + 1
    left_share, right_share = shares.get(left, 0.0), shares.get(right, 0.0)
    if right_share > left_share:
        return right
    if left_share > right_share:
        return left
    return min(left, right)


def _seed_for(core: int, secondary: int, relationship_slug: str,
              shares: Mapping[int, float]) -> int:
    """Stable seed so re-running the generator yields a byte-identical manual.

    Two buyers with the same result get the same book (that is fine and
    intended); the same buyer re-downloading never gets a different one,
    which would look broken.
    """
    material = "|".join([
        str(core), str(secondary), relationship_slug,
        ",".join(f"{t}:{shares.get(t, 0.0):.4f}" for t in TYPE_IDS),
    ])
    return int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")


def build_profile(
    result: Mapping[str, Any] | None = None,
    *,
    scores: Any = None,
    relationship: Any = None,
    subject_name: Any = None,
    question_count: int | None = None,
    allow_unscored: bool = False,
) -> Profile:
    """Normalise a raw quiz result into a :class:`Profile`.

    Args:
        result: A mapping as it arrives from the web app. Recognised keys:
            ``scores``/``s``, ``relationship``, ``name``/``subject_name``,
            ``question_count``.
        allow_unscored: When the scores are entirely unusable (absent, all
            zero, non-numeric), raise :class:`InputError` by default. Set
            this to fall back to an evenly-weighted profile instead -- only
            appropriate when a paid download must not hard-fail.

    Raises:
        InputError: if the scores are unusable and ``allow_unscored`` is False.
    """
    data: Mapping[str, Any] = result or {}
    warnings: list[str] = []

    raw_scores = scores if scores is not None else (
        data.get("scores") if data.get("scores") is not None else data.get("s")
    )
    raw_relationship = relationship if relationship is not None else data.get("relationship")
    raw_name = subject_name if subject_name is not None else (
        data.get("subject_name") if data.get("subject_name") is not None else data.get("name")
    )

    qc_raw = question_count if question_count is not None else data.get("question_count")
    qc = DEFAULT_QUESTION_COUNT
    if qc_raw is not None:
        try:
            qc = int(qc_raw)
        except (TypeError, ValueError):
            warnings.append(f"Unreadable question_count {qc_raw!r}; used {DEFAULT_QUESTION_COUNT}.")
        else:
            if qc <= 0:
                warnings.append(f"question_count {qc} is not positive; used {DEFAULT_QUESTION_COUNT}.")
                qc = DEFAULT_QUESTION_COUNT

    rel, rel_warnings = resolve_relationship(raw_relationship)
    warnings.extend(rel_warnings)

    parsed, score_warnings = parse_scores(raw_scores, question_count=qc)
    warnings.extend(score_warnings)

    name, name_warnings = _clean_name(raw_name)
    warnings.extend(name_warnings)

    total = sum(parsed.values())
    degraded = False

    if total <= 0:
        if not allow_unscored:
            raise InputError(
                "Quiz result contains no usable scores. Pass allow_unscored=True to "
                "generate a generic manual anyway."
            )
        degraded = True
        warnings.append(
            "No usable scores: generated an evenly-weighted manual. This buyer's "
            "result should be investigated."
        )
        shares = {t: 1.0 / len(TYPE_IDS) for t in TYPE_IDS}
    else:
        shares = {t: parsed[t] / total for t in TYPE_IDS}

    order = sorted(TYPE_IDS, key=lambda t: (-shares[t], t))
    core, secondary, tertiary = order[0], order[1], order[2]

    if degraded:
        # An even split has no real winner; anchor on 9 (the least
        # opinionated archetype) rather than letting sort order imply
        # a precision the data does not have.
        core, secondary, tertiary = 9, 6, 3

    ties = [t for t in TYPE_IDS if t != core and abs(shares[t] - shares[core]) < 1e-9]
    if ties and not degraded:
        warnings.append(
            f"Type {core} tied with {', '.join(map(str, ties))}; resolved to the "
            "lowest type id for reproducibility."
        )

    gap = shares[core] - shares[secondary]
    if degraded:
        blend_mode = "pure"
    elif gap <= SPLIT_MARGIN:
        blend_mode = "split"
    elif shares[secondary] < SECONDARY_FLOOR:
        blend_mode = "pure"
    else:
        blend_mode = "blended"

    if degraded:
        confidence = "low"
    elif shares[core] >= DOMINANCE_CEILING and gap > SPLIT_MARGIN:
        confidence = "high"
    elif gap <= SPLIT_MARGIN or shares[core] < 0.22:
        confidence = "low"
    else:
        confidence = "moderate"

    return Profile(
        core=core,
        secondary=secondary,
        tertiary=tertiary,
        wing=_wing_of(core, shares),
        scores=dict(parsed),
        shares=shares,
        question_count=qc,
        relationship=rel,
        subject_name=name,
        blend_mode=blend_mode,
        confidence=confidence,
        seed=_seed_for(core, secondary, rel.slug, shares),
        warnings=tuple(warnings),
        degraded=degraded,
    )
