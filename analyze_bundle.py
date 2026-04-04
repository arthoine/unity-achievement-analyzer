import warnings
warnings.filterwarnings("ignore")

import UnityPy
import json
import os
import argparse
import glob
import sys
import subprocess

# Version Unity principale (Dofus 3)
UNITY_VERSION = "6000.1.17f1"
# Versions alternatives essayées si la principale crash
ALT_VERSIONS = ["2022.3.20f1", "2021.3.27f1", "2020.3.48f1"]

UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION

parser = argparse.ArgumentParser(
    description="Extrait les assets Unity depuis des fichiers .bundle"
)
parser.add_argument("--bundle-dir", default="data", help="Dossier contenant les fichiers .bundle")
parser.add_argument("--catalog", default=None)
parser.add_argument("--hash", default=None)
parser.add_argument("--output", default="output")
parser.add_argument("--extract-images", action="store_true")
parser.add_argument("--unity-version", default=None)
parser.add_argument("--worker", default=None, help="Mode interne : traite un seul bundle")
parser.add_argument("--worker-version", default=UNITY_VERSION, help="Version Unity à utiliser dans le worker")
args = parser.parse_args()

if args.unity_version:
    UNITY_VERSION = args.unity_version
    UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION

# ─── MODE WORKER : traite UN seul bundle ─────────────────────────────────────────────
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

                if obj.type.name == "MonoBehaviour":
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

# ─── HELPER : lance un worker avec une version donnée ────────────────────────────────
def run_worker(bundle_path, version, output, extract_images, timeout=120):
    """Lance le worker pour un bundle avec la version Unity spécifiée.
    Retourne True si succès, False si crash/timeout."""
    out_path = os.path.join(output, os.path.basename(bundle_path) + ".json")
    cmd = [
        sys.executable, __file__,
        "--worker", bundle_path,
        "--output", output,
        "--worker-version", version,
    ]
    if extract_images:
        cmd.append("--extract-images")
    try:
        result = subprocess.run(cmd, timeout=timeout, capture_output=True)
        if result.returncode == 0 and os.path.exists(out_path):
            # Vérifie que le JSON n'est pas vide
            with open(out_path, "r") as f:
                content = json.load(f)
            if len(content) > 0:
                return True
        return False
    except subprocess.TimeoutExpired:
        return False

# ─── MODE PRINCIPAL ────────────────────────────────────────────────────────────────────
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
        # Vérifie que le fichier existant n'est pas vide (résultat d'un crash précédent)
        try:
            with open(out_path, "r") as f:
                existing = json.load(f)
            if len(existing) > 0:
                print(f"[{i}/{total}] ✅ déjà traité : {name}")
                continue
        except Exception:
            pass  # Fichier corrompu -> on le retrait

    print(f"[{i}/{total}] 🔍 {name}", flush=True)

    # ── Tentative 1 : version principale
    ok = run_worker(bundle_path, UNITY_VERSION, args.output, args.extract_images)

    # ── Tentatives 2+ : versions alternatives
    if not ok:
        for alt_v in ALT_VERSIONS:
            print(f"  🔄 Retry {alt_v}...", end=" ", flush=True)
            ok = run_worker(bundle_path, alt_v, args.output, args.extract_images, timeout=180)
            if ok:
                print(f"✅ OK avec {alt_v}")
                break
            else:
                print("❌")

    if not ok:
        print(f"  ❌ crash sur toutes les versions")
        crashes.append(name)

# ─── FUSION ──────────────────────────────────────────────────────────────────────────────────
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
    print(f"❌ {len(crashes)} bundle(s) en échec : {', '.join(crashes)}")
if args.extract_images:
    print(f"🖼  Images → {os.path.join(args.output, 'images/')}")
