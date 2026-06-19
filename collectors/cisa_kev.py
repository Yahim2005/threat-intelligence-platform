"""Collecteur CISA KEV : catalogue des vulnérabilités activement exploitées.
Source : JSON statique, sans auth, sans rate limit, mis à jour quotidiennement.
"""
import logging
from datetime import datetime

from collectors.base import BaseCollector
from core.normalize import detect_and_normalize
from core.tags import make_tag

logger = logging.getLogger(__name__)

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


class CisaKevCollector(BaseCollector):
    name = "CISA KEV"

    def fetch(self):
        response = self.http_get_with_retry(KEV_URL)
        return response.json()

    def parse(self, raw: dict) -> list[dict]:
        records = []
        for vuln in raw.get("vulnerabilities", []):
            cve_id = vuln.get("cveID")
            if not cve_id:
                continue

            normalized = detect_and_normalize(cve_id)
            if normalized is None:
                logger.warning(f"[CISA KEV] Type non détecté, ignoré : '{cve_id}'")
                continue
            value, ioc_type = normalized

            try:
                seen_at = datetime.strptime(vuln["dateAdded"], "%Y-%m-%d")
            except (ValueError, KeyError):
                seen_at = datetime.utcnow()

            records.append({
                "value": value,
                "type": ioc_type,
                "seen_at": seen_at,
                "metadata": {
                    "vendor": vuln.get("vendorProject"),
                    "product": vuln.get("product"),
                    "name": vuln.get("vulnerabilityName"),
                    "source": "cisa_kev",
                },
                "tag_names": [make_tag("kind", "vulnerability"), make_tag("source", "kev")],
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