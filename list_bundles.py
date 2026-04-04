#!/usr/bin/env python3
"""
list_bundles.py — Inventaire de tous les bundles dans assets_final.json
=======================================================================
Affiche chaque bundle unique avec le nombre d'objets et les classes Unity
qu'il contient, pour savoir ce qu'on peut extraire.

Usage :
    python list_bundles.py
    python list_bundles.py --assets output/assets_final.json
    python list_bundles.py --assets output/assets_final.json --bundle itemsdataroot
"""

import json
import argparse
import os
import sys
from collections import defaultdict, Counter

DEFAULT_ASSETS = "output/assets_final.json"


def main():
    parser = argparse.ArgumentParser(description="Inventaire des bundles Unity")
    parser.add_argument("--assets",  default=DEFAULT_ASSETS)
    parser.add_argument("--bundle",  default=None, help="Inspecter un bundle spécifique")
    args = parser.parse_args()

    if not os.path.exists(args.assets):
        print(f"❌ Fichier introuvable : {args.assets}")
        sys.exit(1)

    print(f"📂 Lecture {args.assets}…")
    with open(args.assets, encoding="utf-8") as f:
        data = json.load(f)
    print(f"   → {len(data):,} objets au total\n")

    # Groupe par bundle
    bundles = defaultdict(list)
    for obj in data:
        bundles[obj.get("bundle", "?")].append(obj)

    if args.bundle:
        # Mode détail : affiche toutes les classes Unity d'un bundle
        b = args.bundle.lower()
        match = {k: v for k, v in bundles.items() if b in k.lower()}
        if not match:
            print(f"❌ Aucun bundle contenant '{args.bundle}'")
            print("Bundles disponibles :")
            for k in sorted(bundles): print(f"  {k}")
            sys.exit(1)
        for bname, objs in sorted(match.items()):
            classes = Counter(o.get("type", "?") for o in objs)
            total_refs = 0
            for o in objs:
                refs = o.get("data", {}).get("references", {}).get("RefIds", [])
                total_refs += len(refs)
            print(f"📦 {bname}  ({len(objs)} objets, {total_refs} refs)")
            for cls, cnt in classes.most_common():
                print(f"   {cnt:>5}x  {cls}")
            # Exemple d'un premier objet avec refs
            for o in objs:
                refs = o.get("data", {}).get("references", {}).get("RefIds", [])
                if refs:
                    sample = refs[0]
                    print(f"\n   🔍 Exemple premier RefId :")
                    print(json.dumps(sample, indent=6, ensure_ascii=False)[:800])
                    break
        return

    # Mode liste : résumé de tous les bundles
    print(f"{'Bundle':<45} {'Objets':>6}  {'Refs':>7}  Classes")
    print("-" * 90)
    for bname in sorted(bundles.keys()):
        objs = bundles[bname]
        classes = Counter(o.get("type", "?") for o in objs)
        total_refs = 0
        for o in objs:
            refs = o.get("data", {}).get("references", {}).get("RefIds", [])
            total_refs += len(refs)
        top_classes = ", ".join(f"{c}({n})" for c, n in classes.most_common(3))
        print(f"{bname:<45} {len(objs):>6}  {total_refs:>7}  {top_classes}")

    print(f"\n📊 Total : {len(bundles)} bundles, {len(data):,} objets")
    print("\nPour inspecter un bundle : python list_bundles.py --bundle <nom>")


if __name__ == "__main__":
    main()
