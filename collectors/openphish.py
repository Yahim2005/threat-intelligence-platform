"""Collecteur OpenPhish.

Source : https://openphish.com/feed.txt
IOCs   : URLs de phishing actives (durée de vie courte — quelques heures/jours)
Auth   : aucune (feed public)

Particularité métier : les URLs de phishing ont une durée de vie très courte.
Ce feed sera important pour le mécanisme de "decay" (J10) — un IOC qui disparaît
du feed plusieurs runs de suite passe automatiquement en statut inactif.
"""
import logging
from datetime import datetime

import httpx

from app.models.enums import IOCType
from collectors.base import BaseCollector

logger = logging.getLogger(__name__)

OPENPHISH_URL = "https://raw.githubusercontent.com/openphish/public_feed/refs/heads/main/feed.txt"


class OpenPhishCollector(BaseCollector):

    name = "OpenPhish"

    def fetch(self) -> str:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(OPENPHISH_URL)
            response.raise_for_status()
            return response.text

    def parse(self, raw: str) -> list[dict]:
        """Traduit le feed OpenPhish en records standards.

        Format : une URL par ligne, pas de métadonnées.
        Pas de date individuelle → seen_at = maintenant (date de collecte).
        """
        records = []

        for line in raw.splitlines():
            url = line.strip()
            if not url or not url.startswith("http"):
                continue

            records.append({
                "value":   url,
                "type":    IOCType.url,
                "seen_at": datetime.utcnow(),
                "metadata": {
                    "threat_type": "phishing",
                    "source":      "openphish",
                },
                "tag_names": [],
                "context": {},
            })

        return records


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    OpenPhishCollector().run()