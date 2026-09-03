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

3. **Otherwise, ask the user what to do with the missing codes.** Present the missing list, then
   ask via AskUserQuestion with a small, fixed set of choices — the missing list itself can be
   longer than AskUserQuestion supports as options, so don't try to turn each set code into its
   own option:
   - Download all of them
   - Let the user name specific codes (a follow-up in plain conversation, not another
     AskUserQuestion — free-form since the count is arbitrary)
   - Skip for now

4. **Download what was chosen.** `python sync_sets.py --all` for "all of them", or
   `python sync_sets.py CODE [CODE...]` for specific codes the user named. Report each line
   `sync_sets.py` prints (set + subSet count + card count written, or "not found on GitHub" for
   a code that doesn't actually exist there — a typo, or a set genuinely not built by anyone
   yet). A `404` result is not an error to fix here; point the user at `mtg-set-builder` for that
   code instead if they want it built.

5. **Don't offer to commit anything.** This skill only ever reads from GitHub and writes to the
   local cache — nothing it does changes what's committed, so there's nothing to offer to commit
   (unlike `mtg-set-builder`'s step 4, which is about a *new* build).
