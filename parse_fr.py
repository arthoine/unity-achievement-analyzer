#!/usr/bin/env python3
"""
parse_fr.py — Parser du fichier I18n/fr.bin de Dofus 3
=======================================================
Extrait tous les textes FR depuis le fichier binaire Ankama et les exporte
en JSON {str(id) -> texte} utilisable par resolve_names.py.

Format du fichier :
    \\x02 + lang (2 bytes) + uint32 LE (nb entrées)
    Index : [id uint32 LE][offset uint32 LE] x N
    Strings : préfixées par un varint LEB128 (longueur en bytes UTF-8)

Usage:
    python parse_fr.py
    python parse_fr.py --input "C:\\...\\fr.bin" --output fr_texts.json

Chemin par défaut (installation Dofus standard Windows) :
    %LOCALAPPDATA%\\Ankama\\Dofus-dofus3\\Dofus_Data\\StreamingAssets\\Content\\I18n\\fr.bin
"""

import struct
import json
import argparse
import os
import sys
from pathlib import Path

DEFAULT_FR_BIN = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Ankama", "Dofus-dofus3", "Dofus_Data",
    "StreamingAssets", "Content", "I18n", "fr.bin"
)
DEFAULT_OUTPUT = "fr_texts.json"


def read_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Lit un entier LEB128 unsigned. Retourne (valeur, nouvelle_position)."""
    result, shift = 0, 0
    while True:
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, pos


def read_string(data: bytes, offset: int) -> str:
    """Lit une string UTF-8 préfixée par un varint (longueur en bytes)."""
    length, pos = read_varint(data, offset)
    return data[pos:pos + length].decode("utf-8", errors="replace")


def parse_fr_bin(path: str) -> dict[int, str]:
    """
    Parse le fichier fr.bin et retourne un dict {id: texte}.
    """
    with open(path, "rb") as f:
        data = f.read()

    # Header
    magic = data[0]          # 0x02
    lang  = data[1:3].decode("ascii")
    total = struct.unpack_from("<I", data, 3)[0]

    print(f"[...] Fichier   : {path}")
    print(f"[...] Langue    : {lang}")
    print(f"[...] Entrées   : {total:,}")

    # Index
    print("[...] Chargement de l'index...")
    index: dict[int, int] = {}
    pos = 7
    for _ in range(total):
        if pos + 8 > len(data):
            break
        entry_id = struct.unpack_from("<I", data, pos)[0]
        offset   = struct.unpack_from("<I", data, pos + 4)[0]
        index[entry_id] = offset
        pos += 8

    print(f"[OK] Index : {len(index):,} entrées (IDs {min(index):,} → {max(index):,})")

    # Lecture des textes
    print("[...] Lecture des textes...")
    texts: dict[int, str] = {}
    errors = 0
    for entry_id, offset in index.items():
        try:
            texts[entry_id] = read_string(data, offset)
        except Exception:
            errors += 1

    print(f"[OK] {len(texts):,} textes lus", end="")
    if errors:
        print(f", {errors} erreurs ignorées")
    else:
        print()

    return texts


def main():
    parser = argparse.ArgumentParser(
        description="Parse fr.bin de Dofus 3 et exporte les textes en JSON"
    )
    parser.add_argument(
        "--input", "-i",
        default=DEFAULT_FR_BIN,
        help=f"Chemin vers fr.bin (défaut: %LOCALAPPDATA%\\Ankama\\...\\fr.bin)"
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT,
        help=f"Fichier JSON de sortie (défaut: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--preview", "-p",
        action="store_true",
        help="Afficher un aperçu des nameIds des catégories d'achievements"
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[ERREUR] fr.bin introuvable : {args.input}", file=sys.stderr)
        print("  → Vérifie le chemin ou utilise --input pour le spécifier.", file=sys.stderr)
        sys.exit(1)

    texts = parse_fr_bin(args.input)

    # Export JSON (clés en string pour compatibilité JSON standard)
    print(f"[...] Export → {args.output}")
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in texts.items()}, f, ensure_ascii=False, indent=2)
    print(f"[OK] Exporté → {args.output}")

    if args.preview:
        # Exemples avec les nameIds des catégories achievements connus
        examples = [272244, 272245, 272246, 272247, 272248, 272249, 272256, 272268]
        print("\n--- Aperçu nameIds catégories achievements ---")
        for nid in examples:
            print(f"  [{nid:>7}] = {texts.get(nid, 'NOT FOUND')!r}")


if __name__ == "__main__":
    main()
