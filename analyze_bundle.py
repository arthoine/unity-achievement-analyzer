import warnings
warnings.filterwarnings("ignore")

import UnityPy
import json
import os
import argparse
import glob
import sys
import subprocess

# Version Unity de Dofus 3 (détectée depuis globalgamemanagers)
UnityPy.config.FALLBACK_UNITY_VERSION = "6000.1.17f1"

parser = argparse.ArgumentParser(
    description="Extrait les assets Unity depuis des fichiers .bundle"
)
parser.add_argument("--bundle-dir", default="data", help="Dossier contenant les fichiers .bundle")
parser.add_argument("--catalog", default=None, help="Chemin vers le fichier catalog .bin")
parser.add_argument("--hash", default=None, help="Chemin vers le fichier .hash")
parser.add_argument("--output", default="output", help="Dossier de sortie (défaut: output/)")
parser.add_argument("--extract-images", action="store_true", help="Extraire les Texture2D/Sprites en PNG")
parser.add_argument("--unity-version", default=None, help="Forcer une version Unity (ex: 6000.1.17f1)")
parser.add_argument("--worker", default=None, help="Mode interne : traite un seul bundle")
args = parser.parse_args()

if args.unity_version:
    UnityPy.config.FALLBACK_UNITY_VERSION = args.unity_version

# ─── MODE WORKER : traite UN seul bundle ───────────────────────────────────────
if args.worker:
    bundle_path = args.worker
    name = os.path.basename(bundle_path)
    os.makedirs(args.output, exist_ok=True)
    results = []

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

                # Lecture des données réelles via typetree
                if obj.type.name == "MonoBehaviour":
                    try:
                        tree = obj.read_typetree()
                        if tree:
                            obj_info["data"] = tree
                    except Exception:
                        pass

                # Extraction images
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

# ─── MODE PRINCIPAL ────────────────────────────────────────────────────────────
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
        print(f"[{i}/{total}] ✅ déjà traité : {name}")
        continue

    print(f"[{i}/{total}] 🔍 {name}", flush=True)

    cmd = [sys.executable, __file__,
           "--worker", bundle_path,
           "--output", args.output,
           "--unity-version", UnityPy.config.FALLBACK_UNITY_VERSION]
    if args.extract_images:
        cmd.append("--extract-images")

    try:
        result = subprocess.run(cmd, timeout=120, capture_output=True)
        if result.returncode != 0:
            print(f"  ❌ crash (code {result.returncode})")
            crashes.append(name)
        elif not os.path.exists(out_path):
            print(f"  ⚠️  pas de sortie générée")
    except subprocess.TimeoutExpired:
        print(f"  ⏱️  timeout")
        crashes.append(name)

# ─── FUSION ────────────────────────────────────────────────────────────────────
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
