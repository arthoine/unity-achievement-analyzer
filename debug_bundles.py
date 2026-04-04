#!/usr/bin/env python3
"""
debug_bundles.py — Liste tous les bundles et classes Unity dans assets_final.json
Usage : python debug_bundles.py "output/assets_final.json"
"""
import json, sys, os
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else "output/assets_final.json"

if not os.path.exists(path):
    print(f"❌ Fichier introuvable : {path}")
    sys.exit(1)

with open(path, encoding="utf-8") as f:
    data = json.load(f)

# bundle → { classe → count }
bundles = defaultdict(lambda: defaultdict(int))

for obj in data:
    bundle = obj.get("bundle", "?")
    if obj.get("type") != "MonoBehaviour":
        continue
    d = obj.get("data", {})
    if not isinstance(d, dict):
        continue
    refs = d.get("references", {}).get("RefIds", [])
    for ref in refs:
        cls = ref.get("type", {}).get("class", "?")
        bundles[bundle][cls] += 1

print(f"{'BUNDLE':<55} {'CLASSE UNITY':<35} COUNT")
print("-" * 100)
for bundle in sorted(bundles):
    for cls, count in sorted(bundles[bundle].items(), key=lambda x: -x[1]):
        short = bundle.split("/")[-1].replace(".asset.bundle", "")
        print(f"{short:<55} {cls:<35} {count}")
    print()
