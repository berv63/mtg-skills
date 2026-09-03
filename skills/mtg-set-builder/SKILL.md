---
name: mtg-set-builder
description: "Resolve a single target Magic: The Gathering set — from the shared sets/ cache, or freshly built from Scryfall if it isn't cached yet — and let the user pick which subSet groups to include. This is the shared intake step mtg-checklist and mtg-checklist-needs both run before building anything; it can also be invoked on its own just to add or refresh a cached set."
---

Produces two things for whichever skill invoked it (or for its own sake): exactly one confirmed
set code, and the confirmed list of `subSet` groups (from `../../sets/<CODE>.json`) to work with.
Never resolves more than one set per run — a checklist covers one set at a time. `build_set.py`
in this same folder is the working engine (fetches Scryfall, writes into `../../sets/`) — `sets/`
itself holds only data, no scripts. `../../sets/README.md` holds the schema, the scrape
mechanics, `MANUAL_SUBSET_OVERRIDES`, and the full "Verifying a build" writeup — read it before
step 2, don't duplicate it here.

1. **Resolve exactly one set code.** If the user already named one (a code like "HOB", or a
   plain-language name you can map to one), use it. Otherwise, glob `../../sets/*.json` and present
   the cached codes via AskUserQuestion (an "Other" option is always available for a code that
   isn't cached yet) — ask which single set they want. A product's companion token set (e.g.
   `THOB` alongside `HOB`) is a separate code/file; if their request could mean either, ask which
   one specifically rather than guessing.

2. **Build the set if `../../sets/<CODE>.json` doesn't exist yet.** Tell the user this means a live
   Scryfall fetch (two requests: the card API, and a scrape of the set's Scryfall web page — see
   `../../sets/README.md`) before running `build_set.py <CODE>` (same folder as this file; it
   resolves `../../sets/` itself regardless of your working directory — Docker fallback per
   `../../sets/README.md`'s "Running without Python installed" if Python isn't available locally).
   Skip this step entirely for a code that's already cached.

3. **Verify a new build with the user before trusting it.** Follow `../../sets/README.md`
   "Verifying a build" exactly: present every `subSet` group (name, first card, last card, count),
   batched a few per question round, and ask for confirmation. When the user corrects a group
   (a split, a wrong boundary, a bad name), add a `MANUAL_SUBSET_OVERRIDES` entry in
   `build_set.py` and rebuild with `--force` — never hand-edit the JSON. Repeat until every group
   is confirmed. Skip entirely for a set that was already cached (and thus already verified in an
   earlier run) — this is a one-time cost per set, not a per-use one.

4. **Offer to commit a set you just built or corrected.** If step 2 or 3 changed anything under
   `../../sets/`, ask whether the user wants it committed. If yes: create a branch (e.g.
   `add-set-<CODE>` or `fix-set-<CODE>`), commit the changed `sets/` files there. If the repo has
   a configured remote, offer to push and open a PR (`gh pr create`); if it doesn't, say so
   plainly — the commit sits on that local branch until the user adds a remote and pushes it
   themselves. Never push or open a PR without being asked, and never commit at all if the user
   said no. Skip this step entirely if nothing changed.

5. **Present the set's subSet groups for selection.** Once the cache exists and is verified, list
   every `subSet` name from `../../sets/<CODE>.json` (including "no subSet / ungrouped" for a null
   group, with its card count) via AskUserQuestion with `multiSelect: true` — the user picks which
   groups belong in this checklist. Skip this step only if the user already told you exactly which
   subsets they want (e.g. "just the main set, skip the promos").

6. **Recap and confirm before handing off.** State back: the set code, the selected subSet
   names and their combined card count, and which checklist skill is about to run
   (`mtg-checklist` or `mtg-checklist-needs`). Get an explicit go-ahead before that skill starts
   building `SECTIONS` from `../../sets/<CODE>.json`, filtered to only the confirmed subsets.
