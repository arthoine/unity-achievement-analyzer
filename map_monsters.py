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
    python map_monsters.py --texts fr_texts.json --assets output/assets_final.json --monster-id 31
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


def parse_grades(raw_grades: list) -> list:
    """Extrait les stats de chaque grade depuis les données brutes Unity."""
    grades = []
    for g in raw_grades:
        grades.append({
            "grade":            g.get("grade", 0),
            "level":            g.get("level", 0),
            "lifePoints":       g.get("lifePoints", 0),
            "actionPoints":     g.get("actionPoints", 0),
            "movementPoints":   g.get("movementPoints", 0),
            "gradeXp":          g.get("gradeXp", 0),          # XP absolu donné au joueur
            "strength":         g.get("strength", 0),
            "intelligence":     g.get("intelligence", 0),
            "chance":           g.get("chance", 0),
            "agility":          g.get("agility", 0),
            "wisdom":           g.get("wisdom", 0),
            "earthResistance":  g.get("earthResistance", 0),
            "fireResistance":   g.get("fireResistance", 0),
            "waterResistance":  g.get("waterResistance", 0),
            "airResistance":    g.get("airResistance", 0),
            "neutralResistance":g.get("neutralResistance", 0),
            "paDodge":          g.get("paDodge", 0),
            "pmDodge":          g.get("pmDodge", 0),
            "damageReflect":    g.get("damageReflect", 0),
            "minDroppedKamas":  g.get("minDroppedKamas", 0),
            "maxDroppedKamas":  g.get("maxDroppedKamas", 0),
        })
    return grades


def parse_drops(raw_drops: list) -> list:
    """Extrait la table de drops depuis les données brutes Unity."""
    drops = []
    for d in raw_drops:
        drops.append({
            "objectId":   d.get("objectId", 0),
            "dropPct":    round(d.get("percentDropForGrade1", 0.0), 4),  # % grade 1 comme référence
            "count":      d.get("count", 0),
            "criterions": d.get("criterions", ""),
            "disableDropModificator": bool(d.get("disableDropModificator", 0)),
        })
    return drops


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

    if args.debug_raw:
        print("📦 Chargement assets…")
        load_assets_final(args.assets)
        debug_raw(args.debug_raw, args.assets)
        return

    print(f"📖 Textes FR : {args.texts}")
    texts = load_texts(args.texts)
    print(f"   → {len(texts):,} textes (IDs {min(texts)} → {max(texts)})")

    print("📦 Chargement bundles…")
    monsters_raw   = load_data("monstersdataroot",          args.assets)
    races_raw      = load_data("monsterracesdataroot",      args.assets)
    superraces_raw = load_data("monstersuperracesdataroot", args.assets)
    minibosses_raw = load_data("monsterminibossesdataroot", args.assets)

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
        superraces_named[sid] = {"id": sid, "name": t(texts, d.get("nameId"))}

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

    # ─── Mini-boss index (monsterId → miniBossId)
    # MonsterMiniBossData contient le champ monsterId qui pointe vers le monstre normal
    monster_to_miniboss = {}
    for mb in minibosses_raw.values():
        normal_id = mb.get("monsterId")
        if normal_id:
            monster_to_miniboss[normal_id] = mb.get("id", 0)

    # ─── Monstres
    monsters_named = {}
    for mid, d in monsters_raw.items():
        # "race" (pas "raceId") est le vrai champ Unity
        race = races_named.get(d.get("race", 0), {})

        grades = parse_grades(d.get("grades", []))
        drops  = parse_drops(d.get("drops", []))

        levels = [g["level"] for g in grades if g["level"] > 0]
        level_min = min(levels) if levels else 0
        level_max = max(levels) if levels else 0

        # correspondingMiniBossId : l'ID du mini-boss lié à ce monstre normal
        mini_boss_id = d.get("correspondingMiniBossId", 0)

        monsters_named[mid] = {
            "id": mid,
            "name": t(texts, d.get("nameId")),
            "raceId": d.get("race", 0),
            "raceName": race.get("name", ""),
            "superRaceId": race.get("superRaceId", 0),
            "superRaceName": race.get("superRaceName", ""),
            "isBoss": bool(d.get("isBoss", 0)),
            "isMiniBoss": mid in monster_to_miniboss,
            "correspondingMiniBossId": mini_boss_id,
            "isQuestMonster": bool(d.get("isQuestMonster", 0)),
            "canTackle": bool(d.get("canTackle", 0)),
            "levelMin": level_min,
            "levelMax": level_max,
            "subareas": d.get("subareas", []),          # liste des sous-zones
            "spells": d.get("spells", []),              # IDs de sorts
            "grades": grades,
            "drops": drops,
            "speedAdjust": d.get("speedAdjust", 0),
            "aggressiveZoneSize": d.get("aggressiveZoneSize", 0),
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

    # ─── Export CSV (une ligne par monstre, sans grades/drops)
    if args.csv:
        out_csv = os.path.join(args.output, "monsters_named.csv")
        fields = ["id", "name", "raceName", "superRaceName", "levelMin", "levelMax",
                  "isBoss", "isMiniBoss", "correspondingMiniBossId", "isQuestMonster",
                  "canTackle", "aggressiveZoneSize", "speedAdjust"]
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
            if m["isBoss"]:         flags.append("BOSS")
            if m["isMiniBoss"]:     flags.append("mini-boss")
            if m["isQuestMonster"]: flags.append("quête")
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
            print(f"   Race         : {m['raceName']} (super-race: {m['superRaceName']})")
            flags = []
            if m["isBoss"]:         flags.append("Boss")
            if m["isMiniBoss"]:     flags.append("Mini-boss")
            if m["isQuestMonster"]: flags.append("Quête")
            if flags:
                print(f"   Tags         : {', '.join(flags)}")
            if m["correspondingMiniBossId"]:
                print(f"   Mini-boss ID : {m['correspondingMiniBossId']}")
            print(f"   Zones        : {m['subareas']}")
            print(f"   Sorts        : {m['spells']}")
            print(f"   Grades       : {len(m['grades'])}")
            for g in m["grades"]:
                kamas = f"  kamas:{g['minDroppedKamas']}-{g['maxDroppedKamas']}" if g['maxDroppedKamas'] else ""
                print(f"     Grade {g['grade']}: Nv{g['level']:>3}  "
                      f"PV:{g['lifePoints']:>5}  PA:{g['actionPoints']}  PM:{g['movementPoints']}  "
                      f"XP:{g['gradeXp']:>6}  "
                      f"Res terre/feu/eau/air/neu: {g['earthResistance']:>4}/{g['fireResistance']:>4}/{g['waterResistance']:>4}/{g['airResistance']:>4}/{g['neutralResistance']:>4}"
                      f"{kamas}")
            print(f"\n   Drops ({len(m['drops'])}) :")
            for drop in m["drops"]:
                crit = f"  [{drop['criterions']}]" if drop["criterions"] else ""
                print(f"     item:{drop['objectId']:<7} {drop['dropPct']:>6.2f}%  x{drop['count']}{crit}")

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
