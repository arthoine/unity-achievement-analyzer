# unity-achievement-analyzer

Extraction et analyse des achievements Dofus 3 depuis les Unity Asset Bundles.

> `parse_fr.py` est désormais intégré directement dans ce repo — plus besoin de `dofus-data-extractor`.

## Scripts

| Script | Rôle |
|--------|------|
| `parse_fr.py` | Parse `fr.bin` → `fr_texts.json` (332k textes FR) |
| `analyze_bundle.py` | Parcourt les `.bundle` → `output/assets_final.json` |
| `resolve_names.py` | Résout les nameId → `achievements_fr.json` (arbre FR) |
| `test.py` | Debug / exploration d'un bundle unique |

## Installation

```bash
pip install -r requirements.txt
```

## Pipeline complet

### Étape 1 — Générer fr_texts.json

```bash
# Chemin auto-détecté (installation Dofus standard Windows)
python parse_fr.py

# Ou avec un chemin custom
python parse_fr.py --input "C:\...\I18n\fr.bin" --output fr_texts.json

# Avec aperçu des nameIds catégories achievements
python parse_fr.py --preview
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
  --texts  fr_texts.json \
  --assets output/assets_final.json \
  --output achievements_fr.json
```

### Options

**`parse_fr.py`**

| Option | Défaut | Description |
|--------|--------|-------------|
| `--input` | `%LOCALAPPDATA%\Ankama\...\fr.bin` | Chemin vers fr.bin |
| `--output` | `fr_texts.json` | Fichier JSON de sortie |
| `--preview` | false | Affiche un aperçu des nameIds achievements |

**`resolve_names.py`**

| Option | Défaut | Description |
|--------|--------|-------------|
| `--texts` | `fr_texts.json` | Chemin vers fr_texts.json |
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

## Bundles sources

| Bundle | Contenu |
|--------|---------|
| `data_assets_achievementcategoriesdataroot.asset.bundle` | Catégories |
| `data_assets_achievementsdataroot.asset.bundle` | Achievements |
| `data_assets_achievementobjectivesdataroot.asset.bundle` | Objectifs |
| `data_assets_achievementrewardsdataroot.asset.bundle` | Récompenses |
