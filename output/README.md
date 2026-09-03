# output/ — rendered checklist HTML

Sister folder to `../sets/` and `../owned/`, holding the one artifact `mtg-checklist-needs`
actually delivers to the user: the rendered Needs/Available checklist HTML. Created on demand the
first time the skill runs (no need to ask before creating the empty folder).

## Naming

`<CODE>_needs_avail.html` — e.g. `HOB_needs_avail.html`. If that file already exists from an
earlier run, the skill **always asks the user** (never decides on its own) whether to overwrite it
or create a new one; a "new" choice gets the first unused `<CODE>_needs_avail_<N>.html` (`_1`,
`_2`, ...). See `../skills/mtg-checklist-needs/REFERENCE.md` "The output/ folder" for the exact
resolution recipe and `../skills/mtg-checklist-needs/SKILL.md` step 5.

This folder (and everything under it except this file) is git-ignored — see the repo root
`.gitignore`. Rendered output is fully regenerable from `sets/` + `owned/` + a rules selection, so
there's nothing here worth version-controlling.
