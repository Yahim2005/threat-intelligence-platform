"""Collecteur Certificate Transparency — surveillance des certificats SSL
émis pour des domaines ressemblant aux institutions camerounaises.

Chaque certificat SSL émis dans le monde est publié dans des logs publics
(RFC 6962). crt.sh agrège ces logs et permet une recherche par mot-clé.
Un certificat émis pour un domaine contenant "antic" ou "camtel" mais qui
n'est PAS le domaine officiel est un signal fort de préparation de phishing —
souvent le tout premier indice, avant même que le site soit actif.

Note de fiabilité : crt.sh est un service communautaire gratuit avec des
pannes fréquentes (502/504). Le retry est géré par BaseCollector.http_get_with_retry.
Si le service est indisponible, ce run échouera proprement et sera retenté
au prochain cycle de collecte (toutes les 6h via GitHub Actions).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime

from dotenv import load_dotenv
from app.database import SessionLocal
from app.models.monitored_asset import MonitoredAsset
from core.normalize import detect_and_normalize
from collectors.base import BaseCollector


def _get_all_legitimate_domains(session) -> set[str]:
    """Voir collectors/typosquat_monitor.py — même principe : un domaine
    détecté n'est suspect que s'il ne correspond à AUCUNE institution connue.
    """
    assets = session.query(MonitoredAsset).all()
    domains = set()
    for a in assets:
        if a.domain:
            domains.add(a.domain.lower())
        for alias in (a.known_aliases or []):
            domains.add(alias.lower())
    return domains

load_dotenv()
logger = logging.getLogger(__name__)

CRTSH_URL = "https://crt.sh/"
REQUEST_DELAY = 2.0  # secondes entre requêtes — politesse envers un service déjà fragile


class CTMonitor(BaseCollector):

    name = "Certificate Transparency Monitor (crt.sh)"

    def fetch(self) -> list[dict]:
        """Interroge crt.sh pour chaque domaine surveillé et récupère
        les certificats correspondant au mot-clé de marque.
        """
        session = SessionLocal()
        try:
            assets = (
                session.query(MonitoredAsset)
                .filter(MonitoredAsset.domain.isnot(None))
                .filter(MonitoredAsset.active.is_(True))
                .all()
            )
            targets = [
                {"domain": a.domain, "name": a.name, "acronym": a.acronym}
                for a in assets
            ]
        finally:
            session.close()

        logger.info(f"{len(targets)} domaines à interroger sur crt.sh")

        results = []
        for i, target in enumerate(targets, 1):
            label = target["domain"].split(".")[0]
            if i % 10 == 0:
                logger.info(f"  crt.sh {i}/{len(targets)}…")

            try:
                response = self.http_get_with_retry(
                    CRTSH_URL,
                    params={"q": f"%{label}%", "output": "json"},
                    timeout=30.0,
                )
                certs = response.json()
                if certs:
                    results.append({"target": target, "certs": certs})
            except Exception as e:
                logger.warning(f"crt.sh échec pour {target['domain']} : {e}")

            time.sleep(REQUEST_DELAY)

        return results

    def parse(self, raw: list[dict]) -> list[dict]:
        """Convertit les certificats trouvés en records IOC standards.
        Exclut les certificats légitimes (domaine officiel ou ses sous-domaines).
        """
        session = SessionLocal()
        try:
            legitimate_domains = _get_all_legitimate_domains(session)
        finally:
            session.close()

        records = []
        seen_values = set()

        for entry in raw:
            target = entry["target"]
            official_domain = target["domain"].lower()
            acronym = target["acronym"] or target["name"][:20]
            tag_name = f"ct:{acronym.lower().replace(' ', '_')}"

            label = official_domain.split(".")[0]
            confidence_tag = (
                "ct:potential" if len(label) <= 4 else "ct:confirmed"
            )

            for cert in entry["certs"]:
                name_value = cert.get("name_value", "")
                issuer = cert.get("issuer_name", "")
                timestamp = cert.get("entry_timestamp", "")

                for candidate in name_value.split("\n"):
                    candidate = candidate.strip().lower()
                    if not candidate:
                        continue
                    if candidate.startswith("*."):
                        candidate = candidate[2:]

                    if candidate == official_domain or candidate.endswith("." + official_domain):
                        continue

                    if candidate in legitimate_domains:
                        continue  # domaine officiel connu (alias ou autre institution)

                    if candidate in seen_values:
                        continue
                    seen_values.add(candidate)

                    normalized = detect_and_normalize(candidate)
                    if normalized is None:
                        continue
                    norm_value, norm_type = normalized

                    records.append({
                        "value": norm_value,
                        "type": norm_type,
                        "seen_at": datetime.utcnow(),
                        "tag_names": [tag_name, "ct-monitor", confidence_tag],
                        "metadata": {
                            "source": "ct_monitor",
                            "target_domain": official_domain,
                            "target_name": target["name"],
                            "issuer_name": issuer,
                            "cert_entry_timestamp": timestamp,
                        },
                        "context": {
                            "target": official_domain,
                            "issuer": issuer,
                        },
                    })

        return records


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    CTMonitor().run()
