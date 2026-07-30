#!/usr/bin/env python3
"""
Supprime les Threat générées par l'ancien mécanisme de clustering
(co-occurrence par tag malware:*, source de collecte ou "Unknown Cluster").

Ces artefacts n'ont plus de sens depuis le passage au clustering par
institution ciblée (core/clustering.py) : ils sont supprimés (avec leurs
lignes threat_indicators) plutôt que laissés comme statut mort en base.

À exécuter une seule fois, avant le premier run de la nouvelle
extract_clusters(). Usage :
    python scripts/cleanup_legacy_threats.py --dry-run
    python scripts/cleanup_legacy_threats.py
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.threat import Threat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("cleanup_legacy_threats")


def run(dry_run: bool) -> None:
    session = SessionLocal()
    try:
        threats = session.query(Threat).all()
        logger.info("%d Threat(s) trouvée(s) en base", len(threats))

        for t in threats[:20]:
            logger.info("  %s | type=%s | %d IOC(s)", t.name, t.threat_type.value, len(t.indicators))
        if len(threats) > 20:
            logger.info("  ... et %d autres", len(threats) - 20)

        if dry_run:
            logger.info("[DRY-RUN] %d Threat(s) seraient supprimées (rien n'a été modifié)", len(threats))
            return

        count = len(threats)
        for t in threats:
            session.delete(t)  # cascade sur threat_indicators (ondelete=CASCADE)
        session.commit()
        logger.info("%d Threat(s) supprimée(s)", count)

    except Exception as exc:
        session.rollback()
        logger.error("Erreur : %s", exc)
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Nettoyage des Threat de l'ancien mécanisme")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.dry_run)


if __name__ == "__main__":
    main()
