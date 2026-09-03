---
name: mtg-checklist
description: Build or update a printable Magic: The Gathering collection checklist for a set — checkboxes per finish (non-foil/foil/surge foil), rarity, print-optimized multi-column layout. Use when the user wants a checklist for an MTG set, wants to regenerate/update an existing one built with this skill, or wants to track owned cards across finishes for a set.
---

Builds a compact, print-ready HTML checklist: one row per card number, two checkboxes (the
card's two real finishes), rarity abbreviated, laid out in 2-3 columns per page with a header
that repeats at every column top and at every color change. `template.py` in this folder is
the working engine (CSS + row/column logic) validated on The Hobbit (HOB/HOC/THOB, 418 rows) —
copy it per project rather than rewriting it. `REFERENCE.md` holds the classification rules and
exact commands; read it before step 1.

1. **Get the card list and work out the finish structure.** Source is whatever the user gives
   you (an exported checklist PDF/site) or Scryfall directly. For every logical section of the
   set, decide which finish pair applies — NF/TF (default frame, one collector number per card),
   NF/SF (collector-only alternate frame, the foil printing has its *own* collector number), or
   NF-only (extended art, tokens, basic lands, scene cards — one real finish). See REFERENCE.md
   "Classifying finishes" for the exact patterns and the count-ratio trick that confirms a guess.
   Done when every card number in the source maps to exactly one section and mode, and the
   reconstructed row count matches the source's stated total (see REFERENCE.md if it doesn't
   match exactly — small integer multiples are normal).

2. **Fetch real color data from Scryfall** for every set code involved — do not guess or invent
   colors. Use the curl recipe in REFERENCE.md "Fetching color data" (WebFetch gets a 403 here;
   curl doesn't). Classify each card as Land / Colorless / White / Blue / Black / Red / Green /
   Multicolor per the rule in REFERENCE.md, and build a `{SET:number -> group}` lookup. Done when
   every card number from step 1 resolves in the lookup with zero misses (verify by checking, not
   assuming).

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
