# -*- coding: utf-8 -*-
"""Computes a per-card Needs count (copies still wanted) and Available count (owned copies you'd
trade away) for a set's checklist, against the shared ownership cache in ../../owned/<CODE>/.

To use for a new set:

1. Set OWNED_DIR to the absolute path of this set's owned/<CODE>/ folder (create it, and get the
   user's collection export(s) into it, per SKILL.md step 2 and owned/README.md).
2. Make sure owned/<CODE>/rules.json exists (SKILL.md's rules step writes it) before running this.
3. Replace CARD_LIST below with the real flat card list — one dict per checklist row, reusing the
   same section data built for mtg-checklist's template.py, plus each row's subSet and treatment
   (see SKILL.md step 1 / REFERENCE.md "Building CARD_LIST from the shared sets/ cache").
4. Run this script; it writes needs_result.json for template_needs.py to consume.

See REFERENCE.md "The completion rules" and "Matching by printing vs. by name" before assuming
this is safe for a set with genuine same-name-but-different-card base-set rows.
"""
import csv
import glob
import json
import os
import re

# ---------------------------------------------------------------------------
# Config — replace with the real set's data.
# ---------------------------------------------------------------------------

OWNED_DIR = r"C:\Berv\mtg-skills\owned\EX1"  # absolute path to this set's owned/<CODE>/ folder
RULES_PATH = os.path.join(OWNED_DIR, "rules.json")

OWNED_CSV_GLOB = os.path.join(OWNED_DIR, "collection_*.csv")
OWNED_DECK_GLOB = os.path.join(OWNED_DIR, "*.txt")

# Fallback target when neither Rule #1, #2, nor #3 (for R/MR) applies to a rarity.
DEFAULT_TARGET = {"C": 4, "UC": 4, "R": 1, "MR": 1}

# ---------------------------------------------------------------------------
# Data model — replace with the real set's flat card list.
# ---------------------------------------------------------------------------
# One dict per checklist row. "numbers" is a 1- or 2-tuple of collector numbers this row
# represents (2 only for an NF/SF paired row, matching mtg-checklist's row shapes exactly).
# "subSet" and "treatment" come straight from ../../sets/<CODE>.json (see REFERENCE.md).

CARD_LIST = [
    {"set_code": "EX1", "numbers": ("1",), "name": "Example Common Creature", "rarity": "C",
     "subSet": "Draft Cards", "treatment": "Base Set"},
    {"set_code": "EX1", "numbers": ("2",), "name": "Example Legend", "rarity": "R",
     "subSet": "Draft Cards", "treatment": "Base Set"},
    {"set_code": "EX1", "numbers": ("3",), "name": "Example Mythic", "rarity": "MR",
     "subSet": "Draft Cards", "treatment": "Base Set"},
]

# ---------------------------------------------------------------------------
# Engine — stable; edit only if the ownership file formats genuinely differ.
# ---------------------------------------------------------------------------

with open(RULES_PATH, encoding="utf-8") as _f:
    _rules_cfg = json.load(_f)
RULES = set(_rules_cfg.get("rules", []))
EXCLUDED_SUBSETS = set(_rules_cfg.get("excluded_subsets", []))

NAME_HEADERS = ["Card Name", "Name"]
QTY_HEADERS = ["Quantity", "Qty", "Count"]
SET_HEADERS = ["Set Code", "Set", "Edition Code", "Edition"]
NUMBER_HEADERS = ["Collector Number", "Card Number", "Number", "#"]


def _find_header(fieldnames, candidates):
    if not fieldnames:
        return None
    lower = {fn.strip().lower(): fn for fn in fieldnames}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None


_set_codes_in_list = {row["set_code"] for row in CARD_LIST}
_single_set_code = next(iter(_set_codes_in_list)) if len(_set_codes_in_list) == 1 else None

owned_by_printing = {}       # (set_code, number) -> qty, from CSV rows with printing detail
owned_by_name_fallback = {}  # name -> qty, from rows/files with no printing detail (base-set only)


def add_printing(set_code, number, qty):
    key = (set_code, str(number).strip())
    owned_by_printing[key] = owned_by_printing.get(key, 0) + qty


def add_name_fallback(name, qty):
    owned_by_name_fallback[name] = owned_by_name_fallback.get(name, 0) + qty


csv_rows = 0
csv_files_per_printing = 0
csv_files_name_only = 0
for csv_path in glob.glob(OWNED_CSV_GLOB):
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        name_col = _find_header(reader.fieldnames, NAME_HEADERS)
        qty_col = _find_header(reader.fieldnames, QTY_HEADERS)
        set_col = _find_header(reader.fieldnames, SET_HEADERS)
        num_col = _find_header(reader.fieldnames, NUMBER_HEADERS)
        if not name_col or not qty_col:
            print(f"SKIPPING {csv_path}: no Card Name / Quantity column found "
                  f"(saw {reader.fieldnames})")
            continue
        per_printing = num_col is not None and (set_col is not None or _single_set_code is not None)
        if per_printing:
            csv_files_per_printing += 1
        else:
            csv_files_name_only += 1
        for row in reader:
            name = row[name_col]
            qty = int(row[qty_col])
            csv_rows += 1
            number = row[num_col].strip() if (per_printing and row.get(num_col)) else ""
            if per_printing and number:
                set_code = row[set_col].strip().upper() if set_col else _single_set_code
                add_printing(set_code, number, qty)
            else:
                add_name_fallback(name, qty)

deck_line_re = re.compile(r"^(\d+)\s+(.+)$")
deck_lines = 0
for path in glob.glob(OWNED_DECK_GLOB):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line == "Deck":
                continue
            m = deck_line_re.match(line)
            if not m:
                print("UNPARSED LINE in", path, ":", repr(line))
                continue
            qty, name = m.group(1), m.group(2)
            add_name_fallback(name, int(qty))
            deck_lines += 1

# ---------------------------------------------------------------------------
# The completion rules — see REFERENCE.md "The completion rules" for the full writeup.
# ---------------------------------------------------------------------------


def target_needs(rarity):
    """Rule #3 (R/MR only) beats Rule #2 (all cards) beats Rule #1 (all cards) beats the
    DEFAULT_TARGET baseline — most-specific-selected-rule wins, not a max() of floors."""
    if rarity in ("R", "MR") and "3" in RULES:
        return 2
    if "2" in RULES:
        return 4
    if "1" in RULES:
        return 1
    return DEFAULT_TARGET.get(rarity, 4)


def keep_threshold(rarity):
    """How many copies of a row's own printing to always keep — Available = owned - this,
    floored at 0. Rule #4 sets an R/MR-specific keep-threshold independent of the Needs target;
    everything else defaults to keeping exactly your Needs target (nothing is "spare" until you've
    met your own goal)."""
    if rarity in ("R", "MR") and "4" in RULES:
        return 2
    return target_needs(rarity)


rows_by_name = {}
for row in CARD_LIST:
    rows_by_name.setdefault(row["name"], []).append(row)


def printing_owned(set_code, numbers):
    return sum(owned_by_printing.get((set_code, n), 0) for n in numbers)


results = []
zero_owned_names = set()
for row in CARD_LIST:
    set_code, numbers, name, rarity = row["set_code"], row["numbers"], row["name"], row["rarity"]
    subset, treatment = row.get("subSet"), row.get("treatment", "Base Set")
    target = target_needs(rarity)
    excluded = subset in EXCLUDED_SUBSETS

    row_owned = printing_owned(set_code, numbers)
    if treatment == "Base Set":
        row_owned += owned_by_name_fallback.get(name, 0)

    if treatment == "Base Set" and "5" in RULES:
        # Pool in every other printing of this name's OWN exact-printing ownership (never the
        # name-fallback pool, which already only ever lands on the base row). The flat-Needs-of-1
        # gate only fires when there's actually pooled alt-art ownership to gate (row_owned==0 but
        # pooled_extra>0) — a card with no alt-art counterpart at all (pooled_extra always 0) must
        # fall through to the normal target shortfall, or every unowned card with no alt-art twin
        # would wrongly show Needs=1 instead of its real target.
        pooled_extra = sum(
            printing_owned(other["set_code"], other["numbers"])
            for other in rows_by_name[name] if other is not row
        )
        pooled_total = row_owned + pooled_extra
        if row_owned == 0 and pooled_extra > 0:
            needs = 1
        else:
            needs = max(0, target - pooled_total)
    else:
        needs = max(0, target - row_owned)

    if excluded:
        needs_display = None  # not tracked — Rule #6, "don't care about this subSet"
        available = row_owned  # 100% available regardless of any keep-threshold
    else:
        needs_display = needs
        available = max(0, row_owned - keep_threshold(rarity))

    results.append({
        "set_code": set_code,
        "num": "/".join(numbers),
        "primary_number": numbers[0],
        "name": name,
        "rarity": rarity,
        "subSet": subset,
        "treatment": treatment,
        "have": row_owned,
        "needs": needs_display,
        "available": available,
        "excluded": excluded,
    })
    if row_owned == 0:
        zero_owned_names.add(name)

with open("needs_result.json", "w", encoding="utf-8") as f:
    json.dump({
        "rules": sorted(RULES),
        "excluded_subsets": sorted(EXCLUDED_SUBSETS),
        "csv_rows": csv_rows,
        "csv_files_per_printing": csv_files_per_printing,
        "csv_files_name_only": csv_files_name_only,
        "deck_lines": deck_lines,
        "unique_owned_printings": len(owned_by_printing),
        "unique_owned_fallback_names": len(owned_by_name_fallback),
        "results": results,
        "names_with_zero_owned": sorted(zero_owned_names),
    }, f, ensure_ascii=False, indent=2)

print("csv_rows", csv_rows,
      "per-printing files", csv_files_per_printing,
      "name-only files", csv_files_name_only,
      "deck_lines", deck_lines)
print("rows with 0 owned copies:", len(zero_owned_names))
