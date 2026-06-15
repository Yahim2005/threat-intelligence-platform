"""Collecteur ThreatFox (abuse.ch).

Source : https://threatfox-api.abuse.ch/api/v1/
IOCs   : types variés (IP, domaine, URL, hash) avec contexte malware
Auth   : ABUSECH_AUTH_KEY dans .env (même clé que URLhaus)
"""
import logging
import os
from datetime import datetime

import httpx
from dotenv import load_dotenv

from app.models.enums import IOCType
from collectors.base import BaseCollector

load_dotenv()
logger = logging.getLogger(__name__)

THREATFOX_URL = "https://threatfox-api.abuse.ch/api/v1/"

# Mapping ThreatFox → nos IOCType.
# Les types absents (ex: "cve") seront ignorés silencieusement.
IOC_TYPE_MAP = {
    "ip:port":    IOCType.ip,
    "domain":     IOCType.domain,
    "url":        IOCType.url,
    "md5_hash":   IOCType.md5,
    "sha256_hash": IOCType.sha256,
    "sha1_hash":  IOCType.sha1,
}


class ThreatFoxCollector(BaseCollector):

    name = "abuse.ch - ThreatFox"

    def fetch(self) -> dict:
        """POST à l'API ThreatFox — IOCs des dernières 24h."""
        auth_key = os.environ.get("ABUSECH_AUTH_KEY", "")
        if not auth_key:
            raise ValueError("ABUSECH_AUTH_KEY manquant dans .env")

        with httpx.Client(timeout=30) as client:
            response = client.post(
                THREATFOX_URL,
                headers={"Auth-Key": auth_key},
                json={"query": "get_iocs", "days": 1},
            )
            response.raise_for_status()
            return response.json()

    def parse(self, raw: dict) -> list[dict]:
        """Traduit les IOCs ThreatFox en records standards.

        Particularités :
        - Types mixtes → mapping via IOC_TYPE_MAP
        - ip:port → on extrait l'IP, le port va en contexte
        - Types non supportés (cve…) → ignorés avec compteur
        """
        data = raw.get("data") or []
        records = []
        skipped = 0

        for entry in data:
            ioc_type_str = entry.get("ioc_type", "")

            # Type non supporté → on ignore
            if ioc_type_str not in IOC_TYPE_MAP:
                skipped += 1
                continue

            ioc_type = IOC_TYPE_MAP[ioc_type_str]
            raw_ioc = entry.get("ioc", "").strip()

            # "185.220.101.47:443" → value="185.220.101.47", port="443"
            if ioc_type_str == "ip:port" and ":" in raw_ioc:
                value, port = raw_ioc.rsplit(":", 1)
            else:
                value, port = raw_ioc, None

            if not value:
                continue

            # Format date ThreatFox : "2024-06-01 08:00:00 UTC"
            date_str = entry.get("first_seen", "").strip()
            try:
                seen_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
            except ValueError:
                seen_at = datetime.utcnow()

            records.append({
                "value":   value,
                "type":    ioc_type,
                "seen_at": seen_at,
                "tags": {
                    "malware":     entry.get("malware_printable", "").strip(),
                    "threat_type": entry.get("threat_type", "").strip(),
                    "source":      "threatfox",
                },
                "context": {
                    "threatfox_id": entry.get("id"),
                    "ioc_type":     ioc_type_str,
                    "port":         port,
                    "confidence":   entry.get("confidence_level"),
                    "reporter":     entry.get("reporter"),
                    "reference":    entry.get("reference"),
                },
            })

        if skipped:
            logger.debug(f"{skipped} entrée(s) ignorée(s) — type non supporté")

        return records


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    ThreatFoxCollector().run()