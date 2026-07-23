"""
Scan de surface d'attaque nationale.

Pour chaque ASN camerounais suivi (monitored_assets), récupère les plages
IP annoncées (RIPEstat) puis interroge Shodan InternetDB pour chaque IP,
une simple consultation passive de leur base déjà scannée, pas un scan
actif de notre part.

Résumable : la progression est suivie par préfixe CIDR dans
exposed_assets_scan_progress. Si le script est interrompu, relance-le :
il reprend là où il s'est arrêté (les préfixes déjà marqués 'done' sont
sautés).

Débit volontairement prudent (InternetDB a un rate-limit non documenté
précisément, avec des bans temporaires observés en usage réel autour de
600 requêtes en rafale sans throttling).

Usage :
    python -m scripts.scan_attack_surface
"""
from __future__ import annotations

import ipaddress
import logging
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.monitored_asset import MonitoredAsset
from app.models.exposed_asset import ExposedAsset, ExposedAssetScanProgress

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("scan_attack_surface")

RIPESTAT_URL = "https://stat.ripe.net/data/announced-prefixes/data.json"
INTERNETDB_URL = "https://internetdb.shodan.io"

MAX_RUNTIME_SECONDS = 5.5 * 3600  # marge de sécurité avant la limite 6h de GitHub Actions

MAX_WORKERS = 5
TARGET_RPS = 3  # très prudent, la vraie limite observée est bien en-deçà de la doc officielle

SENSITIVE_PORTS = {
    21: "FTP", 23: "Telnet", 3389: "RDP", 3306: "MySQL",
    5432: "PostgreSQL", 27017: "MongoDB", 6379: "Redis",
    9200: "Elasticsearch", 5900: "VNC", 445: "SMB",
}


class RateLimiter:
    """Limite globale de débit partagée entre threads (fenêtre glissante 1s),
    avec une pause globale partagée si un 429 est reçu, évite que chaque
    thread fasse sa propre pause indépendante, ce qui gaspille du temps
    et continue de marteler le serveur pendant le backoff.
    """

    def __init__(self, max_per_second: int):
        self.max_per_second = max_per_second
        self.timestamps: deque[float] = deque()
        self.lock = threading.Lock()
        self.paused_until = 0.0

    def acquire(self):
        while True:
            with self.lock:
                now = time.monotonic()
                if now < self.paused_until:
                    wait = self.paused_until - now
                else:
                    while self.timestamps and now - self.timestamps[0] > 1.0:
                        self.timestamps.popleft()
                    if len(self.timestamps) < self.max_per_second:
                        self.timestamps.append(now)
                        return
                    wait = 0.05
            time.sleep(wait)

    def trigger_global_backoff(self, seconds: float):
        with self.lock:
            self.paused_until = max(self.paused_until, time.monotonic() + seconds)


rate_limiter = RateLimiter(TARGET_RPS)


def get_prefixes_for_asn(asn: int) -> list[str]:
    """Récupère les préfixes IPv4 annoncés par un ASN via RIPEstat."""
    try:
        resp = httpx.get(RIPESTAT_URL, params={"resource": f"AS{asn}"}, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        prefixes = [p["prefix"] for p in data["data"]["prefixes"]]
        return [p for p in prefixes if ":" not in p]
    except Exception as e:
        logger.warning(f"Erreur RIPEstat pour AS{asn} : {e}")
        return []


def query_internetdb(ip: str) -> dict | None:
    """Interroge InternetDB pour une IP. Retourne None si rien trouvé ou erreur."""
    rate_limiter.acquire()
    try:
        resp = httpx.get(f"{INTERNETDB_URL}/{ip}", timeout=5.0)
        if resp.status_code == 404:
            return None
        if resp.status_code == 429:
            logger.warning("Rate limit atteint, pause de 60s")
            time.sleep(60)
            return query_internetdb(ip)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def compute_risk_level(data: dict) -> str:
    """Classe le niveau de risque selon les ports/CVEs exposés."""
    if data.get("vulns"):
        return "high"
    ports = set(data.get("ports", []))
    if ports & set(SENSITIVE_PORTS.keys()):
        return "medium"
    return "info"


def upsert_exposed_asset(session, ip: str, data: dict, monitored_asset_id) -> None:
    existing = session.query(ExposedAsset).filter_by(ip_address=ip).first()
    risk = compute_risk_level(data)
    now = datetime.utcnow()
    if existing:
        existing.hostnames = data.get("hostnames", [])
        existing.ports = data.get("ports", [])
        existing.cpes = data.get("cpes", [])
        existing.vulns = data.get("vulns", [])
        existing.tags = data.get("tags", [])
        existing.risk_level = risk
        existing.last_seen = now
        existing.monitored_asset_id = monitored_asset_id
    else:
        session.add(ExposedAsset(
            id=uuid4(),
            ip_address=ip,
            monitored_asset_id=monitored_asset_id,
            hostnames=data.get("hostnames", []),
            ports=data.get("ports", []),
            cpes=data.get("cpes", []),
            vulns=data.get("vulns", []),
            tags=data.get("tags", []),
            risk_level=risk,
            first_seen=now,
            last_seen=now,
        ))


def scan_prefix(asn: int, prefix: str, monitored_asset_id) -> dict:
    """Scanne toutes les IPs d'un préfixe CIDR. Retourne des stats."""
    network = ipaddress.ip_network(prefix, strict=False)
    ips = [str(ip) for ip in network.hosts()] or [str(network.network_address)]

    found = {"scanned": 0, "exposed": 0, "high_risk": 0, "network_failures": 0}
    session = SessionLocal()
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(query_internetdb, ip): ip for ip in ips}
            for future in as_completed(futures):
                ip = futures[future]
                try:
                    data = future.result()
                except Exception:
                    # Échec réseau persistant sur cette IP, comptabilisé mais
                    # ne bloque pas le reste du préfixe
                    found["network_failures"] += 1
                    continue
                found["scanned"] += 1
                if data:
                    found["exposed"] += 1
                    risk = compute_risk_level(data)
                    if risk == "high":
                        found["high_risk"] += 1
                    upsert_exposed_asset(session, ip, data, monitored_asset_id)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur sur le préfixe {prefix} : {e}")
    finally:
        session.close()

    return found


def run() -> None:
    start_time = time.monotonic()

    # Rafraîchissement hebdomadaire : les préfixes scannés il y a plus de
    # 7 jours redeviennent "pending" (InternetDB n'est mis à jour qu'une
    # fois par semaine côté Shodan, inutile de rescanner plus souvent).
    from sqlalchemy import text as sql_text

    session = SessionLocal()
    try:
        stale = session.execute(
            sql_text(
                """UPDATE exposed_assets_scan_progress
                   SET status = 'pending'
                   WHERE status = 'done' AND scanned_at < now() - interval '7 days'"""
            )
        )
        session.commit()
        if stale.rowcount:
            logger.info(f"{stale.rowcount} préfixes remis en file (rafraîchissement hebdomadaire)")
    except Exception as e:
        logger.warning(f"Erreur rafraîchissement hebdomadaire : {e}")
        session.rollback()
    finally:
        session.close()

    session = SessionLocal()
    try:
        assets = (
            session.query(MonitoredAsset)
            .filter(MonitoredAsset.asn.isnot(None))
            .all()
        )
        asn_map = {a.asn: a.id for a in assets}
    finally:
        session.close()

    logger.info(f"{len(asn_map)} ASN à traiter")

    total_scanned = total_exposed = total_high_risk = 0

    budget_exceeded = False

    for asn, monitored_asset_id in asn_map.items():
        if budget_exceeded:
            break

        prefixes = get_prefixes_for_asn(asn)
        if not prefixes:
            continue

        for prefix in prefixes:
            if time.monotonic() - start_time > MAX_RUNTIME_SECONDS:
                logger.info(
                    "Budget de temps atteint (%.0f min), arrêt propre, "
                    "reprise au prochain lancement.",
                    MAX_RUNTIME_SECONDS / 60,
                )
                budget_exceeded = True
                break

            try:
                session = SessionLocal()
                try:
                    progress = (
                        session.query(ExposedAssetScanProgress)
                        .filter_by(asn=asn, prefix=prefix)
                        .first()
                    )
                    if progress and progress.status == "done":
                        session.close()
                        continue

                    if not progress:
                        progress = ExposedAssetScanProgress(
                            id=uuid4(), asn=asn, prefix=prefix, status="in_progress"
                        )
                        session.add(progress)
                    else:
                        progress.status = "in_progress"
                    session.commit()
                finally:
                    session.close()
            except Exception as e:
                # Erreur DB transitoire (réseau, veille...), on ne perd pas
                # tout le scan pour un seul préfixe : on log et on continue.
                # Ce préfixe sera retenté au prochain lancement (pas marqué "done").
                logger.error(f"Erreur DB sur le préfixe {prefix} (AS{asn}), on continue : {e}")
                continue

            network_size = ipaddress.ip_network(prefix, strict=False).num_addresses
            logger.info(f"AS{asn} : scan de {prefix} ({network_size} IPs)…")

            stats = scan_prefix(asn, prefix, monitored_asset_id)
            total_scanned += stats["scanned"]
            total_exposed += stats["exposed"]
            total_high_risk += stats["high_risk"]

            # Si trop d'échecs réseau (coupure wifi probable), on NE marque PAS
            # le préfixe comme terminé, il sera repris entièrement au prochain run
            failure_rate = stats["network_failures"] / max(stats["scanned"] + stats["network_failures"], 1)
            mark_done = failure_rate < 0.10  # tolère jusqu'à 10% d'échecs isolés

            try:
                session = SessionLocal()
                try:
                    progress = (
                        session.query(ExposedAssetScanProgress)
                        .filter_by(asn=asn, prefix=prefix)
                        .first()
                    )
                    if progress:
                        if mark_done:
                            progress.status = "done"
                            progress.scanned_at = datetime.utcnow()
                        else:
                            progress.status = "pending"
                        session.commit()
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"Erreur DB en finalisant le préfixe {prefix} (AS{asn}) : {e}")

            status_note = "" if mark_done else " (NON marqué terminé, trop d'échecs réseau, sera repris)"
            logger.info(
                f"  → {stats['scanned']} IPs scannées, "
                f"{stats['exposed']} exposées, {stats['high_risk']} à haut risque, "
                f"{stats['network_failures']} échecs réseau{status_note}"
            )

    logger.info(
        f"Terminé, total : {total_scanned} IPs scannées, "
        f"{total_exposed} exposées, {total_high_risk} à haut risque"
    )


if __name__ == "__main__":
    run()
