# 🎮 Unity Achievement Categories Analyzer

Analyse d'Asset Bundle Unity contenant les **catégories d'achievements** d'un jeu (extrait d'APK/build Unity).

## 📁 Fichiers fournis
- `data/data_assets_achievementcategoriesdataroot.asset.bundle` (5 Ko) : Asset Bundle des catégories d'achievements
- `data/catalog_1.0-2.bin` (97 Ko) : Catalogue binaire Unity
- `data/catalog_1.0-3.hash` (32 bytes) : Hash de vérification

## 🚀 Installation

```bash
pip install -r requirements.txt
```

## 🔍 Utilisation

### 1. Extraire le contenu de l'Asset Bundle
```bash
python analyze_bundle.py
```

Le script génère un fichier `output/achievements.json` avec tous les objets extraits.

### 2. Analyser avec Ollama
```bash
ollama run llama3.2 "Analyse ces données d'achievements Unity : $(cat output/achievements.json | head -c 2000)"
```

## 📊 Script d'analyse

Le script `analyze_bundle.py` :
- Charge l'Asset Bundle Unity
- Extrait tous les objets (ScriptableObjects, textures, etc.)
- Sauvegarde le résultat en JSON lisible par un LLM

## 🛠 Dépendances
- [UnityPy](https://github.com/K0lb3/UnityPy) — Lecture des Asset Bundles Unity en Python

## 🔗 Contexte
Fichiers extraits d'un jeu Unity. L'Asset Bundle contient des ScriptableObjects définissant les catégories de succès.

---
*Antoine · Lyon · 2026*
