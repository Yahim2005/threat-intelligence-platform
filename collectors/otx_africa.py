"""Collecteur AlienVault OTX — Pulses géographiques Afrique/Cameroun.

Recherche les pulses OTX mentionnant des mots-clés liés au Cameroun
et à l'Afrique de l'Ouest. Complémentaire au collecteur OTX principal
qui récupère les pulses par abonnement.

Auth   : OTX_API_KEY dans .env (header X-OTX-API-KEY)
"""
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from app.models.enums import IOCType
from core.normalize import detect_and_normalize
from collectors.base import BaseCollector

load_dotenv()
logger = logging.getLogger(__name__)

OTX_BASE_URL = "https://otx.alienvault.com/api/v1"
STATE_FILE   = Path(".state/otx_africa_last_run.json")

# Mots-clés de recherche — ordre par pertinence décroissante
SEARCH_QUERIES = [
    "Cameroon",
    "Cameroun",
    "West Africa",
    "Africa malware",
    "ANTIC Cameroon",
    "Camtel",
    "MTN Cameroon",
]

OTX_TYPE_MAP = {
    "IPv4":            IOCType.ip,
    "IPv6":            IOCType.ip,
    "domain":          IOCType.domain,
    "hostname":        IOCType.domain,
    "URL":             IOCType.url,
    "URI":             IOCType.url,
    "FileHash-MD5":    IOCType.md5,
    "FileHash-SHA256": IOCType.sha256,
    "FileHash-SHA1":   IOCType.sha1,
    "email":           IOCType.email,
    "CIDR":            IOCType.cidr,
}

# Tag géographique ajouté sur chaque IOC trouvé
GEO_TAG = "geo:africa"


def _read_last_run() -> str | None:
    try:
        data = json.loads(STATE_FILE.read_text())
        return data.get("last_run")
    except (FileNotFoundError, KeyError, ValueError):
        return None


def _write_last_run(dt: datetime) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps({"last_run": dt.isoformat()}))


class OTXAfricaCollector(BaseCollector):

    name = "AlienVault OTX Africa"

    def fetch(self) -> list[dict]:
        api_key = os.environ.get("OTX_API_KEY", "")
        if not api_key:
            raise ValueError("OTX_API_KEY manquant dans .env")

        headers   = {"X-OTX-API-KEY": api_key}
        run_start = datetime.utcnow()

        seen_pulse_ids: set[str] = set()
        pulse_meta: dict[str, dict] = {}  # id → {geo_tag}

        with httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
        ) as client:

            # ── Phase 1 : collecter les IDs de pulses pertinents ──────────────
            for query in SEARCH_QUERIES:
                logger.info("Recherche OTX : '%s'", query)
                page = 1

                while True:
                    url = f"{OTX_BASE_URL}/search/pulses"
                    params = {"q": query, "limit": 20, "page": page}

                    response = None
                    for attempt in range(1, 4):
                        try:
                            response = client.get(url, headers=headers, params=params)
                            if response.status_code in (502, 503, 504):
                                time.sleep(2 ** attempt)
                                response = None
                                continue
                            response.raise_for_status()
                            break
                        except httpx.TimeoutException:
                            time.sleep(2 ** attempt)

                    if response is None:
                        logger.error("Échec requête pour '%s' page %d", query, page)
                        break

                    data    = response.json()
                    results = data.get("results", [])
                    if not results:
                        break

                    new_count = 0
                    for pulse in results:
                        pid = pulse.get("id", "")
                        if pid and pid not in seen_pulse_ids:
                            seen_pulse_ids.add(pid)
                            title = pulse.get("name", "").lower()
                            desc  = pulse.get("description", "").lower()
                            geo   = "geo:cameroon" if (
                                "cameroon" in title or "cameroun" in title or
                                "cameroon" in desc  or "cameroun" in desc
                            ) else GEO_TAG
                            pulse_meta[pid] = {
                                "geo_tag":    geo,
                                "pulse_name": pulse.get("name", ""),
                            }
                            new_count += 1

                    logger.info(
                        "  '%s' page %d — %d pulses (%d nouveaux)",
                        query, page, len(results), new_count
                    )

                    total   = data.get("count", 0)
                    fetched = page * 20
                    if fetched >= total or fetched >= 100:
                        break
                    page += 1
                    time.sleep(0.5)

            logger.info("%d pulses uniques identifiés — récupération des indicateurs…", len(pulse_meta))

            # ── Phase 2 : récupérer les indicateurs de chaque pulse ───────────
            all_pulses: list[dict] = []
            for i, (pid, meta) in enumerate(pulse_meta.items(), 1):
                if i % 20 == 0:
                    logger.info("  Récupération pulse %d/%d…", i, len(pulse_meta))
                try:
                    resp = client.get(
                        f"{OTX_BASE_URL}/pulses/{pid}",
                        headers=headers,
                    )
                    resp.raise_for_status()
                    pulse_data = resp.json()
                    pulse_data["_geo_tag"] = meta["geo_tag"]
                    # Limiter à 500 indicateurs par pulse (les plus récents)
                    if len(pulse_data.get("indicators", [])) > 500:
                        pulse_data["indicators"] = pulse_data["indicators"][:500]
                    pulse_data["_pulse_name"] = meta["pulse_name"]
                    all_pulses.append(pulse_data)
                    time.sleep(0.3)  # politesse API
                except Exception as e:
                    logger.warning("Pulse %s ignoré : %s", pid, e)

        _write_last_run(run_start)
        logger.info("Total : %d pulses avec indicateurs récupérés", len(all_pulses))
        return all_pulses

    def parse(self, raw: list[dict]) -> list[dict]:
        records = []
        skipped = 0

        for pulse in raw:
            pulse_name = pulse.get("name", "").strip()
            pulse_id   = pulse.get("id", "")
            geo_tag    = pulse.get("_geo_tag", GEO_TAG)

            for indicator in pulse.get("indicators", []):
                otx_type = indicator.get("type", "")

                if otx_type not in OTX_TYPE_MAP:
                    skipped += 1
                    continue

                value = indicator.get("indicator", "").strip()
                if not value:
                    continue

                date_str = indicator.get("created", "").strip()
                try:
                    seen_at = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    seen_at = datetime.utcnow()

                normalized = detect_and_normalize(value)
                if normalized is None:
                    continue

                norm_value, norm_type = normalized

                records.append({
                    "value":   norm_value,
                    "type":    norm_type,
                    "seen_at": seen_at,
                    "tag_names": [geo_tag],   # tag géographique automatique
                    "metadata": {
                        "pulse_name": pulse_name,
                        "source":     "otx_africa",
                        "geo_tag":    geo_tag,
                    },
                    "context": {
                        "pulse_id": pulse_id,
                        "otx_type": otx_type,
                    },
                })

        if skipped:
            logger.debug("%d indicateurs ignorés — type non supporté", skipped)

        return records


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    OTXAfricaCollector().run()
