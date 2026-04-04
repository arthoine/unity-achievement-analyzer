"""
Extrait items (id, name_id, name) depuis les bundles Unity Dofus.
Output: items.csv (item_id, name_id, name)
"""
import re
import csv
import glob
import os
import sys

# Les JSON sont dans le même dossier que le script
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(DATA_DIR, "items.csv")

# Langue cible pour les noms (adapter si besoin)
LANG = "fr"

def find_item_bundles(data_dir):
    patterns = [
        os.path.join(data_dir, "*itemsdataroot*.json"),
        os.path.join(data_dir, "*items*dataroot*.json"),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p, recursive=True))
    return sorted(set(files))

def find_i18n_files(data_dir):
    patterns = [
        os.path.join(data_dir, f"*i18n*{LANG}*.json"),
        os.path.join(data_dir, f"*{LANG}*i18n*.json"),
        os.path.join(data_dir, "*i18n*.json"),
        os.path.join(data_dir, "*texts*.json"),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p, recursive=True))
    return sorted(set(files))

def load_i18n(files):
    """Charge le dictionnaire nameId -> texte depuis les fichiers i18n."""
    texts = {}

    kv_pattern = re.compile(r'"?(\d+)"?\s*[=:]\s*"([^"]*)"')

    for filepath in files:
        print(f"Chargement i18n: {os.path.basename(filepath)}")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"  Erreur: {e}")
            continue

        id_text = re.compile(
            r'\bid\s+(\d+)\b[^\n]*\n(?:.*?\n)*?.*?\btext\s+"([^"\\]*(?:\\.[^"\\]*)*)"',
            re.DOTALL
        )
        count = 0
        for m in id_text.finditer(content):
            nid = int(m.group(1))
            text = m.group(2).replace('\\n', ' ').replace('\\"', '"').strip()
            if nid not in texts and text:
                texts[nid] = text
                count += 1

        if count == 0:
            for m in kv_pattern.finditer(content):
                nid = int(m.group(1))
                text = m.group(2).strip()
                if nid not in texts and text:
                    texts[nid] = text

    print(f"Total textes i18n chargés: {len(texts)}")
    return texts

def extract_items(files):
    """Extrait les items: (id, nameId, typeId) depuis les bundles ItemsDataRoot."""
    items = {}

    block_pattern = re.compile(
        r'id\s+(\d+),\s*nameId\s+(\d+),\s*typeId\s+(\d+)'
    )

    for filepath in files:
        print(f"Lecture items: {os.path.basename(filepath)}")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        count = 0
        for m in block_pattern.finditer(content):
            item_id = int(m.group(1))
            name_id = int(m.group(2))
            type_id = int(m.group(3))
            if item_id not in items:
                items[item_id] = {"name_id": name_id, "type_id": type_id}
                count += 1

        if count == 0:
            alt_pattern = re.compile(r'id\s+(\d+)\s*,\s*nameId\s+(\d+)')
            for m in alt_pattern.finditer(content):
                item_id = int(m.group(1))
                name_id = int(m.group(2))
                if item_id not in items:
                    items[item_id] = {"name_id": name_id, "type_id": 0}
                    count += 1

        print(f"  -> {count} items extraits")

    return items

def main():
    print(f"Dossier de recherche: {DATA_DIR}")

    item_files = find_item_bundles(DATA_DIR)
    if not item_files:
        print(f"[ERREUR] Aucun fichier items trouvé dans: {DATA_DIR}")
        sys.exit(1)
    print(f"Fichiers items: {len(item_files)}")

    i18n_files = find_i18n_files(DATA_DIR)
    print(f"Fichiers i18n: {len(i18n_files)}")

    items = extract_items(item_files)
    print(f"Total items: {len(items)}")

    texts = {}
    if i18n_files:
        texts = load_i18n(i18n_files)
    else:
        print("[WARN] Aucun fichier i18n trouvé, colonne 'name' sera vide")

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "name_id", "name"])
        for item_id in sorted(items.keys()):
            data = items[item_id]
            name_id = data["name_id"]
            name = texts.get(name_id, "")
            writer.writerow([item_id, name_id, name])

    print(f"Sauvegardé: {OUTPUT}")

    named = sum(1 for item_id in items if texts.get(items[item_id]["name_id"]))
    print(f"Items avec nom: {named}/{len(items)}")

if __name__ == "__main__":
    main()
