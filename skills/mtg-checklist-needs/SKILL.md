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

**Everything runs from the user's current working directory — there's no required project-folder
location or repo-root relationship for this skill.** Both `compute_needs.py` and
`template_needs.py` use paths relative to wherever they're actually run from, never an absolute,
machine-specific path: `compute_needs.py` looks for the user's ownership data directly inside the
current working directory (`owned/<CODE>/`, `Owned/<CODE>/`, or a bare `<CODE>/` folder — whichever
already exists, defaulting to `owned/<CODE>/` if none do — see its own docstring /
`_find_owned_dir`), and `template_needs.py` writes the rendered checklist to a `code/` subfolder of
that same current working directory. Copy both scripts straight into the directory the user is
currently working in — no dedicated `projects/<name>/` folder needed.

0. **Resolve the target set and subset selection first.** Follow the `mtg-set-builder` skill's
   full procedure before doing anything below — it resolves exactly one set code (building and
   verifying it in `../../sets/` if it isn't cached yet), lets the user pick which `subSet` groups
   to include, and gets an explicit go-ahead on a recap of both. Don't start step 1 until that
   recap is confirmed.

1. **Confirm the completion rules for this set.** Ask the user which of REFERENCE.md's six
   completion rules apply (multiSelect), and — only if Rule #6 is selected — which selected
   subSets (from step 0) they don't care about completing. Recap the selection back in plain
   language (REFERENCE.md "Recapping a rules selection to the user" has the pattern) before
   writing anything. Find the ownership folder for this set in the current working directory —
   `owned/<CODE>/`, `Owned/<CODE>/`, or a bare `<CODE>/`, per `compute_needs.py`'s
   `_find_owned_dir` — creating `owned/<CODE>/` if none of those exist yet, and write the confirmed
   selection to `<that folder>/rules.json` (schema in REFERENCE.md "The ownership folder").
   Skip the questions (but still read the existing file) if that folder's `rules.json` already
   exists from an earlier run in this same working directory and the user hasn't asked to change
   their rules — just confirm the existing selection back to them in one line.

2. **Get the flat card list.** Build `CARD_LIST` from the selected subsets' cards in
   `../../sets/<CODE>.json` (step 0) — one dict per row with `set_code`, `numbers` (a 1- or
   2-tuple of collector-number strings), `name`, `rarity`, `subSet`, `treatment` — per
   REFERENCE.md "Building CARD_LIST from the shared sets/ cache". Done when the row count matches
   the selected subsets' combined card count from step 0 exactly.

3. **Gather ownership data.** Tell the user to place a collection export CSV (e.g. from
   mythic.tools) and, optionally, plain-text decklists into the ownership folder resolved in step 1
   (inside the current working directory) — this folder is reused across every future run for this
   set *as long as you keep working from the same directory*; a different working directory starts
   fresh and needs its own copy. See REFERENCE.md "The ownership folder" for the exact
   columns/line format expected, and "Matching by printing vs. by name" for why a
   collector-number column matters for anything beyond the base-set rows. Done when every file the
   user wants counted is in that folder and matches the glob patterns `compute_needs.py` expects.

4. **Compute the Needs/Available counts.** Copy `compute_needs.py` into the current working
   directory — set its `SET_CODE` constant to the real set code (its `OWNED_DIR` derives from that
   automatically, per step 1's resolved folder) — and replace the example `CARD_LIST` with the real
   flat list from step 2. Run it — it writes `needs_result.json`. Done when the printed
   `csv_rows`/`deck_lines`/`unique_owned_*` counts look sane and `names_with_zero_owned` in the
   output doesn't include cards you know the user owns (that's usually a name-matching mismatch —
   see REFERENCE.md "Matching by printing vs. by name" — check for punctuation or apostrophe
   differences between the export and Scryfall's name before assuming they're really missing that
   many cards).

5. **Resolve the output path.** Create a `code/` subfolder *inside the current working directory*
   if it doesn't exist yet — no need to ask, this is just an empty folder. The default target is
   `code/<CODE>_needs_avail.html`, relative to the current working directory. If that file
   **doesn't** exist, use it as-is. If it **does** exist, ask the user (AskUserQuestion) whether to
   overwrite it or create a new file — if they pick "new", find the first unused
   `<CODE>_needs_avail_<N>.html` (`_1`, `_2`, ...) and use that. Never silently overwrite and never
   silently pick a numbered name on your own — this is always the user's call when the target
   already exists. See REFERENCE.md "The project's code/ folder" for the exact resolution recipe.

6. **Generate the HTML.** Copy `template_needs.py` into the current working directory, point it at
   `SECTIONS` built from the same selected subsets (step 0, collector numbers as **strings** —
   matching the cache and `CARD_LIST`, see REFERENCE.md's note on the int/string lookup trap),
   `color_lookup.json` derived the same way `mtg-checklist` step 2 does, and the `needs_result.json`
   from step 4. Its `OUTPUT_PATH` already points at `code/EX1_needs_avail.html` relatively — set the
   filename to exactly what step 5 resolved (real set code, `_1`/`_2`/... suffix if that's what the
   user chose). Keep every convention as-is unless asked
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
   written `code/` file (inside the current working directory) in the browser — check that a
   multi-column section actually reads as one continuous section (no stray break) and that a small
   section's unused columns just render empty, not broken.
