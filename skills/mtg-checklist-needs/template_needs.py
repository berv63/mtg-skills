# -*- coding: utf-8 -*-
"""Reusable engine for the "Needs" variant of a compact, print-ready MTG checklist —
same layout/pagination as mtg-checklist's template.py, but each row gets a Needs column
(copies still wanted) and an Available column (owned copies you'd trade away) instead of
finish checkboxes.

To use for a new set:

1. Replace TITLE, SET_COLORS, and the example SECTIONS below with the real set data —
   reuse the exact same SECTIONS/color_lookup.json built for this set's mtg-checklist
   run (see that skill's SKILL.md step 1 / REFERENCE.md "Classifying finishes"; the mode
   values are identical here, the checkboxes just aren't rendered).
2. Run compute_needs.py first so needs_result.json exists.
3. Run this script, then calibrate UNIT_BUDGET against a real PDF render exactly as for
   mtg-checklist's template.py (see that skill's REFERENCE.md "Measuring real page fit").

Do not restructure the pagination logic without re-reading mtg-checklist/REFERENCE.md's
"header-gluing bug" and "full pagination model" notes — this file shares that engine
verbatim; a fix made there needs to be ported here too (and vice versa).
"""
import html
import json

TITLE = "Example Set — MTG Finish-Level Checklist"

with open("color_lookup.json", encoding="utf-8") as _f:
    COLOR_LOOKUP = json.load(_f)

def color_group(set_code, number):
    return COLOR_LOOKUP.get(f"{set_code}:{number}", "Colorless")

with open("needs_result.json", encoding="utf-8") as _f:
    _NEEDS_DATA = json.load(_f)
RULES_APPLIED = _NEEDS_DATA.get("rules", [])
EXCLUDED_SUBSETS = _NEEDS_DATA.get("excluded_subsets", [])
# Keyed by (set_code, primary collector number) — see REFERENCE.md "Matching by printing vs.
# by name": only a base-set row ever pools ownership across other printings of its name: every
# other row is matched to its own exact printing. "needs" is None for a row in a Rule #6
# excluded subSet (not tracked, shown as "—").
NEEDS_BY_KEY = {
    (r["set_code"], r["primary_number"]): {"needs": r["needs"], "available": r["available"]}
    for r in _NEEDS_DATA["results"]
}

# ---------------------------------------------------------------------------
# Data model — replace everything below this line with the real set's data.
# See mtg-checklist's template.py for the full mode reference; identical here.
# ---------------------------------------------------------------------------

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
RULE_LABELS = {
    "1": "#1 at least 1 of each card",
    "2": "#2 at least 4 of each card",
    "3": "#3 at least 2 of each R/MR",
    "4": "#4 trade down to 2 of each R/MR",
    "5": "#5 base-set Needs pools alt-art ownership",
    "6": "#6 don't-care subsets excluded",
}
UNIT_BUDGET = 43  # rows + header-transitions per column; recalibrate against a real PDF render
TRANSITION_COST = 3  # a color-header row's true cost, incl. the 9px margin-top before it
KEEP_WITH_HEADER = 2  # a header must never be stranded with fewer than this many rows below it
SECTION_HEAD_COST = 2  # approx unit-cost of a new section's title bar + border chrome
MIN_USEFUL_LEFTOVER = 6  # below this many leftover units, just start the next section fresh
MAX_CHAIN = 999  # effectively unbounded — see mtg-checklist/REFERENCE.md "full pagination model"

def esc(s):
    return html.escape(str(s), quote=True)

def extract_num_name_rarity(mode, row):
    """Reduce any row tuple shape down to (display_number, name, rarity)."""
    if mode == "NF_SF":
        nf_num, sf_num, name, rarity = row
        return f"{nf_num}/{sf_num}", name, rarity
    if mode == "SEASONAL":
        num, name, rarity, _finish = row
        return num, name, rarity
    # NF_TF, NF_TF_TBD, NF_ONLY, TF_ONLY, SPECIAL:* all share (number, name, rarity)
    num, name, rarity = row
    return num, name, rarity

def row_primary_number(mode, row):
    """The collector number to key the color lookup off of (NF number for NF_SF rows)."""
    return row[0]

def row_html(set_code, mode, row):
    num, name, rarity = extract_num_name_rarity(mode, row)
    # str() guards against a SECTIONS row using an int literal for its number while
    # needs_result.json's primary_number (from compute_needs.py's CARD_LIST) is always a string —
    # a silent type mismatch here would make every row's lookup miss and show "?".
    primary_number = str(row_primary_number(mode, row))
    entry = NEEDS_BY_KEY.get((set_code, primary_number))
    if entry is None:
        # "?" flags a CARD_LIST row missing from compute_needs.py — a data bug, not a real result.
        needs_display, avail_display = "?", "?"
    else:
        needs, available = entry["needs"], entry["available"]
        needs_display = "—" if needs is None else ("" if needs == 0 else str(needs))
        avail_display = "" if available == 0 else str(available)
    return f"""<div class="card-row">
  <span class="needs">{needs_display}</span>
  <span class="avail">{avail_display}</span>
  <span class="num">{num}</span>
  <span class="name">{esc(name)}</span>
  <span class="rarity {RARITY_CLASS[rarity]}">{rarity}</span>
</div>"""

def compute_units(col, set_code, mode):
    units = 0
    last_group = None
    for row in col:
        grp = color_group(set_code, row_primary_number(mode, row))
        units += 1 if grp == last_group else TRANSITION_COST
        last_group = grp
    return units

def chunk_into_columns(rows, cols, set_code, mode, first_budget=None):
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
    rules_line = ", ".join(RULE_LABELS.get(r, "#" + r) for r in RULES_APPLIED) or \
        "none (defaults: 4 C/UC, 1 R/MR)"
    not_tracked_line = (" &middot; not tracked: " + esc(", ".join(EXCLUDED_SUBSETS))) if EXCLUDED_SUBSETS else ""

    parts = []
    parts.append(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{esc(TITLE)} (Needs)</title>
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
.col-header .needs-h{{flex:0 0 34px; text-align:center;}}
.col-header .avail-h{{flex:0 0 34px; text-align:center;}}
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
.needs{{
  flex:0 0 34px; height:11px; border-bottom:1px solid var(--chk-border);
  text-align:center; font-size:10.5px; font-weight:700; color:var(--ink);
}}
.avail{{
  flex:0 0 34px; height:11px; border-bottom:1px solid var(--chk-border);
  text-align:center; font-size:10.5px; font-weight:700; color:var(--sub);
}}
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
<p class="subtitle">Needs/Available edition &middot; R = Rarity (C / UC / R / MR)</p>
<div class="legend">
  <span><b>C</b> = Common</span>
  <span><b>UC</b> = Uncommon</span>
  <span><b>R</b> = Rare</span>
  <span><b>MR</b> = Mythic Rare</span>
  <span><b>Needs</b> = copies still wanted; blank = already met, <b>&mdash;</b> = not tracked (a
  Rule #6 "don't care" subset), <b>?</b> = missing from compute_needs.py's card list (data bug)</span>
  <span><b>Avail</b> = owned copies of this exact printing you'd trade away; blank = none spare</span>
  <span>Cards stay in numeric order; the column header updates to show the color of the cards below it, and repeats wherever the color changes</span>
  <span>Completion rules applied: {esc(rules_line)}{not_tracked_line}</span>
</div>
""")

    page_remaining = None
    chain_depth = 0
    for set_code, title, mode, rows in SECTIONS:
        color = SET_COLORS.get(set_code, "#a8842f")
        cols = 3 if len(rows) > 20 else 2

        first_budget = None
        if page_remaining is not None and chain_depth < MAX_CHAIN:
            candidate = page_remaining - SECTION_HEAD_COST
            if candidate >= MIN_USEFUL_LEFTOVER:
                trial = chunk_into_blocks(rows, cols, set_code, mode, candidate)
                fresh = chunk_into_blocks(rows, cols, set_code, mode, None)
                if len(trial) <= len(fresh):
                    first_budget = candidate

        force_break = page_remaining is not None and first_budget is None
        section_class = "section force-break" if force_break else "section"

        parts.append(f'<div class="{section_class}" style="--set-color:{color}">')
        parts.append(f'''<div class="section-head">
  <div><span class="set-tag">{esc(set_code)}</span><h2>{esc(title)}</h2></div>
  <span class="section-count">{len(rows)} cards</span>
</div>''')

        def col_header_html(group_name):
            return f'''<div class="col-header">
  <span class="needs-h">Needs</span>
  <span class="avail-h">Avail</span>
  <span class="num-h">#</span>
  <span class="name-h">Card Name ({esc(group_name)})</span>
  <span class="rarity-h">R</span>
</div>'''

        blocks = chunk_into_blocks(rows, cols, set_code, mode, first_budget)

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
                            parts.append(row_html(set_code, mode, kr))
                        parts.append("</div>")
                        i = j
                        last_group = group
                    else:
                        parts.append(row_html(set_code, mode, row))
                        i += 1
                parts.append("</div>")
            parts.append("</div>")

        if mode == "NF_TF_TBD":
            parts.append('<div class="footnote">*These cards are announced for future eternal-legal supporting products; exact finish has not yet been specified.</div>')
        if mode == "SEASONAL":
            parts.append('<div class="footnote">Each row is a distinct seasonal/promo print of the same card, not a paired NF/SF version of one print.</div>')
        parts.append("</div>")

    total = sum(len(rows) for _, _, _, rows in SECTIONS)
    parts.append(f'<p class="subtitle">Total unique card-number rows: {total}</p>')
    parts.append("</body></html>")
    return "\n".join(parts)

if __name__ == "__main__":
    out = build()
    with open("needs_output.html", "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote needs_output.html, length", len(out))
