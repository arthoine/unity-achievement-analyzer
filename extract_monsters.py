"""
Extrait la liste des IDs de monstres depuis les bundles Unity Dofus.
Output: monsters.csv (monster_id)
"""
import re
import csv
import glob
import os
import sys

# Les JSON sont dans le même dossier que le script
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(DATA_DIR, "monsters.csv")

def find_monster_bundles(data_dir):
    patterns = [
        os.path.join(data_dir, "*monster*dataroot*.json"),
        os.path.join(data_dir, "*monsters*.json"),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p, recursive=True))
    return files

def extract_monster_ids(files):
    monster_ids = set()

    # Méthode 1: blocs MonsterData avec id
    id_pattern = re.compile(r'type class MonsterData.*?id\s+(\d+)', re.DOTALL)

    for filepath in files:
        print(f"Lecture: {os.path.basename(filepath)}")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        for match in id_pattern.finditer(content):
            monster_ids.add(int(match.group(1)))

        # Méthode 2: objectsById mkeys dans un MonsterDataRoot
        root_pattern = re.compile(
            r'mName\s+MonsterDataRoot.*?objectsById\s+mkeys\s+([\d,\s]+)',
            re.DOTALL
        )
        for match in root_pattern.finditer(content):
            keys_str = match.group(1)
            ids = re.findall(r'\d+', keys_str)
            for id_val in ids:
                monster_ids.add(int(id_val))

    return sorted(monster_ids)

def main():
    print(f"Dossier de recherche: {DATA_DIR}")
    files = find_monster_bundles(DATA_DIR)
    if not files:
        print(f"[ERREUR] Aucun fichier monstre trouvé dans: {DATA_DIR}")
        print("Patterns cherchés: *monster*dataroot*.json, *monsters*.json")
        # Lister les JSON disponibles pour aider au debug
        all_json = glob.glob(os.path.join(DATA_DIR, "*.json"))
        monster_like = [f for f in all_json if 'monster' in os.path.basename(f).lower()]
        if monster_like:
            print(f"Fichiers monster trouvés quand même: {monster_like}")
        else:
            print(f"JSON disponibles (10 premiers): {[os.path.basename(f) for f in all_json[:10]]}")
        sys.exit(1)

    print(f"Fichiers trouvés: {len(files)}")
    monster_ids = extract_monster_ids(files)
    print(f"Monstres extraits: {len(monster_ids)}")

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["monster_id"])
        for mid in monster_ids:
            writer.writerow([mid])

    print(f"Sauvegardé: {OUTPUT}")

if __name__ == "__main__":
    main()
