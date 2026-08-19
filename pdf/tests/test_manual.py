"""Test suite.

Run with ``pytest -q`` from the project root, or ``python tests/test_manual.py``
if pytest is not installed.

The suite is organised around the four guarantees the generator makes:

1. Nothing broken or raw ever prints (templating + QA).
2. The blend is coherent for every core/secondary pairing.
3. Bad input degrades predictably instead of crashing or lying.
4. The output is exactly 24 pages, with nothing truncated.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enneagram_manual import (  # noqa: E402
    InputError, QAFailure, __version__, build_document, build_profile, check,
    generate, self_test,
)
from enneagram_manual.blending import Blender, RepetitionLedger  # noqa: E402
from enneagram_manual.content import (  # noqa: E402
    ARCHETYPES, LENSES, VOCABULARY, iter_templates, validate_content,
)
from enneagram_manual.document import PAGE_COUNT, Script  # noqa: E402
from enneagram_manual.errors import TemplateError  # noqa: E402
from enneagram_manual.layout import measure_fill, render_pdf  # noqa: E402
from enneagram_manual.models import (  # noqa: E402
    DEFAULT_RELATIONSHIP, RELATIONSHIPS, parse_scores, resolve_relationship,
)
from enneagram_manual.qa import ERROR, enforce  # noqa: E402
from enneagram_manual.templating import assert_clean, field_names, render  # noqa: E402

ALL_TYPES = sorted(ARCHETYPES)
ALL_SLUGS = sorted(LENSES)


def scores_for(core: int, secondary: int | None = None, *, core_weight: int = 7,
               secondary_weight: int = 3) -> dict[int, int]:
    scores = {t: 1 for t in ALL_TYPES}
    scores[core] = core_weight
    if secondary is not None:
        scores[secondary] = secondary_weight
    return scores


# ==========================================================================
# 1. Templating: nothing raw can print
# ==========================================================================

class TestTemplating:
    def test_missing_key_raises_rather_than_printing_a_hole(self):
        with pytest.raises(TemplateError, match="does not provide"):
            render("Hello {missing}", {"subject": "your mom"}, where="t")

    def test_empty_value_raises(self):
        with pytest.raises(TemplateError, match="would print a hole"):
            render("Hello {subject}", {"subject": "   "}, where="t")

    def test_positional_placeholder_rejected(self):
        with pytest.raises(TemplateError, match="use a named one"):
            field_names("Hello {}")

    @pytest.mark.parametrize("bad", [
        "Value: {leftover}", "Tag [[name]]", "Tag <<name>>", "TODO: write this",
        "Result: None", "Score: undefined", "Hi %s", "Path ${HOME}",
    ])
    def test_residue_detected(self, bad):
        with pytest.raises(TemplateError):
            assert_clean(bad, where="t")

    def test_typography_is_normalised(self):
        out = render("A  b -- c...  don't", {}, where="t")
        assert "  " not in out
        assert " — " in out, "em dashes are spaced, house style"
        assert "…" in out
        # A substitution landing after a sentence break gets capitalised.
        assert "Don’t" in out

    def test_lowercase_substitution_at_sentence_start_is_capitalised(self):
        # The bug this prevents: "your mom does not need you to grovel."
        out = render("{subject} does not need this. {subject} needs that.",
                     {"subject": "your mom"}, where="t")
        assert out.startswith("Your mom")
        assert ". Your mom needs" in out

    def test_whole_copy_bank_passes_static_audit(self):
        from enneagram_manual.templating import audit_templates
        assert audit_templates(iter_templates(), VOCABULARY) == []

    def test_copy_bank_is_structurally_complete(self):
        validate_content()  # raises ContentError if not


# ==========================================================================
# 2. Blending: coherent for every pairing
# ==========================================================================

class TestBlending:
    @pytest.mark.parametrize("core", ALL_TYPES)
    @pytest.mark.parametrize("secondary", ALL_TYPES)
    def test_every_core_secondary_pairing_builds_and_passes_qa(self, core, secondary):
        if core == secondary:
            pytest.skip("core and secondary are always distinct by construction")
        profile = build_profile(scores=scores_for(core, secondary), relationship="mom")
        doc = build_document(profile)
        assert enforce(doc, strict=True) == []

    def test_conflicting_claims_produce_a_tension_paragraph(self):
        # Type 5 (needs-space, withholds) under Type 2 (needs-contact,
        # over-discloses) is the canonical contradiction.
        profile = build_profile(scores=scores_for(5, 2, core_weight=6, secondary_weight=4),
                                relationship="boyfriend")
        blender = Blender(profile)
        assert blender.conflicts(), "expected a claim conflict for 5/2"
        doc = build_document(profile)
        blend_text = doc.text_of(doc.sections[5]).lower()
        assert any(m in blend_text for m in
                   ("do not resolve", "alternate", "internal split", "swing", "hold both"))

    def test_weak_secondary_is_not_described_as_a_driver(self):
        profile = build_profile(scores={**{t: 0 for t in ALL_TYPES}, 3: 11, 4: 1},
                                relationship="mom")
        assert profile.blend_mode == "pure"
        blend_text = build_document(profile).text_of(build_document(profile).sections[5])
        assert "footnote" in blend_text.lower() or "background" in blend_text.lower()

    def test_near_tie_is_reported_as_a_split(self):
        profile = build_profile(scores={**{t: 0 for t in ALL_TYPES}, 2: 6, 7: 6},
                                relationship="best-friend")
        assert profile.blend_mode == "split"
        assert profile.confidence == "low"

    def test_output_is_deterministic(self):
        args = dict(scores=scores_for(7, 8), relationship="dad", subject_name="Sam")
        a = build_document(build_profile(**args)).all_text
        b = build_document(build_profile(**args)).all_text
        assert a == b

    def test_repetition_ledger_detects_reuse(self):
        ledger = RepetitionLedger()
        ledger.add("a permanent internal audit running quietly underneath", "first")
        assert ledger.would_collide("the permanent internal audit never stops")
        assert not ledger.would_collide("something else entirely, unrelated wording here")


# ==========================================================================
# 3. Input handling: graceful degradation, no lying
# ==========================================================================

class TestInput:
    @pytest.mark.parametrize("raw,expected_slug", [
        ("mom", "mom"), ("MOM", "mom"), ("mother", "mom"), (" Best-Friend ", "best-friend"),
        ("best_friend", "best-friend"), ("bff", "best-friend"), ("wife", "girlfriend"),
        ("gf", "girlfriend"), ("husband", "boyfriend"),
    ])
    def test_relationship_aliases_resolve(self, raw, expected_slug):
        rel, _ = resolve_relationship(raw)
        assert rel.slug == expected_slug

    @pytest.mark.parametrize("raw", [None, "", "   ", "cousin", 42, object()])
    def test_unknown_relationship_defaults_with_a_warning(self, raw):
        rel, warnings = resolve_relationship(raw)
        assert rel.slug == DEFAULT_RELATIONSHIP
        assert warnings, "a silent default is worse than a loud one"

    def test_share_link_string_parses(self):
        scores, warnings = parse_scores("1-2-0-3-1-0-4-0-1")
        assert scores[4] == 3 and scores[7] == 4
        assert warnings == []

    @pytest.mark.parametrize("raw", ["1-2-3", "1-2-3-4-5-6-7-8-9-10-11", "", "a-b-c-d-e-f-g-h-i"])
    def test_malformed_score_strings_do_not_crash(self, raw):
        scores, warnings = parse_scores(raw)
        assert set(scores) == set(ALL_TYPES)
        assert all(isinstance(v, float) and v >= 0 for v in scores.values())
        assert warnings

    @pytest.mark.parametrize("value", [-5, float("nan"), float("inf"), "seven", None, [1]])
    def test_hostile_score_values_are_clamped_to_zero(self, value):
        scores, _ = parse_scores({3: value})
        assert scores[3] == 0.0

    def test_scores_above_the_question_count_are_clamped(self):
        scores, warnings = parse_scores({1: 900}, question_count=12)
        assert scores[1] == 12
        assert any("clamped" in w for w in warnings)

    def test_no_scores_raises_by_default(self):
        with pytest.raises(InputError, match="no usable scores"):
            build_profile({"relationship": "mom"})

    def test_no_scores_degrades_when_explicitly_allowed(self):
        profile = build_profile({"relationship": "mom"}, allow_unscored=True)
        assert profile.degraded and profile.confidence == "low"
        assert any("investigated" in w for w in profile.warnings)
        # And the QA gate flags it so it is never sold silently.
        violations = check(build_document(profile))
        assert any(v.rule == "degraded-input" for v in violations)

    def test_extreme_concentration_reads_as_high_confidence(self):
        profile = build_profile(scores={**{t: 0 for t in ALL_TYPES}, 8: 12},
                                relationship="dad")
        assert profile.percent(8) == 100
        assert profile.confidence == "high" and profile.blend_mode == "pure"

    def test_percentages_never_round_to_a_misleading_zero(self):
        profile = build_profile(scores={**{t: 0 for t in ALL_TYPES}, 1: 999, 2: 1},
                                relationship="mom", question_count=1000)
        assert profile.percent(2) == 1, "a real but tiny share must not print as 0%"

    def test_ties_break_deterministically_and_are_reported(self):
        a = build_profile(scores={t: 4 for t in ALL_TYPES}, relationship="mom")
        b = build_profile(scores={t: 4 for t in ALL_TYPES}, relationship="mom")
        assert a.core == b.core == 1
        assert any("tied" in w for w in a.warnings)

    @pytest.mark.parametrize("name,expected", [
        ("  Diane  ", "Diane"),
        ("D<script>", "Dscript"),
        ("A" * 100, "A" * 40),
        ("", ""),
        (None, ""),
    ])
    def test_names_are_sanitised(self, name, expected):
        profile = build_profile(scores=scores_for(1), relationship="mom", subject_name=name)
        assert profile.subject_name == expected

    def test_unnamed_subject_falls_back_to_the_relationship(self):
        profile = build_profile(scores=scores_for(1), relationship="mom")
        assert profile.subject_ref == "your mom"
        assert profile.subject_possessive == "your mom’s" or \
               profile.subject_possessive == "your mom's"

    def test_possessive_handles_a_trailing_s(self):
        profile = build_profile(scores=scores_for(1), relationship="mom", subject_name="Chris")
        assert profile.subject_possessive == "Chris'"

    def test_bad_question_count_falls_back(self):
        profile = build_profile(scores=scores_for(1), relationship="mom", question_count=0)
        assert profile.question_count == 12
        assert any("not positive" in w for w in profile.warnings)


# ==========================================================================
# 4. QA gate and document structure
# ==========================================================================

class TestQualityGate:
    def test_all_45_combinations_pass_strict_qa(self):
        assert self_test(strict=True) == []

    def test_document_is_exactly_24_pages(self):
        doc = build_document(build_profile(scores=scores_for(4, 5), relationship="mom"))
        assert len(doc.sections) == PAGE_COUNT
        assert [s.number for s in doc.sections] == list(range(1, PAGE_COUNT + 1))

    def test_parent_manuals_never_use_romantic_framing(self):
        for slug in ("mom", "dad"):
            for type_id in ALL_TYPES:
                doc = build_document(build_profile(scores=scores_for(type_id), relationship=slug))
                violations = [v for v in check(doc) if v.rule == "relationship-frame"]
                assert violations == [], f"{slug}/{type_id}: {violations}"

    def test_qa_failure_blocks_the_save_and_writes_nothing(self, tmp_path):
        doc = build_document(build_profile(scores=scores_for(1), relationship="mom"))
        broken = doc.sections[3].blocks[1].__class__("They have a personality disorder.")
        sections = list(doc.sections)
        sections[3] = doc.sections[3].__class__(
            number=4, kicker="k", title="t", blocks=(broken,), budget=2000)
        doc = doc.__class__(profile=doc.profile, sections=tuple(sections),
                            blend_conflicts=(), repetition_collisions=())
        target = tmp_path / "should-not-exist.pdf"
        with pytest.raises(QAFailure):
            enforce(doc)
        assert not target.exists()

    def test_scripts_stay_short_enough_to_say_out_loud(self):
        for slug in ALL_SLUGS:
            for type_id in ALL_TYPES:
                doc = build_document(build_profile(scores=scores_for(type_id), relationship=slug))
                for section in doc.sections:
                    for block in section.blocks:
                        if isinstance(block, Script):
                            assert len(block.text) <= 240

    def test_titles_all_fit_the_header(self):
        from enneagram_manual.layout import fit_title, title_overflows
        for slug in ALL_SLUGS:
            for type_id in ALL_TYPES:
                doc = build_document(build_profile(scores=scores_for(type_id), relationship=slug))
                for section in doc.sections:
                    if section.style != "cover":
                        assert not title_overflows(section.title), \
                            f"{slug}/{type_id} p{section.number}: {section.title!r}"

    def test_overlong_title_trims_at_a_word_boundary(self):
        from enneagram_manual.layout import fit_title
        trimmed = fit_title("Running the conversation you have been avoiding for months")
        assert trimmed.endswith("…")
        assert not trimmed.rstrip("…").endswith(" ")
        # never mid-word
        assert all(w.isalpha() or not w.isalnum()
                   for w in trimmed.rstrip("…").split()[-1:])

    def test_doubled_article_is_caught(self):
        from enneagram_manual.qa import rule_article_agreement
        doc = build_document(build_profile(scores=scores_for(3, 7), relationship="mom"))
        Para = doc.sections[3].blocks[1].__class__
        broken = doc.sections[3].__class__(
            number=4, kicker="k", title="t",
            blocks=(Para("You are dealing with the The Frontrunner here."),))
        doc = doc.__class__(profile=doc.profile,
                            sections=tuple([broken] + list(doc.sections[1:])),
                            blend_conflicts=(), repetition_collisions=())
        assert any(v.rule == "article-agreement" for v in rule_article_agreement(doc))

    def test_no_page_is_visually_underfilled(self):
        doc = build_document(build_profile(scores=scores_for(3, 7), relationship="mom"))
        fill = measure_fill(doc)
        assert len(fill) == PAGE_COUNT
        assert all(0.0 < v <= 1.0 for v in fill.values())
        thin = {p: v for p, v in fill.items() if v < 0.35}
        assert not thin, f"pages that will print looking empty: {thin}"


# ==========================================================================
# 5. Rendering
# ==========================================================================

class TestRendering:
    def test_pdf_has_24_pages_and_no_truncation(self, tmp_path):
        report = generate(scores=scores_for(6, 5), relationship="girlfriend",
                          subject_name="Ren", out_path=tmp_path / "m.pdf")
        assert report.path.exists() and report.path.stat().st_size > 10_000
        assert _page_count(report.path) == PAGE_COUNT
        assert report.ok

    def test_regenerating_produces_an_identical_file(self, tmp_path):
        args = dict(scores=scores_for(2, 1), relationship="dad")
        a = generate(**args, out_path=tmp_path / "a.pdf").path.read_bytes()
        b = generate(**args, out_path=tmp_path / "b.pdf").path.read_bytes()
        assert a == b, "re-downloads must be byte-identical"

    def test_output_directory_is_created(self, tmp_path):
        target = tmp_path / "deep" / "nested" / "m.pdf"
        generate(scores=scores_for(9), relationship="mom", out_path=target)
        assert target.exists()

    @pytest.mark.parametrize("slug", ALL_SLUGS)
    def test_one_render_per_relationship(self, slug, tmp_path):
        report = generate(scores=scores_for(4, 3), relationship=slug,
                          out_path=tmp_path / f"{slug}.pdf")
        assert _page_count(report.path) == PAGE_COUNT


# ==========================================================================
# 6. CLI
# ==========================================================================

class TestCLI:
    def _run(self, *args, cwd):
        return subprocess.run(
            [sys.executable, "-m", "enneagram_manual", *args],
            cwd=str(Path(__file__).resolve().parents[1]),
            capture_output=True, text=True,
        )

    def test_self_test_exits_zero(self, tmp_path):
        result = self._run("--self-test", "--strict", cwd=tmp_path)
        assert result.returncode == 0, result.stderr

    def test_bad_input_exits_2(self, tmp_path):
        result = self._run("--scores", "0-0-0-0-0-0-0-0-0", "--relationship", "mom",
                           "-o", str(tmp_path / "x.pdf"), cwd=tmp_path)
        assert result.returncode == 2
        assert "bad input" in result.stderr

    def test_happy_path_exits_zero_and_writes(self, tmp_path):
        out = tmp_path / "cli.pdf"
        result = self._run("--scores", "1-2-6-3-1-0-4-0-1", "--relationship", "mom",
                           "--name", "Diane", "-o", str(out), cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        assert out.exists()


def _page_count(path: Path) -> int:
    """Count pages without a PDF library: /Type /Page objects in the raw file."""
    data = path.read_bytes()
    return data.count(b"/Type /Page") - data.count(b"/Type /Pages")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
