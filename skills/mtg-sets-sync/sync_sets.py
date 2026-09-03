# -*- coding: utf-8 -*-
"""Bulk-downloads already-built <CODE>.json set caches straight from this repo's own GitHub
sets/ folder (https://github.com/berv63/mtg-skills/tree/master/sets) into the local ../../sets/
folder — no Scryfall calls, no per-set verification, since a file that's already committed
upstream was already hand-verified when it was built (see sets/README.md "Verifying a build").

Exists because installing this repo's skills via `npx skills add` only pulls down skills/, not
sets/ — so a fresh install has an empty local cache even though the GitHub repo may already have
several sets built. Running this once after install (or any time to pick up newly-added sets)
seeds the local cache so later checklist runs need zero network calls. A set nobody has built yet
won't show up here at all — that still goes through mtg-set-builder's normal live Scryfall
fetch-and-verify flow (build_set.py in the sibling skills/mtg-set-builder/ folder, which also
tries this same GitHub shortcut first for any single code it's asked to build).

Lives here (skills/mtg-sets-sync/), not in sets/ itself, since sets/ is pure data. Resolves
../../sets/ from this file's own location, so it can be run from anywhere.

Usage:
    python sync_sets.py --list              # show what's on GitHub vs. already local
    python sync_sets.py HOB HOC              # download specific codes (skips ones already local)
    python sync_sets.py --all                # download every remote code not already local
    python sync_sets.py HOB --force          # re-download and overwrite even if already local
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

SETS_DIR = Path(__file__).resolve().parent.parent.parent / "sets"
GITHUB_API_CONTENTS_URL = "https://api.github.com/repos/berv63/mtg-skills/contents/sets"
GITHUB_RAW_SETS_URL = "https://raw.githubusercontent.com/berv63/mtg-skills/master/sets"


def list_remote_codes():
    req = urllib.request.Request(GITHUB_API_CONTENTS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        entries = json.load(r)
    return sorted(e["name"][:-len(".json")] for e in entries
                  if e["name"].endswith(".json") and e["type"] == "file")


def list_local_codes():
    return sorted(p.stem for p in SETS_DIR.glob("*.json"))


def download(set_code, force=False):
    out_path = SETS_DIR / f"{set_code.upper()}.json"
    if out_path.exists() and not force:
        print(f"{out_path} already exists, skipping (pass --force to re-download)")
        return
    url = f"{GITHUB_RAW_SETS_URL}/{set_code.upper()}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  {set_code}: not found on GitHub (nobody has built it yet — "
                  f"use mtg-set-builder's normal Scryfall flow instead)")
            return
        raise
    groups = json.loads(raw)  # let a malformed download raise rather than write bad data
    out_path.write_bytes(raw)
    total = sum(len(g["cards"]) for g in groups)
    print(f"downloaded {out_path}: {len(groups)} subSets, {total} cards")


def do_list():
    remote = list_remote_codes()
    local = set(list_local_codes())
    missing = [c for c in remote if c not in local]
    print(f"local sets/ cache: {sorted(local) or '(empty)'}")
    print(f"available on GitHub: {remote}")
    if missing:
        print(f"on GitHub but not local yet: {missing}")
    else:
        print("local cache already has everything GitHub has.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args == ["--list"]:
        do_list()
        sys.exit(0)

    force = "--force" in args
    if "--all" in args:
        remote = list_remote_codes()
        local = set(list_local_codes())
        codes = remote if force else [c for c in remote if c not in local]
        if not codes:
            print("nothing to download — local cache already has everything GitHub has.")
        for code in codes:
            download(code, force=force)
    else:
        codes = [a for a in args if not a.startswith("--")]
        if not codes:
            print("usage: python sync_sets.py [--list | --all | CODE [CODE...]] [--force]")
            sys.exit(1)
        for code in codes:
            download(code, force=force)
