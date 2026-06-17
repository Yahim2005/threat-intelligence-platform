"""Collecteur NVD : flux de CVE avec détails (CVSS, description).
Source : API REST officielle du NIST. Rate limit strict :
  - 5 req / 30s sans clé API
  - 50 req / 30s avec clé API (header apiKey)
Pagination obligatoire : l'API renvoie max ~2000 résultats par page.
On limite la collecte aux CVE modifiées dans les 30 derniers jours.
"""
import os
import time
from datetime import datetime, timedelta
from app.rate_limiter import RateLimiter

import httpx

from app.models.enums import IOCType
from collectors.base import BaseCollector

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
RESULTS_PER_PAGE = 2000
# Pause entre deux requêtes. Avec une clé API (50 req/30s), 0.7s est large.
# Sans clé (5 req/30s), il faudrait monter à ~6.5s — à ajuster si besoin.
PAUSE_BETWEEN_REQUESTS = 0.7


class NvdCollector(BaseCollector):
    name = "NVD"
    # 50 req/30s avec clé API (NVD officiel). Marge de sécurité : on vise 45.
    _rate_limiter = RateLimiter(max_calls=45, period_seconds=30)
    def fetch(self):
        api_key = os.getenv("NVD_API_KEY")
        headers = {"apiKey": api_key} if api_key else {}

        now = datetime.utcnow()
        start = now - timedelta(days=30)
        params_base = {
            "lastModStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "lastModEndDate": now.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "resultsPerPage": RESULTS_PER_PAGE,
        }

        all_vulnerabilities = []
        start_index = 0
        while True:
            params = {**params_base, "startIndex": start_index}
            self._rate_limiter.wait_if_needed()
            response = self.http_get_with_retry(NVD_URL, params=params, headers=headers)
            
            data = response.json()

            page = data.get("vulnerabilities", [])
            all_vulnerabilities.extend(page)

            total_results = data.get("totalResults", 0)
            start_index += RESULTS_PER_PAGE

            if start_index >= total_results or not page:
                break

            time.sleep(PAUSE_BETWEEN_REQUESTS)

        return all_vulnerabilities

    def parse(self, raw: list) -> list[dict]:
        records = []
        for entry in raw:
            cve = entry.get("cve", {})
            cve_id = cve.get("id")
            if not cve_id:
                continue

            try:
                seen_at = datetime.strptime(
                    cve["lastModified"], "%Y-%m-%dT%H:%M:%S.%f"
                )
            except (ValueError, KeyError):
                seen_at = datetime.utcnow()

            description = next(
                (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"),
                None,
            )

            base_score = None
            base_severity = None
            metrics = cve.get("metrics", {})
            for metric_list in metrics.values():
                if metric_list:
                    cvss_data = metric_list[0].get("cvssData", {})
                    base_score = cvss_data.get("baseScore")
                    base_severity = metric_list[0].get("baseSeverity")
                    break

            records.append({
                "value": cve_id,
                "type": IOCType.cve,
                "seen_at": seen_at,
                "metadata": {
                    "description": description,
                    "cvss_score": base_score,
                    "cvss_severity": base_severity,
                    "source": "nvd",
                },
                "tag_names": ["cve"],
                "context": {"vuln_status": cve.get("vulnStatus")},
            })
        return records


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    NvdCollector().run()