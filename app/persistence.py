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
from app.models import Indicator, Sighting, Source, Tag, source
from app.models.enums import IOCType, IndicatorStatus, TLPLevel
from sqlalchemy.exc import IntegrityError

from core.quality import check_quality

from core import quality
from core.quality import check_quality
logger = logging.getLogger(__name__)


def get_or_create_indicator(
    session, value: str, ioc_type: IOCType, source_id=None, tlp: TLPLevel = TLPLevel.CLEAR
) -> tuple[Indicator, bool]:
    """Cherche un indicateur (même value + même type). Le crée s'il n'existe pas.

    Gère les races conditions : si un autre thread/process a créé le même
    indicateur entre notre lecture et notre écriture (scénario réel avec le
    scheduler qui fait tourner plusieurs collecteurs en parallèle), l'INSERT
    échoue avec une violation de contrainte unique. Dans ce cas, on annule
    notre tentative et on relit — l'autre thread a gagné la course, on récupère
    simplement sa ligne au lieu de planter.

    Retourne (indicator, created)."""
    indicator = (
        session.query(Indicator)
        .filter_by(value=value, type=ioc_type)
        .first()
    )
    if indicator:
        return indicator, False

    quality = check_quality(value, ioc_type)
    status = IndicatorStatus.whitelisted if quality.is_false_positive else IndicatorStatus.active

    indicator = Indicator(
        value=value,
        type=ioc_type,
        tlp=tlp,
        confidence=50,
        status=status,
        raw_metadata={"quality_reason": quality.reason} if quality.is_false_positive else None,
        source_id=source_id,
    )
    session.add(indicator)
    try:
        session.flush()  # obtient l'ID sans committer, pour pouvoir créer le Sighting
    except IntegrityError:
        # Un autre thread a créé cet indicateur entre notre lecture et notre écriture.
        session.rollback()
        indicator = (
            session.query(Indicator)
            .filter_by(value=value, type=ioc_type)
            .first()
        )
        if indicator is None:
            # Cas extrêmement improbable : l'autre transaction a aussi été
            # annulée entre-temps. On relance l'exception, le retry global
            # de store_records (à ajouter) s'en occupera.
            raise
        return indicator, False

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
                session, value, ioc_type, source.id, tlp=source.tlp
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