#!/usr/bin/env python3
"""
map_items.py — Mappeur Items Dofus 3 avec noms FR
==================================================
Croise les bundles extraits (items, itemsets, itemtypes, itemsupertypes)
avec fr_texts.json pour produire des JSONs et CSVs lisibles.

Prérequis :
    1. python parse_fr.py --output fr_texts.json

Usage :
    python map_items.py
    python map_items.py --texts fr_texts.json --output output/
    python map_items.py --texts fr_texts.json --output output/ --csv
    python map_items.py --texts fr_texts.json --output output/ --search "Bouftou"

Sorties :
    output/items_named.json        — items avec nom/description FR
    output/itemtypes_named.json    — types avec nom FR
    output/itemsets_named.json     — panoplies avec nom FR + items nommés
    output/items_named.csv         — (avec --csv) CSV plat exploitable

Source de données (par ordre de priorité) :
    1. Fichiers JSON individuels dans output/ (si générés par analyze_bundle.py)
    2. assets_final.json (fallback automatique — extrait via references.RefIds)
"""

import json
import argparse
import os
import sys
import csv

# ─── Chemins par défaut ───────────────────────────────────────────────────────
DEFAULT_TEXTS  = "fr_texts.json"
DEFAULT_OUTPUT = "output"
ASSETS_FINAL   = "assets_final.json"

# ─── Positions d'équipement (slot id → label) ────────────────────────────────
SLOT_NAMES = {
    0: "Chapeau", 1: "Cape", 2: "Amulette", 3: "Anneau",
    4: "Ceinture", 5: "Bottes", 6: "Bouclier", 7: "Familier",
    8: "Monture", 16: "Arme principale", 17: "Arme secondaire",
    22: "Trophée", 23: "Objet vivant", 24: "Plastron",
    26: "Épaulettes", 30: "Dragodinde", 31: "Objet de quête",
}


def load_texts(path: str) -> dict:
    if not os.path.exists(path):
        print(f"❌ fr_texts.json introuvable : {path}")
        print("   → python parse_fr.py --output fr_texts.json")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {int(k): v for k, v in raw.items()}


def t(texts: dict, nid, fallback="") -> str:
    """Résout un nameId en texte FR."""
    if not nid or nid <= 0:
        return fallback
    return texts.get(int(nid), fallback or f"[nameId:{nid}]")


def extract_refs(bundle_data: list) -> list:
    """Extrait les RefIds depuis la structure Unity (references.RefIds)."""
    for obj in bundle_data:
        if obj.get("type") == "MonoBehaviour" and obj.get("data"):
            refs = obj["data"].get("references", {}).get("RefIds", [])
            if refs:
                return refs
    return []


def refs_to_dict(refs: list) -> dict:
    """Transforme les RefIds en dict id→data."""
    result = {}
    for ref in refs:
        d = ref.get("data", {})
        if isinstance(d, dict) and "id" in d:
            result[d["id"]] = d
    return result


def load_bundle_json(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_bundle(output_dir: str, keyword: str) -> str:
    """Cherche un fichier JSON de bundle dans output/ par mot-clé."""
    if not os.path.isdir(output_dir):
        return ""
    for fname in os.listdir(output_dir):
        if keyword in fname and fname.endswith(".json"):
            return os.path.join(output_dir, fname)
    return ""


def load_assets_final(path: str) -> list:
    """Charge assets_final.json une seule fois et le met en cache."""
    if not hasattr(load_assets_final, "_cache"):
        if not os.path.exists(path):
            return []
        print(f"   📂 Lecture assets_final.json ({path})…")
        with open(path, encoding="utf-8") as f:
            load_assets_final._cache = json.load(f)
        print(f"   → {len(load_assets_final._cache):,} objets chargés")
    return load_assets_final._cache


def main():
    parser = argparse.ArgumentParser(
        description="Mappe les items Dofus 3 avec leurs noms FR"
    )
    parser.add_argument("--texts",   default=DEFAULT_TEXTS,  help="Chemin vers fr_texts.json")
    parser.add_argument("--output",  default=DEFAULT_OUTPUT, help="Dossier de sortie")
    parser.add_argument("--assets",  default=ASSETS_FINAL,   help="assets_final.json (fallback si pas de bundles individuels)")
    parser.add_argument("--csv",     action="store_true",    help="Exporter aussi en CSV")
    parser.add_argument("--search",  default=None,           help="Rechercher des items par nom FR (ex: --search Bouftou)")
    parser.add_argument("--item-id", default=None, type=int, help="Afficher les détails d'un item par son ID")
    parser.add_argument("--min-level", default=None, type=int, help="Filtrer items par niveau minimum")
    parser.add_argument("--max-level", default=None, type=int, help="Filtrer items par niveau maximum")
    parser.add_argument("--type-id",   default=None, type=int, help="Filtrer items par typeId")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # ─── Chargement textes FR ────────────────────────────────────────────────
    print(f"📖 Textes FR       : {args.texts}")
    texts = load_texts(args.texts)
    print(f"   → {len(texts):,} textes (IDs {min(texts)} → {max(texts)})")

    # ─── Chargement des bundles ──────────────────────────────────────────────
    # Priorité 1 : fichiers individuels dans output/
    # Priorité 2 : assets_final.json (extrait via references.RefIds du MonoBehaviour)
    def load_data(keyword):
        # Priorité 1 — bundle individuel
        path = find_bundle(args.output, keyword)
        if path:
            data = refs_to_dict(extract_refs(load_bundle_json(path)))
            if data:
                return data

        # Priorité 2 — assets_final.json
        all_objs = load_assets_final(args.assets)
        if not all_objs:
            return {}

        # Trouver le MonoBehaviour du DataRoot correspondant au keyword
        for obj in all_objs:
            if keyword not in obj.get("bundle", ""):
                continue
            if obj.get("type") != "MonoBehaviour":
                continue
            d = obj.get("data", {})
            if not isinstance(d, dict):
                continue
            # Résolution via references.RefIds (structure Unity sérialisée)
            refs = d.get("references", {}).get("RefIds", [])
            if refs:
                result = refs_to_dict(refs)
                if result:
                    return result
            # Résolution via objectsById (certains bundles utilisent cette clé)
            obj_by_id = d.get("objectsById", {})
            keys   = obj_by_id.get("m_keys", [])
            values = obj_by_id.get("m_values", [])
            if keys and values:
                # m_values contient des {rid: X} → on résout les rids dans les RefIds globaux
                rid_map = {}
                global_refs = d.get("references", {}).get("RefIds", [])
                for ref in global_refs:
                    rid_map[ref.get("rid")] = ref.get("data", {})
                result = {}
                for kid, val in zip(keys, values):
                    rid = val.get("rid")
                    if rid and rid in rid_map:
                        item_data = rid_map[rid]
                        if isinstance(item_data, dict):
                            result[kid] = item_data
                if result:
                    return result
        return {}

    print("📦 Chargement bundles…")
    items_raw      = load_data("itemsdataroot")
    itemtypes_raw  = load_data("itemtypesdataroot")
    supertype_raw  = load_data("itemsupertypesdataroot")
    itemsets_raw   = load_data("itemsetsdataroot")

    print(f"   Items       : {len(items_raw):,}")
    print(f"   ItemTypes   : {len(itemtypes_raw):,}")
    print(f"   SuperTypes  : {len(supertype_raw):,}")
    print(f"   ItemSets    : {len(itemsets_raw):,}")

    if not items_raw:
        print("\n⚠️  Aucun item trouvé. Vérifie :")
        print("   • Que assets_final.json est dans le dossier courant (ou --assets chemin)")
        print("   • Ou que les bundles individuels sont dans output/")
        sys.exit(1)

    # ─── Résolution ItemTypes ────────────────────────────────────────────────
    itemtypes_named = {}
    for tid, d in itemtypes_raw.items():
        slots = supertype_raw.get(d.get("superTypeId", 0), {}).get("possiblePositions", [])
        itemtypes_named[tid] = {
            "id": tid,
            "name": t(texts, d.get("nameId")),
            "nameId": d.get("nameId"),
            "superTypeId": d.get("superTypeId"),
            "categoryId": d.get("categoryId"),
            "isInEncyclopedia": d.get("isInEncyclopedia", 0),
            "slots": [SLOT_NAMES.get(s, str(s)) for s in slots],
        }

    # ─── Résolution Items ────────────────────────────────────────────────────
    items_named = {}
    for iid, d in items_raw.items():
        itype = itemtypes_named.get(d.get("typeId", 0), {})
        items_named[iid] = {
            "id": iid,
            "name": t(texts, d.get("nameId")),
            "description": t(texts, d.get("descriptionId"), ""),
            "nameId": d.get("nameId"),
            "typeId": d.get("typeId"),
            "typeName": itype.get("name", ""),
            "superTypeId": itype.get("superTypeId"),
            "slots": itype.get("slots", []),
            "level": d.get("level", 0),
            "price": d.get("price", 0),
            "realWeight": d.get("realWeight", 0),
            "itemSetId": d.get("itemSetId", -1),
            "iconId": d.get("iconId", 0),
            "apCost": d.get("apCost", 0),
            "range": d.get("range", 0),
            "criticalHitProbability": d.get("criticalHitProbability", 0),
            "criticalHitBonus": d.get("criticalHitBonus", 0),
            "isColorable": bool(d.get("isColorable", 0)),
            "recyclingNuggets": d.get("recyclingNuggets", 0),
            "criterions": d.get("criterions", ""),
            "dropMonsterIds": d.get("dropMonsterIds", []),
        }

    # ─── Résolution ItemSets ─────────────────────────────────────────────────
    itemsets_named = {}
    for sid, d in itemsets_raw.items():
        item_ids = d.get("items", [])
        itemsets_named[sid] = {
            "id": sid,
            "name": t(texts, d.get("nameId")),
            "nameId": d.get("nameId"),
            "isCosmetic": bool(d.get("isCosmetic", 0)),
            "bonusIsSecret": bool(d.get("bonusIsSecret", 0)),
            "items": [
                {"id": iid, "name": items_named.get(iid, {}).get("name", f"item:{iid}"),
                 "level": items_named.get(iid, {}).get("level", 0)}
                for iid in item_ids
            ],
        }

    # ─── Rattacher le nom du set aux items ───────────────────────────────────
    for sid, s in itemsets_named.items():
        for item_stub in s["items"]:
            iid = item_stub["id"]
            if iid in items_named:
                items_named[iid]["itemSetName"] = s["name"]

    # ─── Export JSON ─────────────────────────────────────────────────────────
    items_list     = sorted(items_named.values(),     key=lambda x: x["id"])
    itemtypes_list = sorted(itemtypes_named.values(), key=lambda x: x["id"])
    itemsets_list  = sorted(itemsets_named.values(),  key=lambda x: x["id"])

    out_items     = os.path.join(args.output, "items_named.json")
    out_types     = os.path.join(args.output, "itemtypes_named.json")
    out_sets      = os.path.join(args.output, "itemsets_named.json")

    with open(out_items, "w", encoding="utf-8") as f:
        json.dump(items_list, f, ensure_ascii=False, indent=2)
    with open(out_types, "w", encoding="utf-8") as f:
        json.dump(itemtypes_list, f, ensure_ascii=False, indent=2)
    with open(out_sets, "w", encoding="utf-8") as f:
        json.dump(itemsets_list, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(items_list):,} items       → {out_items}")
    print(f"✅ {len(itemtypes_list):,} item types  → {out_types}")
    print(f"✅ {len(itemsets_list):,} item sets   → {out_sets}")

    # ─── Export CSV (optionnel) ───────────────────────────────────────────────
    if args.csv:
        out_csv = os.path.join(args.output, "items_named.csv")
        fields = ["id", "name", "typeName", "slots", "level", "price",
                  "realWeight", "itemSetId", "itemSetName", "iconId",
                  "apCost", "range", "criticalHitProbability", "criticalHitBonus",
                  "isColorable", "recyclingNuggets", "criterions", "description"]
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for item in items_list:
                row = dict(item)
                row["slots"] = ", ".join(item.get("slots", []))
                row["itemSetName"] = item.get("itemSetName", "")
                w.writerow(row)
        print(f"✅ CSV              → {out_csv}")

    # ─── Mode recherche ──────────────────────────────────────────────────────
    if args.search:
        query = args.search.lower()
        results = [i for i in items_list if query in i["name"].lower()]
        print(f"\n🔍 Recherche '{args.search}' → {len(results)} résultats")
        for item in results[:30]:
            set_name = f" (set: {item.get('itemSetName', '')})"
            slots = ", ".join(item["slots"]) or item["typeName"]
            print(f"  [{item['id']:>6}] Nv{item['level']:>3}  {item['name']:<35} {slots}{set_name if item.get('itemSetName') else ''}")
        if len(results) > 30:
            print(f"  ... et {len(results)-30} autres résultats")

    # ─── Mode détail item ────────────────────────────────────────────────────
    if args.item_id:
        item = items_named.get(args.item_id)
        if not item:
            print(f"\n❌ Item {args.item_id} introuvable")
        else:
            print(f"\n📋 Item #{item['id']}")
            for k, v in item.items():
                if v not in (None, "", [], 0, False):
                    print(f"  {k:<28} {v}")
            if item.get("itemSetId", -1) > 0:
                s = itemsets_named.get(item["itemSetId"])
                if s:
                    print(f"\n  🎽 Set '{s['name']}' ({len(s['items'])} pièces):")
                    for piece in sorted(s["items"], key=lambda x: x["level"]):
                        marker = "→" if piece["id"] == item["id"] else " "
                        print(f"    {marker} [{piece['id']:>6}] Nv{piece['level']:>3}  {piece['name']}")

    # ─── Filtre niveau / type ────────────────────────────────────────────────
    if args.min_level is not None or args.max_level is not None or args.type_id:
        filtered = items_list
        if args.min_level is not None:
            filtered = [i for i in filtered if i["level"] >= args.min_level]
        if args.max_level is not None:
            filtered = [i for i in filtered if i["level"] <= args.max_level]
        if args.type_id:
            filtered = [i for i in filtered if i["typeId"] == args.type_id]
        lvl_range = f"nv {args.min_level or '?'}-{args.max_level or '?'}"
        print(f"\n🎯 Filtre ({lvl_range}, type={args.type_id or 'tous'}) → {len(filtered)} items")
        for item in filtered[:20]:
            print(f"  [{item['id']:>6}] Nv{item['level']:>3}  {item['name']:<35} ({item['typeName']})")
        if len(filtered) > 20:
            print(f"  ... et {len(filtered)-20} autres")

    # ─── Aperçu des sets ─────────────────────────────────────────────────────
    print("\n--- Aperçu sets (5 premiers) ---")
    for s in itemsets_list[:5]:
        pieces = ", ".join(p["name"] for p in s["items"][:3])
        more = f" +{len(s['items'])-3}" if len(s["items"]) > 3 else ""
        print(f"  [{s['id']:>4}] {s['name']:<30} {pieces}{more}")


if __name__ == "__main__":
    main()
