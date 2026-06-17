"""Collecteur CISA KEV : catalogue des vulnérabilités activement exploitées.
Source : JSON statique, sans auth, sans rate limit, mis à jour quotidiennement.
"""
from datetime import datetime

import httpx

from app.models.enums import IOCType
from collectors.base import BaseCollector

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


class CisaKevCollector(BaseCollector):
    name = "CISA KEV"

    def fetch(self):
        response = self.http_get_with_retry(KEV_URL)
        return response.json()

    def parse(self, raw: dict) -> list[dict]:
        records = []
        for vuln in raw.get("vulnerabilities", []):
            try:
                seen_at = datetime.strptime(vuln["dateAdded"], "%Y-%m-%d")
            except (ValueError, KeyError):
                seen_at = datetime.utcnow()

            records.append({
                "value": vuln["cveID"],
                "type": IOCType.cve,
                "seen_at": seen_at,
                "metadata": {
                    "vendor": vuln.get("vendorProject"),
                    "product": vuln.get("product"),
                    "name": vuln.get("vulnerabilityName"),
                    "source": "cisa_kev",
                },
                "tag_names": ["kev", "cve"],
                "context": {
                    "due_date": vuln.get("dueDate"),
                    "ransomware_use": vuln.get("knownRansomwareCampaignUse"),
                },
            })
        return records


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    CisaKevCollector().run()