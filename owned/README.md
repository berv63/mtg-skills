# owned/ — shared per-set ownership cache

Sister folder to `../sets/`, but for the opposite kind of data: `sets/<CODE>.json` is a permanent,
never-changing record of what cards exist; `owned/<CODE>/` is a **personal, frequently-changing**
record of which of those cards you actually have. `mtg-checklist-needs` reads this folder — never
`sets/` — for ownership data. Every project that builds a Needs checklist for a given set code
reads and writes the *same* `owned/<CODE>/` folder, so an ownership CSV you drop in once benefits
every future checklist run for that set, not just the one project you were working on.

This folder (and everything under it except this file) is git-ignored — see the repo root
`.gitignore`. Personal collection data doesn't belong committed to a shared repo, and it changes
far too often to track sensibly.

## Layout

```
owned/
  README.md          (this file, tracked in git)
  HOB/
    collection_2026-01-05.csv    (one or more ownership exports, see below)
    welcome_deck.txt             (optional plain-text decklists)
    rules.json                   (the confirmed completion-rules selection for this set)
  LTR/
    ...
```

One subfolder per set code, created on demand the first time `mtg-checklist-needs` is run for that
set. Nothing here is regenerated automatically — a file placed here stays until the user removes
or replaces it.

## Ownership file formats

`compute_needs.py` reads two kinds of source from `owned/<CODE>/`, both matched by glob so any
number of files of each kind works:

- **Collection export CSV** (`collection_*.csv`): at minimum a card-name column and a quantity
  column (header matched case-insensitively against `Card Name`/`Name` and
  `Quantity`/`Qty`/`Count`). If the file *also* has a collector-number column (matched against
  `Collector Number`/`Card Number`/`Number`/`#`) — and either a set-code column
  (`Set Code`/`Set`/`Edition Code`/`Edition`) or the project only involves one set code — every row
  in that file is matched to the **exact printing** it names. If the file has no such
  collector-number column at all, every row in that file is matched by **name only**, and treated
  as if it were a base-set copy (see "Matching by printing vs. by name" below) — this is a
  file-level decision made once per CSV, not a per-row fallback.
- **Plain-text decklists** (`*.txt`): one card per line, `<qty> <name>` (e.g. `4 Lightning Bolt`),
  for cards you only own as part of a preconstructed deck. These never carry a collector number, so
  they always match by name only, same as a name-only CSV. A blank line or exactly `Deck` is
  skipped; anything else unparseable is printed as `UNPARSED LINE` rather than silently dropped.

Quantities from every matched file are summed before Needs/Available are computed. If the same
physical collection is exported to more than one CSV (e.g. split by set, or a periodic re-export),
just drop every file in the folder — the glob picks them all up. Old exports don't need to be
deleted, only the newest one needs to be current, since quantities sum across files — **don't leave
a stale export next to a newer one that represents the same cards**, or counts will double.

## `rules.json` — the completion-rules selection

Each set's `owned/<CODE>/rules.json` records which of `mtg-checklist-needs`' completion rules the
user picked, and (for Rule #6) which subSets they don't care about completing:

```json
{
  "rules": ["1", "3", "5", "6"],
  "excluded_subsets": ["Extended Art Cards", "Bundle Promo"]
}
```

`compute_needs.py` reads this at run time (not hand-transcribed into the script's own constants,
unlike `CARD_LIST`) so re-running the script after an ownership update never requires re-asking the
user which rules apply. See `mtg-checklist-needs`'s REFERENCE.md "The completion rules" for what
each rule number means and how they combine. This file is created the first time
`mtg-checklist-needs` is run for a set (after confirming the rules with the user via
AskUserQuestion) and only changes when the user explicitly asks to change their rules for that set.

## Matching by printing vs. by name

Ownership matching now happens at two different granularities depending on the row:

- **Rows the cache marks `treatment: "Base Set"`** (see `../sets/README.md` "The `treatment`
  field") can, under Rule #5, pool in ownership credit from every other printing of the same card
  name (an owned showcase/extended-art/etc. copy counts toward the base printing's completion).
- **Every other row** (showcase, extended art, borderless, poster, ...) matches **only its own
  exact printing** — an owned copy of a *different* printing of the same name never reduces that
  row's own Needs, even though it may still be feeding pooled credit into the base row.

This means the same CSV needs printing-level detail (set + collector number) to be useful for
anything beyond the base row — a name-only export (or a decklist) can only ever contribute to a
base-set row's count, per the file-level fallback above. See `mtg-checklist-needs`'s REFERENCE.md
for the full rules engine this feeds into.
