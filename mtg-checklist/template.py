# -*- coding: utf-8 -*-
"""Reusable engine for a compact, print-ready MTG finish-level checklist.

Validated on The Hobbit (HOB/HOC/THOB, 418 rows, 6 printed pages). To use for a new set:

1. Replace TITLE, SET_COLORS, and the example SECTIONS below with the real set data
   (see SKILL.md step 1 for how to work out each section's `mode`).
2. Fetch real color data (SKILL.md step 2 / REFERENCE.md "Fetching color data") into
   color_lookup.json, keyed "SETCODE:number" -> "Colorless"|"White"|...|"Land".
3. Run this script, then calibrate ROWS_PER_COLUMN against a real PDF render
   (REFERENCE.md "Measuring real page fit") before delivering.

Do not restructure the header/row logic without re-reading REFERENCE.md's
"header-gluing bug" note — it's easy to reintroduce.
"""
import html
import json

TITLE = "Example Set — MTG Finish-Level Checklist"

with open("color_lookup.json", encoding="utf-8") as _f:
    COLOR_LOOKUP = json.load(_f)

def color_group(set_code, number):
    return COLOR_LOOKUP.get(f"{set_code}:{number}", "Colorless")

# ---------------------------------------------------------------------------
# Data model — replace everything below this line with the real set's data.
# ---------------------------------------------------------------------------
# Each section: (set_code, section_title, mode, rows)
#   mode: 'NF_TF'      -> two checkboxes, same number, labels NF/TF (default frame)
#         'NF_SF'      -> two checkboxes, numbers may differ (nf_num, sf_num), labels NF/SF
#                         (collector-only alternate frame; the SF number is offset from NF)
#         'NF_ONLY'    -> single active checkbox in the NF slot, TF slot blank
#         'TF_ONLY'    -> mirror of NF_ONLY: single active checkbox in the TF slot (a print
#                         that genuinely only ever exists in foil, no nonfoil counterpart)
#         'SPECIAL:X'  -> single checkbox for a one-off promo finish with no NF/TF/SF pair at
#                         all (e.g. SPECIAL:NEON, SPECIAL:HDLR for Gleaming Gold/Raised Foil/
#                         Neon Ink headliners); X becomes the header's second column label and
#                         a "(X)" suffix on the card name
#         'NF_TF_TBD'  -> like NF_TF but the second finish isn't confirmed yet (future cards)
#         'SEASONAL'   -> mixed rows, each row is single-finish (NF or SF), header shows NF | SF
#                         (same name, genuinely different printings — don't merge them)
#
# Row tuples per mode:
#   NF_TF / NF_TF_TBD / NF_ONLY / TF_ONLY / SPECIAL:* : (number, name, rarity)
#   NF_SF                                             : (nf_number, sf_number, name, rarity)
#   SEASONAL                                          : (number, name, rarity, finish)  finish in {'NF','SF'}

EXAMPLE_MAIN_SET = [
    (1, "Example Common Creature", "C"),
    (2, "Example Legend", "R"),
    (3, "Example Mythic", "MR"),
]

EXAMPLE_ALT_FRAME = [(nf, nf + 36, name, rarity) for nf, name, rarity in [
    (100, "Example Alt-Frame Legend", "R"),
]]

SECTIONS = [
    ("EX1", "Main Set / Default Frame", "NF_TF", EXAMPLE_MAIN_SET),
    ("EX1", "Alternate Frame (Collector)", "NF_SF", EXAMPLE_ALT_FRAME),
]

SET_COLORS = {"EX1": "#a8842f"}  # one accent color per set code, used on section borders

# ---------------------------------------------------------------------------
# Engine — stable; edit only if the user asks for a layout change.
# ---------------------------------------------------------------------------

RARITY_CLASS = {"C": "r-c", "UC": "r-uc", "R": "r-r", "MR": "r-mr"}
UNIT_BUDGET = 43  # rows + header-transitions per column; recalibrate against a real PDF render
TRANSITION_COST = 3  # a color-header row's true cost, incl. the 9px margin-top before it —
                     # measured higher than a plain row (cost 1); a section with many small
                     # color groups is visually taller per-row than one with few large ones
KEEP_WITH_HEADER = 2  # a header must never be stranded with fewer than this many rows below it
SECTION_HEAD_COST = 2  # approx unit-cost of a new section's title bar + border chrome
MIN_USEFUL_LEFTOVER = 6  # below this many leftover units, just start the next section fresh
MAX_CHAIN = 999  # effectively unbounded now that every "start fresh" decision forces a real
                 # CSS page break (see force_break below) and SECTION_HEAD_COST is deducted at
                 # every continuation step — the chain naturally stops once page_remaining runs
                 # out, without needing an artificial cap on top of that

def esc(s):
    return html.escape(str(s), quote=True)

def row_html(mode, row):
    if mode == "NF_TF":
        num, name, rarity = row
        return f"""<div class="card-row">
  <label class="chk"><input type="checkbox"></label>
  <label class="chk"><input type="checkbox"></label>
  <span class="num">{num}</span>
  <span class="name">{esc(name)}</span>
  <span class="rarity {RARITY_CLASS[rarity]}">{rarity}</span>
</div>"""
    if mode == "NF_TF_TBD":
        num, name, rarity = row
        return f"""<div class="card-row">
  <label class="chk"><input type="checkbox"></label>
  <label class="chk tbd" title="Finish not yet officially specified"><input type="checkbox"></label>
  <span class="num">{num}</span>
  <span class="name">{esc(name)}</span>
  <span class="rarity {RARITY_CLASS[rarity]}">{rarity}</span>
</div>"""
    if mode == "NF_SF":
        nf_num, sf_num, name, rarity = row
        return f"""<div class="card-row">
  <label class="chk"><input type="checkbox"></label>
  <label class="chk"><input type="checkbox"></label>
  <span class="num">{nf_num}/{sf_num}</span>
  <span class="name">{esc(name)}</span>
  <span class="rarity {RARITY_CLASS[rarity]}">{rarity}</span>
</div>"""
    if mode == "NF_ONLY":
        num, name, rarity = row
        return f"""<div class="card-row">
  <label class="chk"><input type="checkbox"></label>
  <span class="chk blank"></span>
  <span class="num">{num}</span>
  <span class="name">{esc(name)}</span>
  <span class="rarity {RARITY_CLASS[rarity]}">{rarity}</span>
</div>"""
    if mode == "TF_ONLY":
        # mirror of NF_ONLY for a card that exists ONLY in its foil printing
        num, name, rarity = row
        return f"""<div class="card-row">
  <span class="chk blank"></span>
  <label class="chk"><input type="checkbox"></label>
  <span class="num">{num}</span>
  <span class="name">{esc(name)}</span>
  <span class="rarity {RARITY_CLASS[rarity]}">{rarity}</span>
</div>"""
    if mode.startswith("SPECIAL:"):
        # a one-off promo finish with no NF/TF/SF pair at all (e.g. a raised-foil
        # headliner, neon ink treatment, buy-a-box/bundle promo) — single checkbox,
        # name annotated with the mode's abbreviation (mode = "SPECIAL:<ABBR>").
        abbr = mode.split(":", 1)[1]
        num, name, rarity = row
        return f"""<div class="card-row">
  <label class="chk"><input type="checkbox"></label>
  <span class="chk blank"></span>
  <span class="num">{num}</span>
  <span class="name">{esc(name)} <em>({esc(abbr)})</em></span>
  <span class="rarity {RARITY_CLASS[rarity]}">{rarity}</span>
</div>"""
    if mode == "SEASONAL":
        num, name, rarity, finish = row
        first, second = ("<label class=\"chk\"><input type=\"checkbox\"></label>", '<span class="chk blank"></span>')
        if finish != "NF":
            first, second = second, first
        return f"""<div class="card-row">
  {first}
  {second}
  <span class="num">{num}</span>
  <span class="name">{esc(name)}</span>
  <span class="rarity {RARITY_CLASS[rarity]}">{rarity}</span>
</div>"""
    raise ValueError(mode)

def header_labels(mode):
    if mode == "NF_TF":
        return "NF", "TF"
    if mode == "NF_TF_TBD":
        return "NF", "TF*"
    if mode in ("NF_SF", "SEASONAL"):
        return "NF", "SF"
    if mode == "TF_ONLY":
        return "NF", "TF"
    if mode.startswith("SPECIAL:"):
        return "NF", mode.split(":", 1)[1]
    return "NF", ""

def row_primary_number(mode, row):
    """The collector number to key the color lookup off of (NF number for NF_SF rows)."""
    return row[0]

def compute_units(col, set_code, mode):
    """Total (rows + color-header) units actually used by one rendered column."""
    units = 0
    last_group = None
    for row in col:
        grp = color_group(set_code, row_primary_number(mode, row))
        units += 1 if grp == last_group else TRANSITION_COST
        last_group = grp
    return units

def chunk_into_columns(rows, cols, set_code, mode, first_budget=None):
    """Fill each column up to a budget of "units", where a row costs 1 unit and a fresh
    color-header line (whenever the color group changes) costs 1 extra unit. A flat row
    count alone underestimates tall columns that pack many small color groups (lots of
    header lines) and overflows the page — this keeps real vertical space in mind instead.

    The first `cols` columns (i.e. this section's opening block) use `first_budget` instead
    of UNIT_BUDGET when given — this lets a section that starts partway down an already
    partly-filled page size its first block to whatever room is actually left, rather than
    assuming a full fresh page.
    """
    columns = []
    i = 0
    n = len(rows)
    col_index = 0
    while i < n:
        budget = first_budget if (first_budget is not None and col_index < cols) else UNIT_BUDGET
        last_group = None
        units = 0
        j = i
        while j < n:
            grp = color_group(set_code, row_primary_number(mode, rows[j]))
            cost = 1 if grp == last_group else TRANSITION_COST
            if units + cost > budget and j > i:
                break
            units += cost
            last_group = grp
            j += 1
        columns.append(rows[i:j])
        i = j
        col_index += 1
    return columns

def chunk_into_blocks(rows, cols, set_code, mode, first_budget=None):
    """Split rows into page-sized blocks of `cols` columns each (see chunk_into_columns).

    The final block of a section is usually shorter than a full page's worth. Greedily
    filling columns to their budget would pack the first 1-2 columns full and leave the
    rest empty; instead spread that leftover evenly across all `cols` columns so it reads
    as `cols` shorter columns (and the next section can start sooner on the same page).
    """
    columns = chunk_into_columns(rows, cols, set_code, mode, first_budget)
    result = []
    for k in range(0, len(columns), cols):
        block_cols = columns[k:k + cols]
        if len(block_cols) < cols:
            leftover_rows = [r for col in block_cols for r in col]
            per_col = -(-len(leftover_rows) // cols)  # ceil
            block_cols = [leftover_rows[i:i + per_col] for i in range(0, len(leftover_rows), per_col)]
        while len(block_cols) < cols:
            block_cols.append([])
        result.append(block_cols)
    return result

def build():
    parts = []
    parts.append(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{esc(TITLE)}</title>
<style>
:root{{
  --bg:#fbfaf7; --ink:#20201c; --sub:#6b6558; --line:#d8d2c4;
  --accent:#a8842f; --paper:#ffffff; --chk-border:#8c8672;
  --c-common:#4a4a48; --c-uncommon:#2a5f8a; --c-rare:#8a6a1f; --c-mythic:#9c2b2b;
}}
@media (prefers-color-scheme: dark){{
  :root:not([data-theme="light"]){{
    --bg:#1c1a16; --ink:#eae6da; --sub:#a39a86; --line:#4a4436;
    --paper:#242019; --chk-border:#8c8672;
    --c-common:#c9c4b6; --c-uncommon:#7fb3e0; --c-rare:#e0b95c; --c-mythic:#e2726f;
  }}
}}
:root[data-theme="dark"]{{
  --bg:#1c1a16; --ink:#eae6da; --sub:#a39a86; --line:#4a4436;
  --paper:#242019; --chk-border:#8c8672;
  --c-common:#c9c4b6; --c-uncommon:#7fb3e0; --c-rare:#e0b95c; --c-mythic:#e2726f;
}}
*{{box-sizing:border-box;}}
body{{
  background:var(--bg); color:var(--ink); margin:0; padding:24px;
  font-family:"Segoe UI",Calibri,Arial,sans-serif; font-size:12px;
}}
h1{{font-size:22px; margin:0 0 2px 0; letter-spacing:.3px;}}
.subtitle{{color:var(--sub); font-size:12px; margin:0 0 18px 0;}}
.legend{{
  display:flex; flex-wrap:wrap; gap:14px; font-size:11px; color:var(--sub);
  border:1px solid var(--line); border-radius:8px; padding:10px 14px; margin-bottom:22px; background:var(--paper);
}}
.legend b{{color:var(--ink);}}
.section{{
  break-inside: avoid-page; page-break-inside: avoid;
  margin-bottom:26px; border:1px solid var(--line); border-radius:10px; overflow:hidden; background:var(--paper);
}}
.section.force-break{{
  break-before: page; page-break-before: always;
}}
.section-head{{
  display:flex; align-items:baseline; justify-content:space-between; gap:10px;
  padding:10px 16px; border-bottom:2px solid var(--set-color,var(--accent));
  break-after: avoid; page-break-after: avoid;
}}
.section-head .set-tag{{
  font-size:10px; font-weight:700; letter-spacing:.08em; color:var(--set-color,var(--accent));
  text-transform:uppercase; margin-right:8px;
}}
.section-head h2{{font-size:14px; margin:0; display:inline;}}
.section-count{{font-size:10px; color:var(--sub); white-space:nowrap;}}
.block-grid{{
  display:grid; grid-template-columns: repeat(var(--cols, 3), 1fr);
  column-gap:14px; padding:4px 16px 10px;
}}
.block-grid + .block-grid{{
  break-before: page; page-break-before: always;
}}
.col-block{{
  min-width:0; border-left:1px solid var(--line);
}}
.col-block:first-child{{border-left:none;}}
.header-group{{
  break-inside: avoid; page-break-inside: avoid;
}}
.header-group:not(:first-child){{
  margin-top:9px;
}}
.col-block .col-header{{
  display:flex; align-items:center; gap:4px; padding:0 0 3px 10px; margin-bottom:2px; font-size:9px; font-weight:700;
  letter-spacing:.06em; text-transform:uppercase; color:var(--sub); border-bottom:1px solid var(--line);
  break-inside: avoid;
}}
.col-block:first-child .col-header{{padding-left:0;}}
.col-header .chk-h{{flex:0 0 15px; text-align:center;}}
.col-header .num-h{{flex:0 0 40px;}}
.col-header .name-h{{
  flex:1; display:flex; align-items:center; gap:4px; min-width:0;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}}
.col-header .rarity-h{{flex:0 0 22px; text-align:right;}}
.card-row{{
  display:flex; align-items:center; gap:4px; padding:2.5px 0 2.5px 10px;
  break-inside: avoid; page-break-inside: avoid;
  border-bottom:1px solid color-mix(in srgb, var(--line) 60%, transparent);
}}
.col-block:first-child .card-row{{padding-left:0;}}
.card-row:hover{{background:color-mix(in srgb, var(--accent) 6%, transparent);}}
.chk{{width:15px; text-align:center; flex:0 0 15px;}}
.chk input[type="checkbox"]{{
  width:11px; height:11px; margin:0; accent-color:var(--accent); border:1px solid var(--chk-border);
}}
.chk.blank, .chk.tbd{{opacity:.35;}}
.num{{flex:0 0 40px; font-variant-numeric:tabular-nums; color:var(--sub); font-size:10.5px;}}
.name{{flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}}
.rarity{{flex:0 0 22px; text-align:right; font-weight:700; font-size:10px;}}
.r-c{{color:var(--c-common);}} .r-uc{{color:var(--c-uncommon);}} .r-r{{color:var(--c-rare);}} .r-mr{{color:var(--c-mythic);}}
.footnote{{font-size:9.5px; color:var(--sub); padding:6px 16px 10px; font-style:italic;}}
@media print{{
  body{{padding:6px; font-size:10.5px; background:#fff; color:#000;}}
  .section{{break-inside:auto; overflow:visible;}}
  .legend{{display:none;}}
}}
@page{{ margin: 10mm; }}
</style>
</head>
<body>
<h1>{esc(TITLE)}</h1>
<p class="subtitle">Compact checkbox edition &middot; NF = Non-foil &middot; TF = Traditional Foil &middot; SF = Surge Foil &middot; GGF = Gleaming Gold Foil &middot; R = Rarity (C / UC / R / MR)</p>
<div class="legend">
  <span><b>C</b> = Common</span>
  <span><b>UC</b> = Uncommon</span>
  <span><b>R</b> = Rare</span>
  <span><b>MR</b> = Mythic Rare</span>
  <span>Blank checkbox slot = that finish isn't produced for this card</span>
  <span>Numbers shown as <b>NF#/SF#</b> where the foil version has its own distinct collector number</span>
  <span>Cards stay in numeric order; the column header updates to show the color of the cards below it, and repeats wherever the color changes</span>
</div>
""")

    page_remaining = None  # units left on the current page; None = start fresh
    chain_depth = 0  # consecutive sections that have continued onto the same page
    for set_code, title, mode, rows in SECTIONS:
        nf_label, second_label = header_labels(mode)
        color = SET_COLORS.get(set_code, "#a8842f")
        cols = 3 if len(rows) > 20 else 2

        first_budget = None
        if page_remaining is not None and chain_depth < MAX_CHAIN:
            candidate = page_remaining - SECTION_HEAD_COST
            if candidate >= MIN_USEFUL_LEFTOVER:
                # Only actually use this leftover if doing so doesn't force MORE blocks (pages)
                # for this section than starting fresh would — otherwise a small leftover just
                # produces a tiny first block plus a wastefully near-empty forced-fresh second
                # block, which is worse than simply starting the whole section fresh.
                trial = chunk_into_blocks(rows, cols, set_code, mode, candidate)
                fresh = chunk_into_blocks(rows, cols, set_code, mode, None)
                if len(trial) <= len(fresh):
                    first_budget = candidate

        # If we're NOT continuing (first_budget is None) but this also isn't the very first
        # section in the document (page_remaining is not None), the sizing below is about to
        # assume a full fresh page of room — so it must actually GET one via a real CSS break,
        # rather than silently relying on however natural flow happens to fall out. Otherwise
        # the budget bookkeeping for every section after this one is computed against a page
        # that never truly started, producing wrong (wasteful or overflowing) results downstream.
        force_break = page_remaining is not None and first_budget is None
        section_class = "section force-break" if force_break else "section"

        parts.append(f'<div class="{section_class}" style="--set-color:{color}">')
        parts.append(f'''<div class="section-head">
  <div><span class="set-tag">{esc(set_code)}</span><h2>{esc(title)}</h2></div>
  <span class="section-count">{len(rows)} cards</span>
</div>''')

        def col_header_html(group_name):
            return f'''<div class="col-header">
  <span class="chk-h">{nf_label}</span>
  <span class="chk-h">{second_label}</span>
  <span class="num-h">#</span>
  <span class="name-h">Card Name ({esc(group_name)})</span>
  <span class="rarity-h">R</span>
</div>'''

        blocks = chunk_into_blocks(rows, cols, set_code, mode, first_budget)

        # The last block just computed determines how much room is left on the page it ends
        # on, for the next section to potentially continue filling.
        last_block_budget = UNIT_BUDGET if len(blocks) > 1 else (first_budget if first_budget is not None else UNIT_BUDGET)
        last_block = blocks[-1]
        used = max((compute_units(c, set_code, mode) for c in last_block if c), default=0)

        if len(blocks) > 1:
            chain_depth = 0
        elif first_budget is not None:
            chain_depth += 1
        else:
            chain_depth = 0
        page_remaining = max(0, last_block_budget - used)

        for col_chunks in blocks:
            parts.append(f'<div class="block-grid" style="--cols:{cols}">')
            for chunk in col_chunks:
                parts.append('<div class="col-block">')
                last_group = None
                i = 0
                n = len(chunk)
                while i < n:
                    row = chunk[i]
                    num = row_primary_number(mode, row)
                    group = color_group(set_code, num)
                    if group != last_group:
                        # Keep the header glued to its first couple of rows — of the SAME
                        # group only. See REFERENCE.md "header-gluing bug": grabbing rows
                        # blindly mislabels the next group's first card.
                        keep_rows = []
                        j = i
                        while j < n and len(keep_rows) < KEEP_WITH_HEADER:
                            r = chunk[j]
                            g = color_group(set_code, row_primary_number(mode, r))
                            if g != group:
                                break
                            keep_rows.append(r)
                            j += 1
                        parts.append('<div class="header-group">')
                        parts.append(col_header_html(group))
                        for kr in keep_rows:
                            parts.append(row_html(mode, kr))
                        parts.append("</div>")
                        i = j
                        last_group = group
                    else:
                        parts.append(row_html(mode, row))
                        i += 1
                parts.append("</div>")
            parts.append("</div>")

        if mode == "NF_TF_TBD":
            parts.append('<div class="footnote">*These cards are announced for future eternal-legal supporting products; exact foil treatment has not yet been specified.</div>')
        if mode == "GGF_ONLY":
            parts.append('<div class="footnote">Gleaming Gold Foil is a unique Collector Booster headliner treatment &mdash; it does not have separate NF/TF/SF prints.</div>')
        if mode == "SEASONAL":
            parts.append('<div class="footnote">Each row is a distinct seasonal/promo print of the same card, not a paired NF/SF version of one print.</div>')
        parts.append("</div>")

    total = sum(len(rows) for _, _, _, rows in SECTIONS)
    parts.append(f'<p class="subtitle">Total unique card-number rows: {total}</p>')
    parts.append("</body></html>")
    return "\n".join(parts)

if __name__ == "__main__":
    out = build()
    with open("output.html", "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote output.html, length", len(out))
