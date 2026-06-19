"""Collecteur Tor Exit Nodes : liste officielle des nœuds de sortie Tor.
Source : texte brut, une IP par ligne, sans auth, sans rate limit.
Pas malveillant en soi — tag de contexte pour signaler du trafic anonymisé.
"""
from datetime import datetime

import httpx

from core.normalize import detect_and_normalize
from collectors.base import BaseCollector
import logging

from core.tags import make_tag
logger = logging.getLogger(__name__)

TOR_EXIT_URL = "https://check.torproject.org/torbulkexitlist"


class TorExitCollector(BaseCollector):
    name = "Tor Project - Exit List"

    def fetch(self):
        response = self.http_get_with_retry(TOR_EXIT_URL)
        return response.text

    def parse(self, raw: str) -> list[dict]:
        records = []
        now = datetime.utcnow()
        for line in raw.splitlines():
            ip = line.strip()
            if not ip:
                continue
            normalized = detect_and_normalize(ip)
            if normalized is None:
                logger.warning(f"[Tor Project - Exit List] Type non détecté, ignoré : '{ip}'")
                continue
            value, ioc_type = normalized
            records.append({
                "value": value,
                "type": ioc_type,
                "seen_at": now,
                "metadata": {"source": "tor_exit"},
                "tag_names": [make_tag("source", "tor-exit")],
                "context": {},
            })
        return records


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    TorExitCollector().run()