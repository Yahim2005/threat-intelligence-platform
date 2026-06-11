
import csv
import logging
import io
import zipfile
from datetime import datetime

import httpx

from app.database import SessionLocal
from app.models import Indicator, Sighting, Source
from app.models.enums import IOCType, IndicatorStatus, TLPLevel
URLHAUS_FIELDNAMES = [
    "id", "dateadded", "url", "url_status",
    "last_online", "threat", "tags", "urlhaus_link", "reporter"
]
logger = logging.getLogger(__name__)

URLHAUS_CSV_URL = "https://urlhaus.abuse.ch/downloads/csv/"
SOURCE_NAME = "abuse.ch - URLhaus" 

def download_csv(url: str = URLHAUS_CSV_URL) -> str:
    """Télécharge le ZIP URLhaus, le décompresse en mémoire et renvoie le CSV."""
    with httpx.Client(timeout=30) as client:
        response = client.get(url)
        response.raise_for_status()

        # URLhaus renvoie un ZIP, pas un CSV directement
        zip_bytes = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_bytes) as zf:
            csv_filename = zf.namelist()[0]  # premier (et seul) fichier dans le ZIP
            return zf.read(csv_filename).decode("utf-8")


def parse_csv(content: str) -> list[dict]:
    """Parse le CSV URLhaus en ignorant les lignes de commentaire (#)."""
    data_lines = [
        line for line in content.splitlines()
        if not line.startswith("#") and line.strip()
    ]
    if not data_lines:
        return []

    reader = csv.DictReader(data_lines, fieldnames=URLHAUS_FIELDNAMES)
    return [dict(row) for row in reader]

def get_or_create_indicator(
    session, value: str, source_id
) -> tuple[Indicator, bool]:
    """
    Cherche un indicateur existant. S'il n'existe pas, le crée.
    Retourne (indicator, created) où created=True si nouvellement créé.
    """
    indicator = (
        session.query(Indicator)
        .filter_by(value=value, type=IOCType.url)
        .first()
    )

    if indicator:
        return indicator, False

    indicator = Indicator(
        value=value,
        type=IOCType.url,
        tlp=TLPLevel.CLEAR,
        confidence=50,
        status=IndicatorStatus.active,
        source_id=source_id,
    )
    session.add(indicator)
    session.flush()  # obtient l'ID sans committer la transaction
    return indicator, True

def store_indicators(rows: list[dict], session) -> dict:
    """Stocke les indicateurs et sightings. Retourne des stats."""
    source = session.query(Source).filter_by(name=SOURCE_NAME).first()
    if not source:
        logger.warning(f"Source '{SOURCE_NAME}' introuvable en base. Lance d'abord scripts/seeds.py.")

    stats = {"created": 0, "updated": 0, "sightings": 0, "errors": 0}

    for row in rows:
        try:
            url_value = row.get("url", "").strip()
            if not url_value:
                continue

            # Parse de la date
            date_str = row.get("dateadded", "").strip()
            try:
                seen_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                seen_at = datetime.utcnow()

            # Get ou Create
            indicator, created = get_or_create_indicator(
                session, url_value, source.id if source else None
            )

            # Mise à jour des dates
            if not indicator.first_seen or seen_at < indicator.first_seen:
                indicator.first_seen = seen_at
            if not indicator.last_seen or seen_at > indicator.last_seen:
                indicator.last_seen = seen_at

            # Tags depuis le champ threat
            threat = row.get("threat", "").strip()
            if threat:
                indicator.tags = {"threat": threat, "source": "urlhaus"}

            # Sighting
            sighting = Sighting(
                indicator_id=indicator.id,
                seen_at=seen_at,
                source_ref=SOURCE_NAME,
                context={
                    "urlhaus_id": row.get("id"),
                    "url_status": row.get("url_status"),
                    "reporter": row.get("reporter"),
                },
            )
            session.add(sighting)

            if created:
                stats["created"] += 1
            else:
                stats["updated"] += 1
            stats["sightings"] += 1

        except Exception as e:
            logger.error(f"Erreur ligne {row.get('id', '?')} : {e}")
            stats["errors"] += 1

    session.commit()
    return stats

def run():
    """Lance le collecteur URLhaus complet."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("=== Collecteur URLhaus démarré ===")

    try:
        content = download_csv()
        logger.info("CSV téléchargé")
    except httpx.HTTPError as e:
        logger.error(f"Erreur HTTP lors du téléchargement : {e}")
        return

    rows = parse_csv(content)
    logger.info(f"{len(rows)} lignes parsées")
    #print("=== DEBUG première ligne ===")
    #print(rows[0] if rows else "VIDE")
    #print("=== Clés disponibles ===")
    #print(list(rows[0].keys()) if rows else "AUCUNE")

    session = SessionLocal()
    try:
        stats = store_indicators(rows, session)
        logger.info(
            f"Terminé — créés: {stats['created']} | "
            f"mis à jour: {stats['updated']} | "
            f"sightings: {stats['sightings']} | "
            f"erreurs: {stats['errors']}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    run()