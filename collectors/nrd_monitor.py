"""Collecteur de domaines nouvellement enregistres (NRD) - complement a crt.sh.

Telecharge la liste quotidienne gratuite de WhoisDS.com (domaines
nouvellement enregistres, tous TLD majeurs confondus, ~70 000/jour) et la
filtre pour detecter tout domaine contenant un mot-cle de marque d'une
institution camerounaise surveillee - y compris des domaines qui n'ont
structurellement aucun rapport avec le domaine officiel (contrairement au
typosquatting par permutation de dnstwist, qui ne genere que des variantes
proches d'un domaine connu).

La recherche se fait par "mot-cle isole" (limite de mot autour du sigle),
pas par simple sous-chaine, pour eviter l'explosion de faux positifs sur
les sigles courts (SIC, ART, PAD...) au sein de 70 000 domaines/jour.
"""
from __future__ import annotations
import base64
import io
import logging
import re
import zipfile
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

from app.database import SessionLocal
from app.models.monitored_asset import MonitoredAsset
from core.normalize import detect_and_normalize
from collectors.base import BaseCollector

load_dotenv()
logger = logging.getLogger(__name__)

NRD_BASE_URL = "https://whoisds.com/whois-database/newly-registered-domains"
MIN_KEYWORD_LENGTH = 5  # en dessous, trop de collisions avec des mots/TLD courants (ART, PAD, SIC...)


def _get_keyword_targets(session) -> list[dict]:
    """Un mot-cle de marque par institution active (sigle en priorite, sinon
    le premier label du domaine officiel). Deduplique : deux institutions ne
    doivent jamais generer le meme mot-cle a chercher."""
    assets = session.query(MonitoredAsset).filter(MonitoredAsset.active.is_(True)).all()
    targets = []
    seen_keywords = set()
    for a in assets:
        keyword = None
        if a.acronym and len(a.acronym) >= MIN_KEYWORD_LENGTH:
            keyword = a.acronym.lower()
        elif a.domain:
            label = a.domain.split(".")[0]
            if len(label) >= MIN_KEYWORD_LENGTH:
                keyword = label.lower()
        if not keyword or keyword in seen_keywords:
            continue
        seen_keywords.add(keyword)
        targets.append({"keyword": keyword, "name": a.name, "acronym": a.acronym})
    return targets


def _get_all_legitimate_domains(session) -> set[str]:
    """Tous les domaines officiels + alias connus, pour ne pas signaler un
    domaine deja reconnu comme legitime (evite les faux positifs evidents)."""
    assets = session.query(MonitoredAsset).all()
    domains = set()
    for a in assets:
        if a.domain:
            domains.add(a.domain.lower())
        for alias in (a.known_aliases or []):
            domains.add(alias.lower())
    return domains


class NRDMonitor(BaseCollector):
    name = "Newly Registered Domains Monitor"

    def fetch(self) -> list[dict]:
        """Telecharge la liste NRD de la veille (WhoisDS.com, gratuit, pas
        de cle API). La donnee du jour meme est souvent incomplete, on
        prend systematiquement J-1."""
        target_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        encoded = base64.b64encode(f"{target_date}.zip".encode()).decode().rstrip("=")
        url = f"{NRD_BASE_URL}/{encoded}/nrd"

        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                with z.open(z.namelist()[0]) as f:
                    domains = f.read().decode("utf-8", errors="ignore").splitlines()
        except Exception as e:
            logger.error(f"Echec telechargement NRD pour {target_date} : {e}")
            return []

        logger.info(f"{len(domains)} domaines nouvellement enregistres le {target_date}")
        return [{"date": target_date, "domains": domains}]

    def parse(self, raw: list[dict]) -> list[dict]:
        """Croise la liste NRD avec les mots-cles de marque des institutions
        surveillees, via une recherche par mot isole (pas sous-chaine)."""
        if not raw:
            return []

        session = SessionLocal()
        try:
            targets = _get_keyword_targets(session)
            legitimate_domains = _get_all_legitimate_domains(session)
        finally:
            session.close()

        if not targets:
            return []

        keyword_to_target = {t["keyword"]: t for t in targets}
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(t["keyword"]) for t in targets) + r")\b"
        )

        entry = raw[0]
        target_date = entry["date"]
        domains = entry["domains"]

        records = []
        for domain_value in domains:
            domain_value = domain_value.strip().lower()
            if not domain_value or domain_value in legitimate_domains:
                continue

            # Exclut le TLD de la recherche : "ART" est aussi une extension
            # (.art) reelle, et matcherait sinon n'importe quel domaine se
            # terminant par .art, quel que soit son contenu.
            searchable_part = domain_value.rsplit(".", 1)[0]
            match = pattern.search(searchable_part)
            if not match:
                continue

            target = keyword_to_target[match.group(1)]
            normalized = detect_and_normalize(domain_value)
            if normalized is None:
                continue
            norm_value, norm_type = normalized

            acronym = target["acronym"] or target["name"][:20]
            tag_name = f"nrd_watch:{acronym.lower().replace(' ', '_')}"
            records.append({
                "value": norm_value,
                "type": norm_type,
                "seen_at": datetime.utcnow(),
                "tag_names": [tag_name, "nrd_watch"],
                "metadata": {
                    "source": "nrd_monitor",
                    "target_name": target["name"],
                    "matched_keyword": target["keyword"],
                    "registration_date": target_date,
                },
                "context": {
                    "matched_keyword": target["keyword"],
                    "registration_date": target_date,
                },
            })

        logger.info(f"{len(records)} domaines suspects detectes parmi {len(domains)} nouveaux enregistrements")
        return records


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    NRDMonitor().run()
