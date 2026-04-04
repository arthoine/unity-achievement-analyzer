#!/usr/bin/env python3
"""
analyze_single.py — Debug d'un bundle Unity qui crash (0xC0000005)
==================================================================
Stratégie : chaque objet est lu dans un subprocess isolé.
Si le subprocess crash (SIGSEGV / 0xC0000005), on continue quand même.

Usage:
    python analyze_single.py data\\data_assets_itemsdataroot.asset.bundle
    python analyze_single.py data\\data_assets_itemsetsdataroot.asset.bundle
    python analyze_single.py data\\data_assets_itemsdataroot.asset.bundle --path-id 2
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

# ─── Worker (lancé dans un subprocess séparé) ──────────────────────────────
WORKER_SCRIPT = """
import warnings
warnings.filterwarnings("ignore")
import UnityPy, json, sys, traceback

UnityPy.config.FALLBACK_UNITY_VERSION = "{version}"

bundle_path = sys.argv[1]
path_id     = int(sys.argv[2])
out_file    = sys.argv[3]

env = UnityPy.load(bundle_path)
result = {{"path_id": path_id, "success": False}}

for obj in env.objects:
    if obj.path_id != path_id:
        continue
    result["type"] = str(obj.type.name)
    try:
        data = obj.read()
        result["name"] = getattr(data, "name", "Unnamed")
        result["text"] = getattr(data, "text", None)
        tree = obj.read_typetree()
        result["data"] = tree
        result["success"] = True
    except Exception as e:
        result["error"]  = str(e)
        result["trace"]  = traceback.format_exc()
    break

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(result, f, default=str)
"""


def read_obj_subprocess(bundle_path: str, path_id: int, timeout: int = 30) -> dict:
    """Lance un subprocess isolé pour lire un seul objet. Survive aux crash natifs."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        tmp_path = tmp.name

    # Écrit le worker dans un fichier temp
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as wf:
        wf.write(WORKER_SCRIPT.format(version=UNITY_VERSION))
        worker_path = wf.name

    try:
        result = subprocess.run(
            [sys.executable, worker_path, bundle_path, str(path_id), tmp_path],
            timeout=timeout,
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and Path(tmp_path).exists():
            with open(tmp_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return {
                "path_id": path_id,
                "success": False,
                "error": f"Subprocess crash (code {result.returncode})",
                "stderr": result.stderr[:500] if result.stderr else "",
            }

    except subprocess.TimeoutExpired:
        return {"path_id": path_id, "success": False, "error": f"Timeout ({timeout}s)"}
    except Exception as e:
        return {"path_id": path_id, "success": False, "error": str(e)}
    finally:
        for p in [tmp_path, worker_path]:
            try:
                os.unlink(p)
            except:
                pass


def list_path_ids(bundle_path: str) -> list[int]:
    """Récupère la liste des path_ids sans lire les objets."""
    env = UnityPy.load(bundle_path)
    return [(obj.path_id, obj.type.name) for obj in env.objects]


def main():
    parser = argparse.ArgumentParser(description="Debug bundle Unity — subprocess par objet")
    parser.add_argument("bundle", help="Chemin vers le .bundle")
    parser.add_argument("--output", "-o", default=None, help="Fichier JSON de sortie")
    parser.add_argument("--timeout", "-t", type=int, default=30, help="Timeout par objet en secondes (défaut: 30)")
    parser.add_argument("--path-id", type=int, default=None, help="Lire un seul path_id spécifique")
    args = parser.parse_args()

    bundle_path = str(Path(args.bundle))
    if not Path(bundle_path).exists():
        print(f"❌ Introuvable : {bundle_path}")
        sys.exit(1)

    print(f"🎯 Bundle  : {bundle_path}")
    print(f"📊 Unity   : {UNITY_VERSION}")
    print(f"⏱️  Timeout : {args.timeout}s/objet")
    print()

    # Liste les objets sans les lire
    UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION
    try:
        objects = list_path_ids(bundle_path)
    except Exception as e:
        print(f"💥 Impossible de lire le bundle : {e}")
        sys.exit(1)

    if args.path_id:
        objects = [(pid, t) for pid, t in objects if pid == args.path_id]

    print(f"📦 {len(objects)} objet(s) détectés : {objects}")
    print()

    results = []
    crashes = []

    for i, (path_id, type_name) in enumerate(objects):
        print(f"  [{i+1}/{len(objects)}] path_id={path_id} | {type_name} ...", end=" ", flush=True)
        result = read_obj_subprocess(bundle_path, path_id, timeout=args.timeout)
        result["type"] = result.get("type", type_name)
        results.append(result)

        if result["success"]:
            name = result.get("name", "Unnamed")
            data = result.get("data")
            data_keys = list(data.keys())[:5] if isinstance(data, dict) else "N/A"
            print(f"✅ {name!r} | clés: {data_keys}")
        else:
            err = result.get("error", "?")
            print(f"❌ {err}")
            crashes.append(path_id)

    print()
    print(f"✅ {len(results) - len(crashes)}/{len(objects)} OK")
    if crashes:
        print(f"❌ Crash sur path_ids : {crashes}")

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
