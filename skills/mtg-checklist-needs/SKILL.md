---
name: mtg-checklist-needs
description: "Build or update the \"Needs\" variant of a Magic: The Gathering set checklist — same layout as mtg-checklist but with a Needs column (copies still wanted) and an Available column (owned copies to trade away) per card, computed from a collection export against a set of user-chosen completion rules. Use when the user wants to know what they still need to complete a set/playset, what they have spare to trade, or wants to regenerate a needs list built with this skill."
---

Builds the same compact, print-ready checklist layout as `mtg-checklist` — for **one set at a
time**, one row per card number, rarity abbreviated, 2-3 columns per page — but replaces the two
finish checkboxes with two numeric columns: **Needs** (copies still wanted) and **Available**
(owned copies of that exact printing you'd trade away), computed by matching a collection export
against the card list under a small set of completion rules the user picks per set. `compute_needs.py`
computes the counts; `template_needs.py` renders the HTML — both are the working engines (copy
them per project rather than rewriting). `REFERENCE.md` holds the completion-rules writeup, the
ownership file formats, and the sanity checks; read it before step 1.

0. **Resolve the target set and subset selection first.** Follow the `mtg-set-builder` skill's
   full procedure before doing anything below — it resolves exactly one set code (building and
   verifying it in `../../sets/` if it isn't cached yet), lets the user pick which `subSet` groups
   to include, and gets an explicit go-ahead on a recap of both. Don't start step 1 until that
   recap is confirmed.

1. **Confirm the completion rules for this set.** Ask the user which of REFERENCE.md's six
   completion rules apply (multiSelect), and — only if Rule #6 is selected — which selected
   subSets (from step 0) they don't care about completing. Recap the selection back in plain
   language (REFERENCE.md "Recapping a rules selection to the user" has the pattern) before
   writing anything. Create `../../owned/<CODE>/` if it doesn't exist yet, and write the confirmed
   selection to `../../owned/<CODE>/rules.json` (schema in `../../owned/README.md`). Skip the
   questions (but still read the existing file) if `../../owned/<CODE>/rules.json` already exists
   from an earlier run and the user hasn't asked to change their rules — just confirm the existing
   selection back to them in one line.

2. **Get the flat card list.** Build `CARD_LIST` from the selected subsets' cards in
   `../../sets/<CODE>.json` (step 0) — one dict per row with `set_code`, `numbers` (a 1- or
   2-tuple of collector-number strings), `name`, `rarity`, `subSet`, `treatment` — per
   REFERENCE.md "Building CARD_LIST from the shared sets/ cache". Done when the row count matches
   the selected subsets' combined card count from step 0 exactly.

3. **Gather ownership data.** Tell the user to place a collection export CSV (e.g. from
   mythic.tools) and, optionally, plain-text decklists into `../../owned/<CODE>/` (created in step
   1) — this folder is shared across every future run for this set, not per-project. See
   `../../owned/README.md` "Ownership file formats" for the exact columns/line format expected,
   and REFERENCE.md "Matching by printing vs. by name" for why a collector-number column matters
   for anything beyond the base-set rows. Done when every file the user wants counted is in
   `../../owned/<CODE>/` and matches the glob patterns `compute_needs.py` expects.

4. **Compute the Needs/Available counts.** Copy `compute_needs.py` into the project, set
   `OWNED_DIR` to the absolute path of `../../owned/<CODE>/`, replace the example `CARD_LIST` with
   the real flat list from step 2. Run it — it writes `needs_result.json`. Done when the printed
   `csv_rows`/`deck_lines`/`unique_owned_*` counts look sane and `names_with_zero_owned` in the
   output doesn't include cards you know the user owns (that's usually a name-matching mismatch —
   see REFERENCE.md "Matching by printing vs. by name" — check for punctuation or apostrophe
   differences between the export and Scryfall's name before assuming they're really missing that
   many cards).

5. **Generate the HTML.** Copy `template_needs.py` into the project, point it at `SECTIONS` built
   from the same selected subsets (step 0, collector numbers as **strings** — matching the cache
   and `CARD_LIST`, see REFERENCE.md's note on the int/string lookup trap) and `color_lookup.json`
   derived the same way `mtg-checklist` step 2 does, plus the `needs_result.json` from step 4.
   Keep every convention as-is unless asked to change it: two columns (`Needs` / `Avail`),
   `#` / `Card Name (Color)` / `R` columns, same header-repeat and pagination rules as
   `mtg-checklist` (unchanged engine — see that skill's REFERENCE.md for the pagination
   internals, not duplicated here). Done when the script runs with no exceptions and no card shows
   a `?` in either column (a `?` means `compute_needs.py`'s `CARD_LIST` is missing that exact row,
   or a number-type mismatch between `SECTIONS` and `CARD_LIST` — fix before continuing). If
   `python`/`python3` isn't available, see REFERENCE.md "Running without Python installed" for a
   Docker fallback.

6. **Calibrate pagination and sanity-check exactly as in `mtg-checklist` steps 4-5** — same
   engine, same `UNIT_BUDGET`/measuring recipe, same "no blank first page" and "no card range
   silently disappears" checks. Confirm additionally: every row's Needs value is `0`/blank, a
   positive integer, or `—` for a Rule #6 excluded row (never `?`), every row's Available is `0`
   or a positive integer, and a couple of known owned/unowned/excluded cards show the values you
   expect by hand-checking against the rules in REFERENCE.md. Write the file into the user's
   project folder (redeploy to the same path on later edits) and open it in the browser.
