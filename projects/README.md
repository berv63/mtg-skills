# projects/ — mtg-checklist-needs' working copies

Sister folder to `../sets/`, `../owned/`, and `../output/`. Each `mtg-checklist-needs` run creates
one subfolder here (e.g. `projects/hob-needs/`) holding that run's copies of `compute_needs.py` and
`template_needs.py`, plus their intermediate artifacts (`color_lookup.json`, `needs_result.json`).

**This location is required, not just a convention.** Those two scripts use relative paths at
runtime (`../../owned/<CODE>`, `../../output/...`) instead of any absolute path, so they run
correctly on whatever machine the user is on — that only resolves correctly if the project folder
sits directly under the repo root, exactly two levels above where `../../` needs to land. See
`../skills/mtg-checklist-needs/SKILL.md`'s project-folder note and REFERENCE.md "The output/
folder".

`mtg-checklist` (the print-oriented sibling skill) doesn't use this folder — its own docs still
call the destination "the user's project folder" and place it wherever the user wants, since its
`template.py` has no runtime dependency on any shared cache location.

This folder (and everything under it except this file) is git-ignored — see the repo root
`.gitignore`. These are working copies and intermediate JSON, not something to version-control.
