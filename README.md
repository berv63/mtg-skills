# mtg-skills

A small collection of [Agent Skills](https://agentskills.io) for building Magic: The Gathering
collection checklists — a printable one (`mtg-checklist`) and a web-only Needs/Available one
(`mtg-checklist-needs`) — plus permanent, hand-verified caches of Scryfall set data and personal
ownership data they read from. Written for an AI coding agent to follow — this file is the map;
each skill's own `SKILL.md` is the authority on how to actually do its part.

## Install

```bash
npx skills add berv63/mtg-skills --skill '*'         # every skill, to whatever agents you use
npx skills add berv63/mtg-skills --skill mtg-checklist --agent claude-code
```

This is a public repo, so no extra auth is needed either for `npx skills add` or for the
GitHub-hosted `sets/` lookups described below.

`npx skills add` only pulls down the `skills/` folder — **not** `sets/`, `owned/`, `output/`, or
`projects/`. That's fine for `owned/`/`output/`/`projects/` (personal, per-machine data anyway),
but it means a fresh install starts with an empty local `sets/` cache even though this GitHub
repo may already have several sets built and committed. `mtg-set-builder`'s own `build_set.py`
covers this automatically per-set (see below), and `mtg-sets-sync` bulk-seeds several at once —
run it once right after install if you'd rather not pay even that first per-set GitHub round trip
during a checklist run.

## The four skills, and how they fit together

```
skills/mtg-set-builder/      resolves ONE target set + which subSet groups to include
skills/mtg-sets-sync/        bulk-downloads already-built sets/ caches from GitHub (optional, post-install)
skills/mtg-checklist/        renders the finish-checkbox (NF/TF/SF) checklist HTML
skills/mtg-checklist-needs/  renders the Needs/Available checklist HTML (vs. a collection export)
sets/                        the shared cache both checklist skills read from (what cards exist)
owned/                       the shared cache mtg-checklist-needs reads from (what you own)
output/                      where mtg-checklist-needs writes its rendered HTML
projects/                    where mtg-checklist-needs' own working copies of its scripts live
```

**Always run `mtg-set-builder` first.** Whichever checklist skill the user asked for, its own
`SKILL.md` starts with a step 0 that hands off to `mtg-set-builder`'s full procedure: resolve
exactly one set code (from the cached codes in `sets/*.json`, or a fresh one the user names),
build it from Scryfall if it isn't cached yet, verify the result with the user subSet-by-subSet,
optionally commit a new/corrected set, then let the user pick which `subSet` groups actually
belong in this checklist. Only once that's confirmed does `mtg-checklist` or
`mtg-checklist-needs` start building anything. Never skip straight to a checklist skill's step 1
without that handoff — the set code and subset selection it produces are inputs the rest of the
skill depends on.

**A checklist covers exactly one set at a time.** Don't combine multiple set codes into one run,
and don't build a checklist for a set you haven't resolved through `mtg-set-builder` in this
session (even a previously-cached one — its step 1 is nearly free when nothing needs building).

**`mtg-checklist` and `mtg-checklist-needs` are siblings, not a pipeline** — pick whichever one
the user actually asked for (a plain checkbox checklist vs. a "what do I still need" count),
though `mtg-checklist-needs`' own docs note it can reuse a `mtg-checklist` run's section/color
data for the same set rather than re-deriving it.

## The `sets/` cache

One JSON file per set code (`LTR.json`, `HOB.json`, ...), each holding Scryfall's own official
`subSet` breakdown for that set (scraped from its Scryfall web page, not invented from
collector-number ranges) plus per-card color/rarity/finish/treatment/artist data. A set's cards
never change after release, so a set is fetched and hand-verified with the user **once**, then
reused indefinitely — see `sets/README.md` for the full schema, the scrape mechanics, the manual
override table for a Scryfall grouping that needed splitting or renaming, and exactly how to add
or refresh a set. Don't read this cache's raw JSON schema assumptions from memory — it's evolved
across sessions (nested `subSet`/`cards` structure, no per-card `setCode`, `name` preferring
Scryfall's `flavor_name`); check `sets/README.md` if anything about a field's meaning is unclear.

## The `owned/` cache

The opposite kind of data from `sets/`: one folder per set code (`owned/HOB/`, ...) holding the
user's own collection export CSV(s), optional decklists, and a `rules.json` recording which of
`mtg-checklist-needs`' six completion rules apply to that set — see `owned/README.md` and
`skills/mtg-checklist-needs/REFERENCE.md` "The completion rules". Unlike `sets/`, this is personal,
frequently-changing data — it's git-ignored (see `.gitignore`) and only `mtg-checklist-needs`
reads it.

## `mtg-checklist-needs`' project folders must live under `projects/`

Unlike `mtg-checklist` (whose rendered output goes to an arbitrary user-chosen "project folder"),
`mtg-checklist-needs`' copies of `compute_needs.py`/`template_needs.py` use **relative** paths at
runtime to reach `owned/` and `output/` (`../../owned/<CODE>`, `../../output/...`) — there's no
absolute, machine-specific path anywhere in either script, since they need to run correctly on
whatever machine the user is on. That only resolves correctly if the project folder is created
directly under the repo root, e.g. `projects/<descriptive-name>/` — sister to `sets/`, `owned/`,
`output/`, `skills/` — so `../../` from inside it always lands on the repo root, exactly like every
other skill's `../../sets/...` references. This folder is git-ignored too (working copies of the
per-project scripts + intermediate JSON, not something to version-control).

## Repo conventions worth knowing before editing anything here

- Every skill folder is `SKILL.md` (required `name` + `description` frontmatter) plus a
  `REFERENCE.md` for the detailed rules/recipes the `SKILL.md` steps point at — keep that split;
  don't inline REFERENCE.md content back into SKILL.md or vice versa.
- Every script here (`skills/mtg-set-builder/build_set.py`, `skills/*/template*.py`,
  `skills/*/compute_needs.py`) is stdlib-only Python by design, specifically so the Docker
  fallback documented in each skill's REFERENCE.md (`docker run ... python:3-slim python
  <script>.py`) works with zero `pip install` for the core path. `sets/` itself holds only data
  (JSON caches + its own README) — no scripts.
- `build_set.py` resolves the repo's `sets/` folder relative to its own file location, not the
  caller's working directory, so it can be run from anywhere in the repo (or via Docker mounting
  the whole repo root) and still write to the right place.
- This repo is a real git repo with a real remote (`origin` → this GitHub repo). Committing or
  pushing anything — including a new/refreshed `sets/<CODE>.json` — only happens when the user
  asks, per each skill's own explicit git-safety guidance; nothing here should ever auto-commit.
