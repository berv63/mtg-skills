---
name: mtg-checklist-needs
description: "Build or update the \"Needs\" variant of a Magic: The Gathering set checklist — a web-only (not print-oriented) page with a Needs column (copies still wanted) and an Available column (owned copies to trade away) per card, computed from a collection export against a set of user-chosen completion rules. Use when the user wants to know what they still need to complete a set/playset, what they have spare to trade, or wants to regenerate a needs list built with this skill."
---

Builds a compact **web-only** checklist page for **one set at a time** — no print pagination, no
page breaks: each selected `subSet` is one section showing every one of its cards together, split
into 3 columns as evenly as possible by row count. Each row carries two numeric columns instead of
finish checkboxes: **Needs** (copies still wanted) and **Available** (owned copies of that exact
printing you'd trade away), computed by matching a collection export against the card list under a
small set of completion rules the user picks per set. `compute_needs.py` computes the counts;
`template_needs.py` renders the HTML — both are the working engines (copy them per project rather
than rewriting). `REFERENCE.md` holds the completion-rules writeup, the ownership file formats, and
the sanity checks; read it before step 1.

**Project folder location is not free-form for this skill.** Unlike `mtg-checklist`, the copies of
`compute_needs.py`/`template_needs.py` you make below use relative paths at runtime (to
`../../owned/<CODE>/` and `../../output/`) instead of any absolute, machine-specific path — this
has to work on whatever machine the user is on, not just this one. That means the project folder
**must** be created directly under the repo root, sister to `sets/`, `owned/`, `output/`, and
`skills/` — e.g. `projects/<descriptive-name>/` — so `../../` from inside it always lands on the
repo root, exactly like every other skill's `../../sets/...` references. Create that folder (no
need to ask, it's just an empty directory) before step 4.

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

4. **Compute the Needs/Available counts.** Copy `compute_needs.py` into the project folder created
   above — its `OWNED_DIR` already points at `../../owned/EX1` relatively; just change `EX1` to the
   real set code — and replace the example `CARD_LIST` with the real flat list from step 2. Run it
   — it writes `needs_result.json`. Done when the printed
   `csv_rows`/`deck_lines`/`unique_owned_*` counts look sane and `names_with_zero_owned` in the
   output doesn't include cards you know the user owns (that's usually a name-matching mismatch —
   see REFERENCE.md "Matching by printing vs. by name" — check for punctuation or apostrophe
   differences between the export and Scryfall's name before assuming they're really missing that
   many cards).

5. **Resolve the output path.** Create `../../output/` (sister to `sets/`) if it doesn't exist yet
   — no need to ask, this is just an empty folder. The default target is
   `../../output/<CODE>_needs_avail.html`. If that file **doesn't** exist, use it as-is. If it
   **does** exist, ask the user (AskUserQuestion) whether to overwrite it or create a new file —
   if they pick "new", find the first unused `<CODE>_needs_avail_<N>.html` (`_1`, `_2`, ...) and use
   that. Never silently overwrite and never silently pick a numbered name on your own — this is
   always the user's call when the target already exists. See REFERENCE.md "The output/ folder"
   for the exact resolution recipe.

6. **Generate the HTML.** Copy `template_needs.py` into the project folder, point it at `SECTIONS`
   built from the same selected subsets (step 0, collector numbers as **strings** — matching the
   cache and `CARD_LIST`, see REFERENCE.md's note on the int/string lookup trap), `color_lookup.json`
   derived the same way `mtg-checklist` step 2 does, and the `needs_result.json` from step 4. Its
   `OUTPUT_PATH` already points at `../../output/EX1_needs_avail.html` relatively — set the filename
   to exactly what step 5 resolved (real set code, `_1`/`_2`/... suffix if that's what the user
   chose). Keep every convention as-is unless asked
   to change it: two columns (`Needs` / `Avail`), `#` / `Card Name (Color)` / `R` columns, one
   section per `subSet` with every one of its cards shown together (no splitting a section),
   `COLS = 3` columns per section split as evenly as possible by row count (see REFERENCE.md
   "Web-only layout — no pagination"), header repeats wherever the color changes within a column.
   This template is **not** shared with `mtg-checklist`'s pagination engine — don't port
   print-pagination logic back into it. Done when the script runs with no exceptions, writes to
   exactly the path from step 5, and no card shows a `?` in either column (a `?` means
   `compute_needs.py`'s `CARD_LIST` is missing that exact row, or a number-type mismatch between
   `SECTIONS` and `CARD_LIST` — fix before continuing). If `python`/`python3` isn't available, see
   REFERENCE.md "Running without Python installed" for a Docker fallback.

7. **Sanity-check, then deliver.** No pagination/PDF calibration step — this is a plain scrolling
   web page. Confirm: every section's row count reconstructs to the expected total, every row's
   Needs value is `0`/blank, a positive integer, or `—` for a Rule #6 excluded row (never `?`),
   every row's Available is `0` or a positive integer, and a couple of known owned/unowned/excluded
   cards show the values you expect by hand-checking against the rules in REFERENCE.md. Open the
   written `../../output/` file in the browser — check that a multi-column section actually reads
   as one continuous section (no stray break) and that a small section's unused columns just render
   empty, not broken.
