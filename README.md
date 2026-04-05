# unity-achievement-analyzer

Extraction et mapping des données **Dofus 3** depuis les Unity Asset Bundles pour générer des fichiers exploitables, notamment :

- `output/items_named.csv`
- `output/monsters_named.csv`

## Prérequis

- Python 3.10+
- Windows
- Dofus 3 installé

Installe les dépendances :

```bash
pip install -r requirements.txt
```

## Où récupérer les fichiers Dofus

Les bundles Unity sont à récupérer ici :

```text
C:\Users\Antoine\AppData\Local\Ankama\Dofus-dofus3\Dofus_Data\StreamingAssets\Content
```

Dans ce repo, colle les fichiers nécessaires dans le dossier :

```text
input/
```

Tu peux copier directement les bundles utiles depuis le dossier Dofus vers `input/`.

## Fichiers à copier

### Pour les items

Copie dans `input/` :

```text
data_assets_itemsdataroot.asset.bundle
data_assets_itemtypesdataroot.asset.bundle
data_assets_itemsupertypesdataroot.asset.bundle
data_assets_itemsetsdataroot.asset.bundle
```

### Pour les monstres

Copie dans `input/` :

```text
data_assets_monstersdataroot.asset.bundle
data_assets_monsterracesdataroot.asset.bundle
data_assets_monstersuperracesdataroot.asset.bundle
data_assets_monsterminibossesdataroot.asset.bundle
```

### Pour les textes FR

Le script lit aussi les textes français depuis le fichier `fr.bin` de Dofus.

Chemin habituel :

```text
C:\Users\Antoine\AppData\Local\Ankama\Dofus-dofus3\Dofus_Data\StreamingAssets\Content\I18n\fr.bin
```

## Pipeline complet

### 1. Générer `fr_texts.json`

```bash
python parse_fr.py --input "C:\Users\Antoine\AppData\Local\Ankama\Dofus-dofus3\Dofus_Data\StreamingAssets\Content\I18n\fr.bin" --output fr_texts.json
```

### 2. Extraire les bundles Unity en JSON

```bash
python analyze_bundle.py --bundle-dir input/ --output output/
```

Cette commande génère notamment :

- `output/assets_final.json`
- des fichiers JSON individuels dans `output/`

### 3. Générer le CSV des items

```bash
python map_items.py --texts fr_texts.json --assets output/assets_final.json --csv
```

Sorties générées :

- `output/items_named.json`
- `output/itemtypes_named.json`
- `output/itemsets_named.json`
- `output/items_named.csv`

### 4. Générer le CSV des monstres

```bash
python map_monsters.py --texts fr_texts.json --assets output/assets_final.json --csv
```

Sorties générées :

- `output/monsters_named.json`
- `output/monsterraces_named.json`
- `output/monsters_named.csv`

## Commandes minimales à lancer

Si tu veux juste produire les 2 CSVs :

```bash
python parse_fr.py --input "C:\Users\Antoine\AppData\Local\Ankama\Dofus-dofus3\Dofus_Data\StreamingAssets\Content\I18n\fr.bin" --output fr_texts.json
python analyze_bundle.py --bundle-dir input/ --output output/
python map_items.py --texts fr_texts.json --assets output/assets_final.json --csv
python map_monsters.py --texts fr_texts.json --assets output/assets_final.json --csv
```

## Résultat final

À la fin, tu obtiens :

```text
output/items_named.csv
output/monsters_named.csv
```

## Scripts utiles

| Script | Rôle |
|---|---|
| `parse_fr.py` | Parse `fr.bin` en `fr_texts.json` |
| `analyze_bundle.py` | Extrait les bundles Unity vers `output/` |
| `map_items.py` | Construit les données items et exporte `items_named.csv` |
| `map_monsters.py` | Construit les données monstres et exporte `monsters_named.csv` |

## Notes

- Le dossier source Dofus contient beaucoup de bundles, mais seuls ceux listés plus haut sont nécessaires pour générer les CSVs items et monstres.
- Les anciens tests, essais et docs peuvent être déplacés dans `old/` pour garder le repo propre.
