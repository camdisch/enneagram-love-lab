# The Operator's Manual — PDF generator

Turns an Enneagram quiz result into a 24-page, print-quality PDF that has been
checked for broken placeholders, internal contradiction, repetition, tone and
page overflow **before** it is written to disk.

```bash
pip install reportlab

# one manual
python -m enneagram_manual --scores 1-2-6-3-1-0-4-0-1 --relationship mom \
    --name Diane -o manuals/diane.pdf

# every type × relationship (45 PDFs), for reviewing the copy
python -m enneagram_manual --all --outdir manuals

# QA every combination without rendering — run this on every deploy
python -m enneagram_manual --self-test --strict
```

From Python:

```python
from enneagram_manual import generate

report = generate(
    {"s": "1-2-6-3-1-0-4-0-1", "relationship": "mom", "name": "Diane"},
    out_path="manuals/diane.pdf",
)
report.ok            # False if anything blocking survived
report.violations    # non-blocking warnings, worth logging
report.profile.warnings   # every repair made to the buyer's input
report.fill          # {page: 0.0-1.0} how full each page is
```

The `s` value is exactly the share-link param your results page already
produces (`encodeScoresToParam` in `src/lib/share.ts`), so the webhook that
fires on a Stripe payment can hand this the same string the buyer's URL had.

---

## What was asked for, and where it lives

### 1. Template variables are validated so nothing prints raw

`templating.py`. `str.format` fails in the two ways that cost you money: a
missing key only raises when that branch runs, and a stray brace prints raw.
Both are removed:

- `render()` raises on a missing key, an **empty** value (a blank substitution
  is a hole on the page), leftover `{...}`, `[[...]]`, `<<...>>`, `%s`, `${...}`,
  `TODO`, and leaked `None` / `undefined` / `NaN`.
- `audit_templates()` runs the same check **statically over the entire copy
  bank at import time**. A typo in a rarely-hit Type 5 fragment fails the
  import, not a buyer's download. This is the part that actually guarantees
  the property — per-render checks only cover paths you happen to exercise.
- Typography (curly quotes, spaced em dashes, ellipses, sentence casing) is
  normalised in the same place, because it is the last point every string
  passes through before becoming a page.

**Pronoun decision worth knowing:** every line is written with singular
*they/them/their* and the person referred to as `{subject}`. That removes an
entire bug class (`"she need"` / `"they needs"`) and means one string works
whether the buyer tested their mom, their boyfriend, or a friend of unknown
gender. Don't add pronoun variables.

### 2. Blending without contradiction or repetition

`blending.py` + `content.py`.

There are 72 core/secondary pairings and 45 type/relationship combinations.
None are hand-authored. Each archetype declares what it contributes *as a
core* and what flavour it adds *as a secondary*, and:

- **Contradiction** is handled by claim tags. Type 5 carries `needs-space`;
  Type 2 carries `needs-contact`. `CLAIM_CONFLICTS` marks those as
  incompatible, so instead of printing both as fact (visibly wrong about
  someone the reader knows well) the blender emits a *tension* paragraph that
  names the push-pull. That is both truer to how blended types present and
  better copy than either claim alone. `qa.rule_blend_coherence` fails the
  build if a conflict exists and the tension line is missing.
- **Repetition** is handled by `RepetitionLedger`, which indexes
  content-word trigrams (so "they need to be needed" and "needing to be
  needed" collide) and refuses a variant that reuses earlier phrasing.
  Deliberate callbacks — the cheat sheet, the closing quote — are exempt by
  label.
- **Variant selection** is seeded from the profile, so the same result always
  produces a byte-identical PDF. A buyer re-downloading never gets a
  different book.

Relationship-awareness comes from `LENSES` (stakes, power dynamic, channel,
realistic repair window, what you can't change) plus `KIND_FRAMING`, which
has a specific line for each of the 27 archetype × bond-kind pairs. A Type 8
mom and a Type 8 boyfriend read differently without writing 45 manuals.

### 3. Edge cases degrade predictably

`models.py`. Anything can be thrown at `build_profile()` — a mangled webhook
payload, a truncated share link, an empty object. It either returns a fully
populated `Profile` or raises `InputError` with an actionable message. It
never returns a half-valid object and never lets a `None` reach the copy.

| Input | Behaviour |
|---|---|
| Missing / unknown relationship | Falls back to the most neutral vertical, **with a warning** |
| `"mother"`, `"bff"`, `"wife"`, `"BF"` | Resolved via aliases |
| Wrong-length score string | Missing positions → 0, warning recorded |
| Negative, `NaN`, `inf`, `"seven"`, `None` | Clamped to 0, warning recorded |
| Score above the question count | Clamped, warning recorded |
| All scores zero | **Raises** by default; `allow_unscored=True` produces a generic manual flagged loudly in QA |
| Exact tie for top type | Broken deterministically (lowest id), warning recorded |
| 100% concentration | `blend_mode="pure"` — the copy stops making claims about a secondary that scored nothing |
| Secondary under 12% | Same — described as a footnote, never as a driver |
| Top two within 4% | `blend_mode="split"` — the copy says so instead of faking confidence |
| 0.4% share | Prints as 1%, never a misleading 0% |
| Name with markup, emoji, 100 chars | Sanitised and truncated |

Every repair lands on `profile.warnings`, so a degraded manual is something
you can alert on rather than something you learn about from a refund.

### 4. Automated checks that block the save

`qa.py`. Every rule runs over the assembled document — finished, blended,
relationship-specific copy — and any `error` raises `QAFailure` **before a
single byte is written**.

**Blocking (errors):**

| Rule | Catches |
|---|---|
| `no-placeholders` | Any unrendered markup that reached a page |
| `no-empty` | Blank or one-word blocks that render as a gap |
| `article-agreement` | `"the The Frontrunner"`, repeated words |
| `banned-language` | Clinical framing (`diagnosis`, `disorder`), armchair diagnosis (`narcissist`), unsupportable promises (`guaranteed`), prescriptive scolding, and machine-written filler (`delve`, `tapestry`, `it's important to note`) |
| `relationship-frame` | Romantic framing in a parent manual; childhood-authority framing in a partner manual |
| `renderable-characters` | Any glyph the PDF font can't draw (would print as a black box) |
| `typography` | Blocks that don't start capitalised or end with terminal punctuation |
| `script-shape` | A "say this out loud" line too long for anyone to say |
| `duplicate-sentence` | The same sentence twice outside the pages that intend it |
| `blend-coherence` | Contradictory claims asserted as though they agree |
| `section-budget`, `page-fill` | Copy that would overflow the page (measured on wrapped flowables, not guessed from character count) |
| `title-fits` | A page title too wide for the header |

**Non-blocking (warnings):** sentence length, hedging density, second-person
address, phrase repetition, duplicate titles, thin pages, degraded input.

`--strict` promotes warnings to failures. Use it in CI; leave it off in
production so a stylistic nit never blocks a paid download.

Every one of these fired on real bugs during development — the doubled
article, the mid-word title truncation, and a page that printed at 30% fill
were all found by the gate rather than by a reader.

---

## Exit codes

The CLI uses distinct codes so a Stripe webhook wrapper can tell "the buyer
sent garbage" from "our copy bank has a hole in it" without parsing stderr:

| Code | Meaning |
|---|---|
| 0 | Success |
| 2 | Bad input — buyer's result was unusable |
| 3 | Copy-bank bug — ours |
| 4 | QA gate blocked the save — ours |
| 5 | Layout overflow — ours |

---

## Tests

```bash
pip install pytest && python -m pytest tests/ -q
```

152 tests: every core/secondary pairing built and QA'd, every relationship
rendered, hostile input fuzzed, page count and byte-determinism verified.

---

## Two things to check before you ship

1. **Archetype names.** `src/lib/enneagram.ts` wasn't in the zip you sent
   (only changed files were), so I authored the nine names here —
   The Perfector, The Overgiver, The Frontrunner, The Deep Feeler, The Vault,
   The Sentinel, The Escape Artist, The Force, The Peacekeeper. If your site
   uses different names, edit `ARCHETYPES[n].name` in `content.py`; nothing
   else needs to change. A buyer seeing one name on the results page and a
   different one in the PDF is the same trust problem as the price drift I
   flagged last time.

2. **Wiring it to Stripe.** Right now this is a CLI. The natural next step is
   a small webhook handler: on `checkout.session.completed`, read the `s` and
   `relationship` values you passed as Stripe metadata, call `generate()`, and
   email the file. Two things to get right there — pass `allow_unscored=True`
   so a paid download never hard-fails, and log `report.violations` and
   `report.profile.warnings` so a degraded manual reaches you before it
   reaches a review.

## Layout notes

A5, not A4. At this word count a 24-page A4 document prints about 30% full,
which reads as padding; A5 puts the same copy at book density and is what
someone actually reads on a phone from a Stripe receipt. Page fill now sits
around 55–75%.
