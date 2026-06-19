"""Collecteur Feodo Tracker (abuse.ch).

Source : https://feodotracker.abuse.ch/downloads/ipblocklist.json
IOCs   : adresses IP de serveurs Command & Control (botnets bancaires)
Auth   : aucune (feed public JSON)
"""
import json
import logging
from datetime import datetime
import httpx 

from core.normalize import detect_and_normalize
from collectors.base import BaseCollector

import logging

from core.tags import make_tag
logger = logging.getLogger(__name__)



FEODO_URL = "https://feodotracker.abuse.ch/downloads/ipblocklist.json"


class FeodoCollector(BaseCollector):

    name = "abuse.ch - Feodo"

    def fetch(self) -> dict:
        """Télécharge le JSON Feodo et le retourne parsé."""
        with httpx.Client(timeout=30) as client:
            response = client.get(FEODO_URL)
            response.raise_for_status()
            return response.json()

    def parse(self, raw) -> list[dict]:
        """Traduit la blocklist Feodo en records standards.
        L'API retourne une liste JSON à la racine, pas un objet enveloppant.
        """
        # raw est directement une liste d'entrées
        entries = raw if isinstance(raw, list) else raw.get("blocklist", [])
        records = []

        for entry in entries:
            ip = entry.get("ip_address", "").strip()
            if not ip:
                continue

            date_str = entry.get("first_seen", "").strip()
            try:
                seen_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
            except ValueError:
                seen_at = datetime.utcnow()

            malware = entry.get("malware", "").strip()
            normalized = detect_and_normalize(ip)
            if normalized is None:
                logger.warning(f"[abuse.ch - Feodo] Type non détecté, ignoré : '{ip}'")
                continue
            value, ioc_type = normalized
            records.append({
                "value":   value,
                "type":    ioc_type,
                "seen_at": seen_at,
                "metadata": {
                    "malware": malware,
                    "source":  "feodo",
                } if malware else {"source": "feodo"},
                "tag_names": [make_tag("malware", malware)] if malware else [],
                "context": {
                    "port":    entry.get("port"),
                    "status":  entry.get("status"),
                    "country": entry.get("country"),
                    "as_name": entry.get("as_name"),
                },
            })

        return records


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    FeodoCollector().run()