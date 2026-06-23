#!/usr/bin/env python3
"""
Parse le dataset ATT&CK Enterprise (STIX) et produit un index JSON léger.

Usage:
    python scripts/load_attack.py

Produit : data/attack/techniques.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Chemins
ROOT = Path(__file__).resolve().parent.parent
STIX_PATH = ROOT / "data" / "attack" / "enterprise-attack.json"
OUTPUT_PATH = ROOT / "data" / "attack" / "techniques.json"


def extract_tactic_names(objects: list[dict]) -> dict[str, str]:
    """
    Construit un mapping phase_name → tactic display name.
    Ex: "initial-access" → "Initial Access"
    Les x-mitre-tactic ont un champ 'x_mitre_shortname' qui correspond
    aux phase_name des kill_chain_phases des techniques.
    """
    tactics = {}
    for obj in objects:
        if obj.get("type") == "x-mitre-tactic":
            shortname = obj.get("x_mitre_shortname", "")
            name = obj.get("name", "")
            if shortname and name:
                tactics[shortname] = name
    return tactics


def extract_techniques(objects: list[dict], tactics: dict[str, str]) -> list[dict]:
    """
    Extrait les techniques ATT&CK depuis les objets STIX attack-pattern.
    Filtre les sous-techniques (T1566.001) si on veut uniquement les techniques parentes,
    mais on les inclut ici pour le mapping fin.
    Ignore les techniques dépréciées ou révoquées.
    """
    techniques = []

    for obj in objects:
        if obj.get("type") != "attack-pattern":
            continue

        # Ignorer les techniques dépréciées ou révoquées
        if obj.get("x_mitre_deprecated") or obj.get("revoked"):
            continue

        # Extraire l'ID ATT&CK (ex: T1566, T1566.001)
        technique_id = None
        for ref in obj.get("external_references", []):
            if ref.get("source_name") == "mitre-attack":
                technique_id = ref.get("external_id")
                break

        if not technique_id:
            continue

        # Extraire la/les tactique(s) — une technique peut appartenir à plusieurs
        technique_tactics = []
        for phase in obj.get("kill_chain_phases", []):
            if phase.get("kill_chain_name") == "mitre-attack":
                phase_name = phase.get("phase_name", "")
                technique_tactics.append(phase_name)

        # Description courte (première phrase uniquement pour l'index)
        description = obj.get("description", "")
        short_desc = description.split("\n")[0][:200] if description else ""

        name = obj.get("name", "")

        techniques.append({
            "technique_id": technique_id,
            "name": name,
            "tactics": technique_tactics,           # liste de phase_names
            "tactic_names": [                       # noms affichables
                tactics.get(t, t) for t in technique_tactics
            ],
            "is_subtechnique": "." in technique_id, # T1566.001 → True
            "description": short_desc,
        })

    # Trier par technique_id pour la lisibilité
    techniques.sort(key=lambda x: x["technique_id"])
    return techniques


def extract_malware_techniques(objects: list[dict]) -> dict[str, list[str]]:
    """
    Construit un mapping malware_name_lower → [technique_ids].
    Utilise les relationships STIX : malware --uses--> attack-pattern.
    Utile pour le mapping heuristique basé sur les tags malware:*.
    """
    # Index id → name pour les malwares
    malware_by_id: dict[str, str] = {}
    for obj in objects:
        if obj.get("type") == "malware":
            malware_by_id[obj["id"]] = obj.get("name", "").lower()

    # Index id → technique_id pour les attack-patterns
    technique_by_id: dict[str, str] = {}
    for obj in objects:
        if obj.get("type") == "attack-pattern":
            for ref in obj.get("external_references", []):
                if ref.get("source_name") == "mitre-attack":
                    technique_by_id[obj["id"]] = ref.get("external_id", "")
                    break

    # Parcourir les relationships uses
    malware_techniques: dict[str, list[str]] = {}
    for obj in objects:
        if obj.get("type") != "relationship":
            continue
        if obj.get("relationship_type") != "uses":
            continue

        source_ref = obj.get("source_ref", "")
        target_ref = obj.get("target_ref", "")

        if source_ref in malware_by_id and target_ref in technique_by_id:
            malware_name = malware_by_id[source_ref]
            technique_id = technique_by_id[target_ref]
            if malware_name not in malware_techniques:
                malware_techniques[malware_name] = []
            if technique_id not in malware_techniques[malware_name]:
                malware_techniques[malware_name].append(technique_id)

    return malware_techniques


def main() -> None:
    print(f"Lecture de {STIX_PATH}...")
    with open(STIX_PATH, encoding="utf-8") as f:
        data = json.load(f)

    objects = data.get("objects", [])
    print(f"{len(objects)} objets STIX chargés")

    tactics = extract_tactic_names(objects)
    print(f"{len(tactics)} tactiques extraites : {', '.join(tactics.keys())}")

    techniques = extract_techniques(objects, tactics)
    print(f"{len(techniques)} techniques extraites (dont sous-techniques)")

    malware_techniques = extract_malware_techniques(objects)
    print(f"{len(malware_techniques)} malwares avec techniques associées")

    output = {
        "tactics": tactics,
        "techniques": techniques,
        "malware_techniques": malware_techniques,
    }

    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\nIndex écrit dans {OUTPUT_PATH}")
    print(f"Taille : {OUTPUT_PATH.stat().st_size / 1024:.0f} KB")

    # Aperçu
    print("\nExemple de techniques :")
    for t in techniques[:5]:
        print(f"  {t['technique_id']} | {t['name']} | {t['tactics']}")


if __name__ == "__main__":
    main()