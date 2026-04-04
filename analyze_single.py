#!/usr/bin/env python3
"""
analyze_single.py — Debug d'un bundle Unity qui crash (0xC0000005)
==================================================================
Stratégie : chaque objet est lu dans un subprocess isolé.
Le worker essaie plusieurs méthodes de lecture par ordre de risque :
  1. read_typetree()          — méthode normale (peut crash)
  2. read() sans typetree     — lecture basique
  3. obj.get_raw_data()       — bytes bruts si tout le reste crash
  4. Versions Unity alternatives — parfois le crash vient du mauvais parseur

Usage:
    python analyze_single.py data\\data_assets_itemsdataroot.asset.bundle
    python analyze_single.py data\\data_assets_itemsetsdataroot.asset.bundle
    python analyze_single.py data\\data_assets_itemsdataroot.asset.bundle --path-id 5777552850505650748
    python analyze_single.py data\\data_assets_itemsdataroot.asset.bundle --no-typetree
"""

import warnings
warnings.filterwarnings("ignore")

import UnityPy
import json
import sys
import subprocess
import tempfile
import os
import argparse
from pathlib import Path

UNITY_VERSION = "6000.1.17f1"

# Versions alternatives à essayer si la version principale crash
ALT_VERSIONS = [
    "2022.3.20f1",
    "2021.3.27f1",
    "2020.3.48f1",
]

WORKER_SCRIPT = '''
import warnings
warnings.filterwarnings("ignore")
import UnityPy, json, sys, traceback, struct

version    = sys.argv[1]
bundle_path= sys.argv[2]
path_id    = int(sys.argv[3])
out_file   = sys.argv[4]
no_typetree= sys.argv[5] == "1"

UnityPy.config.FALLBACK_UNITY_VERSION = version

result = {"path_id": path_id, "version": version, "success": False, "methods_tried": []}

try:
    env = UnityPy.load(bundle_path)
except Exception as e:
    result["error"] = f"load() crash: {e}"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, default=str)
    sys.exit(0)

for obj in env.objects:
    if obj.path_id != path_id:
        continue

    result["type"] = str(obj.type.name)

    # --- Méthode 1 : read_typetree (si non désactivé) ---
    if not no_typetree:
        try:
            result["methods_tried"].append("read_typetree")
            tree = obj.read_typetree()
            if tree:
                result["data"]    = tree
                result["success"] = True
                result["method"]  = "read_typetree"
                break
        except Exception as e:
            result["typetree_error"] = str(e)

    # --- Méthode 2 : read() basique ---
    try:
        result["methods_tried"].append("read")
        data = obj.read()
        result["name"]    = getattr(data, "name", "Unnamed")
        result["text"]    = getattr(data, "text", None)
        result["success"] = True
        result["method"]  = "read"
        # Essaie quand même le typetree après le read basique
        if not no_typetree and "data" not in result:
            try:
                tree = obj.read_typetree()
                if tree:
                    result["data"]   = tree
                    result["method"] = "read+typetree"
            except:
                pass
        break
    except Exception as e:
        result["read_error"] = str(e)

    # --- Méthode 3 : raw bytes ---
    try:
        result["methods_tried"].append("raw_data")
        raw = bytes(obj.get_raw_data())
        result["raw_size"]    = len(raw)
        result["raw_preview"] = raw[:64].hex()
        result["success"]     = True
        result["method"]      = "raw_bytes"
        break
    except Exception as e:
        result["raw_error"] = str(e)

    break

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(result, f, default=str, ensure_ascii=False)
'''


def read_obj_subprocess(bundle_path: str, path_id: int, timeout: int, version: str, no_typetree: bool) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        tmp_path = tmp.name
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as wf:
        wf.write(WORKER_SCRIPT)
        worker_path = wf.name

    try:
        proc = subprocess.run(
            [sys.executable, worker_path, version, bundle_path, str(path_id), tmp_path, "1" if no_typetree else "0"],
            timeout=timeout,
            capture_output=True,
            text=True
        )
        if proc.returncode == 0 and Path(tmp_path).exists() and Path(tmp_path).stat().st_size > 2:
            with open(tmp_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return {
                "path_id": path_id,
                "version": version,
                "success": False,
                "error": f"Subprocess crash (code {proc.returncode})",
                "stderr": (proc.stderr or "")[:300],
            }
    except subprocess.TimeoutExpired:
        return {"path_id": path_id, "version": version, "success": False, "error": f"Timeout ({timeout}s)"}
    except Exception as e:
        return {"path_id": path_id, "version": version, "success": False, "error": str(e)}
    finally:
        for p in [tmp_path, worker_path]:
            try: os.unlink(p)
            except: pass


def list_path_ids(bundle_path: str) -> list:
    env = UnityPy.load(bundle_path)
    return [(obj.path_id, obj.type.name) for obj in env.objects]


def main():
    parser = argparse.ArgumentParser(description="Debug bundle Unity — subprocess par objet, multi-stratégie")
    parser.add_argument("bundle", help="Chemin vers le .bundle")
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--timeout", "-t", type=int, default=30)
    parser.add_argument("--path-id", type=int, default=None)
    parser.add_argument("--no-typetree", action="store_true", help="Désactive read_typetree (méthode 1)")
    parser.add_argument("--try-alt-versions", action="store_true", help="Essaie des versions Unity alternatives si crash")
    args = parser.parse_args()

    bundle_path = str(Path(args.bundle))
    if not Path(bundle_path).exists():
        print(f"❌ Introuvable : {bundle_path}")
        sys.exit(1)

    print(f"🎯 Bundle   : {bundle_path}")
    print(f"📊 Unity    : {UNITY_VERSION}")
    print(f"⏱️  Timeout  : {args.timeout}s/objet")
    print(f"🔧 Typetree : {'désactivé' if args.no_typetree else 'activé'}")
    print()

    UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION
    try:
        objects = list_path_ids(bundle_path)
    except Exception as e:
        print(f"💥 Impossible de lire le bundle : {e}")
        sys.exit(1)

    if args.path_id:
        objects = [(pid, t) for pid, t in objects if pid == args.path_id]

    print(f"📦 {len(objects)} objet(s) : {objects}")
    print()

    results = []
    crashes = []

    for i, (path_id, type_name) in enumerate(objects):
        print(f"  [{i+1}/{len(objects)}] path_id={path_id} | {type_name}", end=" ", flush=True)

        # Essai version principale
        result = read_obj_subprocess(bundle_path, path_id, args.timeout, UNITY_VERSION, args.no_typetree)

        # Si crash + flag --try-alt-versions → essaie les alternatives
        if not result["success"] and args.try_alt_versions:
            for alt_v in ALT_VERSIONS:
                print(f"\n    🔄 Retry avec Unity {alt_v}...", end=" ", flush=True)
                alt_result = read_obj_subprocess(bundle_path, path_id, args.timeout, alt_v, args.no_typetree)
                if alt_result["success"]:
                    result = alt_result
                    break

        result["type"] = result.get("type", type_name)
        results.append(result)

        if result["success"]:
            method = result.get("method", "?")
            name   = result.get("name", "")
            data   = result.get("data")
            keys   = list(data.keys())[:5] if isinstance(data, dict) else (f"list[{len(data)}]" if isinstance(data, list) else "N/A")
            print(f"✅ méthode={method} | name={name!r} | data={keys}")
        else:
            print(f"❌ {result.get('error', '?')}")
            crashes.append(path_id)

    print()
    print(f"✅ {len(results) - len(crashes)}/{len(objects)} OK")
    if crashes:
        print(f"❌ Crash sur path_ids : {crashes}")
        print()
        print("💡 Suggestions :")
        print("   python analyze_single.py <bundle> --no-typetree")
        print("   python analyze_single.py <bundle> --try-alt-versions")
        print("   python analyze_single.py <bundle> --no-typetree --try-alt-versions")

    out_name = args.output or f"{Path(args.bundle).stem}-debug.json"
    with open(out_name, "w", encoding="utf-8") as f:
        json.dump({
            "bundle": bundle_path,
            "total_objects": len(objects),
            "success_count": len(results) - len(crashes),
            "crashed_path_ids": crashes,
            "results": results,
        }, f, indent=2, default=str, ensure_ascii=False)

    print(f"\n💾 Résultat → {out_name}  ({Path(out_name).stat().st_size / 1024:.1f} Ko)")


if __name__ == "__main__":
    main()
