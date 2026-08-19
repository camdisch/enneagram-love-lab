"""Command-line entry point.

    python -m enneagram_manual --scores 1-2-6-3-1-0-4-0-1 --relationship mom -o out.pdf
    python -m enneagram_manual --json result.json -o out.pdf
    python -m enneagram_manual --all --outdir manuals/     # all 45 combinations
    python -m enneagram_manual --self-test                 # QA every combination, render none

Exit codes are distinct on purpose so a webhook wrapper can tell a bad
payload apart from a bug in our own copy without parsing stderr:

    0  success
    2  bad input (the buyer's result was unusable)
    3  copy-bank bug (our fault)
    4  QA gate blocked the save (our fault)
    5  layout overflow (our fault)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import GenerationReport, __version__, generate, self_test
from .content import ARCHETYPES, LENSES
from .errors import ContentError, InputError, LayoutError, QAFailure, TemplateError

EXIT_OK, EXIT_INPUT, EXIT_CONTENT, EXIT_QA, EXIT_LAYOUT = 0, 2, 3, 4, 5


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="enneagram_manual",
        description="Generate a 24-page Operator's Manual PDF from a quiz result.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    src = p.add_argument_group("input")
    src.add_argument("--scores", help="Encoded scores, e.g. 1-2-6-3-1-0-4-0-1 (types 1-9).")
    src.add_argument("--relationship", choices=sorted(LENSES), help="Which quiz they took.")
    src.add_argument("--name", help="Optional name for the person they tested.")
    src.add_argument("--question-count", type=int, default=None,
                     help="Number of quiz questions (default 12).")
    src.add_argument("--json", dest="json_path",
                     help="Path to a JSON result, or '-' for stdin.")

    out = p.add_argument_group("output")
    out.add_argument("-o", "--out", help="Output PDF path.")
    out.add_argument("--outdir", default="manuals", help="Directory for --all (default: manuals).")

    mode = p.add_argument_group("modes")
    mode.add_argument("--all", action="store_true",
                      help="Render every type x relationship combination.")
    mode.add_argument("--self-test", action="store_true",
                      help="QA every combination without rendering. Exits non-zero on failure.")
    mode.add_argument("--check-only", action="store_true",
                      help="Run the QA gate and report, but write no PDF.")

    flags = p.add_argument_group("behaviour")
    flags.add_argument("--strict", action="store_true",
                       help="Treat QA warnings as failures (recommended in CI).")
    flags.add_argument("--allow-unscored", action="store_true",
                       help="Emit a generic manual instead of failing on unusable scores.")
    flags.add_argument("-q", "--quiet", action="store_true")
    return p


def _report(report: GenerationReport, quiet: bool) -> None:
    if quiet:
        return
    p = report.profile
    print(f"✓ {report.path}")
    print(f"  {p.relationship.label} · core {p.core} · secondary {p.secondary} "
          f"({p.blend_mode}, {p.confidence} confidence)")
    for warning in p.warnings:
        print(f"  ! input: {warning}")
    for v in report.violations:
        print(f"  ! {v.severity}: [{v.rule}] {v.where} — {v.detail}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.self_test:
        failures = self_test(strict=args.strict)
        if failures:
            print(f"✗ {len(failures)} combination(s) failed:", file=sys.stderr)
            for f in failures:
                print(f"  - {f}", file=sys.stderr)
            return EXIT_QA
        if not args.quiet:
            print(f"✓ all {len(LENSES) * len(ARCHETYPES)} combinations pass.")
        return EXIT_OK

    if args.all:
        outdir = Path(args.outdir)
        failures = 0
        for slug in sorted(LENSES):
            for type_id in sorted(ARCHETYPES):
                scores = {t: 1 for t in ARCHETYPES}
                scores[type_id] = 7
                scores[(type_id % 9) + 1] = 3
                target = outdir / slug / f"type-{type_id}.pdf"
                try:
                    report = generate(scores=scores, relationship=slug, out_path=target,
                                      strict=args.strict)
                except (InputError, ContentError, TemplateError, QAFailure, LayoutError) as exc:
                    failures += 1
                    print(f"✗ {slug}/type-{type_id}: {exc}", file=sys.stderr)
                else:
                    _report(report, args.quiet)
        if failures:
            print(f"✗ {failures} combination(s) failed.", file=sys.stderr)
            return EXIT_QA
        return EXIT_OK

    payload: dict = {}
    if args.json_path:
        try:
            raw = sys.stdin.read() if args.json_path == "-" else Path(args.json_path).read_text()
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"✗ could not read JSON input: {exc}", file=sys.stderr)
            return EXIT_INPUT
        if not isinstance(payload, dict):
            print("✗ JSON input must be an object.", file=sys.stderr)
            return EXIT_INPUT

    out = args.out or payload.get("out") or "manual.pdf"

    try:
        if args.check_only:
            from .document import build_document
            from .models import build_profile
            from .qa import check

            profile = build_profile(
                payload, scores=args.scores, relationship=args.relationship,
                subject_name=args.name, question_count=args.question_count,
                allow_unscored=args.allow_unscored,
            )
            violations = check(build_document(profile))
            blocking = [v for v in violations if v.severity == "error" or args.strict]
            for v in violations:
                print(f"  {v.severity}: [{v.rule}] {v.where} — {v.detail}")
            print(f"{'✗' if blocking else '✓'} {len(violations)} finding(s), "
                  f"{len(blocking)} blocking.")
            return EXIT_QA if blocking else EXIT_OK

        report = generate(
            payload, scores=args.scores, relationship=args.relationship,
            subject_name=args.name, question_count=args.question_count,
            out_path=out, allow_unscored=args.allow_unscored, strict=args.strict,
        )
    except InputError as exc:
        print(f"✗ bad input: {exc}", file=sys.stderr)
        return EXIT_INPUT
    except (ContentError, TemplateError) as exc:
        print(f"✗ copy-bank bug: {exc}", file=sys.stderr)
        return EXIT_CONTENT
    except QAFailure as exc:
        print(f"✗ QA gate blocked the save (nothing written):\n{exc}", file=sys.stderr)
        return EXIT_QA
    except LayoutError as exc:
        print(f"✗ layout: {exc}", file=sys.stderr)
        return EXIT_LAYOUT

    _report(report, args.quiet)
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
