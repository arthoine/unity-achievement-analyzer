#!/usr/bin/env python3
"""
test.py - Parse et affiche les catégories d'achievements depuis un Asset Bundle Unity (Dofus)

Utilisation:
    python test.py --bundle chemin/vers/bundle.asset.bundle
    python test.py --bundle ... --json output.json
    python test.py --bundle ... --csv output.csv
    python test.py --bundle ... --raw
"""

import json
import sys
import argparse
from pathlib import Path

try:
    import UnityPy
except ImportError:
    print("[ERREUR] UnityPy n'est pas installé. Lance: pip install unitypy", file=sys.stderr)
    sys.exit(1)

# Version Unity de Dofus (détectée depuis globalgamemanagers)
UnityPy.config.FALLBACK_UNITY_VERSION = "6000.1.17f1"

DEFAULT_BUNDLE = "data_assets_achievementcategoriesdataroot.asset.bundle"


def parse_bundle(bundle_path: str) -> dict | None:
    """
    Ouvre un Asset Bundle Unity et extrait le MonoBehaviour AchievementCategoriesDataRoot.
    Utilise read_typetree() pour obtenir un dict Python natif.
    """
    env = UnityPy.load(bundle_path)

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if not tree:
            continue
        name = tree.get('m_Name', '')
        if 'AchievementCategoriesDataRoot' in str(name):
            return {
                "bundle": str(bundle_path),
                "path_id": obj.path_id,
                "type": obj.type.name,
                "name": name,
                "data": tree
            }

    return None


def extract_categories(raw_data: dict) -> list[dict]:
    """
    Extrait la liste des AchievementCategoryData depuis le typetree.

    Structure attendue dans references.RefIds:
        [{ 'rid': ..., 'type': { 'class': 'AchievementCategoryData', ... }, 'data': { ... } }, ...]
    """
    categories = []

    references = raw_data.get('references')
    if not references:
        print("[AVERTISSEMENT] Clé 'references' introuvable dans le typetree.", file=sys.stderr)
        return categories

    ref_ids = references.get('RefIds', [])
    if not ref_ids:
        print("[AVERTISSEMENT] 'references.RefIds' est vide ou absent.", file=sys.stderr)
        return categories

    for ref in ref_ids:
        ref_type = ref.get('type', {})
        if ref_type.get('class') != 'AchievementCategoryData':
            continue
        cat_data = ref.get('data', {})
        categories.append({
            'id':                  cat_data.get('id'),
            'nameId':              cat_data.get('nameId'),
            'parentId':            cat_data.get('parentId'),
            'icon':                cat_data.get('icon', ''),
            'order':               cat_data.get('order'),
            'color':               cat_data.get('color', ''),
            'achievementIds':      cat_data.get('achievementIds', []),
            'visibilityCriterion': cat_data.get('visibilityCriterion', ''),
            '_rid':                ref.get('rid'),
        })

    categories.sort(key=lambda c: c['id'] or 0)
    return categories


def build_tree(categories: list[dict]) -> list[dict]:
    by_id = {cat['id']: dict(cat, children=[]) for cat in categories}
    roots = []

    for cat in by_id.values():
        parent_id = cat['parentId']
        if parent_id == 0 or parent_id not in by_id:
            roots.append(cat)
        else:
            by_id[parent_id]['children'].append(cat)

    def sort_children(node):
        node['children'].sort(key=lambda c: c['order'] or 0)
        for child in node['children']:
            sort_children(child)

    roots.sort(key=lambda c: c['order'] or 0)
    for root in roots:
        sort_children(root)

    return roots


def print_tree(nodes: list[dict], indent: int = 0) -> None:
    prefix = '  ' * indent
    for node in nodes:
        nb = len(node['achievementIds'])
        color = f" [{node['color']}]" if node['color'] else ''
        icon = f" (icon: {node['icon']})" if node['icon'] else ''
        print(f"{prefix}[{node['id']}] nameId={node['nameId']}{color}{icon}  → {nb} achievement(s)")
        if node['children']:
            print_tree(node['children'], indent + 1)


def export_json(categories: list[dict], path: str) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON exporté → {path}")


def export_csv(categories: list[dict], path: str) -> None:
    import csv
    if not categories:
        print("[AVERTISSEMENT] Aucune catégorie à exporter.", file=sys.stderr)
        return
    fieldnames = ['id', 'nameId', 'parentId', 'icon', 'order', 'color',
                  'nb_achievements', 'achievementIds', 'visibilityCriterion', '_rid']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for cat in categories:
            row = dict(cat)
            row['nb_achievements'] = len(cat['achievementIds'])
            row['achievementIds'] = ','.join(str(i) for i in cat['achievementIds'])
            writer.writerow(row)
    print(f"[OK] CSV exporté → {path}")


def main():
    parser = argparse.ArgumentParser(
        description='Parse un Asset Bundle Unity Dofus pour extraire les AchievementCategories'
    )
    parser.add_argument('--bundle', '-b', default=DEFAULT_BUNDLE,
                        help=f'Chemin vers le .bundle (défaut: {DEFAULT_BUNDLE})')
    parser.add_argument('--unity-version', '-u', default=None,
                        help='Forcer une version Unity (défaut: 6000.1.17f1)')
    parser.add_argument('--json', '-j', metavar='OUTPUT_JSON',
                        help='Exporter les catégories en JSON')
    parser.add_argument('--csv', '-c', metavar='OUTPUT_CSV',
                        help='Exporter les catégories en CSV')
    parser.add_argument('--raw', '-r', action='store_true',
                        help='Afficher le JSON brut du typetree')
    parser.add_argument('--flat', '-f', action='store_true',
                        help="Afficher la liste plate au lieu de l'arbre")
    args = parser.parse_args()

    if args.unity_version:
        UnityPy.config.FALLBACK_UNITY_VERSION = args.unity_version

    bundle_path = Path(args.bundle)
    if not bundle_path.exists():
        print(f"[ERREUR] Bundle introuvable : {bundle_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[...] Chargement du bundle : {bundle_path}")
    print(f"[...] Unity version       : {UnityPy.config.FALLBACK_UNITY_VERSION}")

    raw = parse_bundle(str(bundle_path))
    if raw is None:
        print("[ERREUR] AchievementCategoriesDataRoot introuvable dans ce bundle.", file=sys.stderr)
        sys.exit(1)

    if args.raw:
        print(json.dumps(raw, indent=2, ensure_ascii=False, default=str))
        return

    categories = extract_categories(raw['data'])
    print(f"[OK] {len(categories)} catégorie(s) extraite(s)\n")

    if args.json:
        export_json(categories, args.json)

    if args.csv:
        export_csv(categories, args.csv)

    if not args.json and not args.csv:
        if args.flat:
            for cat in categories:
                nb = len(cat['achievementIds'])
                print(f"  id={cat['id']:>4}  nameId={cat['nameId']:>7}  parentId={cat['parentId']:>4}  "
                      f"order={cat['order']:>3}  achievements={nb:>4}  icon={cat['icon']:<12}  color={cat['color']}")
        else:
            tree = build_tree(categories)
            print("Arbre des catégories (id / nameId / nb achievements):")
            print('-' * 60)
            print_tree(tree)


if __name__ == '__main__':
    main()
