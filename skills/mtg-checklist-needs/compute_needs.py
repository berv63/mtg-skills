# -*- coding: utf-8 -*-
"""Computes a per-card 'Needs' count (copies still needed for a playset) for a set's
checklist, matching ownership by card NAME (not collector number) so alternate-art /
showcase / extended-art printings of the same card count toward the same total.

To use for a new set:

1. Replace CARD_LIST below with the real flat card list (set_code, number, name, rarity) —
   one row per checklist row, reusing the same section data built for mtg-checklist's
   template.py (see SKILL.md step 1).
2. Put your ownership export(s) under Own/ and adjust OWNED_CSV_GLOB / OWNED_DECK_GLOB if
   the filenames don't match (see REFERENCE.md "Ownership file formats").
3. Adjust TARGET_COPIES only if this set's target playset size differs from the default.
4. Run this script; it writes needs_result.json for template_needs.py to consume.

See REFERENCE.md "Matching by name, not number" before assuming this is safe for a set with
genuine same-name-but-different-card rows.
"""
import csv
import glob
import json
import re

TARGET_COPIES = {"C": 4, "UC": 4, "R": 1, "MR": 1}

OWNED_CSV_GLOB = "Own/collection_*.csv"  # mythic.tools-style export: "Card Name","Quantity" columns
OWNED_DECK_GLOB = "Own/*.txt"            # optional decklists, one "<qty> <name>" per line

# ---------------------------------------------------------------------------
# Data model — replace with the real set's flat card list.
# ---------------------------------------------------------------------------
# (set_code, number, name, rarity) — one row per checklist row that should carry a Needs
# count. If the same card name appears more than once (e.g. a showcase reprint), every row
# sharing that name gets the SAME needs value: total owned copies of that name against the
# highest target-playset size among that name's rows.

CARD_LIST = [
    ("EX1", 1, "Example Common Creature", "C"),
    ("EX1", 2, "Example Legend", "R"),
    ("EX1", 3, "Example Mythic", "MR"),
]

# ---------------------------------------------------------------------------
# Engine — stable; edit only if the ownership file formats genuinely differ.
# ---------------------------------------------------------------------------

owned = {}

def add_owned(name, qty):
    owned[name] = owned.get(name, 0) + qty

csv_rows = 0
for csv_path in glob.glob(OWNED_CSV_GLOB):
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            add_owned(row["Card Name"], int(row["Quantity"]))
            csv_rows += 1

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
            add_owned(name, int(qty))
            deck_lines += 1

# Highest target playset size across all rows sharing a name, so a rarity-mismatched
# reprint doesn't shrink the target below what any of its printings actually needs.
target_by_name = {}
for _, _, name, rarity in CARD_LIST:
    target_by_name[name] = max(TARGET_COPIES[rarity], target_by_name.get(name, 0))

results = []
unmatched = set()
for set_code, num, name, rarity in CARD_LIST:
    have = owned.get(name, 0)
    needs = max(0, target_by_name[name] - have)
    results.append({
        "set_code": set_code, "num": num, "name": name, "rarity": rarity,
        "have": have, "needs": needs,
    })
    if name not in owned:
        unmatched.add(name)

with open("needs_result.json", "w", encoding="utf-8") as f:
    json.dump({
        "csv_rows": csv_rows,
        "deck_lines": deck_lines,
        "unique_owned_names": len(owned),
        "results": results,
        "names_with_zero_owned": sorted(unmatched),
    }, f, ensure_ascii=False, indent=2)

print("csv_rows", csv_rows, "deck_lines", deck_lines, "unique_owned_names", len(owned))
print("cards with 0 owned copies found:", len(unmatched))
