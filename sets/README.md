# sets/ — permanent per-set card data cache

A Magic set's card list never changes after it's released, so each set only ever needs to be
fetched from Scryfall once. This folder holds one JSON file per set code (`LTR.json`,
`HOB.json`, ...), each an array of subSet groups, each holding the cards in that group, in
collector-number order overall. `mtg-checklist` and `mtg-checklist-needs` should check here
before hitting Scryfall live for a set they need — see "Using this cache from a skill" below.

## Schema

`<CODE>.json` is an array of groups; the set code itself is never repeated inside the file — it's
already the filename:

```json
[
  {
    "subSet": "Draft Cards",
    "cards": [
      {
        "number": "42",
        "name": "Bilbo, Retired Burglar",
        "color": "Multicolor",
        "type": "Legendary Creature — Hobbit Rogue",
        "rarity": "R",
        "treatment": "Base Set",
        "artist": "John Howe",
        "nonFoilAvailable": true,
        "foilAvailable": true,
        "surgeFoilAvailable": false,
        "otherFoilAvailable": false
      }
    ]
  }
]
```

- `subSet` — Scryfall's own official name for this group (see "The `subSet` grouping" below), or
  `null` if the set's page had no such breakdown at all (true for at least token sets, e.g.
  `THOB.json` is one group with `"subSet": null`). Groups appear in the order their first card is
  encountered in collector-number order — not alphabetical, not by group size.
- `number` — Scryfall's `collector_number`, kept as a **string** (some carry letter suffixes,
  e.g. `"232a"`, `"H13"`) — don't coerce to int.
- `name` — see "The `name` field" below; not always Scryfall's raw `name`.
- `color` — `Land` / `Colorless` / `White` / `Blue` / `Black` / `Red` / `Green` / `Multicolor`,
  same classification rule as `mtg-checklist`'s REFERENCE.md "Fetching color data": land by
  type first, then by count of `colors`.
- `type` — Scryfall's raw `type_line`.
- `rarity` — abbreviated `C`/`UC`/`R`/`MR` (falls back to `S`/`B` for `special`/`bonus`
  rarities, or the rarity's first letter uppercased for anything else Scryfall introduces).
- `nonFoilAvailable` / `foilAvailable` — from Scryfall's `finishes` field directly
  (`foilAvailable` is true for `finishes` containing `foil` OR `etched`).
- `surgeFoilAvailable` — true if `promo_types` contains `surgefoil`.
- `otherFoilAvailable` — true if `promo_types` intersects a known set of *other* special foil
  treatments (galaxy foil, ripple foil, neon ink, etc. — see `OTHER_FOIL_PROMO_TYPES` in
  `build_set.py`). **This list is a heuristic, not authoritative** — Scryfall adds new foil
  treatment promo_types almost every set. If a set's checklist shows a card's special foil as
  plain `foilAvailable` with `otherFoilAvailable` false, check that print's real `promo_types` on
  Scryfall and add the missing value to the set in `build_set.py`.

One entry per real Scryfall print object, no promo-type filtering applied (unlike
`mtg-checklist`'s per-project `EXCLUDE_PROMO` step, which is about deciding which prints belong
in a *specific retail product's* checklist). This cache is the complete raw record; filtering
which cards go into a given checklist is a downstream decision made per-project. No `setCode` per
card — it's redundant with the filename — and no per-card `section` key either, since that's now
the array's grouping key (`subSet`) rather than a repeated field on every card.

## The `name` field — printed name, not always Scryfall's Oracle `name`

`build_row` uses `card["flavor_name"] or card["name"]` — Scryfall's `name` field is the card's
Oracle/functional identity (shared across every printing of the same card, whatever it's called
on any given print), while `flavor_name` is what's actually printed on *this specific card* when
it differs. Universes Beyond sets do this often: a new card reskins an existing card's exact
rules text under new art and a new in-theme name. Confirmed on LTR `#398`: Scryfall's `name` is
`"Trailblazer's Boots"` (the reprinted card it functions as) but `flavor_name` is `"Lórien
Brooch"` (what's printed on the LTR card) — `name` here is `"Lórien Brooch"`, matching what a
collector actually sees.

**This has a real, opposite-direction cost for `mtg-checklist-needs`.** That skill's
`compute_needs.py` matches ownership by exact name string against a collection export — and a
collection export (mythic.tools or similar) is far more likely to list the Oracle name
(`"Trailblazer's Boots"`) than the flavor name, since that's the functional card being tracked.
A `CARD_LIST` built from this cache's `name` field would then fail to match that ownership record
at all (`names_with_zero_owned` would wrongly include it even if the user owns copies under the
reprinted name). If a project's `Own/` export can plausibly contain Oracle names for a reskinned
card, resolve it there — override that one row's name back to the export's naming convention (or
match on Scryfall's `oracle_id` instead of name) — rather than changing this cache's `name` back
to the Oracle name and losing the printed-name benefit for everything else.

## The `treatment` field

A generic frame/border classification, derived *only* from real structured Scryfall fields
(`frame_effects`, `border_color`, `full_art`, `promo_types`) — never from collector-number
ranges or guesswork. Checked in this priority order (first match wins, since a print can carry
more than one of these signals at once):

1. `"poster" in promo_types` → **Poster**
2. `"showcase" in frame_effects` → **Showcase**
3. `"extendedart" in frame_effects` → **Extended Art**
4. `border_color == "borderless" and full_art` → **Full Art Borderless**
5. `border_color == "borderless"` → **Borderless**
6. `full_art` → **Full Art**
7. otherwise → **Base Set**

This reliably reproduces most of what a hand-built `mtg-checklist` project treats as a distinct
section (verified against HOB: `Showcase` count 50 raw prints / 2 = 25 rows, matching that
project's "Dragon Hoard Frame" section exactly; `Extended Art` count 28, matching that project's
"Extended Art" section exactly).

**What `treatment` deliberately does NOT give you: a set's own editorial name for a specific
alternate frame or narrative scene.** Scryfall has no field for "this alternate frame is called
Dragon Hoard" or "this card belongs to the Fight with the Great Goblin scene" — those are names a
human assigned when building the checklist, informed by preview articles or the actual artwork,
not something the API exposes as a string. What `treatment` (plus `artist`, below) gives you is
the automatic *grouping* — which rows structurally belong together — so the remaining manual work
is just attaching a name to each group, not re-deriving the groups themselves from collector-number
ranges by hand.

**`treatment` is per real Scryfall print object, and an NF/SF paired row should trust the
NF-numbered member.** Verified on HOB: a "Poster"-treatment card's non-foil print carries
`promo_types` including `"poster"`, but its separately-numbered surge-foil twin sometimes doesn't
carry `"poster"` at all — same visual design, under-tagged data — so that SF print's row here
reads `"Borderless"` even though it's really the same Poster/"Book Cover Frame" treatment as its
NF pair. When collapsing an NF/SF pair into one checklist row (`mtg-checklist`'s `NF_SF` mode),
use the NF number's `treatment` value for the pair, not the SF number's.

## The `subSet` grouping — Scryfall's own official breakdown, scraped from its website

Scryfall's **human-facing set page** (`https://scryfall.com/sets/<code>` — not the JSON API,
which has no equivalent field) renders every set's booster/product breakdown as named groups —
e.g. HOB's page groups its 321 cards into `Draft Cards` (193), `Dragon Hoard Frame Cards` (25),
`Dragon Hoard Surge Foils` (25), `Borderless Scene Cards` (15), `Book Cover Cards` (10), `Book
Cover Surge Foils` (10), `Journey Basic Lands` (5), `Seasonal Basics` (4), `Surge Foil Seasonal
Basics` (4), `Extended Art Cards` (28), `Gleaming Headliner` (1), `Bundle Promo` (1). These are
Scryfall's own curated, official names — this is what a hand-built checklist's section titles
should actually be sourced from, not reverse-engineered from collector-number ranges or
frame/promo-type guessing, and it's exactly what `<CODE>.json`'s top-level `subSet` groups are
built from.

`build_set.py` fetches that page (`fetch_section_map`) and matches its `data-card-id` attributes
(one per card shown under each `<h2 class="card-grid-header">`) against the API's `id` field for
each print — a set-code- and set-name-agnostic join, robust to punctuation/HTML-entity
differences in card names. A card lands in the `subSet: null` group when the set page has no such
breakdown at all (true for at least token sets — all of `THOB.json` is one `subSet: null` group)
or, rarely, when a print the set page doesn't list under any header.

**This can be *more* granular than what a previous hand-built project used, not just a source for
it.** On `HOC`, Scryfall's own page names two distinct narrative scenes individually — `Scene:
Crack the Plates` (6 cards) and `Scene: Treasures of Smaug` (6 cards) — where an earlier
hand-built Hobbit checklist project lumped both under one generic title, "Scene Box New-to-Magic
Scene Card" (12 cards). Always prefer the scraped `subSet` name over inventing your own grouping
name when it's non-null.

**When Scryfall's own grouping alone isn't granular enough, fall back to `treatment` + `artist`
within a `subSet: null` group (or a single scraped group that's actually visibly two themes).**
HOB's own page groups two genuinely different movie battles under one umbrella, `Borderless Scene
Cards` (15 cards) — Scryfall didn't split those two scenes into separate groups the way it did for
HOC. Grouping that group's cards further by `artist` recovers the split (verified: 6 cards by Ted
Nasmith vs. 9 by Denman Rooke, matching a prior hand-built checklist's "Fight with the Great
Goblin Scene" / "The Five Armies Clash! Scene" split exactly) — but naming each sub-group is still
a manual, per-scene judgment call (reading the cards' names/art, or an official preview article),
not something either the scraped grouping or `treatment` can give you directly.

**A confirmed split gets baked in as a permanent override, not a one-off hand-edit.**
`build_set.py`'s `MANUAL_SUBSET_OVERRIDES` is a `{SET_CODE: [(lo, hi, name), ...]}` escape hatch
for exactly this. Two examples confirmed with the user so far, both rebuilt with `--force`
afterward:

- `HOB`'s scraped `Borderless Scene Cards` group covers two distinct movie battles with no
  subSet-level split of its own — confirmed against the artist-based split (Ted Nasmith vs.
  Denman Rooke, see "The `artist` field" below) and overridden into `#199`-`204` →
  `"Fight with the Great Goblin Scene"` and `#205`-`213` → `"The Five Armies Clash! Scene"`.
- `LTR`'s scraped `Scene Cards` group (53 cards, `#399`-`451`) covers seven distinct movie scenes
  Scryfall's page left combined — the user supplied the scene titles and exact number ranges
  directly (not derivable from any Scryfall field, structured or scraped), overridden into seven
  named sub-groups from `"Bilbo's Birthday Party Scene"` (`#399`-`404`) through `"Mount Doom
  Scene"` (`#448`-`451`).

Add a new override only after that same kind of confirmation (either a verified structural signal
like `artist`, or the user directly supplying the split), never as a guess, and always through
this table in `build_set.py` — never by hand-editing `<CODE>.json` directly, since a later
`--force` rebuild would silently discard a hand-edit.

**Sanity-check after building/refreshing a set:** `build_set.py` prints a warning if the section
page's total card-id count doesn't match the API's print count for that set (a sign the set page
paginated — not observed on any set built so far, up to LTR's 856 cards — or that some print
genuinely isn't listed on the page). Treat a `subSet: null` group on a set whose other groups are
mostly non-null as suspicious and worth checking by hand, not as an expected gap — and see
"Verifying a build" below for the per-group confirmation step to run after every build.

## The `artist` field

Straight from Scryfall's `artist` field. Its main use here: a project's "plain borderless, no
special promo tag" cards (`treatment == "Borderless"`) can still span more than one distinct named
scene/theme within a single `subSet` group, and — at least for panorama-style Scene cards — each
distinct scene is illustrated by one dedicated artist across all its cards. Grouping such cards
further by `artist` recovers that split: on HOB's `Borderless Scene Cards` group, this exactly
separates "Fight with the Great Goblin Scene" (6 cards, artist Ted Nasmith, `#199`-`#204`) from
"The Five Armies Clash! Scene" (9 cards, artist Denman Rooke, `#205`-`#213`) — a distinction
neither the scraped `subSet` name nor `treatment` makes on its own, since both sub-groups share an
identical `treatment` and the same `subSet`. As with `treatment`, this only gives you the
grouping; the scene's actual title still has to come from a human (spoiler article, box art, or
just describing what's depicted).

## Building/refreshing a set's cache

`build_set.py` lives in `../skills/mtg-set-builder/`, not in this folder — `sets/` holds only
data. It resolves this folder relative to its own file location, so it can be run from anywhere
(the repo root, this folder, wherever) and still write here:

```bash
python ../skills/mtg-set-builder/build_set.py HOB HOC THOB      # any number of set codes in one run
python ../skills/mtg-set-builder/build_set.py LTR --force       # re-fetch even though LTR.json already exists
```

Without `--force`, a set code whose `<CODE>.json` already exists is skipped — that's the whole
point of this cache (a set's cards don't change once released, so a re-fetch is never *needed*,
only ever a deliberate correction). Only pass `--force` if you have a specific reason to believe
the cached data is wrong (a Scryfall data-entry fix, a bugged promo_types tag, etc.) — this is a
network call to a third party, not a routine step.

**Before hitting Scryfall at all, `build_set.py` first checks this repo's own GitHub `sets/`
folder** (`https://github.com/berv63/mtg-skills/tree/master/sets`) for an already-built copy of
the requested code, and downloads that instead if found — installing this repo's skills via
`npx skills add` only pulls down `skills/`, not `sets/`, so a fresh install otherwise has an
empty local cache even for sets someone else already built and committed upstream. `--force`
skips this check and goes straight to Scryfall (the point of `--force` is correcting a *stale*
build, and the GitHub copy is presumably the stale thing being corrected). A copy pulled this way
needs no local re-verification — it was already hand-verified when it was built and committed —
see `mtg-set-builder`'s SKILL.md step 3. `mtg-sets-sync` (a sibling skill,
`skills/mtg-sets-sync/`) does the same GitHub download for several set codes at once, useful for
seeding the whole local cache right after a fresh install rather than hitting this shortcut one
code at a time as each checklist run happens to need it.

`build_set.py` talks to Scryfall directly via `urllib` (stdlib) — no `requests`, `curl`, or HTML
parser dependency (the section scrape uses two small regexes, not a full HTML parser — see "The
`subSet` grouping" above). Two requests per set code: the JSON API (`api.scryfall.com/cards/search`,
paginated via `has_more`/`next_page`) for the card data, and the human set page
(`scryfall.com/sets/<code>`) for the `subSet` breakdown. The API requires `User-Agent: Mozilla/5.0`
and `Accept: */*` — it returns a plain `400 Bad Request` without an explicit `Accept` header
(discovered empirically — Python's `urllib` default request doesn't send one). The set page only
needs the `User-Agent`.

After writing `<CODE>.json`, `build_set.py` prints one line per `subSet` group — its name, card
count, and its first and last card (number + name) in collector-number order, e.g.:

```
wrote HOB.json: 12 subSets, 321 cards
  - 'Draft Cards': 193 cards, first #1 'Long-Bodied Grey Dog', last #193 'Forest'
  - 'Journey Basic Lands': 5 cards, first #194 'Plains', last #198 'Forest'
  ...
```

That printed list is exactly what "Verifying a build" below walks through with the user — the
script doesn't ask for confirmation itself (it has no interactive step), it just prints what
there is to confirm.

## Verifying a build

After building or `--force`-rebuilding a set, confirm each `subSet` group with the user **one
group at a time** before treating the cache as trustworthy — this is what actually catches a bad
scrape (a section-page markup change, a card that landed in the wrong group, a `subSet` that
should have split into two scenes but didn't). For each group, present:

- the `subSet` name (or "no subSet / ungrouped" if `null`),
- the first card in the group (number + name),
- the last card in the group (number + name),
- the card count,

and ask whether that looks right. Batch a few groups per question round rather than one at a
time in separate messages — it's the same confirmation, just less back-and-forth. If something's
off (wrong boundary card, a group that's obviously two different themes, a suspicious `null`),
fix `build_set.py` or `OTHER_FOIL_PROMO_TYPES`/the section-parsing regex as needed and rebuild
with `--force` before re-verifying — don't hand-patch the JSON output directly, or the next
`--force` rebuild will silently overwrite the fix.

Once every group is confirmed, this repo (`mtg-skills`) is a git repo — offer to commit the new
or corrected `sets/` files on a branch (see `mtg-set-builder`'s SKILL.md step 4 for exactly how);
never commit without being asked.

### Running without Python installed

Same Docker fallback as both skills — mount the whole repo root (not just `sets/`), since
`build_set.py` needs to see its own `../../sets/` relative to itself:

```bash
cd /path/to/mtg-skills
docker run --rm -v "$(pwd):/work" -w /work python:3-slim python skills/mtg-set-builder/build_set.py HOB
```

```powershell
cd C:\path\to\mtg-skills
docker run --rm -v "${PWD}:/work" -w /work python:3-slim python skills/mtg-set-builder/build_set.py HOB
```

(On Git Bash specifically, prefix with `MSYS_NO_PATHCONV=1` — Git Bash otherwise rewrites
`/work` into a bogus Windows path before Docker sees it.)

## Using this cache from a skill

Before doing a live Scryfall fetch for a set (`mtg-checklist`'s REFERENCE.md "Fetching color
data", or the equivalent step in `mtg-checklist-needs`), check whether `../../sets/<CODE>.json`
already exists for every set code the product involves. If it does, derive `color_lookup.json`
straight from its groups' `color`/`number` fields — the set code comes from the filename, since
it's not repeated inside the file:

```python
import json
color_lookup = {}
for code in ["HOB", "HOC"]:
    for group in json.load(open(f"../../sets/{code}.json", encoding="utf-8")):
        for card in group["cards"]:
            color_lookup[f"{code}:{card['number']}"] = card["color"]
```

Zero network calls, same data. If a set code is missing, run `../mtg-set-builder/build_set.py`
for it once (see above), then proceed the same way. Only fall back to a one-off live `curl`/`urllib` query for a
set code you don't intend to keep (rare — most work here is on real released products worth
caching permanently).

For `mtg-checklist`'s step 1 (working out each section's title and finish mode), the file's
`subSet` groups largely *are* that step already done — each group's `subSet` name should become
the checklist section title verbatim wherever it's non-null. Only fall back to grouping a
`subSet: null` group's cards by `treatment` (and, for a `Borderless` cluster covering more than
one evident theme, further by `artist`) and only invent a title by hand as the last resort for a
sub-group neither field separates on its own.
