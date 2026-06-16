"""Collecteur AlienVault OTX.

Source : https://otx.alienvault.com/api/v1/
IOCs   : tous types, regroupés en pulses (mini-corrélations communautaires)
Auth   : OTX_API_KEY dans .env (header X-OTX-API-KEY)
Particularités :
  - Pagination cursor-based (champ "next" dans la réponse)
  - Premier run : 30 derniers jours (évite de tout récupérer)
  - Runs suivants : collecte incrémentale via modified_since
  - Retry automatique sur erreurs transitoires (502/503/timeout)
  - pulse_name conservé en tag → futur pivot de corrélation (J12-J14)
"""
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv

from app.models.enums import IOCType
from collectors.base import BaseCollector

load_dotenv()
logger = logging.getLogger(__name__)

OTX_BASE_URL = "https://otx.alienvault.com/api/v1"
STATE_FILE   = Path(".state/otx_last_run.json")

# Mapping OTX indicator type → nos IOCType
# Types absents (CVE, Mutex, FilePath…) sont ignorés silencieusement
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


def _read_last_run() -> datetime | None:
    """Lit la date du dernier run. Retourne None si premier run."""
    try:
        data = json.loads(STATE_FILE.read_text())
        return datetime.fromisoformat(data["last_run"])
    except (FileNotFoundError, KeyError, ValueError):
        return None


def _write_last_run(dt: datetime) -> None:
    """Sauvegarde la date du run. Appelé uniquement après succès."""
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps({"last_run": dt.isoformat()}))


class OTXCollector(BaseCollector):

    name = "AlienVault OTX"

    def fetch(self) -> list[dict]:
        """Récupère les pulses OTX avec pagination, collecte incrémentale et retry.

        - Premier run  : 30 derniers jours (évite de tout récupérer)
        - Runs suivants : depuis le dernier run
        - Retry        : jusqu'à 3 tentatives sur erreurs transitoires (502/503/timeout)
        """
        api_key = os.environ.get("OTX_API_KEY", "")
        if not api_key:
            raise ValueError("OTX_API_KEY manquant dans .env")

        headers   = {"X-OTX-API-KEY": api_key}
        last_run  = _read_last_run()
        run_start = datetime.utcnow()

        if last_run:
            since = last_run
            logger.info(f"Collecte incrémentale depuis {last_run.strftime('%Y-%m-%d %H:%M')}")
        else:
            since = run_start - timedelta(days=30)
            logger.info("Premier run — collecte des 30 derniers jours")

        params = {
            "limit":          50,
            "modified_since": since.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        all_pulses = []
        url  = f"{OTX_BASE_URL}/pulses/subscribed"
        page = 1

        with httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
        ) as client:
            while url:
                response = None

                # Retry sur erreurs transitoires
                for attempt in range(1, 4):
                    try:
                        response = client.get(url, headers=headers, params=params)

                        if response.status_code in (502, 503, 504):
                            wait = 2 ** attempt
                            logger.warning(
                                f"Page {page} — HTTP {response.status_code}, "
                                f"retry {attempt}/3 dans {wait}s…"
                            )
                            time.sleep(wait)
                            response = None
                            continue

                        response.raise_for_status()
                        break  # succès

                    except httpx.TimeoutException:
                        wait = 2 ** attempt
                        logger.warning(
                            f"Page {page} — timeout, retry {attempt}/3 dans {wait}s…"
                        )
                        time.sleep(wait)

                if response is None:
                    logger.error(f"Page {page} — échec après 3 tentatives, arrêt.")
                    break

                data    = response.json()
                results = data.get("results", [])
                all_pulses.extend(results)
                logger.info(f"Page {page} — {len(results)} pulse(s)")

                url    = data.get("next")
                params = {}   # modified_since uniquement sur la 1ère requête
                page  += 1

        # Sauvegarde APRÈS succès — si fetch échoue à mi-chemin,
        # on recommence depuis le même point au prochain run
        _write_last_run(run_start)
        logger.info(f"Total : {len(all_pulses)} pulse(s) récupéré(s)")
        return all_pulses

    def parse(self, raw: list[dict]) -> list[dict]:
        """Aplatit les pulses en records standards.

        Chaque pulse contient N indicateurs.
        Le nom du pulse est conservé dans les tags de chaque indicateur
        pour reconstituer le regroupement lors de la corrélation (J12-J14).
        """
        records = []
        skipped = 0

        for pulse in raw:
            pulse_name = pulse.get("name", "").strip()
            pulse_id   = pulse.get("id", "")

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

                records.append({
                    "value":   value,
                    "type":    OTX_TYPE_MAP[otx_type],
                    "seen_at": seen_at,
                    "metadata": {
                        "pulse_name": pulse_name,
                        "source":     "otx",
                    },
                    "context": {
                        "pulse_id":    pulse_id,
                        "otx_type":    otx_type,
                        "description": indicator.get("description", ""),
                    },
                })

        if skipped:
            logger.debug(f"{skipped} indicateur(s) ignoré(s) — type non supporté")

        return records


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    OTXCollector().run()