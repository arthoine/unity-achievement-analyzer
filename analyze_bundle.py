import UnityPy
import json
import os
import argparse
import glob

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
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

# Affichage des infos
if args.hash and os.path.exists(args.hash):
    with open(args.hash, "r") as f:
        print(f"🔑 Hash catalog : {f.read().strip()}")

if args.catalog and os.path.exists(args.catalog):
    size = os.path.getsize(args.catalog)
    print(f"📦 Catalog .bin : {args.catalog} ({size // 1024} Ko)")

# Trouver tous les .bundle dans le dossier
bundle_files = glob.glob(os.path.join(args.bundle_dir, "*.bundle"))
if not bundle_files:
    print(f"❌ Aucun fichier .bundle trouvé dans '{args.bundle_dir}'")
    exit(1)

print(f"\n🗂  {len(bundle_files)} bundle(s) trouvé(s) dans '{args.bundle_dir}' :")
for b in bundle_files:
    print(f"   - {os.path.basename(b)} ({os.path.getsize(b) // 1024} Ko)")

all_objects = []

for bundle_path in bundle_files:
    print(f"\n🔍 Lecture de {os.path.basename(bundle_path)}...")
    env = UnityPy.load(bundle_path)

    for obj in env.objects:
        try:
            data = obj.read()
            obj_info = {
                "bundle": os.path.basename(bundle_path),
                "path_id": obj.path_id,
                "type": str(obj.type.name),
                "name": getattr(data, 'name', 'Unnamed'),
            }

            if hasattr(data, 'm_Script') and data.m_Script:
                obj_info["script"] = str(data.m_Script)

            if hasattr(data, 'text'):
                obj_info["text_preview"] = data.text[:500]

            # Extraction des images si demandée
            if args.extract_images and obj.type.name in ["Texture2D", "Sprite"]:
                img_dir = os.path.join(args.output, "images")
                os.makedirs(img_dir, exist_ok=True)
                img = data.image
                img_path = os.path.join(img_dir, f"{data.name}.png")
                img.save(img_path)
                obj_info["image_saved"] = img_path

            all_objects.append(obj_info)
        except Exception as e:
            print(f"  ⚠️  Erreur objet {obj.path_id}: {e}")

output_path = os.path.join(args.output, "assets.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(all_objects, f, indent=2, ensure_ascii=False)

print(f"\n✅ {len(all_objects)} objets extraits → {output_path}")
if args.extract_images:
    print(f"🖼  Images extraites → {os.path.join(args.output, 'images/')}")
