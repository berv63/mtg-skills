# Reference: mtg-checklist

## Running without Python installed

`template.py` only uses the standard library (`html`, `json`) — no venv or pip install needed to
generate the HTML. If neither `python` nor `python3` resolves on the machine, run it in Docker
instead, mounting the project folder (the one containing `template.py` and `color_lookup.json`)
as the working directory:

```bash
docker run --rm -v "$(pwd):/work" -w /work python:3-slim python template.py
```

On Windows PowerShell, use `${PWD}` instead of `$(pwd)`:

```powershell
docker run --rm -v "${PWD}:/work" -w /work python:3-slim python template.py
```

This pulls the official `python:3-slim` image on first run (needs internet access once), then
executes fully offline. No custom Dockerfile is required for this step.

The optional pagination-calibration step (REFERENCE.md "Measuring real page fit") additionally
needs `pymupdf` and `pypdf`, which aren't in the base image. Either `pip install` them inside a
throwaway container, or bake a small image once and reuse it:

```bash
docker run --rm -v "$(pwd):/work" -w /work python:3-slim \
  bash -c "pip install --quiet pymupdf pypdf && python measure.py"
```

Headless Edge/Chrome for the actual PDF render still has to run on the host (or a browser-capable
container) — the calibration script above only covers the pixel-measurement/text-extraction half
that's pure Python.

## Classifying finishes

Real MTG products mix products/sources into one printed "finish-level item" count, which is
almost always a multiple of the true row count — don't mistake that multiplier for extra
finishes. Check: `stated_count / actual_distinct_rows` should be a small integer (2, 3...). If
it isn't a clean integer, you've mis-split the section.

- **NF/TF (default frame, e.g. Play Boosters):** non-foil and traditional foil share the *same*
  collector number. A stated count of `cards * 2` confirms this.
- **NF/SF (collector-only alternate frame — Dragon Hoard, Book Cover, "Classic Artist," etc.):**
  the surge-foil printing gets its *own* collector number, offset from the non-foil one by a
  fixed amount for that whole section (e.g. +36, +40 — find the offset by matching card names
  across the two number ranges). Show both numbers in the `#` column as `nf#/sf#`. A stated count
  of `cards * 3` (2 product-source variants of NF + 1 SF) is typical here.
  - **One-off exception:** a single "headliner" card sometimes gets a unique promo finish (e.g.
    Gleaming Gold Foil) with no NF/TF/SF pair at all — one checkbox, footnote it.
- **NF-only (extended art, tokens, basic lands, scene/preview cards):** one real finish. Give it
  one active checkbox and leave the second slot present-but-blank (`<span class="chk blank">`)
  so columns stay aligned. A stated count of `cards * 2` here means 2 product sources, not 2
  finishes — don't assume it's NF/TF just because the math works.
- **Not-yet-released / future support cards:** the source may say "finish not yet officially
  specified." Keep them in the checklist (mode `NF_TF_TBD`), footnote it, don't invent an answer.
- **Same-name promo variants (seasonal/prerelease basic lands, etc.):** several rows can share one
  card name but each is a genuinely distinct printing (different number, different finish) — list
  them as separate rows, don't merge them into one NF/SF pair.
- **Foil-only-only, no NF/TF/SF pair at all (e.g. Neon Ink, Raised Foil headliners, buy-a-box,
  bundle promos):** use mode `SPECIAL:<ABBR>` (e.g. `SPECIAL:NEON`, `SPECIAL:HDLR`) — single
  checkbox, name gets a `(<ABBR>)` suffix, header's second column shows the abbreviation. Always
  footnote what the abbreviation means.
- **Supplemental/"Eternal"-style sets can split finish availability per PRINT, not per frame.**
  Don't assume "default frame = NF/TF, alt frame = NF/SF" like a normal expansion — check Scryfall's
  own `finishes` field per card first (it may already say `['nonfoil']`, `['foil']`, or
  `['nonfoil','foil']` directly — trust that over any frame-based assumption). When some cards in
  such a set have both finishes at one number while others get a *separate* number per finish, auto-detect
  the pairs by grouping same-name prints and matching a `finishes==['nonfoil']` print against a
  `finishes==['foil']` print with identical `frame_effects`/`border_color`/`frame` — that confirms
  they're the same design, just released as two different single-finish objects. If a print has no
  match for its name, it's a genuine single-finish oddity — mode `NF_ONLY` or the mirror `TF_ONLY`
  (single checkbox in the *second* slot instead of the first, for a card that only ever exists in
  foil).

## Check the shared sets/ cache before fetching live

A set's card list never changes after release, so before doing a live Scryfall fetch, check
whether `../sets/<CODE>.json` already exists (sibling `sets/` folder at the repo root — see its
README.md) for every set code this product involves. `<CODE>.json` is an array of `{subSet,
cards}` groups, not a flat card list — the set code is only the filename, not a repeated field.
If it's cached, derive `color_lookup.json` by walking both levels (`for group in data: for card
in group["cards"]: ...`), keying `f"{CODE}:{card['number']}" -> card['color']` — zero network
calls, and each card's `type`/`rarity`/`nonFoilAvailable`/`foilAvailable`/`surgeFoilAvailable`/
`otherFoilAvailable` fields also cover most of what "Classifying finishes" below asks you to work
out by hand. If a set code isn't cached yet, run `sets/build_set.py <CODE>` once (see its
README.md), then proceed the same way — only fall back to the one-off live fetch below for a set
you don't intend to keep.

The cache's `subSet` grouping (see its README.md "The `subSet` grouping") does most of step 1's
section-title work directly — each group's name is Scryfall's own official name for it (scraped
from its set page, e.g. "Dragon Hoard Frame Cards", "Ring Showcases", "Scene: Treasures of
Smaug"), and should be used verbatim as the checklist's section title wherever it's non-null. For
a `subSet: null` group, fall back to bucketing its cards by `treatment` (Base Set / Full Art /
Borderless / Full Art Borderless / Showcase / Extended Art / Poster, derived from structured card
fields) — grouping a `treatment == "Borderless"` cluster further by `artist` can still split out
distinct narrative-scene sub-groups Scryfall's own page left combined (each scene is typically
illustrated by one dedicated artist across all its cards). Only invent a title by hand, informed
by preview/spoiler material or the cards' own art and names, for a sub-group that neither the
scraped grouping nor `treatment`+`artist` separates on its own. After building/rebuilding a set's
cache, run through its README.md "Verifying a build" step with the user before treating it as
trustworthy.

## Deriving mode from cached finish flags

For a card row sourced from `../sets/<CODE>.json` (the normal path now that `mtg-set-builder`
resolves the set first), map its finish flags directly instead of re-classifying by hand:

- `nonFoilAvailable and foilAvailable and not surgeFoilAvailable and not otherFoilAvailable` →
  `NF_TF`.
- `nonFoilAvailable and not foilAvailable` → `NF_ONLY`.
- `not nonFoilAvailable and (foilAvailable or surgeFoilAvailable or otherFoilAvailable)` →
  `TF_ONLY` (unless it's paired into an `NF_SF` row — see below).

**A true two-checkbox `NF_SF` row only exists when the user selected *both* sides of the pair.**
This cache represents a plain-numbered print and its separately-numbered surge/other-foil twin as
two distinct rows — often in two distinct `subSet` groups entirely (e.g. HOB's `Dragon Hoard
Frame Cards` holds the plain-numbered prints, `Dragon Hoard Surge Foils` holds their
separately-numbered surge-foil twins for the *same* 25 designs). Build an `NF_SF` row only by
matching `name` across the *selected* subsets' cards (same approach as `mtg-checklist-needs`'
ownership matching — see that skill's REFERENCE.md "Matching by name, not number"), and only when
both the plain-numbered and separately-numbered prints of that name were actually selected in step
0. If the user selected only one side of such a pair, render that side alone with its own
single-finish mode from the rules above — don't synthesize a checkbox for a subset/finish they
didn't ask for. Verify a couple of known pairs by hand (name + both numbers) before trusting a
bulk pairing pass across a whole set.

## Fetching color data

Only needed as a fallback if the set isn't in `sets/` and you have a specific reason not to cache
it there first. WebFetch returns 403 on Scryfall's API; curl with a browser-like User-Agent works
fine:

```bash
curl -s -A "Mozilla/5.0" "https://api.scryfall.com/cards/search?q=set%3A<code>&order=set&unique=prints" -o page1.json
```

Paginate via the response's `has_more` / `next_page` fields until exhausted. Save each card's
`collector_number`, `colors`, `type_line`. Classify, in this order:

1. `"Land"` in `type_line` → **Land** (a land's `color_identity` often includes the color of mana
   it taps for — ignore that; group by type, not by what it produces).
2. `colors` empty → **Colorless**.
3. `len(colors) == 1` → the matching WUBRG name (White/Blue/Black/Red/Green).
4. otherwise → **Multicolor**.

Display order in the checklist: Colorless → White → Blue → Black → Red → Green → Multicolor →
Land. Adventure/split/MDFC cards carry a top-level `colors` field already merged across faces —
no special handling needed.

## The header-gluing bug (do not reintroduce)

A header must only claim rows that share its color. A naive "grab the next N rows so the header
isn't orphaned" will blindly pull in the *first* row of the next color group too, mislabeling it
under the wrong header. Always re-check each candidate row's group before including it:

```python
keep_rows = []
j = i
while j < n and len(keep_rows) < KEEP_WITH_HEADER:
    if color_group(set_code, row_primary_number(mode, chunk[j])) != group:
        break
    keep_rows.append(chunk[j])
    j += 1
```

## The full pagination model (read this before touching break-inside/break-before)

Pagination is computed entirely in Python (deterministic, exact) — CSS is only asked to place
already-correctly-sized blocks, never to decide where content overflows. Four pieces work
together; don't add one back without the others, and don't remove one without re-checking the
rest still hold:

1. **`chunk_into_columns` fills every column to a unit budget**, greedily. A row costs 1 unit, a
   fresh color-header line costs 1 more (see "Column sizing" below). Normally the budget is
   `UNIT_BUDGET` (a full page), but see (4) for a section's *opening* block.
2. **A section's *last* block is usually short of a full `cols`-worth** — `chunk_into_blocks`
   detects that (fewer than `cols` populated columns come out of the greedy fill) and re-splits
   just that leftover evenly across all `cols` columns, so it reads as `cols` shorter columns
   instead of 1-2 packed full next to empty ones.
3. **`.block-grid + .block-grid` forces a page break** before the 2nd, 3rd, etc. block *within
   the same section* — each such block is sized to `UNIT_BUDGET` (a full page), so giving it a
   full fresh page is always correct.
4. **`page_remaining` threads a leftover-units count from section to section.** After laying out
   a section, its last block's actual usage (via `compute_units`, the *tallest* column in that
   block) is subtracted from whatever budget that block was given, and the remainder — minus
   `SECTION_HEAD_COST` for the next section's own title bar — becomes `first_budget` for the
   *next* section's opening block (via `chunk_into_columns`'s `first_budget` param), provided it
   clears `MIN_USEFUL_LEFTOVER`. This is what lets a short section start filling the tail end of
   the previous page instead of always jumping to a fresh one — and, critically, it sizes that
   opening block to *exactly* what's left, so nothing overflows and nothing needs to fragment.
   Because of this, the first block-grid of a section needs no forced break and no
   `break-inside: avoid` — it was already sized to fit. `.section-head`'s `break-after: avoid`
   plus `.header-group`'s `break-inside: avoid` still guard against a header ending up alone with
   zero or one row before a break.

Do not fall back to letting CSS "just flow" a section's opening block and hoping fragmentation
sorts it out — that produced inconsistent, wrong-looking column splits (verified against real
render output, not a hypothetical) because the browser doesn't know your per-color-header unit
budget. Always compute the exact split in Python first.

If you're tempted to add `break-inside: avoid` back onto `.block-grid` to stop some new edge
case, that's a sign (1)-(4) are broken for the section in question — fix the sizing/budget
threading, don't paper over it with a forced break (that's exactly the regression that motivated
this note).

## Column sizing must account for header density, not just row count

A flat rows-per-column number (e.g. "37 rows fits one page") only holds if every section has a
similar number of color-header lines per column. A section that packs many small color groups
into few cards (e.g. a scattered alternate-frame reprint list) can have 5-10x the header lines of
a normal section for the same row count, and *will* overflow a column sized by row count alone —
the overflow doesn't error, it silently clips (see next section), producing missing card ranges
that look like a data bug but are a sizing bug. Fix: size columns by a unit budget where a row
costs 1 unit and *every* color-group change costs `TRANSITION_COST` extra units
(`chunk_into_columns` in `template.py` does this — don't go back to plain row-count chunking).

**A header transition costs more than +1.** The first cut of this model used `TRANSITION_COST=1`
(a transition = 2 total units), calibrated only against a low-density section. A section that
packs colors much more densely (measured on a real set: an 18-transitions-per-20-rows hotspot,
vs ~5/20 for a normal section) still overflowed at that cost, because a header line's true
vertical cost — the 9px `margin-top` before it, smaller font, its own padding/border — is closer
to 3 total units than 2. Recalibrated to `TRANSITION_COST=3`, `UNIT_BUDGET=43`. If you hit
persistent ~95%+ fill on some page no matter what `UNIT_BUDGET` you try (moving the budget just
shifts *which* rows land in the tight spot, not whether one exists), suspect this exact issue:
find the worst color-transition density in the document first —

```python
for set_code, title, mode, rows in SECTIONS:
    nums = [row_primary_number(mode, r) for r in rows]
    groups = [color_group(set_code, n) for n in nums]
    worst = max(sum(1 for j in range(1, 20) if w[j] != w[j-1]) + 1
                for w in (groups[i:i+20] for i in range(len(groups) - 19)))
    print(title, "worst 20-row transition count:", worst)
```

— before spending time re-tuning `UNIT_BUDGET` alone. A hotspot at 15+/20 needs a higher
`TRANSITION_COST`, not a lower budget.

**Accept an irreducible ceiling on extreme hotspots, don't chase perfection.** Even after
recalibrating, an extreme density hotspot (a stretch where nearly every card is a different
color) can still land a column around ~94-96% fill — full-document pixel measurement across many
`(UNIT_BUDGET, TRANSITION_COST)` combinations showed this ceiling recurring almost identically
regardless of the exact constants, because different values just relocate the hotspot rather than
eliminate its inherent size. Verify no page renders *blank* (the real danger — see below) and that
every row is still present (per-row spot check, not just page count); a page sitting at ~95% that
still renders its content correctly is a cosmetic tightness, not a data-loss bug. Don't burn
excessive time pushing every last page under some arbitrary threshold once those two are clean.

## "Start fresh" must be a REAL page break, or all downstream bookkeeping is fiction

`first_budget` threading (see "The full pagination model" below) decides, for every section,
either "continue with N leftover units" or "start fresh with a full `UNIT_BUDGET`." That second
case is only true if a *real* CSS page break happens there — and originally, nothing enforced
that. A section could be sized as if it got a full fresh page while actually still flowing
right after the previous section's tail with no break at all (because no CSS rule inserted one
for the *first* block of a section — only `.block-grid + .block-grid` did, for a 2nd+ block
*within* one section). The result: every `page_remaining` computed after such a section is
fiction — sometimes producing visible dead whitespace (a small section given a phantom full
budget doesn't use it, and nothing was there to fill the gap), sometimes risking real overflow
(a large section sized for a fresh page that never actually started). This is the actual
mechanism behind "every page has a ton of wasted whitespace" symptom reports.

Fix: whenever the code decides `first_budget = None` for a section that is *not* the very first
in the document (i.e. `page_remaining is not None`), it must add a `force-break` class
(`break-before: page`) to that section — making the "fresh full page" assumption true, not
assumed. Never let a "start fresh" *sizing* decision exist without a corresponding *forced* break.

## Don't continue with a leftover so small it forces an extra, near-empty block

A small-but-"useful" leftover (passing `MIN_USEFUL_LEFTOVER`) can still be too small for the
section's row count: `chunk_into_columns` fills the section's *first* block to that small budget,
then whatever doesn't fit spills into a second block forced onto a fresh page — and if the
section is itself small (e.g. 16 rows), that forced second block ends up using only a sliver of
its full `UNIT_BUDGET`, rendering as a nearly blank page. Fix: before committing to a leftover,
compare `chunk_into_blocks(rows, cols, ..., candidate)` against `chunk_into_blocks(rows, cols,
..., None)` (starting fresh) — only use the leftover if it does not require *more* blocks than
starting fresh would. If it does, decline the leftover (`force-break` kicks in instead, per
above) and let the section start clean in as few blocks as it naturally needs.

Together, these two fixes make `MAX_CHAIN` unnecessary as a hard cap (set to an effectively
unbounded value) — a chain now terminates naturally once `page_remaining - SECTION_HEAD_COST`
drops below `MIN_USEFUL_LEFTOVER`, or once continuing would require an extra block, both of
which are now correctly enforced with a real break when they trigger. The original cap was a
band-aid for a case (cumulative section-chrome overflow) that these two fixes address at the
root instead.

## `overflow:hidden` + print fragmentation silently deletes content

`.section` has `overflow:hidden` for the rounded-corner card look on screen. If a section's total
content is taller than one page and needs to fragment across a page break, browsers computing
that fragmentation against a box with `overflow:hidden` can **clip** whatever falls outside the
first page's worth of height instead of flowing it to the next page — no error, no warning, the
rows just vanish from the render even though they're correctly in the HTML. Symptom: a column
shows the first N rows then jumps straight to a much higher number, skipping a chunk in between,
and the skipped rows don't appear anywhere else in the document either. Diagnosis: check the raw
HTML has the missing rows (it will); if so, this is print fragmentation clipping, not a data bug.
Fix already applied: `@media print { .section { overflow: visible; } }` — keep it, don't remove it
as a "cleanup."

## Measuring real page fit

Don't tune `UNIT_BUDGET` by guessing from repeated user feedback rounds — render for real
and measure. On Windows, headless Edge needs its own `--user-data-dir` (a fresh scratch folder)
or it silently fails to write the PDF ("Access is denied"), and the target URL must be a proper
`file:///C:/...` path (use `cygpath -m` from Git Bash to convert):

```bash
WIN_HTML=$(cygpath -m "/path/to/checklist.html")
WIN_PDF=$(cygpath -m "/path/to/check.pdf")
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless --disable-gpu --no-sandbox \
  --user-data-dir="/path/to/scratch/edge-profile" \
  --print-to-pdf="$WIN_PDF" "file:///$WIN_HTML"
```

Then measure actual ink density per column band (not just "is there any pixel") to find where
real content ends, excluding the footer margin:

```python
from PIL import Image
img = Image.open("page1.png").convert("L")   # render via PyMuPDF: pip install pymupdf
w, h = img.size
px = img.load()
for xs, xe in [(60, 470), (560, 970), (1050, 1460)]:  # approx column bands
    last_y = 0
    for y in range(280, h - 70):                       # skip title and footer
        if sum(1 for x in range(xs, xe, 3) if px[x, y] < 150) > 5:
            last_y = y
    print(xs, xe, last_y, f"{last_y/h*100:.1f}%")
```

The column with the *most* stacked color-header lines is the tightest one — size
`UNIT_BUDGET` to that column's real capacity, not an average. `pip install pymupdf` renders
PDF pages to PNG (`doc[i].get_pixmap(matrix=fitz.Matrix(2.5,2.5))`) without needing poppler.

**Leave real margin, don't chase the exact edge.** A value that measures as "just barely fits"
(content ending past ~94% of page height) is fragile two ways: it doesn't survive small rendering
differences between a headless print-to-pdf and the user's own browser/printer (this is what
caused a real bleed-onto-next-page report after shipping a value calibrated to ~95.5%), and — seen
once on a real set — a specific row-count value can trigger a genuine Chromium print-fragmentation
bug where an entire first page renders blank and its content silently shifts to page 2, while the
row count one or two away renders perfectly fine. Always re-render and check *all* page lengths
(`len(page.extract_text())` for every page, not just page 1) after picking a final value — a
suspiciously short page 1 (just the title/legend, no rows) means this bug, not a content problem.
If it happens, don't debug the CSS — just try an adjacent row count instead. Prefer a value with
genuine headroom (content ending noticeably before ~94%) over the tightest one that technically fits.

## Verifying placement

`pypdf` (already available) extracts page text for a cheap spot check — search for
`f"{number} {name}"` (not just the name, since names repeat across a set's alternate-frame
sections) to disambiguate which printing you're actually locating:

```python
from pypdf import PdfReader
pages = [(p.extract_text() or "") for p in PdfReader("check.pdf").pages]
f"{num} {name}" in pages[expected_page_index]
```
