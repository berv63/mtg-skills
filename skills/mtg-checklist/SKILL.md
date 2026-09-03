---
name: mtg-checklist
description: "Build or update a printable Magic: The Gathering collection checklist for a set — checkboxes per finish (non-foil/foil/surge foil), rarity, print-optimized multi-column layout. Use when the user wants a checklist for an MTG set, wants to regenerate/update an existing one built with this skill, or wants to track owned cards across finishes for a set."
---

Builds a compact, print-ready HTML checklist for **one set at a time**: one row per card number,
two checkboxes (the card's two real finishes), rarity abbreviated, laid out in 2-3 columns per
page with a header that repeats at every column top and at every color change. `template.py` in
this folder is the working engine (CSS + row/column logic) validated on The Hobbit (HOB/HOC/THOB,
418 rows) — copy it per project rather than rewriting it. `REFERENCE.md` holds the classification
rules and exact commands; read it before step 1.

0. **Resolve the target set and subset selection first.** Follow the `mtg-set-builder` skill's
   full procedure before doing anything below — it resolves exactly one set code (building and
   verifying it in `../../sets/` if it isn't cached yet), lets the user pick which `subSet` groups
   to include, and gets an explicit go-ahead on a recap of both. Don't start step 1 until that
   recap is confirmed.

1. **Build `SECTIONS` from the selected subSet groups.** The normal source now is
   `../../sets/<CODE>.json` (resolved in step 0): each confirmed `subSet` name becomes a section
   title, and its cards already carry `number`/`name`/`rarity`/`nonFoilAvailable`/
   `foilAvailable`/`surgeFoilAvailable`/`otherFoilAvailable`. Derive each row's `mode` (`NF_TF`,
   `NF_SF`, `NF_ONLY`, `TF_ONLY`, `SPECIAL:X`, ...) from those flags per REFERENCE.md "Deriving
   mode from cached finish flags" — don't re-classify by hand when the cache already has this.
   Only fall back to REFERENCE.md "Classifying finishes" (working from an exported checklist
   PDF/site, or a fresh Scryfall query) for a source `mtg-set-builder` couldn't resolve into the
   cache at all. Done when every selected subset's cards reconstruct to exactly its confirmed
   count from step 0, with every row assigned exactly one mode.

2. **Build `color_lookup.json` from the same cache.** Each cached card already has its `color`
   field (Land / Colorless / White / Blue / Black / Red / Green / Multicolor) — walk the selected
   subsets' cards and key `f"{CODE}:{number}" -> color`, no live fetch needed (see
   `../../sets/README.md` "Using this cache from a skill" for the exact snippet). Only do a live
   Scryfall fetch (REFERENCE.md "Fetching color data" — WebFetch gets a 403 here, curl doesn't)
   for the PDF/site fallback path in step 1. Done when every card number from step 1 resolves in
   the lookup with zero misses (verify by checking, not assuming).

3. **Generate the HTML.** Copy `template.py` into the project, replace the example `SECTIONS`
   data with the real one from step 1, point it at the color lookup from step 2. Keep every
   convention in the template as-is unless the user explicitly asks to change it: NF/TF or NF/SF
   checkbox pair, `#` / `Card Name (Color)` / `R` columns, rarity abbreviated C/UC/R/MR, header
   repeats per column and per color change, a header only ever claims rows that share its color
   (see REFERENCE.md "The header-gluing bug" — do not reintroduce it). Done when the script runs
   and produces the HTML with no exceptions. If `python`/`python3` isn't available on this
   machine, see REFERENCE.md "Running without Python installed" for a Docker fallback.

4. **Calibrate pagination by measuring, not guessing.** Render the HTML to a real PDF with
   headless Edge/Chrome and pixel-measure how far each column's content actually reaches versus
   the printable page height — the exact recipe, including the Windows path/profile gotchas, is
   in REFERENCE.md "Measuring real page fit". Adjust `UNIT_BUDGET` (rows + color-header lines per
   column — see REFERENCE.md "Column sizing must account for header density") so the *tightest*
   column fills close to the page without overflowing. A section with many small color groups
   packed into few cards needs the same treatment — it can silently overflow (and, worse, clip
   via `overflow:hidden`, see REFERENCE.md) even when a "similar" section fits fine. Done when a
   re-render confirms every page's text length is non-trivial (no blank first page — a real
   Chromium bug, not a content bug) and no card range silently disappears from a column.

5. **Sanity-check, then deliver.** Confirm: every section's row count reconstructs to the
   expected total, zero color-lookup misses, and a text-extraction spot check (REFERENCE.md
   "Verifying placement") shows a couple of known boundary cards on the page/column you expect.
   Write the file into the user's project folder (redeploy to the same path on later edits) and
   open it in the browser.
