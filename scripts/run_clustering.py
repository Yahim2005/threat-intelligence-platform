#!/usr/bin/env python3
"""
Extrait les clusters d'indicateurs corrélés et crée les entités Threat.

Usage:
    python scripts/run_clustering.py --dry-run
    python scripts/run_clustering.py
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
from core.clustering import extract_clusters

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("run_clustering")


def run(dry_run: bool) -> None:
    logger.info("Démarrage clustering | dry_run=%s", dry_run)

    session = SessionLocal()
    try:
        results = extract_clusters(session)

        if dry_run:
            session.rollback()
            logger.info("[DRY-RUN] %d clusters auraient été créés", len(results))
            for r in results[:10]:
                logger.info(
                    "  [DRY-RUN] %s | type=%s | %d indicateurs",
                    r["name"], r["threat_type"], r["indicator_count"],
                )
            if len(results) > 10:
                logger.info("  ... et %d autres", len(results) - 10)
        else:
            logger.info(
                "Terminé | %d Threats créées/mises à jour",
                len(results),
            )
            for r in results[:10]:
                logger.info(
                    "  %s | type=%s | %d indicateurs",
                    r["name"], r["threat_type"], r["indicator_count"],
                )

    except Exception as exc:
        session.rollback()
        logger.error("Erreur : %s", exc)
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Clustering des indicateurs en Threats")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.dry_run)


if __name__ == "__main__":
    main()