# unity-achievement-analyzer

Extraction et analyse des achievements Dofus 3 depuis les Unity Asset Bundles.

## Repos liés

- [`dofus-data-extractor`](https://github.com/arthoine/dofus-data-extractor) — Parse le fichier `fr.bin` (332 038 textes FR)
- [`dofus-map-extractor`](https://github.com/arthoine/dofus-map-extractor) — Extraction des données de maps

## Pipeline complet

```
dofus-data-extractor/
  parse_fr.py  →  fr_texts.json (332k textes FR)

unity-achievement-analyzer/
  analyze_bundle.py  →  output/assets_final.json (données brutes des bundles)
  resolve_names.py   →  achievements_fr.json     (arbre résolu en français)
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Étape 1 — Générer fr_texts.json

```bash
# Dans le repo dofus-data-extractor
python parse_fr.py
# → génère fr_texts.json
```

### Étape 2 — Extraire les bundles

```bash
# Copier les bundles achievement dans data/
cp .../Content/Data/data_assets_achievement*.bundle data/

python analyze_bundle.py --bundle-dir data/ --output output/
# → génère output/assets_final.json
```

### Étape 3 — Résoudre les noms FR

```bash
python resolve_names.py \
  --texts  ../dofus-data-extractor/fr_texts.json \
  --assets output/assets_final.json \
  --output achievements_fr.json
```

### Options resolve_names.py

| Option | Défaut | Description |
|--------|--------|-------------|
| `--texts` | `../dofus-data-extractor/fr_texts.json` | Chemin vers fr_texts.json |
| `--assets` | `output/assets_final.json` | Chemin vers assets_final.json |
| `--output` | `achievements_fr.json` | Fichier de sortie |
| `--flat` | false | Sortie plate au lieu de l'arbre catégories→achievements |

## Sortie (arbre)

```json
[
  {
    "id": 1,
    "name": "Donjons",
    "order": 0,
    "achievements": [
      {
        "id": 74,
        "name": "Larve Royale",
        "description": "Terminer le donjon Larve Royale.",
        "points": 10,
        "objectives": [
          { "id": 101, "name": "Vaincre la Larve Royale", "order": 0 }
        ],
        "rewards": []
      }
    ]
  }
]
```

## Structure des fichiers sources

| Bundle | Contenu |
|--------|---------|
| `data_assets_achievementcategoriesdataroot.asset.bundle` | Catégories |
| `data_assets_achievementsdataroot.asset.bundle` | Achievements |
| `data_assets_achievementobjectivesdataroot.asset.bundle` | Objectifs |
| `data_assets_achievementrewardsdataroot.asset.bundle` | Récompenses |
