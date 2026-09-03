---
name: mtg-sets-sync
description: "Bulk-download already-built set caches from this repo's own GitHub sets/ folder (github.com/berv63/mtg-skills/tree/master/sets) into the local sets/ cache, so later checklist runs need zero network calls. Use right after installing these skills via `npx skills add` (which pulls only skills/, not sets/, so a fresh install starts with an empty local cache), or any time to pick up sets that were built and committed since the last sync."
---

Seeds (or tops up) the local `../../sets/` cache from whatever's already built and committed in
this repo's own GitHub `sets/` folder — no Scryfall calls, no per-set verification with the user,
since a file that's already committed upstream was already hand-verified when it was built (see
`../../sets/README.md` "Verifying a build"). `sync_sets.py` in this same folder is the working
engine; `sets/` itself holds only data, no scripts.

This is a convenience on top of `mtg-set-builder`, not a replacement for it: a set nobody has
built yet won't show up here at all, and still needs `mtg-set-builder`'s normal live
Scryfall-fetch-and-verify flow. (`build_set.py` also tries this same GitHub shortcut on its own
for any single code it's asked to build, so running this skill isn't strictly required — it's
just faster to seed several sets at once up front than to hit the shortcut one code at a time as
each checklist run happens to need it.)

1. **List what's on GitHub vs. what's already local.** Run `python sync_sets.py --list` (same
   folder as this file; resolves `../../sets/` itself regardless of your working directory —
   same Docker fallback as `mtg-set-builder` if Python isn't available locally, substituting
   `skills/mtg-sets-sync/sync_sets.py` for `skills/mtg-set-builder/build_set.py` in the command).
   This prints the local cache's codes, every code available on GitHub, and (if any) which of
   those aren't local yet.

2. **If nothing's missing, say so and stop.** No download needed.

3. **Let the user pick which missing codes to download via an actual multi-select list**, not a
   yes/no/name-them-yourself question. AskUserQuestion caps each question at 4 options, so batch
   the missing codes into groups of up to 4 and ask one `multiSelect: true` question per batch —
   each set code is its own checkbox option (label the code itself; a short generic description
   like "on GitHub, not yet in the local sets/ cache" is fine since this cache has no per-set
   full-name data to draw a richer description from). This mirrors `mtg-set-builder` step 3's
   "batch a few per question round" pattern for the same reason: one question round per up-to-4
   codes, not one round per code and not one giant list. Union the checked options across every
   batch into the final download list — an empty union (nothing checked in any batch) means skip
   entirely, no download step needed.

4. **Download what was chosen.** `python sync_sets.py CODE [CODE...]` for the codes selected
   across all batches (or skip this step entirely if nothing was checked). Report each line
   `sync_sets.py` prints (set + subSet count + card count written, or "not found on GitHub" for
   a code that doesn't actually exist there — a typo, or a set genuinely not built by anyone
   yet). A `404` result is not an error to fix here; point the user at `mtg-set-builder` for that
   code instead if they want it built.

5. **Don't offer to commit anything.** This skill only ever reads from GitHub and writes to the
   local cache — nothing it does changes what's committed, so there's nothing to offer to commit
   (unlike `mtg-set-builder`'s step 4, which is about a *new* build).
