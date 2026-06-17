"""Persistance générique des collecteurs : get-or-create d'indicateurs + sightings.

Ce module ne connaît AUCUNE source en particulier. Il consomme des
« enregistrements standards » (dicts au format commun produits par le parse()
de chaque collecteur) et les écrit en base de la même façon, quelle que soit
leur origine.

Format d'un enregistrement standard :
    {
        "value":   str,             # l'IOC (obligatoire)
        "type":    IOCType,         # url, ip, hash... (obligatoire)
        "seen_at": datetime | None, # quand la source l'a observé
        "tags":    dict | None,     # métadonnées → posées sur l'Indicator
        "context": dict | None,     # détails de l'observation → posés sur le Sighting
    }
"""
import logging
from datetime import datetime
from app.models import Indicator, Sighting, Source, Tag
from app.models.enums import IOCType, IndicatorStatus, TLPLevel

logger = logging.getLogger(__name__)


def get_or_create_indicator(
    session, value: str, ioc_type: IOCType, source_id=None
) -> tuple[Indicator, bool]:
    """Cherche un indicateur (même value + même type). Le crée s'il n'existe pas.
    Retourne (indicator, created)."""
    indicator = (
        session.query(Indicator)
        .filter_by(value=value, type=ioc_type)
        .first()
    )
    if indicator:
        return indicator, False

    indicator = Indicator(
        value=value,
        type=ioc_type,
        tlp=TLPLevel.CLEAR,
        confidence=50,
        status=IndicatorStatus.active,
        source_id=source_id,
    )
    session.add(indicator)
    session.flush()  # obtient l'ID sans committer, pour pouvoir créer le Sighting
    return indicator, True

def get_or_create_tag(session, name: str) -> Tag:
    """Cherche un tag par son nom, le crée s'il n'existe pas."""
    tag = session.query(Tag).filter_by(name=name).first()
    if tag is None:
        tag = Tag(name=name)
        session.add(tag)
        session.flush()
    return tag


def attach_tag(session, indicator: Indicator, tag_name: str) -> None:
    """Attache un tag à un indicateur, sans créer de doublon."""
    tag = get_or_create_tag(session, tag_name)
    if tag not in indicator.tags:
        indicator.tags.append(tag)


def store_records(records: list[dict], source_name: str, session) -> dict:
    """Persiste une liste d'enregistrements standards, quelle que soit la source.
    Chaque record est committé individuellement : un échec sur un record
    n'affecte jamais les autres (isolation au niveau de la transaction).
    Retourne un dict de stats {created, updated, sightings, errors}."""
    source = session.query(Source).filter_by(name=source_name).first()
    if not source:
        raise ValueError(
            f"Source '{source_name}' introuvable en base. "
            f"Lance d'abord scripts/seeds.py."
        )

    stats = {"created": 0, "updated": 0, "sightings": 0, "errors": 0}

    for record in records:
        try:
            value = record["value"][:2048]  # tronque pour respecter la limite de colonne
            ioc_type = record["type"]
            seen_at = record.get("seen_at") or datetime.utcnow()

            indicator, created = get_or_create_indicator(
                session, value, ioc_type, source.id
            )

            # Fenêtre temporelle
            if not indicator.first_seen or seen_at < indicator.first_seen:
                indicator.first_seen = seen_at
            if not indicator.last_seen or seen_at > indicator.last_seen:
                indicator.last_seen = seen_at

            # Métadonnées brutes du collecteur (fusion avec l'existant)
            if record.get("metadata"):
                indicator.raw_metadata = {
                    **(indicator.raw_metadata or {}),
                    **record["metadata"],
                }

            # Tags normalisés (relation many-to-many)
            for tag_name in record.get("tag_names") or []:
                attach_tag(session, indicator, tag_name)

            # Sighting
            session.add(Sighting(
                indicator_id=indicator.id,
                seen_at=seen_at,
                source_ref=source_name,
                context=record.get("context") or {},
            ))

            session.commit()
            stats["created" if created else "updated"] += 1
            stats["sightings"] += 1

        except Exception as e:
            session.rollback()
            stats["errors"] += 1
            logger.error(f"Erreur sur '{record.get('value', '?')}' : {e}")

    return stats