---
name: mtg-checklist-needs
description: "Build or update the \"Needs\" variant of a Magic: The Gathering set checklist — same layout as mtg-checklist but with a single numeric \"copies still needed\" column per card instead of finish checkboxes, computed from a collection export. Use when the user wants to know what they still need to complete a set/playset, or wants to regenerate a needs list built with this skill."
---

Builds the same compact, print-ready checklist layout as `mtg-checklist` — for **one set at a
time**, one row per card number, rarity abbreviated, 2-3 columns per page — but replaces the two
finish checkboxes with one numeric **Needs** column: copies still required for a playset (4 for
Common/Uncommon, 1 for Rare/Mythic by default), computed by matching your collection export
against the card list **by name**, so an owned alternate-art/showcase/extended-art printing still
counts toward the same card's total. `compute_needs.py` computes the counts; `template_needs.py`
renders the HTML — both are the working engines (copy them per project rather than rewriting).
`REFERENCE.md` holds the ownership file formats and the sanity checks; read it before step 1.

0. **Resolve the target set and subset selection first.** Follow the `mtg-set-builder` skill's
   full procedure before doing anything below — it resolves exactly one set code (building and
   verifying it in `../../sets/` if it isn't cached yet), lets the user pick which `subSet` groups
   to include, and gets an explicit go-ahead on a recap of both. Don't start step 1 until that
   recap is confirmed.

1. **Get the flat card list.** Build `CARD_LIST` from the selected subsets' cards in
   `../../sets/<CODE>.json` (step 0) — `(set_code, number, name, rarity)` per card, including
   reprints/alternate-art printings under their own number — per that cache's README.md "Building
   CARD_LIST from the shared sets/ cache". Done when the row count matches the selected subsets'
   combined card count from step 0 exactly.

2. **Gather ownership data** into a per-project `Own/` folder: a collection export CSV (e.g. from
   mythic.tools) and, optionally, plain-text decklists. See REFERENCE.md "Ownership file formats"
   for the exact columns/line format expected. Done when every file you want counted is in `Own/`
   and matches the glob patterns `compute_needs.py` expects.

3. **Compute the Needs counts.** Copy `compute_needs.py` into the project, replace the example
   `CARD_LIST` with the real flat list from step 1, adjust `TARGET_COPIES` only if this set's
   target playset size differs from the 4/4/1/1 default. Run it — it writes `needs_result.json`.
   Done when the printed `csv_rows`/`deck_lines`/`unique_owned_names` counts look sane and
   `names_with_zero_owned` in the output doesn't include cards you know you own (that's usually a
   name-matching mismatch — see REFERENCE.md "Matching by name, not number" — check for punctuation
   or apostrophe differences between the export and Scryfall's name before assuming you're really
   missing that many cards).

4. **Generate the HTML.** Copy `template_needs.py` into the project, point it at `SECTIONS` built
   from the same selected subsets (step 0) and `color_lookup.json` derived the same way
   `mtg-checklist` step 2 does, plus the `needs_result.json` from step 3. Keep every convention as-is unless asked to change it: single
   `Needs` column, `#` / `Card Name (Color)` / `R` columns, same header-repeat and pagination rules
   as `mtg-checklist` (unchanged engine — see that skill's REFERENCE.md for the pagination
   internals, not duplicated here). Done when the script runs with no exceptions and no card shows
   a `?` in its Needs column (a `?` means `compute_needs.py`'s `CARD_LIST` is missing that exact
   row — fix before continuing). If `python`/`python3` isn't available, see REFERENCE.md "Running
   without Python installed" for a Docker fallback.

5. **Calibrate pagination and sanity-check exactly as in `mtg-checklist` steps 4-5** — same
   engine, same `UNIT_BUDGET`/measuring recipe, same "no blank first page" and "no card range
   silently disappears" checks. Confirm additionally: every row's Needs value is `0` or a positive
   integer (never blank/`?`), and a couple of known owned/unowned cards show the value you expect.
   Write the file into the user's project folder (redeploy to the same path on later edits) and
   open it in the browser.
