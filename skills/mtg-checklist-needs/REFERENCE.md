# Reference: mtg-checklist-needs

## Running without Python installed

Both scripts only use the standard library (`csv`, `glob`, `json`, `os`, `re`, `html`) — no venv
or pip install needed for the core workflow, and neither one has an absolute path anywhere in it.
Both `OWNED_DIR` (`compute_needs.py`) and `OUTPUT_PATH` (`template_needs.py`) are relative to the
current working directory — `owned/<CODE>` (or `Owned/<CODE>`/bare `<CODE>`, see
`_find_owned_dir`) and `code/<CODE>_needs_avail.html` respectively — with no repo-root dependency
at all, so they resolve correctly regardless of where that directory happens to be. If neither
`python` nor `python3` resolves on the machine, run them in Docker instead — just mount the current
working directory itself:

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
executes fully offline. No custom Dockerfile is required for either step — there's no
pagination-calibration step here at all (see "Web-only layout — no pagination" below), so nothing
in this skill ever needs `pymupdf`/`pypdf`/a headless browser.

## Web-only layout — no pagination

This template targets a scrolling web page, not a printed page, and deliberately does **not**
share `mtg-checklist`'s pagination engine (`UNIT_BUDGET`, `TRANSITION_COST`, `chunk_into_columns`/
`chunk_into_blocks`, `page_remaining` chaining, `force-break` classes, `@media print`, `@page`) —
none of that exists in `template_needs.py` any more. Each `subSet` is one `.section` containing
**every** one of its cards, laid out via `split_into_columns(rows, COLS)` — a plain even split by
row count (`divmod(len(rows), COLS)`, extra rows going to the earliest columns), no page-fit budget
and no color-header-density accounting. A color group is free to span a column boundary; the
column header at the top of every column always reflects whatever group its first row belongs to
(even mid-group), and repeats again further down that column wherever the color changes — same
visual convention as before, just without any print-break logic driving where columns split.

If the user ever wants a print-oriented version of this same Needs/Available data back, that's a
different template (closer to `mtg-checklist`'s engine, ported to carry two numeric columns instead
of checkboxes) — don't try to bolt print pagination back onto this file piecemeal.

## The project's code/ folder

The rendered checklist is the one artifact this skill delivers to the user, and it's written
*inside the current working directory itself* — a `code/` subfolder right alongside the copies of
`compute_needs.py`/`template_needs.py` (created on demand, no need to ask before creating the
empty folder itself) — never a shared repo-level location. This is a deliberate design choice, not
an accident: an earlier version wrote to a shared `../../output/` folder sister to `sets/`/`owned/`,
resolved relative to a `projects/<name>/` folder that was **required** to sit directly under the
repo root. That broke down as soon as the assumption didn't hold — these skills installed globally
via `npx skills add` land in `~/.agents/skills/`, completely detached from any real repo checkout,
so a run from there put the rendered file somewhere under `~/.agents/output/`, nowhere near
anything the user was actually working on. There is no `projects/` folder or repo-root requirement
any more: wherever the user happens to be working *is* the project, full stop, and both the
ownership lookup (`compute_needs.py`'s `OWNED_DIR`, see "Matching by printing vs. by name" below)
and the rendered output stay self-contained inside that one directory. The default filename is
`<CODE>_needs_avail.html`.

**Resolving the exact path (SKILL.md step 5), before `template_needs.py` ever runs — all relative
to the current working directory:**

1. `os.makedirs("code", exist_ok=True)`.
2. If `code/<CODE>_needs_avail.html` doesn't exist, that's the target — done.
3. If it does exist, ask the user via AskUserQuestion: overwrite the existing file, or create a new
   one. Never decide this yourself and never overwrite silently — a previous run's file may still
   be open in the user's browser or shared with someone else.
4. If they choose "new," find the first free `<CODE>_needs_avail_<N>.html` starting at `_1` (glob
   `code/<CODE>_needs_avail_*.html`, parse the trailing integer, use `max + 1` — don't just try
   `_1` and stop if a `_2` already exists without `_1`, i.e. don't assume no gaps).

Set `template_needs.py`'s `OUTPUT_PATH` constant to that resolved relative path (same
`os.path.join("code", "<resolved filename>")` shape as the placeholder already there) before
running it — the script itself never prompts (nothing in this skill is interactive Python; the
overwrite decision belongs at the SKILL.md/agent level, not baked into the engine). The script
creates `code/` itself too (`os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)`) as a safety
net, but step 5 should already have done this.

`needs_result.json`/`color_lookup.json` are intermediate artifacts and stay directly in the project
folder wherever `compute_needs.py`/`template_needs.py` are copied to; only the final rendered HTML
goes one level deeper, into that same project folder's `code/` subfolder.

## The ownership folder

Personal, frequently-changing data — which cards the user actually owns — as opposed to `sets/`'s
permanent, never-changing record of which cards exist. Lives inside the current working directory
(see "The project's code/ folder" above for why): `owned/<CODE>/`, `Owned/<CODE>/`, or a bare
`<CODE>/`, whichever `_find_owned_dir` finds first, defaulting to `owned/<CODE>/` if none exist yet.
It's reused across every future `mtg-checklist-needs` run *from that same working directory* for
that set — an ownership CSV dropped in once benefits every later run there, not just the one that
created it — but starting from a different working directory starts fresh. Nothing here is
regenerated automatically; a file placed here stays until the user removes or replaces it.

```
owned/                (or Owned/, or skip this level entirely)
  HOB/
    collection_2026-01-05.csv    (one or more ownership exports, see below)
    welcome_deck.txt             (optional plain-text decklists)
    rules.json                   (the confirmed completion-rules selection for this set)
```

If the user is tracking more than one set from the same working directory, each gets its own
`<CODE>/` subfolder as shown above. This folder should be added to whatever ignore file the user's
own working directory uses (if it's version-controlled at all) — personal collection data doesn't
belong committed anywhere, and it changes far too often to track sensibly.

### Ownership file formats

`compute_needs.py` reads two kinds of source from the resolved ownership folder, both matched by
glob so any number of files of each kind works:

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

### `rules.json` — the completion-rules selection

The ownership folder's `rules.json` records which of this skill's completion rules the user picked,
and (for Rule #6) which subSets they don't care about completing:

```json
{
  "rules": ["1", "3", "5", "6"],
  "excluded_subsets": ["Extended Art Cards", "Bundle Promo"]
}
```

`compute_needs.py` reads this at run time (not hand-transcribed into the script's own constants,
unlike `CARD_LIST`) so re-running the script after an ownership update never requires re-asking the
user which rules apply. See "The completion rules" below for what each rule number means and how
they combine. This file is created the first time `mtg-checklist-needs` is run for a set (after
confirming the rules with the user via AskUserQuestion) and only changes when the user explicitly
asks to change their rules for that set.

## The completion rules

Six independent yes/no rules the user picks per set (stored in the resolved ownership folder's
`rules.json` — `owned/<CODE>/rules.json` by default, see "The project's code/ folder" above — in a
`rules` array, by number as strings — `"1"` through `"6"`). None of them require each other; any
combination is legal. `compute_needs.py`'s `target_needs`/`keep_threshold` functions are the
executable version of everything below — read this alongside them, not instead of them.

- **#1 — "I want at least one of every card."** Sets the Needs target to 1 for every row,
  *unless* a stronger rule below also applies. Applies to every `treatment`, not just Base Set —
  wanting at least one of a specific alt-art/showcase printing is a normal, common goal.
- **#2 — "I want to own at least 4 of each card."** Sets the Needs target to 4, unless Rule #3
  overrides it for R/MR. **Only applies to `treatment == "Base Set"` rows** — a target of 4 (or
  2, for #3) is a playset-completion goal, and nobody wants 4 copies of the same
  alt-art/showcase/extended-art printing. A non-base-set row is untouched by #2/#3 regardless of
  rarity; it falls through to Rule #1's flat target of 1 (if selected) or the `DEFAULT_TARGET`
  baseline, exactly as if #2/#3 were never checked for that row.
- **#3 — "I want to own at least 2 of each R/MR card."** Sets the Needs target to 2, but only for
  Base-Set-treatment Rare/Mythic Rare rows (same base-set-only restriction as #2, above — an R/MR
  alt-art row falls through to #1/`DEFAULT_TARGET` instead). **This is a specific override, not a
  floor to be maxed with Rule #2** — if both #2 and #3 are checked, a base-set R/MR row gets 2
  (Rule #3 wins), not 4. This was confirmed explicitly with the user rather than assumed; don't
  "fix" it back to `max(2, 4)`.
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

State back, in plain language, exactly what will happen for each rarity **and each treatment** —
not just which numbers were checked; #2/#3's base-set-only scope is easy to state wrong as "every
common/uncommon" when it actually only covers base-set-treatment rows. E.g. for
`rules: ["1","2","3"]`: "Base-set commons/uncommons target 4 copies (Rule #2). Base-set
rares/mythics target 2 copies (Rule #3 overriding Rule #2's 4). Every alt-art/showcase/extended-art
row, regardless of rarity, targets just 1 copy (Rule #1 — #2/#3 don't apply to those printings)."

Another example, for `rules: ["2","3","4","5"]`: "Base-set commons/uncommons target 4 copies.
Base-set rares/mythics target 2 copies (Rule #3 overriding Rule #2's 4), but you're willing to
trade down to 2 of those regardless (Rule #4 — redundant with #3 here since both land on 2, but
would matter if you later drop #3). Alt-art rows fall back to the default target (1 for R/MR, 4
for C/UC) since #2/#3 don't apply to them and #1 isn't selected. Base-set rows will credit owned
alt-art copies toward completion once you own at least one real base-set copy (Rule #5)."
Catching a misunderstanding here is much cheaper than after `compute_needs.py` has run.

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

Two separate ownership pools are built from the resolved ownership folder's files (`OWNED_DIR` —
`owned/<CODE>/` by default, see "The project's code/ folder" above), and which pool a `CARD_LIST`
row draws from depends on both the row's `treatment` and whether Rule #5 is on:

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

No PDF/pypdf step — this is a plain HTML page, so open the file written to the project's `code/`
directly in a browser
(or `grep`/`Grep` the raw HTML for `f"{name}"` if a quick headless check is enough) to confirm a
specific card landed where expected and its Needs/Available values read correctly. Cross-check
`needs_result.json` directly for a couple of cards the user knows the real owned-copy count for —
including at least one Rule #5 alt-art-credit case (if Rule #5 is on) and one Rule #6
excluded-subSet case (if Rule #6 is on) — before ever rendering the HTML; it's a much cheaper place
to catch a matching or rules-logic bug than re-rendering. In the browser, also confirm each
section reads as one continuous block (no visual break partway through) and that a section smaller
than `COLS` cards just leaves its extra columns empty rather than looking broken.
