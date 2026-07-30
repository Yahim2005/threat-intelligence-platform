#!/usr/bin/env python3
"""
Envoie le digest IOC Cameroun aux destinataires actifs (email_recipients),
tous les 3 jours (voir core.email_digest.should_send_now -- le workflow
GitHub tourne quotidiennement, c'est cette fonction qui garantit l'espacement
réel de 3 jours plutôt qu'un cron */3 approximatif sur le jour du mois).

Usage:
    python scripts/send_email_digest.py --dry-run   # génère le HTML, n'envoie rien, n'écrit pas email_digest_log
    python scripts/send_email_digest.py --force      # ignore le délai de 3 jours (tests)
    python scripts/send_email_digest.py              # envoi réel normal
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
from core.email_digest import (
    MIN_DAYS_BETWEEN_SENDS,
    build_digest_html,
    get_active_recipients,
    get_digest_indicators,
    log_successful_send,
    send_digest_email,
    should_send_now,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("send_email_digest")


def run(dry_run: bool, force: bool, output: str) -> None:
    session = SessionLocal()
    try:
        if not force and not should_send_now(session):
            logger.info(
                "Moins de %d jours depuis le dernier envoi réussi -- rien à faire aujourd'hui.",
                MIN_DAYS_BETWEEN_SENDS,
            )
            return

        indicators = get_digest_indicators(session)
        html_body = build_digest_html(indicators)
        recipients = get_active_recipients(session)

        if dry_run:
            Path(output).write_text(html_body, encoding="utf-8")
            logger.info(
                "[DRY-RUN] %d IOC(s), %d destinataire(s) actif(s) -- aperçu écrit dans %s "
                "(aucun email envoyé, email_digest_log non modifié)",
                len(indicators), len(recipients), output,
            )
            return

        if not recipients:
            logger.warning("Aucun destinataire actif -- aucun email envoyé.")
            return

        send_digest_email([r.email for r in recipients], html_body)
        log_successful_send(session, recipient_count=len(recipients), ioc_count=len(indicators))
        logger.info(
            "Digest envoyé à %d destinataire(s), %d IOC(s).",
            len(recipients), len(indicators),
        )

    except Exception as exc:
        session.rollback()
        logger.error("Erreur : %s", exc)
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Digest IOC Cameroun par email")
    parser.add_argument("--dry-run", action="store_true", help="Génère le HTML sans envoyer ni logger")
    parser.add_argument("--force", action="store_true", help="Ignore le délai de 3 jours entre deux envois")
    parser.add_argument("--output", default="digest_preview.html", help="Fichier de sortie en --dry-run")
    args = parser.parse_args()
    run(args.dry_run, args.force, args.output)


if __name__ == "__main__":
    main()
