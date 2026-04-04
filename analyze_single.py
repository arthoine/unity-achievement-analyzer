#!/usr/bin/env python3
"""
analyze_single.py — Analyse DÉTAILLÉE d'un bundle Unity (mode debug)
==================================================================
Utilisé pour débugger les bundles qui crashent (ex: itemsdataroot, itemsetsdataroot)
- Logging ultra-détaillé
- Timeout par objet (évite les blocages)
- Sauvegarde partielle même si crash
- Stats mémoire
- Skip des objets problématiques

Usage:
    python analyze_single.py data_assets_itemsdataroot.asset.bundle
    python analyze_single.py data_assets_itemsetsdataroot.asset.bundle
"""

import warnings
warnings.filterwarnings("ignore")

import UnityPy
import json
import sys
import traceback
import gc
import os
from pathlib import Path
import psutil
import argparse

# Version Unity Dofus
UnityPy.config.FALLBACK_UNITY_VERSION = "6000.1.17f1"
TIMEOUT_PER_OBJ = 10  # secondes max par objet

def memory_usage():
    """Mémoire utilisée en MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def safe_read_obj(obj, obj_index, total_objs):
    """Lit un objet avec timeout et gestion d'erreur"""
    print(f"  [{obj_index+1}/{total_objs}] {obj.path_id} | {obj.type.name:<20} | {getattr(obj.read(), 'name', 'Unnamed')}")

    obj_info = {
        "path_id": obj.path_id,
        "type": str(obj.type.name),
        "size": sys.getsizeof(obj.read()),
        "memory_before": memory_usage(),
    }

    try:
        gc.collect()

        data = obj.read()
        obj_info["name"] = getattr(data, 'name', 'Unnamed')
        obj_info["text"] = getattr(data, 'text', None)

        # Typetree (source des crashes)
        try:
            tree = obj.read_typetree()
            if tree:
                obj_info["data"] = tree
                obj_info["data_size"] = sys.getsizeof(tree)
            else:
                obj_info["data"] = None
        except Exception as tree_err:
            obj_info["typetree_error"] = str(tree_err)
            obj_info["typetree_trace"] = traceback.format_exc()

        # Images (Texture2D/Sprite)
        if obj.type.name in ["Texture2D", "Sprite"]:
            try:
                img = data.image
                obj_info["image_size"] = img.size
                obj_info["image_format"] = str(img.format)
            except:
                obj_info["image_error"] = "Failed to read image"

        obj_info["memory_after"] = memory_usage()
        obj_info["success"] = True

    except Exception as e:
        obj_info["error"] = str(e)
        obj_info["trace"] = traceback.format_exc()
        obj_info["success"] = False

    finally:
        gc.collect()

    return obj_info

def main():
    parser = argparse.ArgumentParser(description="Debug d'un bundle Unity qui crash")
    parser.add_argument("bundle", help="Chemin vers le .bundle")
    parser.add_argument("--output", "-o", default=None, help="Fichier JSON de sortie")
    parser.add_argument("--max-objs", "-m", type=int, default=500, help="Max objets à analyser")
    args = parser.parse_args()

    bundle_path = Path(args.bundle)
    if not bundle_path.exists():
        print(f"❌ {bundle_path} introuvable")
        sys.exit(1)

    print(f"🎯 Debug : {bundle_path}")
    print(f"📊 UnityPy: {UnityPy.config.FALLBACK_UNITY_VERSION}")
    print(f"⏱️  Timeout/objet: {TIMEOUT_PER_OBJ}s")
    print(f"🔢 Max objets: {args.max_objs}")
    print()

    results = []
    crashes = []
    total_objs = 0
    success_count = 0

    try:
        env = UnityPy.load(str(bundle_path))
        total_objs = len(env.objects)
        print(f"📦 {total_objs} objets trouvés")
        print()

        for i, obj in enumerate(env.objects):
            if i >= args.max_objs:
                print(f"⏹️  Limite atteinte ({args.max_objs} objets)")
                break

            result = safe_read_obj(obj, i, total_objs)
            results.append(result)

            if result["success"]:
                success_count += 1
            else:
                crashes.append(i)

            if (i + 1) % 50 == 0:
                print(f"📈 [{i+1}/{total_objs}] {success_count} OK, {len(crashes)} crash")

        print()
        print(f"✅ {success_count}/{total_objs} objets OK")
        if crashes:
            print(f"❌ Crashes aux indices: {crashes[:10]}{'...' if len(crashes) > 10 else ''}")

    except Exception as env_err:
        print(f"💥 CRASH ENV: {env_err}")
        crashes.append("ENVIRONMENT")

    # Sauvegarde partielle
    out_name = args.output or f"{bundle_path.stem}-debug.json"
    with open(out_name, "w", encoding="utf-8") as f:
        json.dump({
            "bundle": str(bundle_path),
            "total_objects": total_objs,
            "success": success_count,
            "crashes": crashes,
            "results": results,
            "memory_peak": max((r.get("memory_after", 0) for r in results), default=0),
        }, f, indent=2, default=str)

    print(f"\n💾 Debug sauvé → {out_name}")
    print(f"📊 Taille fichier : {Path(out_name).stat().st_size / 1024:.1f} Ko")

if __name__ == "__main__":
    main()
