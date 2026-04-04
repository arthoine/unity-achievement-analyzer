import warnings
warnings.filterwarnings("ignore")

import UnityPy
import json
import os
import argparse
import glob

# Version Unity de Dofus 3 (détectée depuis globalgamemanagers)
UnityPy.config.FALLBACK_UNITY_VERSION = "6000.1.17f1"

parser = argparse.ArgumentParser(
    description="Extrait les assets Unity depuis des fichiers .bundle"
)
parser.add_argument(
    "--bundle-dir",
    default="data",
    help="Dossier contenant les fichiers .bundle (défaut: data/)"
)
parser.add_argument(
    "--catalog",
    default=None,
    help="Chemin vers le fichier catalog .bin (ex: data/catalog_1.0.bin)"
)
parser.add_argument(
    "--hash",
    default=None,
    help="Chemin vers le fichier .hash (ex: data/catalog_1.0.hash)"
)
parser.add_argument(
    "--output",
    default="output",
    help="Dossier de sortie pour le JSON (défaut: output/)"
)
parser.add_argument(
    "--extract-images",
    action="store_true",
    help="Extraire aussi les Texture2D / Sprites en PNG"
)
parser.add_argument(
    "--unity-version",
    default=None,
    help="Forcer une version Unity spécifique (ex: 6000.1.17f1)"
)
args = parser.parse_args()

if args.unity_version:
    UnityPy.config.FALLBACK_UNITY_VERSION = args.unity_version

print(f"🎮 Unity version : {UnityPy.config.FALLBACK_UNITY_VERSION}")

os.makedirs(args.output, exist_ok=True)

if args.hash and os.path.exists(args.hash):
    with open(args.hash, "r") as f:
        print(f"🔑 Hash catalog : {f.read().strip()}")

if args.catalog and os.path.exists(args.catalog):
    size = os.path.getsize(args.catalog)
    print(f"📦 Catalog .bin : {args.catalog} ({size // 1024} Ko)")

bundle_files = glob.glob(os.path.join(args.bundle_dir, "*.bundle"))
if not bundle_files:
    print(f"❌ Aucun fichier .bundle trouvé dans '{args.bundle_dir}'")
    exit(1)

print(f"\n🗂  {len(bundle_files)} bundle(s) trouvé(s) dans '{args.bundle_dir}' :")
for b in bundle_files:
    print(f"   - {os.path.basename(b)} ({os.path.getsize(b) // 1024} Ko)")

all_objects = []
total = len(bundle_files)

for i, bundle_path in enumerate(bundle_files, 1):
    name = os.path.basename(bundle_path)
    print(f"[{i}/{total}] 🔍 {name}")
    try:
        env = UnityPy.load(bundle_path)
    except Exception as e:
        print(f"  ❌ Impossible de lire : {e}")
        continue

    for obj in env.objects:
        try:
            data = obj.read()
            obj_info = {
                "bundle": name,
                "path_id": obj.path_id,
                "type": str(obj.type.name),
                "name": getattr(data, 'name', 'Unnamed'),
            }

            if hasattr(data, 'm_Script') and data.m_Script:
                obj_info["script"] = str(data.m_Script)

            if hasattr(data, 'text'):
                obj_info["text_preview"] = data.text[:500]

            if args.extract_images and obj.type.name in ["Texture2D", "Sprite"]:
                img_dir = os.path.join(args.output, "images")
                os.makedirs(img_dir, exist_ok=True)
                try:
                    img = data.image
                    img_path = os.path.join(img_dir, f"{data.name}.png")
                    img.save(img_path)
                    obj_info["image_saved"] = img_path
                except Exception as ie:
                    print(f"  ⚠️  Image {data.name}: {ie}")

            all_objects.append(obj_info)
        except Exception as e:
            print(f"  ⚠️  Objet {obj.path_id}: {e}")

output_path = os.path.join(args.output, "assets.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(all_objects, f, indent=2, ensure_ascii=False)

print(f"\n✅ {len(all_objects)} objets extraits → {output_path}")
if args.extract_images:
    print(f"🖼  Images → {os.path.join(args.output, 'images/')}")
