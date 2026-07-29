"""
Calcule le score de pertinence Cameroun pour chaque IOC actif.
Stocke le résultat dans indicators.cameroon_relevance (0-6).

Signaux :
  +3  IP hébergée au Cameroun (GeoIP country_code = CM)
  +2  IP sur ASN camerounais (Camtel, MTN, Orange, Nexttel, Yoomee)
  +2  Domaine/URL avec TLD .cm
  +1  Domaine/URL avec mot-clé institutionnel camerounais
  +1  IOC appartenant à un cluster contenant un IOC camerounais

Usage :
    python -m scripts.score_cameroon
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

import geoip2.database
import psycopg2
import psycopg2.extras
import os
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("score_cameroon")

# ── Configuration ──────────────────────────────────────────────────────────────

CITY_DB  = Path(__file__).resolve().parent.parent / "data" / "GeoLite2-City.mmdb"
ASN_DB   = Path(__file__).resolve().parent.parent / "data" / "GeoLite2-ASN.mmdb"

# Mots-clés dans les domaines/URLs
CAMEROON_KEYWORDS = [
    "camtel", "mtn.cm", "orange.cm", "nexttel", "yoomee",
    "antic", "minpostel", "minfopra", "minfi", "spm.cm",
    "afriland", "bicec", "sgbc", "scb-cameroun", "nfc-bank",
    "uy1.uninet", "uy2.uninet", "univ-yaounde",
    ".gov.cm", "gouv.cm",
]

BATCH_SIZE = 1000


# ── Connexion DB ───────────────────────────────────────────────────────────────

def get_conn():
    url = os.environ["DATABASE_URL"]
    url = re.sub(r"postgresql\+psycopg2", "postgresql", url)
    return psycopg2.connect(url)


def _get_active_cameroon_asns(conn) -> set[int]:
    """
    ASN des institutions actives du référentiel monitored_assets -- même
    logique que score_national_tags (Phase 3) ci-dessous : le référentiel est
    la source de vérité à jour (174 institutions), préférable à une liste
    figée qui ne couvrirait qu'une poignée d'opérateurs et se périmerait
    silencieusement (c'était le cas ici : seul 1 des 5 ASN codés en dur
    correspondait encore à une institution du référentiel, et MTN/Orange
    en étaient absents).
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT asn FROM monitored_assets
            WHERE asn IS NOT NULL AND active = true
        """)
        return {row[0] for row in cur.fetchall()}


# ── Phase 1 : IPs ──────────────────────────────────────────────────────────────

def score_ips(conn, city_reader, asn_reader, cameroon_asns: set[int]) -> dict[str, int]:
    """Retourne {indicator_id: score} pour tous les IOCs de type ip/ipv6."""
    scores: dict[str, int] = {}

    with conn.cursor(name="ip_cursor", cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT id, value
            FROM indicators
            WHERE type IN ('ip', 'ipv6')
            AND status = 'active'
        """)

        batch = cur.fetchmany(BATCH_SIZE)
        total = 0
        while batch:
            for row in batch:
                iid, value = str(row["id"]), row["value"]
                score = 0
                try:
                    city = city_reader.city(value)
                    if city.country.iso_code == "CM":
                        score += 3
                except Exception:
                    pass
                try:
                    asn = asn_reader.asn(value)
                    if asn.autonomous_system_number in cameroon_asns:
                        score += 2
                except Exception:
                    pass
                if score > 0:
                    scores[iid] = score
            total += len(batch)
            if total % 10000 == 0:
                logger.info("  IPs traitées : %d", total)
            batch = cur.fetchmany(BATCH_SIZE)

    logger.info("Phase 1 — %d IPs, %d pertinentes Cameroun", total, len(scores))
    return scores


# ── Phase 2 : Domaines / URLs ──────────────────────────────────────────────────

def score_domains(conn) -> dict[str, int]:
    """Retourne {indicator_id: score} pour domaines et URLs."""
    scores: dict[str, int] = {}

    with conn.cursor(name="domain_cursor", cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT id, value, type
            FROM indicators
            WHERE type IN ('domain', 'url', 'email')
            AND status = 'active'
        """)

        batch = cur.fetchmany(BATCH_SIZE)
        total = 0
        while batch:
            for row in batch:
                iid, value = str(row["id"]), row["value"].lower()
                score = 0

                # TLD .cm
                domain_part = value.split("/")[0] if "/" in value else value
                domain_part = domain_part.split("@")[-1]  # email
                if domain_part.endswith(".cm") or ".cm/" in value:
                    score += 2

                # Mots-clés institutionnels
                for kw in CAMEROON_KEYWORDS:
                    if kw in value:
                        score += 1
                        break  # un seul +1 même si plusieurs mots-clés

                if score > 0:
                    scores[iid] = score
            total += len(batch)
            batch = cur.fetchmany(BATCH_SIZE)

    logger.info("Phase 2 — %d domaines/URLs, %d pertinents Cameroun", total, len(scores))
    return scores


# ── Phase 3 : Tags de surveillance nationale ──────────────────────────────────

def score_national_tags(conn) -> dict[str, int]:
    """
    Un IOC porte un tag typosquat:{institution}, ct:{institution} ou
    nrd_watch:{institution} uniquement quand un de nos propres collecteurs
    de surveillance nationale l'a explicitement rattache a une institution
    camerounaise -- c'est un signal plus fort et plus a jour que la liste de
    mots-cles codee en dur ci-dessus (qui ne couvre qu'une quinzaine
    d'institutions, pas les 143 du referentiel complet).
    """
    scores: dict[str, int] = {}
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT DISTINCT i.id
            FROM indicators i
            JOIN indicator_tags it ON it.indicator_id = i.id
            JOIN tags t ON t.id = it.tag_id
            WHERE i.status = 'active'
            AND (
                (t.name LIKE 'typosquat:%%' AND t.name NOT IN ('typosquat:confirmed', 'typosquat:potential'))
                OR (t.name LIKE 'ct:%%' AND t.name NOT IN ('ct:confirmed', 'ct:potential'))
                OR (t.name LIKE 'nrd_watch:%%' AND t.name != 'nrd_watch')
            )
        """)
        for row in cur.fetchall():
            scores[str(row["id"])] = 4

    logger.info("Phase 3 — %d IOCs rattaches a une institution via nos tags de surveillance nationale", len(scores))
    return scores


# ── Phase 4 : Propagation cluster ─────────────────────────────────────────────

def propagate_clusters(conn, cameroon_ids: set[str]) -> dict[str, int]:
    """
    Pour chaque IOC dans un cluster contenant au moins un IOC camerounais,
    ajoute +1 (s'il n'est pas déjà camerounais lui-même).
    """
    if not cameroon_ids:
        return {}

    propagated: dict[str, int] = {}

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Trouver tous les threats qui contiennent au moins un IOC camerounais
        cur.execute("""
            SELECT DISTINCT ti2.indicator_id
            FROM threat_indicators ti1
            JOIN threat_indicators ti2 ON ti1.threat_id = ti2.threat_id
            WHERE ti1.indicator_id = ANY(%s::uuid[])
            AND ti2.indicator_id != ALL(%s::uuid[])
        """, (list(cameroon_ids), list(cameroon_ids)))

        rows = cur.fetchall()
        for row in rows:
            propagated[str(row["indicator_id"])] = 1

    logger.info("Phase 3 — %d IOCs supplémentaires par propagation cluster", len(propagated))
    return propagated


# ── Écriture en base ───────────────────────────────────────────────────────────

def flush_scores(conn, scores: dict[str, int]) -> None:
    """Met à jour cameroon_relevance en batch."""
    if not scores:
        logger.info("Aucun score à écrire")
        return

    data = [(score, iid) for iid, score in scores.items()]

    with conn.cursor() as cur:
        # Reset d'abord tout à 0
        cur.execute("UPDATE indicators SET cameroon_relevance = 0")

        # Mise à jour par batch
        psycopg2.extras.execute_batch(
            cur,
            "UPDATE indicators SET cameroon_relevance = %s WHERE id = %s::uuid",
            data,
            page_size=BATCH_SIZE,
        )

    conn.commit()
    logger.info("%d IOCs mis à jour avec cameroon_relevance > 0", len(scores))


# ── Orchestration ──────────────────────────────────────────────────────────────

def run() -> None:
    logger.info("Démarrage scoring pertinence Cameroun")

    conn = get_conn()

    cameroon_asns = _get_active_cameroon_asns(conn)
    logger.info("%d ASN d'institutions actives dans le référentiel", len(cameroon_asns))

    # Les bases MaxMind (.mmdb) sont volumineuses (~80 Mo) et exclues du depot
    # git -- absentes en CI tant qu'un telechargement automatise n'est pas mis
    # en place. On saute proprement la phase IP plutot que de planter : le
    # signal des tags de surveillance nationale (Phase 3) reste disponible.
    if CITY_DB.exists() and ASN_DB.exists():
        with geoip2.database.Reader(str(CITY_DB)) as city_reader, \
             geoip2.database.Reader(str(ASN_DB))  as asn_reader:
            ip_scores = score_ips(conn, city_reader, asn_reader, cameroon_asns)
    else:
        logger.warning("Bases GeoIP introuvables (%s) -- phase IP ignoree", CITY_DB.parent)
        ip_scores = {}

    domain_scores = score_domains(conn)

    tag_scores = score_national_tags(conn)

    # Fusion des scores directs
    all_scores: dict[str, int] = {}
    for iid, s in {**ip_scores, **domain_scores, **tag_scores}.items():
        all_scores[iid] = all_scores.get(iid, 0) + s

    cameroon_ids = set(all_scores.keys())
    logger.info("Total IOCs directement liés au Cameroun : %d", len(cameroon_ids))

    # Propagation cluster
    cluster_scores = propagate_clusters(conn, cameroon_ids)
    for iid, s in cluster_scores.items():
        all_scores[iid] = all_scores.get(iid, 0) + s

    logger.info("Total IOCs pertinents Cameroun (avec propagation) : %d", len(all_scores))

    flush_scores(conn, all_scores)
    conn.close()

    logger.info("Scoring Cameroun terminé")


if __name__ == "__main__":
    run()
