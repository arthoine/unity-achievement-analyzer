import UnityPy
import json
import os

BUNDLE_PATH = "data/data_assets_achievementcategoriesdataroot.asset.bundle"
OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

env = UnityPy.load(BUNDLE_PATH)
achievements = []

for obj in env.objects:
    try:
        data = obj.read()
        obj_info = {
            "path_id": obj.path_id,
            "type": str(obj.type.name),
            "name": getattr(data, 'name', 'Unnamed'),
        }

        if hasattr(data, 'm_Script') and data.m_Script:
            obj_info["script"] = str(data.m_Script)

        if hasattr(data, 'text'):
            obj_info["text_preview"] = data.text[:500]

        if hasattr(data, 'm_PathID'):
            obj_info["m_PathID"] = data.m_PathID

        achievements.append(obj_info)
    except Exception as e:
        print(f"Erreur sur l'objet {obj.path_id}: {e}")

output_path = os.path.join(OUTPUT_DIR, "achievements.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(achievements, f, indent=2, ensure_ascii=False)

print(f"✅ {len(achievements)} objets extraits → {output_path}")
