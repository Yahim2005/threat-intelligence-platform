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
        # extract_clusters() commit/rollback en interne selon dry_run --
        # ne pas re-committer/rollback ici en double.
        results = extract_clusters(session, dry_run=dry_run)

        prefix = "[DRY-RUN] " if dry_run else ""
        logger.info("%s%d clusters-institution créés/mis à jour", prefix, len(results))
        for r in results[:10]:
            logger.info(
                "  %s%s | %d indicateurs | mécanismes=%s | %d IP(s) exposée(s)",
                prefix, r["name"], r["indicator_count"],
                r["mechanism_counts"], r["exposed_ip_count"],
            )
        if len(results) > 10:
            logger.info("  ... et %d autres", len(results) - 10)

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