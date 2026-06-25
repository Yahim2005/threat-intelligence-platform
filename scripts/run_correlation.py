#!/usr/bin/env python3
"""
Applique les règles de corrélation sur la base existante.

Usage:
    python scripts/run_correlation.py --dry-run
    python scripts/run_correlation.py --rules resolves_to same_tag
    python scripts/run_correlation.py  # toutes les règles
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
from core.correlation import (
    rule_resolves_to,
    rule_same_tag,
    rule_same_source_batch,
    build_graph,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("run_correlation")

AVAILABLE_RULES = {
    "resolves_to":       rule_resolves_to,
    "same_tag":          rule_same_tag,
    "same_source_batch": rule_same_source_batch,
}


def run(rules: list[str], dry_run: bool) -> None:
    logger.info(
        "Démarrage corrélation | règles=%s | dry_run=%s",
        rules, dry_run,
    )

    session = SessionLocal()
    try:
        total_created = 0

        for rule_name in rules:
            rule_fn = AVAILABLE_RULES[rule_name]
            logger.info("Application de la règle : %s", rule_name)

            relations = rule_fn(session)
            total_created += len(relations)

            if dry_run:
                # Annuler sans persister
                session.rollback()
                logger.info(
                    "  [DRY-RUN] %s : %d relations auraient été créées",
                    rule_name, len(relations),
                )
                # Réafficher les 5 premières
                for rel in relations[:5]:
                    logger.info(
                        "    %s -[%s]-> %s (conf=%d, rule=%s)",
                        rel.source_ref[:8], rel.relationship_type.value,
                        rel.target_ref[:8], rel.confidence, rel.rule,
                    )
            else:
                session.commit()
                logger.info(
                    "  %s : %d relations créées et committées",
                    rule_name, len(relations),
                )

        if not dry_run:
            # Construire et afficher les stats du graphe
            logger.info("Construction du graphe de corrélation...")
            G = build_graph(session)
            logger.info(
                "Graphe final : %d noeuds | %d arêtes | %d composantes connexes",
                G.number_of_nodes(),
                G.number_of_edges(),
                __import__("networkx").number_connected_components(G),
            )

        logger.info("Terminé | total relations créées=%d", total_created)

    except Exception as exc:
        session.rollback()
        logger.error("Erreur : %s", exc)
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Corrélation des indicateurs")
    parser.add_argument(
        "--rules",
        nargs="+",
        choices=list(AVAILABLE_RULES.keys()),
        default=list(AVAILABLE_RULES.keys()),
        help="Règles à appliquer (défaut: toutes)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.rules, args.dry_run)


if __name__ == "__main__":
    main()