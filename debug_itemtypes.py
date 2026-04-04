#!/usr/bin/env python3
"""
debug_itemtypes.py — Inspecte la structure du bundle itemtypesdataroot dans assets_final.json
Usage : python debug_itemtypes.py "C:\\chemin\\vers\\assets_final.json"
"""
import json, sys, os

path = sys.argv[1] if len(sys.argv) > 1 else "assets_final.json"

if not os.path.exists(path):
    print(f"❌ Fichier introuvable : {path}")
    print("Usage : python debug_itemtypes.py \"C:\\chemin\\vers\\assets_final.json\"")
    sys.exit(1)

print(f"📂 Lecture {path}...")
with open(path, encoding="utf-8") as f:
    data = json.load(f)
print(f"   → {len(data):,} objets\n")

for obj in data:
    if "itemtypesdataroot" not in obj.get("bundle", ""):
        continue
    print(f"type={obj['type']}  name={obj.get('name')}  path_id={obj.get('path_id')}")
    d = obj.get("data", {})
    if not isinstance(d, dict):
        print(f"  data type: {type(d)}")
        continue
    print(f"  clés data: {list(d.keys())[:20]}")

    refs = d.get("references", {})
    refids = refs.get("RefIds", [])
    print(f"  RefIds count: {len(refids)}")
    if refids:
        print(f"  RefIds[0]: {refids[0]}")
        print(f"  RefIds[1]: {refids[1] if len(refids) > 1 else 'n/a'}")

    obj_by_id = d.get("objectsById", {})
    if obj_by_id:
        keys = obj_by_id.get("m_keys", [])
        vals = obj_by_id.get("m_values", [])
        print(f"  objectsById: {len(keys)} keys, {len(vals)} values")
        if vals:
            print(f"  exemple val[0]: {vals[0]}")
            print(f"  exemple val[1]: {vals[1] if len(vals) > 1 else 'n/a'}")

    print()
