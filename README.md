# mtg-skills

A small collection of [Agent Skills](https://agentskills.io) for building printable Magic: The
Gathering collection checklists, plus a permanent, hand-verified cache of Scryfall set data they
all read from. Written for an AI coding agent to follow — this file is the map; each skill's own
`SKILL.md` is the authority on how to actually do its part.

## Install

```bash
npx skills add berv63/mtg-skills --skill '*'         # every skill, to whatever agents you use
npx skills add berv63/mtg-skills --skill mtg-checklist --agent claude-code
```

This is a **private** repo — `npx skills add` works the same as for a public one, using whatever
Git credentials/GitHub CLI auth is already configured locally (see the `skills` CLI's own docs,
"Private Repositories"). No extra flags needed if `gh auth status` already succeeds.

## The three skills, and how they fit together

```
skills/mtg-set-builder/      resolves ONE target set + which subSet groups to include
skills/mtg-checklist/        renders the finish-checkbox (NF/TF/SF) checklist HTML
skills/mtg-checklist-needs/  renders the Needs-count checklist HTML (vs. a collection export)
sets/                        the shared cache both checklist skills read from
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

## Repo conventions worth knowing before editing anything here

- Every skill folder is `SKILL.md` (required `name` + `description` frontmatter) plus a
  `REFERENCE.md` for the detailed rules/recipes the `SKILL.md` steps point at — keep that split;
  don't inline REFERENCE.md content back into SKILL.md or vice versa.
- Every script here (`sets/build_set.py`, `skills/*/template*.py`, `skills/*/compute_needs.py`)
  is stdlib-only Python by design, specifically so the Docker fallback documented in each
  skill's REFERENCE.md (`docker run ... python:3-slim python <script>.py`) works with zero
  `pip install` for the core path.
- This repo is a real git repo with a real remote (`origin` → this GitHub repo). Committing or
  pushing anything — including a new/refreshed `sets/<CODE>.json` — only happens when the user
  asks, per each skill's own explicit git-safety guidance; nothing here should ever auto-commit.
