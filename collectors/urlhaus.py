"""Collecteur URLhaus (abuse.ch).

Responsabilités de ce fichier :
  - fetch()  : télécharger le ZIP et décompresser le CSV
  - parse()  : traduire le format CSV URLhaus en records standards

Tout le reste (persistance, logging, stats) est géré par BaseCollector.
"""
import csv
import io
import logging
import zipfile
from datetime import datetime

import httpx

#from app.models.enums import IOCType
from core.normalize import detect_and_normalize
from collectors.base import BaseCollector
from core.tags import make_tag

logger = logging.getLogger(__name__)

URLHAUS_CSV_URL = "https://urlhaus.abuse.ch/downloads/csv/"
URLHAUS_FIELDNAMES = [
    "id", "dateadded", "url", "url_status",
    "last_online", "threat", "tags", "urlhaus_link", "reporter",
]


class URLhausCollector(BaseCollector):

    name = "abuse.ch - URLhaus"  # doit correspondre exactement à Source.name en base

    def fetch(self) -> str:
        """Télécharge le ZIP URLhaus, décompresse en mémoire, retourne le CSV brut."""
        with httpx.Client(timeout=30) as client:
            response = client.get(URLHAUS_CSV_URL)
            response.raise_for_status()
            zip_bytes = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_bytes) as zf:
                csv_filename = zf.namelist()[0]
                return zf.read(csv_filename).decode("utf-8")

    def parse(self, raw: str) -> list[dict]:
        """Traduit le CSV URLhaus en liste de records standards.

        C'est le seul endroit du projet qui connaît le vocabulaire URLhaus
        (noms de colonnes, format de date, champ 'threat'…).
        """
        data_lines = [
            line for line in raw.splitlines()
            if not line.startswith("#") and line.strip()
        ]
        if not data_lines:
            return []

        records = []
        reader = csv.DictReader(data_lines, fieldnames=URLHAUS_FIELDNAMES)

        for row in reader:
            value = row.get("url", "").strip()
            if not value:
                continue

            # Traduction du format de date URLhaus → datetime Python
            try:
                seen_at = datetime.strptime(
                    row.get("dateadded", "").strip(), "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                seen_at = datetime.utcnow()

            threat = row.get("threat", "").strip()
            normalized = detect_and_normalize(value)
            if normalized is None:
                logger.warning(f"[abuse.ch - URLhaus] Type non détecté, ignoré : '{value}'")
                continue
            value, ioc_type = normalized
            records.append({
                "value":   value,
                "type":    ioc_type,
                "seen_at": seen_at,
                "metadata": {"threat": threat, "source": "urlhaus"} if threat
                            else {"source": "urlhaus"},
                "tag_names": [make_tag("kind", threat)] if threat else [],
                "context": {
                    "urlhaus_id": row.get("id"),
                    "url_status": row.get("url_status"),
                    "reporter":   row.get("reporter"),
                },
            })

        return records


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    URLhausCollector().run() 