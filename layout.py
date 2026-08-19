"""PDF rendering: exactly one :class:`~.document.Section` per page, 24 pages.

Overflow is the failure mode that would otherwise ship silently -- copy that
runs past the frame simply vanishes, and the page looks fine. So every page
is laid out into a single :class:`Frame`, and anything the frame could not
fit raises :class:`~.errors.LayoutError` instead of being dropped. Combined
with the character budgets in :mod:`.qa`, that makes a truncated manual
structurally impossible rather than unlikely.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Frame, Paragraph, Spacer

from .document import (
    Bullets, Callout, Chart, Document, KV, Numbered, Para, PullQuote,
    Script, Section, TriggerBlock,
)
from .errors import LayoutError

# A5, not A4. This is read on a phone in a Stripe receipt email, and a
# 24-page A4 document at this word count prints ~30% full, which reads as
# padded. A5 puts the same copy at a comfortable book density.
PAGE_W, PAGE_H = A5
MARGIN_X = 15 * mm
MARGIN_TOP = 16 * mm
MARGIN_BOTTOM = 15 * mm

INK = HexColor("#0C0B0E")
CARD = HexColor("#17151B")
CARD_EDGE = HexColor("#2A2630")
GOLD = HexColor("#D8B678")
GOLD_DIM = HexColor("#8A7448")
TEXT = HexColor("#EAE6DF")
MUTED = HexColor("#9C958B")
DANGER = HexColor("#C4736A")

BODY_FONT = "Helvetica"
BODY_BOLD = "Helvetica-Bold"
DISPLAY_FONT = "Times-Roman"
DISPLAY_ITALIC = "Times-Italic"


def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "body", fontName=BODY_FONT, fontSize=11.2, leading=17.6,
        textColor=TEXT, alignment=TA_LEFT, spaceAfter=9,
    )
    return {
        "body": base,
        "lede": ParagraphStyle("lede", parent=base, fontSize=12.8, leading=20,
                               textColor=TEXT, spaceAfter=11),
        "muted": ParagraphStyle("muted", parent=base, fontSize=9.5, leading=15,
                                textColor=MUTED),
        "bullet": ParagraphStyle("bullet", parent=base, fontSize=11.2, leading=17,
                                 leftIndent=13, spaceAfter=6),
        "kv_key": ParagraphStyle("kv_key", parent=base, fontName=BODY_BOLD, fontSize=8,
                                 leading=11, textColor=GOLD, spaceAfter=2),
        "kv_val": ParagraphStyle("kv_val", parent=base, fontSize=11.2, leading=17,
                                 spaceAfter=10),
        "script": ParagraphStyle("script", parent=base, fontName=DISPLAY_ITALIC,
                                 fontSize=13, leading=19, textColor=TEXT,
                                 leftIndent=12, spaceAfter=4),
        "script_label": ParagraphStyle("script_label", parent=base, fontName=BODY_BOLD,
                                       fontSize=7.5, leading=10, textColor=GOLD,
                                       leftIndent=12, spaceAfter=3),
        "callout_title": ParagraphStyle("callout_title", parent=base, fontName=BODY_BOLD,
                                        fontSize=8, leading=11, textColor=GOLD,
                                        spaceAfter=4),
        "callout_body": ParagraphStyle("callout_body", parent=base, fontSize=10.6,
                                       leading=16.4, spaceAfter=0),
        "quote": ParagraphStyle("quote", parent=base, fontName=DISPLAY_ITALIC,
                                fontSize=15, leading=22, textColor=GOLD,
                                alignment=TA_CENTER, spaceAfter=12, spaceBefore=6),
        "trigger_name": ParagraphStyle("trigger_name", parent=base, fontName=BODY_BOLD,
                                       fontSize=10.6, leading=14, textColor=TEXT,
                                       spaceAfter=3),
        "trigger_lbl": ParagraphStyle("trigger_lbl", parent=base, fontName=BODY_BOLD,
                                      fontSize=7.5, leading=10, textColor=GOLD_DIM,
                                      spaceAfter=1),
        "trigger_txt": ParagraphStyle("trigger_txt", parent=base, fontSize=10, leading=14.6, spaceAfter=5),
        "cover_name": ParagraphStyle("cover_name", parent=base, fontName=DISPLAY_FONT,
                                     fontSize=30, leading=35, textColor=GOLD,
                                     alignment=TA_CENTER, spaceAfter=6),
        "cover_title": ParagraphStyle("cover_title", parent=base, fontSize=11,
                                      leading=17, textColor=MUTED,
                                      alignment=TA_CENTER, spaceAfter=22),
        "cover_glyph": ParagraphStyle("cover_glyph", parent=base, fontName=DISPLAY_FONT,
                                      fontSize=26, leading=30, textColor=GOLD_DIM,
                                      alignment=TA_CENTER, spaceAfter=14),
        "cover_lede": ParagraphStyle("cover_lede", parent=base, fontSize=12, leading=19,
                                     alignment=TA_CENTER, spaceAfter=24),
    }


TITLE_SIZE = 17
TITLE_WIDTH = PAGE_W - 2 * MARGIN_X


def title_overflows(title: str) -> bool:
    """Whether a page title is too wide for the header at its set size."""
    return stringWidth(title, DISPLAY_FONT, TITLE_SIZE) > TITLE_WIDTH


def fit_title(title: str) -> str:
    """Trim an over-long title at a word boundary, with an ellipsis.

    A last-resort safety net -- qa.rule_title_fits fails the build before any
    title gets here needing it -- but truncating mid-word, which is what the
    naive version did, looks like a rendering bug to a buyer.
    """
    if not title_overflows(title):
        return title
    words = title.split()
    while len(words) > 1:
        words.pop()
        candidate = " ".join(words) + "…"
        if not title_overflows(candidate):
            return candidate
    return title[:24] + "…"


def _escape(text: str) -> str:
    """ReportLab paragraphs are mini-XML; unescaped copy would silently break."""
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# --------------------------------------------------------------------------
# Custom flowables
# --------------------------------------------------------------------------

class Rule(Flowable):
    def __init__(self, width: float, colour: Color = CARD_EDGE, thickness: float = 0.6,
                 space_after: float = 10):
        super().__init__()
        self.width, self.colour, self.thickness = width, colour, thickness
        self.height = thickness + space_after
        self._space_after = space_after

    def draw(self) -> None:
        self.canv.setStrokeColor(self.colour)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self._space_after, self.width, self._space_after)


class ScoreBars(Flowable):
    """The result chart. Drawn by hand so the gold bar matches the site."""

    ROW_H = 26

    def __init__(self, rows: tuple[tuple[str, int, bool], ...], width: float):
        super().__init__()
        self.rows, self.width = rows, width
        self.height = self.ROW_H * len(rows) + 6

    def draw(self) -> None:
        c = self.canv
        label_w = 96.0
        pct_w = 34.0
        track_x = label_w + 8
        track_w = self.width - label_w - pct_w - 16
        y = self.height - 18
        for label, pct, is_core in self.rows:
            c.setFont(BODY_BOLD if is_core else BODY_FONT, 9)
            c.setFillColor(TEXT if is_core else MUTED)
            text = label
            while stringWidth(text, BODY_FONT, 9) > label_w and len(text) > 4:
                text = text[:-2]
            c.drawString(0, y, text)

            c.setFillColor(CARD)
            c.roundRect(track_x, y - 3, track_w, 9, 4.5, stroke=0, fill=1)
            filled = max(2.0, track_w * min(max(pct, 0), 100) / 100.0)
            c.setFillColor(GOLD if is_core else GOLD_DIM)
            c.roundRect(track_x, y - 3, filled, 9, 4.5, stroke=0, fill=1)

            c.setFont(BODY_FONT, 9)
            c.setFillColor(MUTED)
            c.drawRightString(self.width, y, f"{pct}%")
            y -= self.ROW_H


class CalloutBox(Flowable):
    """A bordered card. Measures its own wrapped height so it cannot clip."""

    PAD = 11

    def __init__(self, title: str, body: str, width: float, styles: dict,
                 accent: Color = GOLD):
        super().__init__()
        self.width = width
        self.accent = accent
        inner = width - 2 * self.PAD
        self._title = Paragraph(_escape(title.upper()), styles["callout_title"])
        self._body = Paragraph(_escape(body), styles["callout_body"])
        tw, th = self._title.wrap(inner, 10_000)
        bw, bh = self._body.wrap(inner, 10_000)
        self._th, self._bh = th, bh
        self.height = th + bh + 2 * self.PAD + 6

    def draw(self) -> None:
        c = self.canv
        c.setFillColor(CARD)
        c.setStrokeColor(CARD_EDGE)
        c.setLineWidth(0.7)
        c.roundRect(0, 0, self.width, self.height, 7, stroke=1, fill=1)
        c.setFillColor(self.accent)
        c.roundRect(0, 6, 2.5, self.height - 12, 1.2, stroke=0, fill=1)
        self._title.drawOn(c, self.PAD + 4, self.height - self.PAD - self._th)
        self._body.drawOn(c, self.PAD + 4, self.PAD)


# --------------------------------------------------------------------------
# Section -> flowables
# --------------------------------------------------------------------------

def _flowables(section: Section, styles: dict, width: float) -> list:
    out: list = []
    inner = width

    if section.style == "cover":
        blocks = list(section.blocks)
        out.append(Spacer(1, 22))
        out.append(Paragraph(_escape(blocks[0].text), styles["cover_glyph"]))
        out.append(Paragraph(_escape(section.title), styles["cover_name"]))
        out.append(Paragraph(_escape(blocks[1].text), styles["cover_title"]))
        out.append(Rule(inner, GOLD_DIM, 0.8, 18))
        out.append(Paragraph(_escape(blocks[2].text), styles["cover_lede"]))
        out.append(Rule(inner, CARD_EDGE, 0.6, 14))
        for key, value in blocks[3].rows:
            out.append(Paragraph(_escape(key.upper()), styles["kv_key"]))
            out.append(Paragraph(_escape(value), styles["kv_val"]))
        return out

    for block in section.blocks:
        if isinstance(block, Para):
            style = styles["lede"] if not out else styles["body"]
            out.append(Paragraph(_escape(block.text), style))
        elif isinstance(block, PullQuote):
            out.append(Spacer(1, 4))
            out.append(Paragraph(_escape(f"“{block.text}”"), styles["quote"]))
        elif isinstance(block, Bullets):
            for item in block.items:
                colour = {"×": DANGER, "+": GOLD}.get(block.marker, GOLD)
                marker = (f'<font color="#{colour.hexval()[2:]}">{_escape(block.marker)}'
                          f"</font>&nbsp;&nbsp;")
                out.append(Paragraph(marker + _escape(item), styles["bullet"]))
        elif isinstance(block, Numbered):
            for i, item in enumerate(block.items, 1):
                marker = (f'<font color="#{GOLD.hexval()[2:]}"><b>{i}</b></font>&nbsp;&nbsp;')
                out.append(Paragraph(marker + _escape(item), styles["bullet"]))
        elif isinstance(block, Script):
            out.append(Paragraph(_escape(block.label.upper()), styles["script_label"]))
            out.append(Paragraph(_escape(f"“{block.text}”"), styles["script"]))
            out.append(Spacer(1, 7))
        elif isinstance(block, Callout):
            accent = DANGER if block.title.lower().startswith("never") else GOLD
            out.append(CalloutBox(block.title, block.text, inner, styles, accent))
            out.append(Spacer(1, 11))
        elif isinstance(block, KV):
            for key, value in block.rows:
                out.append(Paragraph(_escape(key.upper()), styles["kv_key"]))
                out.append(Paragraph(_escape(value), styles["kv_val"]))
        elif isinstance(block, Chart):
            out.append(ScoreBars(block.rows, inner))
            out.append(Spacer(1, 12))
        elif isinstance(block, TriggerBlock):
            out.extend([
                Paragraph(_escape(block.name), styles["trigger_name"]),
                Paragraph("WHAT YOU SEE", styles["trigger_lbl"]),
                Paragraph(_escape(block.looks_like), styles["trigger_txt"]),
                Paragraph("WHAT IS ACTUALLY HAPPENING", styles["trigger_lbl"]),
                Paragraph(_escape(block.why), styles["trigger_txt"]),
                Paragraph("DO THIS INSTEAD", styles["trigger_lbl"]),
                Paragraph(_escape(block.instead), styles["trigger_txt"]),
                Rule(inner, CARD_EDGE, 0.5, 9),
            ])
        else:  # pragma: no cover - guarded by the Block union
            raise LayoutError(f"No renderer for block type {type(block).__name__}.")
    return out


# --------------------------------------------------------------------------
# Page chrome
# --------------------------------------------------------------------------

def _draw_chrome(c: Canvas, doc: Document, section: Section, styles: dict) -> float:
    """Paint the background and header. Returns the y of the frame's top."""
    c.setFillColor(INK)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

    if section.style == "cover":
        c.setStrokeColor(GOLD_DIM)
        c.setLineWidth(0.8)
        c.rect(9 * mm, 9 * mm, PAGE_W - 18 * mm, PAGE_H - 18 * mm, stroke=1, fill=0)
        c.setFont(BODY_BOLD, 7.5)
        c.setFillColor(GOLD_DIM)
        c.drawCentredString(PAGE_W / 2, PAGE_H - 20 * mm, section.kicker.upper())
        return PAGE_H - 40 * mm

    top = PAGE_H - MARGIN_TOP
    c.setFont(BODY_BOLD, 7.5)
    c.setFillColor(GOLD_DIM)
    c.drawString(MARGIN_X, top, section.kicker.upper())
    c.setFont(BODY_FONT, 7.5)
    c.setFillColor(MUTED)
    c.drawRightString(PAGE_W - MARGIN_X, top,
                      f"{doc.profile.relationship.label.upper()} · "
                      f"{doc.sections[3].title.split(':')[0].upper()}")
    top -= 9
    c.setStrokeColor(CARD_EDGE)
    c.setLineWidth(0.6)
    c.line(MARGIN_X, top, PAGE_W - MARGIN_X, top)

    top -= 22
    c.setFont(DISPLAY_FONT, TITLE_SIZE)
    c.setFillColor(TEXT)
    c.drawString(MARGIN_X, top, fit_title(section.title))
    return top - 14


def _draw_footer(c: Canvas, section: Section) -> None:
    if section.style == "cover":
        return
    c.setFont(BODY_FONT, 7.5)
    c.setFillColor(MUTED)
    c.drawString(MARGIN_X, 9 * mm, "The Operator’s Manual")
    c.drawRightString(PAGE_W - MARGIN_X, 9 * mm, f"{section.number} / 24")


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def measure_fill(doc: Document) -> dict[int, float]:
    """How much of each page's frame the copy actually occupies, 0.0-1.0.

    Character count is a bad proxy for visual weight -- a page of scripts and
    callouts is far taller than its character count suggests -- so this
    measures wrapped flowable height against the real frame. Used to catch
    pages that will print looking half-empty, which is the most common
    complaint about generated PDFs.

    Renders nothing; safe to call in tests and in CI.
    """
    styles = _styles()
    scratch = Canvas("/dev/null", pagesize=A5)
    fills: dict[int, float] = {}
    for section in doc.sections:
        width = PAGE_W - 2 * MARGIN_X
        top = (PAGE_H - 34 * mm) if section.style == "cover" else (PAGE_H - MARGIN_TOP - 47)
        available = top - MARGIN_BOTTOM
        used = 0.0
        for flowable in _flowables(section, styles, width):
            _w, h = flowable.wrapOn(scratch, width, available)
            used += h + getattr(flowable, "getSpaceAfter", lambda: 0)()
        fills[section.number] = round(used / available, 3) if available > 0 else 0.0
    return fills


def render_pdf(doc: Document, path: str | Path, *, title: str | None = None) -> Path:
    """Draw the document. Raises :class:`LayoutError` rather than truncating.

    Args:
        title: PDF metadata title. Defaults to a sensible product title.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = _styles()

    core_name = doc.sections[0].title
    # invariant=1 strips the creation timestamp and randomised document ID,
    # so the same result always produces byte-identical output. That makes
    # re-downloads cacheable and makes regressions diffable.
    c = Canvas(str(path), pagesize=A5, invariant=1)
    c.setTitle(title or f"The Operator’s Manual — {core_name}")
    c.setAuthor("Enneagraphology")
    c.setSubject(f"{doc.profile.relationship.label} · {core_name}")
    c.setCreator("enneagram_manual")

    for section in doc.sections:
        frame_top = _draw_chrome(c, doc, section, styles)
        width = PAGE_W - 2 * MARGIN_X
        height = frame_top - MARGIN_BOTTOM
        if height <= 0:  # pragma: no cover
            raise LayoutError(f"p{section.number}: no vertical space left for content.")

        frame = Frame(MARGIN_X, MARGIN_BOTTOM, width, height,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                      showBoundary=0)
        remaining = _flowables(section, styles, width)
        frame.addFromList(remaining, c)
        if remaining:
            raise LayoutError(
                f"p{section.number} ({section.title!r}) overflowed: "
                f"{len(remaining)} flowable(s) did not fit. Reduce the copy or raise "
                f"the section budget."
            )

        _draw_footer(c, section)
        c.showPage()

    pages = c.getPageNumber() - 1
    if pages != len(doc.sections):  # pragma: no cover
        raise LayoutError(f"Rendered {pages} pages, expected {len(doc.sections)}.")

    c.save()
    return path
