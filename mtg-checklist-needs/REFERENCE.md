# Reference: mtg-checklist-needs

## Running without Python installed

Both scripts only use the standard library (`csv`, `glob`, `json`, `re`, `html`) — no venv or
pip install needed for the core workflow. If neither `python` nor `python3` resolves on the
machine, run them in Docker instead, mounting the project folder (the one containing
`compute_needs.py`, `template_needs.py`, `Own/`, `color_lookup.json`, `sections_data.json`) as
the working directory:

```bash
docker run --rm -v "$(pwd):/work" -w /work python:3-slim python compute_needs.py
docker run --rm -v "$(pwd):/work" -w /work python:3-slim python template_needs.py
```

On Windows PowerShell, use `${PWD}` instead of `$(pwd)`:

```powershell
docker run --rm -v "${PWD}:/work" -w /work python:3-slim python compute_needs.py
docker run --rm -v "${PWD}:/work" -w /work python:3-slim python template_needs.py
```

This pulls the official `python:3-slim` image on first run (needs internet access once), then
executes fully offline. No custom Dockerfile is required for either step. (The optional
pagination-calibration step still needs `pymupdf`/`pypdf` and a real browser — see
`mtg-checklist`'s REFERENCE.md "Running without Python installed" for that recipe; it's shared
across both skills since the rendering/measuring step is identical.)

## Building CARD_LIST from the shared sets/ cache

`compute_needs.py`'s `CARD_LIST` is `(set_code, number, name, rarity)` per row — every field of
that tuple is already present in `../sets/<CODE>.json` (see its README.md), one object per real
print, in collector-number order. If the set(s) involved are already cached there (they should
be, per `mtg-checklist`'s REFERENCE.md — build it via `sets/build_set.py` once if not), build
`CARD_LIST` by loading those JSON files and filtering/mapping rather than hand-transcribing:
`(row["setCode"], row["number"], row["name"], row["rarity"])`, keeping only the rows that
actually belong in this product's checklist (same filtering judgment as `mtg-checklist`'s
`EXCLUDE_PROMO`/section-bucketing step — the cache is unfiltered raw data, this product's
`CARD_LIST` is the curated subset of it).

## Ownership file formats

`compute_needs.py` reads two kinds of source under `Own/` in the project folder, both matched by
glob so any number of files of each kind works:

- **Collection export CSV** (`Own/collection_*.csv`, glob `OWNED_CSV_GLOB`): a mythic.tools-style
  export with at least a `Card Name` column and a `Quantity` column (`csv.DictReader`, so any
  extra columns are ignored). Encoding is read as `utf-8-sig` to tolerate a leading BOM, which
  these exports commonly have.
- **Plain-text decklists** (`Own/*.txt`, glob `OWNED_DECK_GLOB`): one card per line, formatted
  `<qty> <name>` (e.g. `4 Lightning Bolt`), used for cards you own only as part of a preconstructed
  deck (Welcome Deck, Commander precon, etc.) that wouldn't otherwise show up in a boosters-only
  collection export. A line that's blank or exactly `Deck` is skipped (common decklist-export
  header); anything else that doesn't parse as `<digits> <name>` is printed to stdout as
  `UNPARSED LINE` rather than silently dropped or crashing — check that output before trusting the
  result.

Quantities from every matched file are summed per exact card name string before needs are
computed. If the same physical collection is exported to more than one CSV (e.g. split by set),
just drop both files in `Own/` — the glob picks up all of them.

## Matching by name, not number

Ownership is matched by the card's **name string**, not its collector number or set code. This is
deliberate: a played-out alternate-art, showcase, borderless, or extended-art printing of a card
still satisfies that card's playset requirement, and those printings live at different collector
numbers (sometimes in different sections entirely) from the card's default-frame printing. If the
same name appears at multiple rows in `CARD_LIST` (e.g. a main-set card that's also reprinted as a
showcase treatment), every row sharing that name gets the **same** Needs value — computed once
from the total owned copies of that name against the highest target-playset size among that name's
rows (so a reprint with a different rarity doesn't accidentally shrink the target).

The failure mode this causes: two genuinely different cards that happen to share a name (rare, but
real for things like reversible/double-faced cards exported under a single face name, or
same-named seasonal promo prints that are meant to stay separate rows per `mtg-checklist`'s
"Same-name promo variants" rule) will incorrectly share one Needs count. If a set has that
situation, key `CARD_LIST`/`owned` by `(name, distinguishing detail)` instead of bare name — this
is the exception, not the default; verify by checking the actual data, not assuming it doesn't
apply.

A `names_with_zero_owned` entry in `needs_result.json` for a card you know you own almost always
means the export's name string doesn't byte-for-byte match Scryfall's name (curly vs. straight
apostrophe, an em-dash vs. hyphen in split-card names, a trailing collector-set suffix some
exporters append). Compare the two strings directly rather than guessing.

## Verifying the result

Same spot-check approach as `mtg-checklist`'s REFERENCE.md "Verifying placement": `pypdf` extracts
page text from a rendered PDF, so you can search for `f"{name}"` near a known Needs digit to
confirm a specific card landed where expected. Additionally, cross-check `needs_result.json`
directly for a couple of cards you know the real owned-copy count for, before ever rendering the
HTML — it's a much cheaper place to catch a matching bug than a full PDF re-render.
