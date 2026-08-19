/**
 * The PDF renderer, in the browser. Mirrors `enneagram_manual/layout.py`.
 *
 * One section per page, exactly 24 pages, A5. Every block is measured before
 * it is drawn, so copy can never silently run off the bottom of a page — the
 * failure mode that would otherwise ship invisibly, since a truncated page
 * still looks fine.
 *
 * jsPDF is loaded dynamically so its ~350KB never lands in the initial bundle;
 * it is only fetched when someone actually generates a manual.
 */

import type { jsPDF } from "jspdf";

import type { Block, ManualDocument, Section } from "./document";

// A5 in points. Not A4: at this word count A4 prints ~30% full, which reads as
// padding, and this is opened on a phone.
const PAGE_W = 419.53;
const PAGE_H = 595.28;
const MARGIN_X = 42.5;
const MARGIN_TOP = 45.4;
const MARGIN_BOTTOM = 42.5;

const INK = "#0C0B0E";
const CARD = "#17151B";
const CARD_EDGE = "#2A2630";
const GOLD = "#D8B678";
const GOLD_DIM = "#8A7448";
const TEXT = "#EAE6DF";
const MUTED = "#9C958B";
const DANGER = "#C4736A";

const BODY = "helvetica";
const DISPLAY = "times";

interface Style {
  font: string;
  weight: "normal" | "bold" | "italic";
  size: number;
  leading: number;
  colour: string;
  spaceAfter: number;
  indent?: number;
  align?: "left" | "center";
}

type StyleName =
  | "body"
  | "lede"
  | "bullet"
  | "kvKey"
  | "kvVal"
  | "script"
  | "scriptLabel"
  | "calloutTitle"
  | "calloutBody"
  | "quote"
  | "triggerName"
  | "triggerLbl"
  | "triggerTxt"
  | "coverName"
  | "coverTitle"
  | "coverGlyph"
  | "coverLede";

const S: Record<StyleName, Style> = {
  body: { font: BODY, weight: "normal", size: 11.2, leading: 17.6, colour: TEXT, spaceAfter: 9 },
  lede: { font: BODY, weight: "normal", size: 12.8, leading: 20, colour: TEXT, spaceAfter: 11 },
  bullet: {
    font: BODY,
    weight: "normal",
    size: 11.2,
    leading: 17,
    colour: TEXT,
    spaceAfter: 6,
    indent: 13,
  },
  kvKey: { font: BODY, weight: "bold", size: 8, leading: 11, colour: GOLD, spaceAfter: 2 },
  kvVal: { font: BODY, weight: "normal", size: 11.2, leading: 17, colour: TEXT, spaceAfter: 10 },
  script: {
    font: DISPLAY,
    weight: "italic",
    size: 13,
    leading: 19,
    colour: TEXT,
    spaceAfter: 4,
    indent: 12,
  },
  scriptLabel: {
    font: BODY,
    weight: "bold",
    size: 7.5,
    leading: 10,
    colour: GOLD,
    spaceAfter: 3,
    indent: 12,
  },
  calloutTitle: { font: BODY, weight: "bold", size: 8, leading: 11, colour: GOLD, spaceAfter: 4 },
  calloutBody: {
    font: BODY,
    weight: "normal",
    size: 10.6,
    leading: 16.4,
    colour: TEXT,
    spaceAfter: 0,
  },
  quote: {
    font: DISPLAY,
    weight: "italic",
    size: 15,
    leading: 22,
    colour: GOLD,
    spaceAfter: 12,
    align: "center",
  },
  triggerName: { font: BODY, weight: "bold", size: 10.6, leading: 14, colour: TEXT, spaceAfter: 3 },
  triggerLbl: {
    font: BODY,
    weight: "bold",
    size: 7.5,
    leading: 10,
    colour: GOLD_DIM,
    spaceAfter: 1,
  },
  triggerTxt: {
    font: BODY,
    weight: "normal",
    size: 10,
    leading: 14.6,
    colour: TEXT,
    spaceAfter: 5,
  },
  coverName: {
    font: DISPLAY,
    weight: "normal",
    size: 30,
    leading: 35,
    colour: GOLD,
    spaceAfter: 6,
    align: "center",
  },
  coverTitle: {
    font: BODY,
    weight: "normal",
    size: 11,
    leading: 17,
    colour: MUTED,
    spaceAfter: 22,
    align: "center",
  },
  coverGlyph: {
    font: DISPLAY,
    weight: "normal",
    size: 26,
    leading: 30,
    colour: GOLD_DIM,
    spaceAfter: 14,
    align: "center",
  },
  coverLede: {
    font: BODY,
    weight: "normal",
    size: 12,
    leading: 19,
    colour: TEXT,
    spaceAfter: 24,
    align: "center",
  },
};

const TITLE_SIZE = 17;

/** A measured, drawable unit. Height is known before anything is committed. */
interface Item {
  height: number;
  draw: (doc: jsPDF, x: number, y: number, width: number) => void;
}

function textItem(doc: jsPDF, text: string, style: Style, width: number): Item {
  const indent = style.indent ?? 0;
  doc.setFont(style.font, style.weight);
  doc.setFontSize(style.size);
  const lines: string[] = doc.splitTextToSize(text, width - indent);
  return {
    height: lines.length * style.leading + style.spaceAfter,
    draw(d, x, y, w) {
      d.setFont(style.font, style.weight);
      d.setFontSize(style.size);
      d.setTextColor(style.colour);
      let cursor = y + style.leading * 0.78;
      for (const line of lines) {
        if (style.align === "center") d.text(line, x + w / 2, cursor, { align: "center" });
        else d.text(line, x + indent, cursor);
        cursor += style.leading;
      }
    },
  };
}

function ruleItem(colour: string, spaceAfter: number): Item {
  return {
    height: spaceAfter + 0.6,
    draw(d, x, y, w) {
      d.setDrawColor(colour);
      d.setLineWidth(0.5);
      d.line(x, y + 2, x + w, y + 2);
    },
  };
}

function spacer(height: number): Item {
  return { height, draw: () => {} };
}

function calloutItem(doc: jsPDF, title: string, body: string, width: number, accent: string): Item {
  const pad = 11;
  const inner = width - pad * 2 - 4;
  const t = textItem(doc, title.toUpperCase(), { ...S.calloutTitle, indent: 0 }, inner);
  const b = textItem(doc, body, { ...S.calloutBody, indent: 0 }, inner);
  const boxHeight = t.height + b.height + pad * 2;
  return {
    height: boxHeight + 9,
    draw(d, x, y, w) {
      d.setFillColor(CARD);
      d.setDrawColor(CARD_EDGE);
      d.setLineWidth(0.6);
      d.roundedRect(x, y, w, boxHeight, 5, 5, "FD");
      d.setFillColor(accent);
      d.rect(x, y + 5, 2, boxHeight - 10, "F");
      t.draw(d, x + pad + 4, y + pad, inner);
      b.draw(d, x + pad + 4, y + pad + t.height, inner);
    },
  };
}

function chartItem(rows: [string, number, boolean][], width: number): Item {
  const rowH = 26;
  return {
    height: rowH * rows.length + 10,
    draw(d, x, y, w) {
      const labelW = 96;
      const pctW = 34;
      const trackX = x + labelW + 8;
      const trackW = w - labelW - pctW - 16;
      let cursor = y + 10;
      for (const [label, pct, isCore] of rows) {
        d.setFont(BODY, isCore ? "bold" : "normal");
        d.setFontSize(9);
        d.setTextColor(isCore ? TEXT : MUTED);
        d.text(label, x, cursor);

        d.setFillColor(CARD);
        d.roundedRect(trackX, cursor - 6.5, trackW, 9, 4.5, 4.5, "F");
        const filled = Math.max(2, (trackW * Math.min(Math.max(pct, 0), 100)) / 100);
        d.setFillColor(isCore ? GOLD : GOLD_DIM);
        d.roundedRect(trackX, cursor - 6.5, filled, 9, 4.5, 4.5, "F");

        d.setFont(BODY, "normal");
        d.setTextColor(MUTED);
        d.text(`${pct}%`, x + w, cursor, { align: "right" });
        cursor += rowH;
      }
    },
  };
}

function itemsFor(doc: jsPDF, section: Section, width: number): Item[] {
  const items: Item[] = [];

  if (section.style === "cover") {
    // The cover page plan is fixed in document.ts: glyph, subtitle, lede, kv.
    const [glyph, subtitle, lede, kv] = section.blocks as [Block, Block, Block, Block];
    items.push(spacer(22));
    if (glyph.kind === "glyph") items.push(textItem(doc, glyph.text, S.coverGlyph, width));
    items.push(textItem(doc, section.title, S.coverName, width));
    if (subtitle.kind === "para") items.push(textItem(doc, subtitle.text, S.coverTitle, width));
    items.push(ruleItem(GOLD_DIM, 13));
    if (lede.kind === "para") items.push(textItem(doc, lede.text, S.coverLede, width));
    items.push(ruleItem(CARD_EDGE, 11));
    if (kv.kind === "kv") {
      for (const [k, v] of kv.rows) {
        items.push(textItem(doc, k.toUpperCase(), S.kvKey, width));
        items.push(textItem(doc, v, S.kvVal, width));
      }
    }
    return items;
  }

  let first = true;
  for (const block of section.blocks) {
    switch (block.kind) {
      case "para":
        items.push(textItem(doc, block.text, first ? S.lede : S.body, width));
        first = false;
        break;
      case "pullquote":
        items.push(spacer(3));
        items.push(textItem(doc, `“${block.text}”`, S.quote, width));
        break;
      case "bullets":
        for (const item of block.items) {
          items.push(textItem(doc, `${block.marker}  ${item}`, S.bullet, width));
        }
        break;
      case "numbered":
        block.items.forEach((item, i) => {
          items.push(textItem(doc, `${i + 1}  ${item}`, S.bullet, width));
        });
        break;
      case "script":
        items.push(textItem(doc, block.label.toUpperCase(), S.scriptLabel, width));
        items.push(textItem(doc, `“${block.text}”`, S.script, width));
        items.push(spacer(5));
        break;
      case "callout":
        items.push(
          calloutItem(
            doc,
            block.title,
            block.text,
            width,
            block.title.toLowerCase().startsWith("never") ? DANGER : GOLD,
          ),
        );
        break;
      case "kv":
        for (const [k, v] of block.rows) {
          items.push(textItem(doc, k.toUpperCase(), S.kvKey, width));
          items.push(textItem(doc, v, S.kvVal, width));
        }
        break;
      case "chart":
        items.push(chartItem(block.rows, width));
        items.push(spacer(9));
        break;
      case "trigger":
        items.push(textItem(doc, block.name, S.triggerName, width));
        items.push(textItem(doc, "WHAT YOU SEE", S.triggerLbl, width));
        items.push(textItem(doc, block.looks_like, S.triggerTxt, width));
        items.push(textItem(doc, "WHAT IS ACTUALLY HAPPENING", S.triggerLbl, width));
        items.push(textItem(doc, block.why, S.triggerTxt, width));
        items.push(textItem(doc, "DO THIS INSTEAD", S.triggerLbl, width));
        items.push(textItem(doc, block.instead, S.triggerTxt, width));
        items.push(ruleItem(CARD_EDGE, 8));
        break;
      case "glyph":
        break;
    }
  }
  return items;
}

function titleFits(doc: jsPDF, title: string): boolean {
  doc.setFont(DISPLAY, "normal");
  doc.setFontSize(TITLE_SIZE);
  return doc.getTextWidth(title) <= PAGE_W - 2 * MARGIN_X;
}

function fitTitle(doc: jsPDF, title: string): string {
  if (titleFits(doc, title)) return title;
  const words = title.split(" ");
  while (words.length > 1) {
    words.pop();
    const candidate = `${words.join(" ")}…`;
    if (titleFits(doc, candidate)) return candidate;
  }
  return title.slice(0, 24) + "…";
}

function drawChrome(doc: jsPDF, manual: ManualDocument, section: Section): number {
  doc.setFillColor(INK);
  doc.rect(0, 0, PAGE_W, PAGE_H, "F");

  if (section.style === "cover") {
    doc.setDrawColor(GOLD_DIM);
    doc.setLineWidth(0.7);
    doc.rect(25.5, 25.5, PAGE_W - 51, PAGE_H - 51, "S");
    doc.setFont(BODY, "bold");
    doc.setFontSize(7.5);
    doc.setTextColor(GOLD_DIM);
    doc.text(section.kicker.toUpperCase(), PAGE_W / 2, 56.7, { align: "center" });
    return 96;
  }

  let top = MARGIN_TOP;
  doc.setFont(BODY, "bold");
  doc.setFontSize(7.5);
  doc.setTextColor(GOLD_DIM);
  doc.text(section.kicker.toUpperCase(), MARGIN_X, top);
  doc.setFont(BODY, "normal");
  doc.setTextColor(MUTED);
  // Page 4's title is "<Archetype>: who they are"; the part before the colon
  // is the archetype name, used as a running head.
  const runningHead = (manual.sections[3]?.title ?? "").split(":")[0] ?? "";
  doc.text(
    `${manual.profile.relationship.label.toUpperCase()} · ${runningHead.toUpperCase()}`,
    PAGE_W - MARGIN_X,
    top,
    { align: "right" },
  );

  top += 9;
  doc.setDrawColor(CARD_EDGE);
  doc.setLineWidth(0.5);
  doc.line(MARGIN_X, top, PAGE_W - MARGIN_X, top);

  top += 22;
  doc.setFont(DISPLAY, "normal");
  doc.setFontSize(TITLE_SIZE);
  doc.setTextColor(TEXT);
  doc.text(fitTitle(doc, section.title), MARGIN_X, top);
  return top + 14;
}

function drawFooter(doc: jsPDF, section: Section): void {
  if (section.style === "cover") return;
  doc.setFont(BODY, "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(MUTED);
  doc.text("The Operator’s Manual", MARGIN_X, PAGE_H - 25.5);
  doc.text(`${section.number} / 24`, PAGE_W - MARGIN_X, PAGE_H - 25.5, { align: "right" });
}

export interface RenderResult {
  blob: Blob;
  /** page number -> fraction of the frame the copy occupies. */
  fill: Record<number, number>;
}

/**
 * Draw the manual. Throws rather than letting a page overflow silently.
 */
export async function renderPdf(manual: ManualDocument): Promise<RenderResult> {
  const { jsPDF: JsPDF } = await import("jspdf");
  const doc = new JsPDF({ unit: "pt", format: "a5", compress: true });

  doc.setProperties({
    title: `The Operator's Manual — ${manual.sections[0]?.title ?? ""}`,
    author: "Enneagraphology",
    subject: `${manual.profile.relationship.label} · ${manual.sections[0]?.title ?? ""}`,
  });

  const width = PAGE_W - 2 * MARGIN_X;
  const fill: Record<number, number> = {};

  manual.sections.forEach((section, index) => {
    if (index > 0) doc.addPage();
    const top = drawChrome(doc, manual, section);
    const available = PAGE_H - MARGIN_BOTTOM - top;

    const items = itemsFor(doc, section, width);
    const used = items.reduce((sum, item) => sum + item.height, 0);
    fill[section.number] = Math.round((used / available) * 1000) / 1000;

    if (used > available) {
      throw new Error(
        `p${section.number} ("${section.title}") overflowed: needs ${Math.round(used)}pt of ` +
          `${Math.round(available)}pt. Reduce the copy or raise the section budget.`,
      );
    }

    let cursor = top;
    for (const item of items) {
      item.draw(doc, MARGIN_X, cursor, width);
      cursor += item.height;
    }
    drawFooter(doc, section);
  });

  return { blob: doc.output("blob"), fill };
}
