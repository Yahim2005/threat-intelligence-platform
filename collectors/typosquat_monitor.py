"""Collecteur de typosquatting — surveillance des domaines camerounais.

Pour chaque institution dans monitored_assets ayant un domaine renseigné,
lance dnstwist pour détecter les variantes (typo, homoglyphes, insertion...)
qui sont réellement enregistrées et résolvent en DNS.

Chaque variante détectée devient un IOC de type domain, taggé
`typosquat:{acronyme}` pour tracer l'institution ciblée.
"""
from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime

from dotenv import load_dotenv
from app.database import SessionLocal
from app.models.monitored_asset import MonitoredAsset
from app.models.enums import IOCType
from core.normalize import detect_and_normalize
from collectors.base import BaseCollector


def _get_all_legitimate_domains(session) -> set[str]:
    """Tous les domaines officiels + alias connus, toutes institutions confondues.
    Une variante détectée qui correspond à l'un de ces domaines n'est PAS du
    typosquatting — c'est probablement un autre domaine légitime de la même
    institution (ex: minhdu.cm ET minhdu.gov.cm sont tous deux officiels).
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

DNSTWIST_TIMEOUT = 90  # secondes par domaine


class TyposquatMonitor(BaseCollector):

    name = "Typosquat Monitor (dnstwist)"

    def fetch(self) -> list[dict]:
        """Récupère la liste des domaines à surveiller depuis monitored_assets,
        puis lance dnstwist sur chacun.
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

        logger.info(f"{len(targets)} domaines à analyser avec dnstwist")

        results = []
        for i, target in enumerate(targets, 1):
            domain = target["domain"]
            if i % 10 == 0:
                logger.info(f"  dnstwist {i}/{len(targets)}…")
            try:
                proc = subprocess.run(
                    [
                        "dnstwist", "--registered", "--format", "json",
                        "--threads", "128",
                        domain,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=DNSTWIST_TIMEOUT,
                )
                if proc.returncode != 0:
                    logger.warning(f"dnstwist a échoué pour {domain} : {proc.stderr[:200]}")
                    continue
                variants = json.loads(proc.stdout)
                results.append({"target": target, "variants": variants})
            except subprocess.TimeoutExpired:
                logger.warning(f"dnstwist timeout pour {domain} (> {DNSTWIST_TIMEOUT}s)")
            except json.JSONDecodeError:
                logger.warning(f"Sortie JSON invalide pour {domain}")
            except Exception as e:
                logger.warning(f"Erreur dnstwist pour {domain} : {e}")

        return results

    def parse(self, raw: list[dict]) -> list[dict]:
        """Convertit les résultats dnstwist en records IOC standards.
        Exclut le domaine original (*original) et tout domaine correspondant
        à une institution légitime connue, quelle qu'elle soit — pas
        seulement la cible de ce run précis.
        """
        session = SessionLocal()
        try:
            legitimate_domains = _get_all_legitimate_domains(session)
        finally:
            session.close()

        records = []

        for entry in raw:
            target = entry["target"]
            acronym = target["acronym"] or target["name"][:20]
            tag_name = f"typosquat:{acronym.lower().replace(' ', '_')}"

            # Signal de confiance : un domaine cible court (ex: "aer.cm", "sic.cm")
            # génère beaucoup de coïncidences statistiques dans l'espace des permutations.
            # Un domaine cible long rend une variante détectée bien plus significative.
            target_label = target["domain"].split(".")[0]
            confidence_tag = (
                "typosquat:potential" if len(target_label) <= 4
                else "typosquat:confirmed"
            )

            for variant in entry["variants"]:
                if variant.get("fuzzer") == "*original":
                    continue

                domain_value = variant.get("domain", "").strip()
                if not domain_value:
                    continue

                if domain_value.lower() in legitimate_domains:
                    continue  # domaine officiel connu (alias ou autre institution) — pas du typosquatting

                normalized = detect_and_normalize(domain_value)
                if normalized is None:
                    continue
                norm_value, norm_type = normalized

                records.append({
                    "value": norm_value,
                    "type": norm_type,
                    "seen_at": datetime.utcnow(),
                    "tag_names": [tag_name, "typosquat", confidence_tag],
                    "metadata": {
                        "source": "typosquat_monitor",
                        "target_domain": target["domain"],
                        "target_name": target["name"],
                        "fuzzer": variant.get("fuzzer"),
                        "dns_a": variant.get("dns_a"),
                        "dns_mx": variant.get("dns_mx"),
                    },
                    "context": {
                        "fuzzer_type": variant.get("fuzzer"),
                        "target": target["domain"],
                    },
                })

        return records


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    TyposquatMonitor().run()
