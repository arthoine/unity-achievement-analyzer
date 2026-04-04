import warnings
warnings.filterwarnings("ignore")

import UnityPy
import json
import os
import argparse
import glob
import sys
import subprocess
import tempfile

# Version Unity principale (Dofus 3)
UNITY_VERSION = "6000.1.17f1"
# Versions alternatives essayées si la principale crash
ALT_VERSIONS = ["2022.3.20f1", "2021.3.27f1", "2020.3.48f1"]

UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION

# Script worker isolé par objet (utilisé comme dernier recours)
PER_OBJ_WORKER = '''
import warnings; warnings.filterwarnings("ignore")
import UnityPy, json, sys
version, bundle_path, path_id_str, out_file = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
UnityPy.config.FALLBACK_UNITY_VERSION = version
path_id = int(path_id_str)
result = {"path_id": path_id, "success": False}
try:
    env = UnityPy.load(bundle_path)
    for obj in env.objects:
        if obj.path_id != path_id: continue
        result["type"] = str(obj.type.name)
        try:
            tree = obj.read_typetree()
            if tree:
                result["data"] = tree
                result["success"] = True
                result["method"] = "read_typetree"
                break
        except Exception: pass
        try:
            data = obj.read()
            result["name"] = getattr(data, "name", "Unnamed")
            result["success"] = True
            result["method"] = "read"
        except Exception: pass
        break
except Exception as e:
    result["error"] = str(e)
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(result, f, default=str, ensure_ascii=False)
'''

parser = argparse.ArgumentParser(
    description="Extrait les assets Unity depuis des fichiers .bundle"
)
parser.add_argument("--bundle-dir", default="data")
parser.add_argument("--catalog", default=None)
parser.add_argument("--hash", default=None)
parser.add_argument("--output", default="output")
parser.add_argument("--extract-images", action="store_true")
parser.add_argument("--unity-version", default=None)
parser.add_argument("--worker", default=None)
parser.add_argument("--worker-version", default=UNITY_VERSION)
parser.add_argument("--no-typetree", action="store_true")
args = parser.parse_args()

if args.unity_version:
    UNITY_VERSION = args.unity_version
    UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION

# ─── MODE WORKER : traite UN bundle entier en un process ────────────────────────────
if args.worker:
    bundle_path = args.worker
    name = os.path.basename(bundle_path)
    os.makedirs(args.output, exist_ok=True)
    results = []
    UnityPy.config.FALLBACK_UNITY_VERSION = args.worker_version
    try:
        env = UnityPy.load(bundle_path)
        for obj in env.objects:
            try:
                data = obj.read()
                obj_info = {
                    "bundle": name,
                    "path_id": obj.path_id,
                    "type": str(obj.type.name),
                    "name": getattr(data, 'name', 'Unnamed'),
                    "text": getattr(data, 'text', None),
                }
                if obj.type.name == "MonoBehaviour" and not args.no_typetree:
                    try:
                        tree = obj.read_typetree()
                        if tree:
                            obj_info["data"] = tree
                    except Exception:
                        pass
                if args.extract_images and obj.type.name in ["Texture2D", "Sprite"]:
                    img_dir = os.path.join(args.output, "images")
                    os.makedirs(img_dir, exist_ok=True)
                    try:
                        img = data.image
                        img_path = os.path.join(img_dir, f"{data.name}.png")
                        img.save(img_path)
                        obj_info["image_saved"] = img_path
                    except Exception as ie:
                        obj_info["image_error"] = str(ie)
                results.append(obj_info)
            except Exception:
                pass
    except Exception:
        pass
    out_path = os.path.join(args.output, name + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    sys.exit(0)

# ─── HELPERS ────────────────────────────────────────────────────────────────────────
def run_worker(bundle_path, version, output, extract_images, no_typetree=False, timeout=120):
    """Worker bundle entier. Retourne True si JSON non vide produit."""
    out_path = os.path.join(output, os.path.basename(bundle_path) + ".json")
    cmd = [sys.executable, __file__, "--worker", bundle_path,
           "--output", output, "--worker-version", version]
    if extract_images: cmd.append("--extract-images")
    if no_typetree:    cmd.append("--no-typetree")
    try:
        result = subprocess.run(cmd, timeout=timeout, capture_output=True)
        if result.returncode == 0 and os.path.exists(out_path):
            with open(out_path, "r") as f:
                content = json.load(f)
            return len(content) > 0
        return False
    except subprocess.TimeoutExpired:
        return False


def run_per_object(bundle_path, version, output, timeout=60):
    """
    Dernier recours : lit chaque objet dans un subprocess isolé.
    Identique à la stratégie de analyze_single.py.
    Retourne True si au moins un objet MonoBehaviour avec data a été récupéré.
    """
    name = os.path.basename(bundle_path)
    os.makedirs(output, exist_ok=True)

    # Liste les path_ids dans le process courant (listing seul ne crash pas)
    UnityPy.config.FALLBACK_UNITY_VERSION = version
    try:
        env = UnityPy.load(bundle_path)
        objects = [(obj.path_id, obj.type.name) for obj in env.objects]
    except Exception:
        return False

    # Écrit le script worker dans un fichier temp
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as wf:
        wf.write(PER_OBJ_WORKER)
        worker_path = wf.name

    results = []
    try:
        for path_id, type_name in objects:
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tf:
                tmp_path = tf.name
            try:
                proc = subprocess.run(
                    [sys.executable, worker_path, version, bundle_path, str(path_id), tmp_path],
                    timeout=timeout, capture_output=True
                )
                if proc.returncode == 0 and os.path.exists(tmp_path):
                    with open(tmp_path, "r", encoding="utf-8") as f:
                        obj_result = json.load(f)
                    obj_info = {
                        "bundle": name,
                        "path_id": path_id,
                        "type": obj_result.get("type", type_name),
                        "name": obj_result.get("name", ""),
                    }
                    if "data" in obj_result:
                        obj_info["data"] = obj_result["data"]
                    results.append(obj_info)
            except subprocess.TimeoutExpired:
                results.append({"bundle": name, "path_id": path_id, "type": type_name,
                                 "error": "timeout"})
            finally:
                try: os.unlink(tmp_path)
                except: pass
    finally:
        try: os.unlink(worker_path)
        except: pass

    if not results:
        return False

    out_path = os.path.join(output, name + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    return any("data" in r for r in results)


# ─── MODE PRINCIPAL ─────────────────────────────────────────────────────────────────
print(f"🎮 Unity version : {UnityPy.config.FALLBACK_UNITY_VERSION}")
os.makedirs(args.output, exist_ok=True)

if args.hash and os.path.exists(args.hash):
    with open(args.hash, "r") as f:
        print(f"🔑 Hash catalog : {f.read().strip()}")
if args.catalog and os.path.exists(args.catalog):
    size = os.path.getsize(args.catalog)
    print(f"📦 Catalog .bin : {args.catalog} ({size // 1024} Ko)")

bundle_files = sorted(glob.glob(os.path.join(args.bundle_dir, "*.bundle")))
if not bundle_files:
    print(f"❌ Aucun fichier .bundle trouvé dans '{args.bundle_dir}'")
    sys.exit(1)

total = len(bundle_files)
print(f"\n🗂  {total} bundle(s) trouvé(s) dans '{args.bundle_dir}'\n")

crashes = []

for i, bundle_path in enumerate(bundle_files, 1):
    name = os.path.basename(bundle_path)
    out_path = os.path.join(args.output, name + ".json")

    if os.path.exists(out_path):
        try:
            with open(out_path, "r") as f:
                existing = json.load(f)
            if len(existing) > 0:
                print(f"[{i}/{total}] ✅ déjà traité : {name}")
                continue
        except Exception:
            pass

    print(f"[{i}/{total}] 🔍 {name}", flush=True)

    # ── T1 : version principale + typetree
    ok = run_worker(bundle_path, UNITY_VERSION, args.output, args.extract_images)

    # ── T2-4 : versions alternatives + typetree
    if not ok:
        for alt_v in ALT_VERSIONS:
            print(f"  🔄 Retry {alt_v}...", end=" ", flush=True)
            ok = run_worker(bundle_path, alt_v, args.output, args.extract_images, timeout=180)
            if ok: print(f"✅ OK avec {alt_v}"); break
            else:  print("❌")

    # ── T5 : principale sans typetree
    if not ok:
        print(f"  🔄 Retry sans typetree...", end=" ", flush=True)
        ok = run_worker(bundle_path, UNITY_VERSION, args.output, args.extract_images,
                        no_typetree=True, timeout=180)
        if ok: print("✅ OK (sans typetree)")

    # ── T6-8 : alternatives sans typetree
    if not ok:
        for alt_v in ALT_VERSIONS:
            print(f"  🔄 Retry {alt_v} sans typetree...", end=" ", flush=True)
            ok = run_worker(bundle_path, alt_v, args.output, args.extract_images,
                            no_typetree=True, timeout=180)
            if ok: print(f"✅ OK avec {alt_v} (sans typetree)"); break
            else:  print("❌")

    # ── T9 (dernier recours) : per-object subprocess (stratégie analyze_single)
    if not ok:
        print(f"  🔄 Retry per-object...", end=" ", flush=True)
        for v in [UNITY_VERSION] + ALT_VERSIONS:
            ok = run_per_object(bundle_path, v, args.output)
            if ok: print(f"✅ OK per-object ({v})"); break
        if not ok: print("❌")

    if not ok:
        print(f"  ❌ crash irrécupérable")
        crashes.append(name)

# ─── FUSION ────────────────────────────────────────────────────────────────────────
print(f"\n📦 Fusion des résultats...")
all_objects = []
for bundle_path in bundle_files:
    name = os.path.basename(bundle_path)
    out_path = os.path.join(args.output, name + ".json")
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                all_objects.extend(json.load(f))
        except Exception:
            pass

final_path = os.path.join(args.output, "assets_final.json")
with open(final_path, "w", encoding="utf-8") as f:
    json.dump(all_objects, f, indent=2, ensure_ascii=False)

print(f"✅ {len(all_objects)} objets extraits → {final_path}")
if crashes:
    print(f"❌ {len(crashes)} bundle(s) irrécupérables : {', '.join(crashes)}")
if args.extract_images:
    print(f"🖼  Images → {os.path.join(args.output, 'images/')}")
