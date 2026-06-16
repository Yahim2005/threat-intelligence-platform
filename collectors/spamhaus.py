"""Collecteur Spamhaus DROP.

Source : https://www.spamhaus.org/drop/drop.txt
IOCs   : plages IP (CIDR) appartenant à des réseaux cybercriminels
Auth   : aucune (liste publique)
Note Admiralty : A1 — référence absolue anti-spam/cybercrime depuis 1998
"""
import logging
from datetime import datetime

import httpx

from app.models.enums import IOCType
from collectors.base import BaseCollector

logger = logging.getLogger(__name__)

SPAMHAUS_DROP_URL = "https://www.spamhaus.org/drop/drop.txt"


class SpamhausDropCollector(BaseCollector):

    name = "Spamhaus - DROP"

    def fetch(self) -> str:
        """Télécharge la liste DROP en texte brut."""
        with httpx.Client(timeout=30) as client:
            response = client.get(SPAMHAUS_DROP_URL)
            response.raise_for_status()
            return response.text

    def parse(self, raw: str) -> list[dict]:
        """Traduit la liste DROP en records standards.

        Format d'une ligne de données : "1.2.3.0/24 ; SBL12345"
        Lignes commençant par ';' → commentaires, ignorées.
        Pas de date par entrée → seen_at = maintenant (date de collecte).
        """
        records = []

        for line in raw.splitlines():
            line = line.strip()

            # Commentaires et lignes vides
            if not line or line.startswith(";"):
                continue

            # "1.10.16.0/20 ; SBL256704" → cidr="1.10.16.0/20", ref="SBL256704"
            parts = line.split(";")
            cidr = parts[0].strip()
            sbl_ref = parts[1].strip() if len(parts) > 1 else None

            if not cidr:
                continue

            records.append({
                "value":   cidr,
                "type":    IOCType.cidr,
                "seen_at": datetime.utcnow(),
                "metadata": {
                    "source": "spamhaus_drop",
                },
                "tag_names": [],
                "context": {
                    "sbl_reference": sbl_ref,
                },
            })

        return records


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    SpamhausDropCollector().run()