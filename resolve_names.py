#!/usr/bin/env python3
"""
resolve_names.py — Résolution des nameId Dofus 3
=================================================
Utilise fr_texts.json (généré par dofus-data-extractor/parse_fr.py)
pour résoudre les nameId présents dans assets_final.json
(généré par unity-achievement-analyzer/analyze_bundle.py).

Usage:
    python resolve_names.py \\
        --texts   ../dofus-data-extractor/fr_texts.json \\
        --assets  output/assets_final.json \\
        --output  achievements_fr.json
"""

import json
import argparse
import os
import sys

# ─── Champs qui contiennent des nameId à résoudre ─────────────────────────────
NAME_ID_FIELDS = {
    "nameId",
    "descriptionId",
    "shortDescriptionId",
    "tooltipId",
    "criterionId",
}


def load_texts(path: str) -> dict:
    """Charge fr_texts.json → dict {int_id: str}"""
    if not os.path.exists(path):
        print(f"❌ fr_texts.json introuvable : {path}")
        print("   → Génère-le d'abord avec : python parse_fr.py (dofus-data-extractor)")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    # Les clés sont des strings dans le JSON, on les convertit en int
    return {int(k): v for k, v in raw.items()}


def resolve_value(val, texts: dict):
    """Résout récursivement les nameId dans une valeur (dict, list, int)."""
    if isinstance(val, dict):
        return {k: resolve_value(v, texts) for k, v in val.items()}
    if isinstance(val, list):
        return [resolve_value(item, texts) for item in val]
    return val


def resolve_object(obj: dict, texts: dict) -> dict:
    """
    Résout les nameId dans un objet extrait.
    Pour chaque champ `xxxId` connu, ajoute `xxxText` avec le texte FR.
    """
    if "data" not in obj or not isinstance(obj["data"], dict):
        return obj

    resolved = dict(obj)
    data = dict(obj["data"])

    for field in NAME_ID_FIELDS:
        if field in data and isinstance(data[field], int) and data[field] > 0:
            text = texts.get(data[field])
            if text:
                data[field + "_text"] = text

    # Résolution récursive dans les sous-structures (ex: objectifs imbriqués)
    resolved["data"] = resolve_value(data, texts)
    return resolved


def build_achievement_tree(objects: list, texts: dict) -> list:
    """
    Construit un arbre achievements lisible :
    catégorie → achievements → objectifs
    """
    categories = {}
    achievements = {}
    objectives = {}
    rewards = {}

    for obj in objects:
        bundle = obj.get("bundle", "")
        data = obj.get("data") or {}
        if not isinstance(data, dict):
            continue

        obj_id = data.get("id")
        if obj_id is None:
            continue

        if "achievementcategories" in bundle:
            name_id = data.get("nameId", 0)
            categories[obj_id] = {
                "id": obj_id,
                "name": texts.get(name_id, f"nameId:{name_id}"),
                "nameId": name_id,
                "order": data.get("order", 0),
                "achievements": [],
            }

        elif "achievementsdataroot" in bundle:
            name_id = data.get("nameId", 0)
            desc_id = data.get("descriptionId", 0)
            achievements[obj_id] = {
                "id": obj_id,
                "name": texts.get(name_id, f"nameId:{name_id}"),
                "description": texts.get(desc_id, "") if desc_id else "",
                "nameId": name_id,
                "categoryId": data.get("categoryId"),
                "points": data.get("points", 0),
                "level": data.get("level", 0),
                "objectives": [],
                "rewards": [],
            }

        elif "achievementobjectivesdataroot" in bundle:
            name_id = data.get("nameId", 0)
            objectives[obj_id] = {
                "id": obj_id,
                "name": texts.get(name_id, f"nameId:{name_id}"),
                "nameId": name_id,
                "achievementId": data.get("achievementId"),
                "order": data.get("order", 0),
            }

        elif "achievementrewardsdataroot" in bundle:
            rewards[obj_id] = {
                "id": obj_id,
                "achievementId": data.get("achievementId"),
                "itemId": data.get("itemId"),
                "quantity": data.get("quantity", 1),
                "type": data.get("type"),
            }

    # Rattacher objectifs aux achievements
    for obj in objectives.values():
        ach_id = obj.get("achievementId")
        if ach_id and ach_id in achievements:
            achievements[ach_id]["objectives"].append(obj)

    # Rattacher rewards aux achievements
    for rew in rewards.values():
        ach_id = rew.get("achievementId")
        if ach_id and ach_id in achievements:
            achievements[ach_id]["rewards"].append(rew)

    # Trier les objectifs par order
    for ach in achievements.values():
        ach["objectives"].sort(key=lambda x: x.get("order", 0))

    # Rattacher achievements aux catégories
    for ach in achievements.values():
        cat_id = ach.get("categoryId")
        if cat_id and cat_id in categories:
            categories[cat_id]["achievements"].append(ach)

    # Trier catégories par order
    result = sorted(categories.values(), key=lambda x: x.get("order", 0))

    # Stats
    total_ach = sum(len(c["achievements"]) for c in result)
    total_obj = sum(
        len(a["objectives"])
        for c in result
        for a in c["achievements"]
    )
    print(f"🏆 {len(result)} catégories, {total_ach} achievements, {total_obj} objectifs")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Résout les nameId Dofus 3 via fr_texts.json"
    )
    parser.add_argument(
        "--texts",
        default="../dofus-data-extractor/fr_texts.json",
        help="Chemin vers fr_texts.json (dofus-data-extractor)",
    )
    parser.add_argument(
        "--assets",
        default="output/assets_final.json",
        help="Chemin vers assets_final.json (unity-achievement-analyzer)",
    )
    parser.add_argument(
        "--output",
        default="achievements_fr.json",
        help="Fichier JSON de sortie",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Sortie plate (tous les objets avec nameId résolus) au lieu de l'arbre",
    )
    args = parser.parse_args()

    print(f"📖 Chargement textes FR : {args.texts}")
    texts = load_texts(args.texts)
    print(f"   → {len(texts):,} textes chargés (IDs {min(texts)} → {max(texts)})")

    print(f"📦 Chargement assets   : {args.assets}")
    if not os.path.exists(args.assets):
        print(f"❌ assets_final.json introuvable : {args.assets}")
        print("   → Lance d'abord : python analyze_bundle.py --bundle-dir data/")
        sys.exit(1)

    with open(args.assets, encoding="utf-8") as f:
        objects = json.load(f)
    print(f"   → {len(objects):,} objets chargés")

    if args.flat:
        # Mode plat : résolution nameId sur tous les objets
        resolved = [resolve_object(obj, texts) for obj in objects]
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(resolved, f, ensure_ascii=False, indent=2)
        print(f"✅ Sortie plate → {args.output}")
    else:
        # Mode arbre : catégories → achievements → objectifs
        print("🌳 Construction de l'arbre achievements...")
        tree = build_achievement_tree(objects, texts)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)
        print(f"✅ Arbre achievements → {args.output}")

    # Aperçu
    print("\n--- Aperçu ---")
    if not args.flat and tree:
        for cat in tree[:5]:
            nb = len(cat["achievements"])
            print(f"  [{cat['id']:>4}] {cat['name']:<20} ({nb} achievements)")
        if len(tree) > 5:
            print(f"  ... et {len(tree)-5} autres catégories")


if __name__ == "__main__":
    main()
