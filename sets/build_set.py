# -*- coding: utf-8 -*-
"""Fetches every Scryfall print for one or more set codes and writes <CODE>.json in this
folder — a permanent, offline cache (a set's cards never change after release, so this only
ever needs to run once per set code). See README.md for the schema and how mtg-checklist /
mtg-checklist-needs should consume it instead of re-fetching Scryfall each time.

Usage:
    python build_set.py HOB HOC THOB      # any number of set codes in one run
    python build_set.py LTR --force       # re-fetch and overwrite even if already cached
"""
import json
import os
import re
import sys
import time
import urllib.request

RARITY_MAP = {"common": "C", "uncommon": "UC", "rare": "R", "mythic": "MR",
              "special": "S", "bonus": "B"}

# Known non-surge foil-treatment promo_types (heuristic, not authoritative — see README.md;
# Scryfall adds new foil-treatment promo_types almost every set).
OTHER_FOIL_PROMO_TYPES = {
    "galaxyfoil", "ripplefoil", "texturedfoil", "neonink", "oilslick", "halofoil",
    "gilded", "raisedfoil", "doublerainbow", "confettifoil", "fracturefoil",
    "rainbowfoil", "silverfoil", "goldfoil", "stepandcompleatfoil", "embossedfoil",
    "colorshiftedfoil", "invisibleink", "gleaminggold",
}


def numparts(cn):
    m = re.match(r"(\d+)(\D*)", cn)
    if not m:
        return (10**9, cn)
    return (int(m.group(1)), m.group(2))


def color_of(card):
    if "Land" in card["type_line"]:
        return "Land"
    colors = card.get("colors") or []
    if not colors:
        return "Colorless"
    if len(colors) == 1:
        return {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}[colors[0]]
    return "Multicolor"


def treatment_of(card):
    """Generic frame/border treatment bucket, derived only from real structured Scryfall
    fields (frame_effects, border_color, full_art, promo_types) — see README.md "The
    treatment field" for the priority order and, importantly, what this does NOT capture
    (a set's own editorial name for a specific alternate frame or narrative scene grouping,
    e.g. "Dragon Hoard Frame" or "Fight with the Great Goblin Scene" — those need the
    `artist` field plus per-set curation, not a generic classifier)."""
    fe = set(card.get("frame_effects") or [])
    pt = set(card.get("promo_types") or [])
    border = card.get("border_color")
    full_art = bool(card.get("full_art"))
    if "poster" in pt:
        return "Poster"
    if "showcase" in fe:
        return "Showcase"
    if "extendedart" in fe:
        return "Extended Art"
    if border == "borderless" and full_art:
        return "Full Art Borderless"
    if border == "borderless":
        return "Borderless"
    if full_art:
        return "Full Art"
    return "Base Set"


def fetch_all_prints(set_code):
    url = (f"https://api.scryfall.com/cards/search?q=set%3A{set_code.lower()}"
           f"&order=set&unique=prints&include_extras=true&include_variations=true")
    cards = []
    while url:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"})
        with urllib.request.urlopen(req) as r:
            data = json.load(r)
        cards.extend(data["data"])
        url = data.get("next_page") if data.get("has_more") else None
        if url:
            time.sleep(0.1)  # be polite to Scryfall's rate limit
    return cards


_HEADER_RE = re.compile(
    r'<h2 class="card-grid-header" id="([^"]+)">.*?card-grid-header-content">\s*([^<\n]+)', re.S)
_CARD_ID_RE = re.compile(r'data-card-id="([0-9a-f-]{36})"')


def fetch_section_map(set_code):
    """Scrapes https://scryfall.com/sets/<code> (the human-facing set page, NOT the JSON API
    — the API has no equivalent field) for its booster-configuration breakdown: each
    `<h2 class="card-grid-header">` is one of Scryfall's own named groups for this set (e.g.
    "Dragon Hoard Frame Cards", "Borderless Scene Cards", "Ring Showcases"), and every card
    shown under it carries a `data-card-id` matching the API's `id` field. Returns
    {scryfall_card_id: section_title}. See README.md "The `section` field" for what this can
    and can't tell you.

    Returns an empty dict (rather than raising) if the page has no such breakdown at all —
    true for older/simpler sets with no special treatments; every row's `section` just stays
    None in that case."""
    url = f"https://scryfall.com/sets/{set_code.lower()}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        html = r.read().decode("utf-8")

    headers = [(m.start(), m.group(1), m.group(2).strip()) for m in _HEADER_RE.finditer(html)]
    boundaries = [h[0] for h in headers] + [len(html)]
    section_map = {}
    for i, (pos, _slug, title) in enumerate(headers):
        chunk = html[pos:boundaries[i + 1]]
        for card_id in _CARD_ID_RE.findall(chunk):
            section_map.setdefault(card_id, title)  # first section a card-id appears in wins
    return section_map


def build_row(card, section_map):
    """One card's row — no setCode (redundant with the enclosing <CODE>.json filename) and
    no subSet key (that's the enclosing group's key, not a per-card field)."""
    finishes = card.get("finishes") or []
    promo_types = set(card.get("promo_types") or [])
    rarity = RARITY_MAP.get(card["rarity"], card["rarity"][:1].upper())
    # flavor_name (when set) is what's actually printed on THIS card — Universes Beyond sets
    # commonly reskin an existing card's rules text under new art/flavor (e.g. LTR #398 prints
    # as "Lórien Brooch" but Scryfall's `name` is the Oracle/functional identity, "Trailblazer's
    # Boots"). Prefer the printed name; see README.md "The `name` field" for what this means for
    # mtg-checklist-needs' name-based ownership matching.
    name = card.get("flavor_name") or card["name"]
    return {
        "number": card["collector_number"],
        "name": name,
        "color": color_of(card),
        "type": card["type_line"],
        "rarity": rarity,
        "treatment": treatment_of(card),
        "artist": card.get("artist"),
        "nonFoilAvailable": "nonfoil" in finishes,
        "foilAvailable": "foil" in finishes or "etched" in finishes,
        "surgeFoilAvailable": "surgefoil" in promo_types,
        "otherFoilAvailable": bool(promo_types & OTHER_FOIL_PROMO_TYPES),
    }


# Manual escape hatch for a scraped subSet that's confirmed (per README.md "Verifying a build")
# to actually cover more than one distinct theme Scryfall's own page left combined — e.g. HOB's
# "Borderless Scene Cards" spans two different movie battles with no subSet-level split of their
# own. {SET_CODE: [(lo, hi, override_name), ...]} — a card whose collector number (integer part
# only) falls in [lo, hi] gets override_name instead of whatever fetch_section_map found for it.
# Confirmed against the set page + the two artists' number ranges (see README.md "The `artist`
# field"); add a new entry here only after the same kind of confirmation, never as a guess.
MANUAL_SUBSET_OVERRIDES = {
    "HOB": [
        (199, 204, "Fight with the Great Goblin Scene"),
        (205, 213, "The Five Armies Clash! Scene"),
    ],
    "LTR": [
        (399, 404, "Bilbo's Birthday Party Scene"),
        (405, 410, "Bridge of Khazad-dûm Scene"),
        (411, 419, "Isengard Destroyed Scene"),
        (420, 437, "The Battle of the Pelennor Fields Scene"),
        (438, 441, "The Scouring of the Shire Scene"),
        (442, 447, "Departure to the Grey Havens Scene"),
        (448, 451, "Mount Doom Scene"),
    ],
}


def override_subset(set_code, number, scraped_name):
    for lo, hi, name in MANUAL_SUBSET_OVERRIDES.get(set_code.upper(), []):
        n, _suffix = numparts(number)
        if lo <= n <= hi:
            return name
    return scraped_name


def group_by_subset(set_code, cards, section_map):
    """Sorts by collector number, then groups into [{"subSet": name, "cards": [...]}, ...] —
    one group per distinct subSet name (Scryfall's own scraped name, overridden per
    MANUAL_SUBSET_OVERRIDES where applicable, or None if the set page had no breakdown for that
    card), in the order each subSet is first encountered in collector-number order."""
    keyed = [(override_subset(set_code, c["collector_number"], section_map.get(c["id"])), c)
             for c in cards]
    keyed.sort(key=lambda kc: numparts(kc[1]["collector_number"]))

    order = []
    groups = {}
    for sub_set, card in keyed:
        if sub_set not in groups:
            groups[sub_set] = []
            order.append(sub_set)
        groups[sub_set].append(build_row(card, section_map))
    return [{"subSet": sub_set, "cards": groups[sub_set]} for sub_set in order]


def build_set(set_code, force=False):
    out_path = f"{set_code.upper()}.json"
    if os.path.exists(out_path) and not force:
        print(f"{out_path} already exists, skipping (sets never change — pass --force to re-fetch)")
        return
    cards = fetch_all_prints(set_code)
    try:
        section_map = fetch_section_map(set_code)
    except Exception as e:
        print(f"  warning: could not fetch section breakdown for {set_code} ({e}); "
              f"'subSet' will be null for every card")
        section_map = {}
    if section_map and len(section_map) != len(cards):
        print(f"  warning: {set_code} section page covered {len(section_map)} cards but the API "
              f"returned {len(cards)} — some cards' 'subSet' may be null (mismatch: possibly a "
              f"paginated set page, or a print the set page doesn't list separately)")
    groups = group_by_subset(set_code, cards, section_map)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)
    total = sum(len(g["cards"]) for g in groups)
    print(f"wrote {out_path}: {len(groups)} subSets, {total} cards")
    for g in groups:
        cards_g = g["cards"]
        first, last = cards_g[0], cards_g[-1]
        print(f"  - {g['subSet']!r}: {len(cards_g)} cards, "
              f"first #{first['number']} {first['name']!r}, "
              f"last #{last['number']} {last['name']!r}")


if __name__ == "__main__":
    args = sys.argv[1:]
    force = "--force" in args
    codes = [a for a in args if not a.startswith("--")]
    if not codes:
        print("usage: python build_set.py CODE [CODE...] [--force]")
        sys.exit(1)
    for code in codes:
        build_set(code, force=force)
