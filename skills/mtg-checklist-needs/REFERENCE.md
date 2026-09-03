# Reference: mtg-checklist-needs

## Running without Python installed

Both scripts only use the standard library (`csv`, `glob`, `json`, `os`, `re`, `html`) — no venv
or pip install needed for the core workflow. If neither `python` nor `python3` resolves on the
machine, run them in Docker instead, mounting the project folder (the one containing
`compute_needs.py`, `template_needs.py`, `color_lookup.json`, `needs_result.json`) as the working
directory:

```bash
docker run --rm -v "$(pwd):/work" -w /work python:3-slim python compute_needs.py
docker run --rm -v "$(pwd):/work" -w /work python:3-slim python template_needs.py
```

On Windows PowerShell, use `${PWD}` instead of `$(pwd)`:

```powershell
docker run --rm -v "${PWD}:/work" -w /work python:3-slim python compute_needs.py
docker run --rm -v "${PWD}:/work" -w /work python:3-slim python template_needs.py
```

`compute_needs.py` also needs to see `../../owned/<CODE>/` — either set `OWNED_DIR` to an absolute
Windows path (Docker on Windows can read outside the mounted folder only if you mount the repo
root instead of just the project folder — simplest fix: mount the whole repo root and set
`OWNED_DIR = "/work/owned/<CODE>"` for that run) or copy the set's `owned/<CODE>/` folder next to
the project temporarily. This pulls the official `python:3-slim` image on first run (needs
internet access once), then executes fully offline. No custom Dockerfile is required for either
step. (The optional pagination-calibration step still needs `pymupdf`/`pypdf` and a real browser —
see `mtg-checklist`'s REFERENCE.md "Running without Python installed" for that recipe; it's shared
across both skills since the rendering/measuring step is identical.)

## The completion rules

Six independent yes/no rules the user picks per set (stored in `../../owned/<CODE>/rules.json`'s
`rules` array, by number as strings — `"1"` through `"6"`). None of them require each other; any
combination is legal. `compute_needs.py`'s `target_needs`/`keep_threshold` functions are the
executable version of everything below — read this alongside them, not instead of them.

- **#1 — "I want at least one of every card."** Sets the Needs target to 1 for every rarity,
  *unless* a stronger rule below also applies.
- **#2 — "I want to own at least 4 of each card."** Sets the Needs target to 4 for every rarity,
  unless Rule #3 overrides it for R/MR.
- **#3 — "I want to own at least 2 of each R/MR card."** Sets the Needs target to 2, but only for
  Rare/Mythic Rare rows. **This is a specific override, not a floor to be maxed with Rule #2** — if
  both #2 and #3 are checked, R/MR gets 2 (Rule #3 wins), not 4. This was confirmed explicitly with
  the user rather than assumed; don't "fix" it back to `max(2, 4)`.
- **#4 — "I'm willing to trade down to 2 of each R/MR card."** Sets the *keep-threshold* (not the
  Needs target) to 2 for R/MR rows — `Available = max(0, owned − keep_threshold)`. This is
  independent of whatever the Needs target is; a card can show a Needs target of 4 (Rule #2) and
  still report everything past 2 owned copies as Available (Rule #4), because acquiring toward a
  goal and being willing to part with surplus are different questions.
- **#5 — "I want Needs on base-set cards to search by name, so alt-art copies count toward base-set
  completion, as long as I own at least one real base-set copy."** Only affects rows the cache
  marks `treatment: "Base Set"` (see `../../sets/README.md` "The `treatment` field"). When on, a
  base-set row's Needs is computed against the *pooled* ownership of every other printing sharing
  its name (each matched to its own exact printing, never through the name-only fallback — see
  "Matching by printing vs. by name" below), **except**: if the row's own real base-set printing
  has zero owned copies while pooled alt-art ownership is nonzero, Needs is a flat `1` regardless
  of the target or how much alt-art ownership exists — you specifically need to land one real base
  copy first. If pooled alt-art ownership is *also* zero, this flat-1 override does **not** apply —
  it falls through to the normal `max(0, target − 0)` shortfall, or every unowned card with no
  alt-art counterpart at all would wrongly show Needs=1 instead of its real target. When off, a
  base-set row uses only its own exact-printing (+ name-only-fallback) ownership, exactly like
  every other row.
- **#6 — "I don't care about owning cards from some subSets; everything I have from them is
  available for trade."** Ask which of the selected (step 0) subSets this applies to, via
  AskUserQuestion multiSelect, and store the chosen names verbatim in `rules.json`'s
  `excluded_subsets`. A row whose `subSet` is in that list shows Needs as `—` (not computed, not
  tracked) and Available as its **full** owned count, ignoring any keep-threshold. A copy in an
  excluded subSet still counts fully toward Rule #5's pooled credit for its base-set row (both
  effects apply to the same physical copies at once — this was confirmed explicitly with the user,
  not an oversight: a card can help finish the base set *and* be fully available to trade,
  simultaneously).

**By default (no rules selected at all), Needs falls back to `{C:4, UC:4, R:1, MR:1}` and the
keep-threshold equals the Needs target** — i.e. Available is 0 until you've met your own target.
This matches the skill's original behavior before the rules feature existed.

### Recapping a rules selection to the user

State back, in plain language, exactly what will happen for each rarity — not just which numbers
were checked. E.g. for `rules: ["2","3","4","5"]`: "Commons/uncommons target 4 copies. Rares/mythics
target 2 copies (Rule #3 overriding Rule #2's 4), but you're willing to trade down to 2 of those
regardless (Rule #4 — redundant with #3 here since both land on 2, but would matter if you later
drop #3). Base-set rows will credit owned alt-art copies toward completion once you own at least
one real base-set copy (Rule #5)." Catching a misunderstanding here is much cheaper than after
`compute_needs.py` has run.

## Building CARD_LIST from the shared sets/ cache

`compute_needs.py`'s `CARD_LIST` is a list of dicts: `{"set_code", "numbers", "name", "rarity",
"subSet", "treatment"}` — one per checklist row. `numbers` is always a tuple of collector-number
**strings** (a 2-tuple only for an NF/SF paired row, matching `mtg-checklist`'s row shapes — see
its REFERENCE.md "Deriving mode from cached finish flags"); everything else comes straight off the
matching card object(s) in `../../sets/<CODE>.json`. Build it by walking both levels of the cache
rather than hand-transcribing:

```python
CARD_LIST = [
    {"set_code": code, "numbers": (card["number"],), "name": card["name"],
     "rarity": card["rarity"], "subSet": group["subSet"], "treatment": card["treatment"]}
    for code in ["HOB", "HOC"]
    for group in json.load(open(f"../../sets/{code}.json", encoding="utf-8"))
    for card in group["cards"]
]
```

then merge in any NF/SF pairs (`numbers` becomes `(nf_num, sf_num)`, `treatment` taken from the
NF-numbered member per `../../sets/README.md`) exactly where `mtg-checklist`'s `SECTIONS` merges
them for the same project — **the two files must describe the identical set of rows**, or
`template_needs.py`'s `(set_code, primary_number)` lookup will miss and show `?`. Keep only the
groups/cards that actually belong in this product's checklist (same filtering judgment as
`mtg-checklist`'s `EXCLUDE_PROMO`/section-bucketing step, filtered by the confirmed `subSet`
selection from `mtg-set-builder`, not by hand-picking individual cards).

**Numbers must stay strings in both `CARD_LIST` and `SECTIONS`.** `../../sets/README.md`'s schema
keeps `number` as a string on purpose (letter suffixes like `"232a"`). `template_needs.py` defends
against a stray int literal by `str()`-coercing before its lookup, but don't rely on that — write
real numbers as strings on both sides so the defense never has to fire.

## Matching by printing vs. by name

Two separate ownership pools are built from `../../owned/<CODE>/`'s files, and which pool a
`CARD_LIST` row draws from depends on both the row's `treatment` and whether Rule #5 is on:

- **`owned_by_printing`**, keyed by `(set_code, number)` — built from any CSV row where a
  collector-number column (and either a set-code column or a single-set-code project) was
  detected. Every row except a Rule-#5-pooled base-set row matches **only** this pool, at its own
  exact `numbers`.
- **`owned_by_name_fallback`**, keyed by card name — built from any CSV row with no detected
  collector-number column, and from every decklist line (`.txt` files never carry a collector
  number). Per the user's explicit instruction, a name-only ownership record is always treated as
  a copy of the card's **base-set printing** — it only ever contributes to a row whose
  `treatment == "Base Set"`, never to an alt-art row, and never through Rule #5's cross-printing
  pooling (which only pools `owned_by_printing` entries).

This means a CSV without collector-number detail is only useful for base-set completion tracking —
any alt-art/showcase/extended-art row's own Needs/Available will read as if you own zero of it,
even if you actually have copies, unless that export also carries printing detail. Tell the user
this plainly if a check of `csv_files_name_only` in `needs_result.json` is higher than expected.

**Header detection** (`_find_header` in `compute_needs.py`) matches case-insensitively against a
short candidate list per column (see the constants near the top of the file). If a real
mythic.tools export uses different header text than what's listed, either add the real header
string to the relevant candidate list or rename the column before running — don't silently accept
a file falling back to name-only matching when it actually has printing detail under an
unrecognized header.

**Same-name promo variants still apply here.** If two genuinely different physical cards share one
name and are *both* `treatment == "Base Set"` (rare, but real — see `mtg-checklist`'s REFERENCE.md
"Same-name promo variants"), Rule #5's per-name pooling will incorrectly conflate them, and the
name-only fallback pool can't tell them apart at all. If a set has this situation, key `CARD_LIST`
by `(name, distinguishing detail)` instead of bare name for those rows specifically — this is the
exception, not the default; verify by checking the actual data, not assuming it doesn't apply.

A `names_with_zero_owned` entry in `needs_result.json` for a card the user says they own almost
always means the export's name string doesn't byte-for-byte match Scryfall's name (curly vs.
straight apostrophe, an em-dash vs. hyphen in split-card names, a trailing collector-set suffix
some exporters append) — or, if it's a non-base-set row, that the export lacked printing detail
for that specific copy. Compare the two strings/columns directly rather than guessing.

## Verifying the result

Same spot-check approach as `mtg-checklist`'s REFERENCE.md "Verifying placement": `pypdf` extracts
page text from a rendered PDF, so you can search for `f"{name}"` near a known Needs/Available digit
to confirm a specific card landed where expected. Additionally, cross-check `needs_result.json`
directly for a couple of cards the user knows the real owned-copy count for — including at least
one Rule #5 alt-art-credit case (if Rule #5 is on) and one Rule #6 excluded-subSet case (if Rule #6
is on) — before ever rendering the HTML; it's a much cheaper place to catch a matching or
rules-logic bug than a full PDF re-render.
