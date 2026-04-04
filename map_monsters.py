#!/usr/bin/env python3
"""
map_monsters.py — Mappeur Monstres Dofus 3 avec noms FR
=======================================================
Croise les bundles extraits (monsters, monsterraces, monstersuperraces)
avec fr_texts.json pour produire des JSONs et CSVs lisibles.

Prérequis :
    python parse_fr.py --output fr_texts.json

Usage :
    python map_monsters.py
    python map_monsters.py --texts fr_texts.json --assets output/assets_final.json
    python map_monsters.py --texts fr_texts.json --assets output/assets_final.json --csv
    python map_monsters.py --texts fr_texts.json --assets output/assets_final.json --search "Bouftou"
    python map_monsters.py --texts fr_texts.json --assets output/assets_final.json --monster-id 25
    python map_monsters.py --texts fr_texts.json --assets output/assets_final.json --debug-raw 31
    python map_monsters.py --texts fr_texts.json --assets output/assets_final.json --race-id 5

Sorties :
    output/monsters_named.json      — 5 076 monstres avec nom/race/niveaux/drops
    output/monsterraces_named.json  — 253 races avec nom et super-race
    output/monsters_named.csv       — (avec --csv) CSV plat
"""

import json
import argparse
import os
import sys
import csv

DEFAULT_TEXTS  = "fr_texts.json"
DEFAULT_OUTPUT = "output"
ASSETS_FINAL   = "output/assets_final.json"

BUNDLE_CLASSES = {
    "monstersdataroot":          {"MonsterData"},
    "monsterracesdataroot":      {"MonsterRaceData"},
    "monstersuperracesdataroot": {"MonsterSuperRaceData"},
    "monsterminibossesdataroot": {"MonsterMiniBossData"},
}


def load_texts(path: str) -> dict:
    if not os.path.exists(path):
        print(f"❌ fr_texts.json introuvable : {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {int(k): v for k, v in raw.items()}


def t(texts: dict, nid, fallback="") -> str:
    if not nid or nid <= 0:
        return fallback
    return texts.get(int(nid), fallback or f"[nameId:{nid}]")


def refs_to_dict(refs: list, accepted_classes: set = None) -> dict:
    result = {}
    for ref in refs:
        if accepted_classes:
            ref_class = ref.get("type", {}).get("class", "")
            if ref_class and ref_class not in accepted_classes:
                continue
        d = ref.get("data", {})
        if isinstance(d, dict) and "id" in d:
            result[d["id"]] = d
    return result


def load_assets_final(path: str) -> list:
    if not hasattr(load_assets_final, "_cache"):
        if not os.path.exists(path):
            load_assets_final._cache = []
            return []
        print(f"   📂 Lecture {path}…")
        with open(path, encoding="utf-8") as f:
            load_assets_final._cache = json.load(f)
        print(f"   → {len(load_assets_final._cache):,} objets")
    return load_assets_final._cache


def load_data(keyword: str, assets_path: str) -> dict:
    accepted = BUNDLE_CLASSES.get(keyword)
    all_objs = load_assets_final(assets_path)
    merged = {}
    for obj in all_objs:
        if keyword not in obj.get("bundle", ""):
            continue
        if obj.get("type") != "MonoBehaviour":
            continue
        d = obj.get("data", {})
        if not isinstance(d, dict):
            continue
        refs = d.get("references", {}).get("RefIds", [])
        if refs:
            merged.update(refs_to_dict(refs, accepted))
    return merged


def debug_raw(monster_id: int, assets_path: str):
    """Affiche le dict brut Unity d'un monstre pour inspecter les vrais noms de champs."""
    all_objs = load_assets_final(assets_path)
    for obj in all_objs:
        if "monstersdataroot" not in obj.get("bundle", ""):
            continue
        refs = obj.get("data", {}).get("references", {}).get("RefIds", [])
        for r in refs:
            d = r.get("data", {})
            if isinstance(d, dict) and d.get("id") == monster_id:
                print(f"\n🔍 Données brutes Unity — Monstre #{monster_id}")
                print(f"   Classe Unity : {r.get('type', {}).get('class', '?')}")
                print(json.dumps(d, indent=2, ensure_ascii=False))
                return
    print(f"❌ Monstre {monster_id} introuvable dans monstersdataroot")


def main():
    parser = argparse.ArgumentParser(description="Mappe les monstres Dofus 3 avec leurs noms FR")
    parser.add_argument("--texts",      default=DEFAULT_TEXTS)
    parser.add_argument("--output",     default=DEFAULT_OUTPUT)
    parser.add_argument("--assets",     default=ASSETS_FINAL)
    parser.add_argument("--csv",        action="store_true")
    parser.add_argument("--search",     default=None,  help="Recherche par nom")
    parser.add_argument("--monster-id", default=None,  type=int)
    parser.add_argument("--debug-raw",  default=None,  type=int, help="Dump brut Unity d'un monstre (débogage)")
    parser.add_argument("--race-id",    default=None,  type=int, help="Lister les monstres d'une race")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Mode debug-raw : pas besoin de charger les textes ni de builder tout
    if args.debug_raw:
        print(f"📖 Textes FR : {args.texts}")
        load_texts(args.texts)  # juste pour valider le fichier
        print("📦 Chargement assets…")
        load_assets_final(args.assets)
        debug_raw(args.debug_raw, args.assets)
        return

    print(f"📖 Textes FR : {args.texts}")
    texts = load_texts(args.texts)
    print(f"   → {len(texts):,} textes (IDs {min(texts)} → {max(texts)})")

    print("📦 Chargement bundles…")
    monsters_raw    = load_data("monstersdataroot",          args.assets)
    races_raw       = load_data("monsterracesdataroot",      args.assets)
    superraces_raw  = load_data("monstersuperracesdataroot", args.assets)
    minibosses_raw  = load_data("monsterminibossesdataroot", args.assets)

    print(f"   Monstres    : {len(monsters_raw):,}")
    print(f"   Races       : {len(races_raw):,}")
    print(f"   Super-races : {len(superraces_raw):,}")
    print(f"   Mini-boss   : {len(minibosses_raw):,}")

    if not monsters_raw:
        print("\n⚠️  Aucun monstre trouvé.")
        sys.exit(1)

    # ─── Super-races
    superraces_named = {}
    for sid, d in superraces_raw.items():
        superraces_named[sid] = {
            "id": sid,
            "name": t(texts, d.get("nameId")),
        }

    # ─── Races
    races_named = {}
    for rid, d in races_raw.items():
        sr = superraces_named.get(d.get("superRaceId", 0), {})
        races_named[rid] = {
            "id": rid,
            "name": t(texts, d.get("nameId")),
            "superRaceId": d.get("superRaceId", 0),
            "superRaceName": sr.get("name", ""),
        }

    # ─── Mini-boss index
    miniboss_ids = set()
    for mb in minibosses_raw.values():
        mid = mb.get("monsterId") or mb.get("id")
        if mid:
            miniboss_ids.add(mid)

    # ─── Monstres
    monsters_named = {}
    for mid, d in monsters_raw.items():
        race = races_named.get(d.get("raceId", 0), {})

        grades = []
        for g in d.get("grades", []):
            grades.append({
                "level": g.get("level", 0),
                "lifePoints": g.get("lifePoints", 0),
                "actionPoints": g.get("actionPoints", 0),
                "movementPoints": g.get("movementPoints", 0),
                "xpRatio": g.get("xpRatio", 0),
                "minDroppedKamas": g.get("minDroppedKamas", 0),
                "maxDroppedKamas": g.get("maxDroppedKamas", 0),
            })

        levels = [g["level"] for g in grades if g["level"] > 0]
        level_min = min(levels) if levels else 0
        level_max = max(levels) if levels else 0

        monsters_named[mid] = {
            "id": mid,
            "name": t(texts, d.get("nameId")),
            "raceId": d.get("raceId", 0),
            "raceName": race.get("name", ""),
            "superRaceId": race.get("superRaceId", 0),
            "superRaceName": race.get("superRaceName", ""),
            "isBoss": bool(d.get("isBoss", 0)),
            "isMiniBoss": mid in miniboss_ids,
            "isQuestMonster": bool(d.get("isQuestMonster", 0)),
            "canTackle": bool(d.get("canTackle", 0)),
            "levelMin": level_min,
            "levelMax": level_max,
            "grades": grades,
            "dropMonsterIds": d.get("dropMonsterIds", []),
            "favoriteSubareaId": d.get("favoriteSubareaId", 0),
            "favoriteSubAreaBonus": d.get("favoriteSubAreaBonus", 0),
        }

    # ─── Export JSON
    monsters_list = sorted(monsters_named.values(), key=lambda x: x["id"])
    races_list    = sorted(races_named.values(),    key=lambda x: x["id"])

    def write_json(data, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    out_monsters = os.path.join(args.output, "monsters_named.json")
    out_races    = os.path.join(args.output, "monsterraces_named.json")

    write_json(monsters_list, out_monsters)
    write_json(races_list,    out_races)

    print(f"\n✅ {len(monsters_list):,} monstres  → {out_monsters}")
    print(f"✅ {len(races_list):,} races      → {out_races}")

    # ─── Export CSV
    if args.csv:
        out_csv = os.path.join(args.output, "monsters_named.csv")
        fields = ["id", "name", "raceName", "superRaceName", "levelMin", "levelMax",
                  "isBoss", "isMiniBoss", "isQuestMonster", "canTackle",
                  "favoriteSubareaId", "favoriteSubAreaBonus"]
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(monsters_list)
        print(f"✅ CSV             → {out_csv}")

    # ─── Mode recherche
    if args.search:
        query = args.search.lower()
        results = [m for m in monsters_list if query in m["name"].lower()]
        print(f"\n🔍 '{args.search}' → {len(results)} résultats")
        for m in results[:30]:
            flags = []
            if m["isBoss"]:           flags.append("BOSS")
            if m["isMiniBoss"]:       flags.append("mini-boss")
            if m["isQuestMonster"]:   flags.append("quête")
            lvl = f"Nv{m['levelMin']}-{m['levelMax']}" if m['levelMin'] != m['levelMax'] else f"Nv{m['levelMin']}"
            tag = f" [{', '.join(flags)}]" if flags else ""
            print(f"  [{m['id']:>5}] {lvl:<12} {m['name']:<35} {m['raceName']}{tag}")
        if len(results) > 30:
            print(f"  … et {len(results)-30} autres")

    # ─── Mode détail monstre
    if args.monster_id:
        m = monsters_named.get(args.monster_id)
        if not m:
            print(f"\n❌ Monstre {args.monster_id} introuvable")
        else:
            print(f"\n👾 Monstre #{m['id']} — {m['name']}")
            print(f"   Race       : {m['raceName']} (super-race: {m['superRaceName']})")
            flags = []
            if m["isBoss"]:          flags.append("Boss")
            if m["isMiniBoss"]:      flags.append("Mini-boss")
            if m["isQuestMonster"]:  flags.append("Quête")
            if flags:
                print(f"   Tags       : {', '.join(flags)}")
            print(f"   Grades     : {len(m['grades'])}")
            for i, g in enumerate(m["grades"], 1):
                kamas = f"{g['minDroppedKamas']}-{g['maxDroppedKamas']} kamas" if g['maxDroppedKamas'] else ""
                print(f"     Grade {i}: Nv{g['level']:>3}  PV:{g['lifePoints']:>5}  "
                      f"PA:{g['actionPoints']}  PM:{g['movementPoints']}  "
                      f"xp:{g['xpRatio']}%  {kamas}")

    # ─── Filtre par race
    if args.race_id:
        race = races_named.get(args.race_id)
        filtered = [m for m in monsters_list if m["raceId"] == args.race_id]
        rname = race["name"] if race else f"race:{args.race_id}"
        print(f"\n🏷️  Race '{rname}' → {len(filtered)} monstres")
        for m in filtered:
            lvl = f"Nv{m['levelMin']}-{m['levelMax']}" if m['levelMin'] != m['levelMax'] else f"Nv{m['levelMin']}"
            boss = " [BOSS]" if m["isBoss"] else ""
            print(f"  [{m['id']:>5}] {lvl:<12} {m['name']}{boss}")

    # ─── Aperçu
    print("\n--- Aperçu monstres (10 premiers) ---")
    for m in monsters_list[:10]:
        lvl = f"Nv{m['levelMin']}-{m['levelMax']}" if m['levelMin'] != m['levelMax'] else f"Nv{m['levelMin']}"
        boss = " [BOSS]" if m["isBoss"] else ""
        print(f"  [{m['id']:>5}] {lvl:<12} {m['name']:<35} {m['raceName']}{boss}")


if __name__ == "__main__":
    main()
