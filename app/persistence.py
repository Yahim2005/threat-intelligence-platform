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
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

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

def get_or_create_tag(session, name: str, tag_cache: dict | None = None) -> Tag:
    """Cherche un tag par son nom, le cree s'il n'existe pas.
    tag_cache (optionnel) : dict {name: Tag} partage sur tout un lot d'appels,
    pour eviter un SELECT reseau par tag repete des milliers de fois."""
    if tag_cache is not None and name in tag_cache:
        return tag_cache[name]

    tag = session.query(Tag).filter_by(name=name).first()
    if tag is None:
        tag = Tag(name=name)
        session.add(tag)
        session.flush()

    if tag_cache is not None:
        tag_cache[name] = tag
    return tag


def attach_tag(session, indicator: Indicator, tag_name: str, tag_cache: dict | None = None) -> None:
    """Attache un tag a un indicateur, sans creer de doublon."""
    tag = get_or_create_tag(session, tag_name, tag_cache=tag_cache)
    if tag not in indicator.tags:
        indicator.tags.append(tag)


def _bulk_prefetch_indicators(session, records: list[dict]) -> dict:
    """Pre-charge en quelques requetes groupees les indicateurs deja en base
    parmi ceux du lot a traiter, pour eviter un SELECT reseau par
    enregistrement (determinant sur la latence Cameroun -> Neon)."""
    values = list({r["value"][:2048] for r in records if r.get("value")})
    prefetch = {}
    CHUNK = 2000
    for i in range(0, len(values), CHUNK):
        chunk = values[i:i + CHUNK]
        rows = session.query(Indicator).options(selectinload(Indicator.tags)).filter(Indicator.value.in_(chunk)).all()
        for ind in rows:
            key = (ind.value, ind.type.value if hasattr(ind.type, "value") else ind.type)
            prefetch[key] = ind
    return prefetch


def store_records(records: list[dict], source_name: str, session) -> dict:
    """Persiste une liste d'enregistrements standards, quelle que soit la source.

    Optimisations reseau essentielles pour les gros volumes (dizaines de
    milliers d'enregistrements), determinantes sur une latence Cameroun -> Neon
    de 150-250ms par aller-retour :
    - indicateurs deja connus pre-charges en quelques requetes groupees ;
    - les NOUVEAUX indicateurs d'un meme lot de CHUNK_SIZE sont tous crees en
      memoire puis flushes en UNE SEULE fois (SQLAlchemy regroupe alors les
      INSERT en peu d'aller-retours), au lieu d'un flush par enregistrement ;
    - le commit reseau reel n'a lieu qu'une fois par lot, via un SAVEPOINT qui
      isole un lot defaillant sans affecter les autres lots deja commites.

    Retourne un dict de stats {created, updated, sightings, errors}."""
    source = session.query(Source).filter_by(name=source_name).first()
    if not source:
        raise ValueError(
            f"Source '{source_name}' introuvable en base. "
            f"Lance d'abord scripts/seeds.py."
        )

    stats = {"created": 0, "updated": 0, "sightings": 0, "errors": 0}
    if not records:
        return stats

    # Rejeter les enregistrements structurellement invalides AVANT de créer
    # le SAVEPOINT du lot. Sans cette validation, un seul value=None faisait
    # rollbacker les centaines d'enregistrements valides du même chunk.
    valid_records = []
    for record in records:
        if not isinstance(record, dict) or not record.get("value") or not record.get("type"):
            stats["errors"] += 1
            continue
        valid_records.append(record)
    records = valid_records
    if not records:
        return stats

    CHUNK_SIZE = 500
    indicator_cache = {}
    tag_cache = {}

    for chunk_start in range(0, len(records), CHUNK_SIZE):
        chunk = records[chunk_start:chunk_start + CHUNK_SIZE]
        try:
            # Verrou logique PostgreSQL par (type, value), pris dans un ordre
            # stable. Deux collecteurs concurrents visant le même IOC ne
            # peuvent ainsi effectuer leur prefetch puis leur INSERT en même
            # temps. Le verrou est transactionnel et libéré au commit.
            lock_keys = sorted({
                f"{getattr(record['type'], 'value', record['type'])}:{record['value'][:2048]}"
                for record in chunk
            })
            session.execute(
                text(
                    "SELECT pg_advisory_xact_lock(hashtext(lock_key)) "
                    "FROM unnest(CAST(:lock_keys AS text[])) AS locks(lock_key) "
                    "ORDER BY lock_key"
                ),
                {"lock_keys": lock_keys},
            )
            indicator_cache.update(_bulk_prefetch_indicators(session, chunk))

            with session.begin_nested():
                # Passe 1 : creer en memoire tous les NOUVEAUX indicateurs du
                # lot, sans flush individuel.
                pending_new = []  # [(key, indicator, record), ...]
                to_process = []   # [(indicator, record, created_bool), ...]

                for record in chunk:
                    value = record["value"][:2048]
                    ioc_type = record["type"]
                    ioc_type_key = ioc_type.value if hasattr(ioc_type, "value") else ioc_type
                    key = (value, ioc_type_key)

                    indicator = indicator_cache.get(key)
                    if indicator is not None:
                        to_process.append((indicator, record, False))
                        continue

                    quality = check_quality(value, ioc_type)
                    status = IndicatorStatus.whitelisted if quality.is_false_positive else IndicatorStatus.active
                    indicator = Indicator(
                        value=value,
                        type=ioc_type,
                        tlp=source.tlp,
                        confidence=50,
                        status=status,
                        raw_metadata={"quality_reason": quality.reason} if quality.is_false_positive else None,
                        source_id=source.id,
                    )
                    indicator.tags = []  # marque la collection comme deja chargee (vide) : evite un
                                         # lazy-load reseau au premier acces a .tags plus bas
                    session.add(indicator)
                    indicator_cache[key] = indicator
                    pending_new.append(indicator)
                    to_process.append((indicator, record, True))

                # UN SEUL flush pour tout le lot de nouveaux indicateurs :
                # SQLAlchemy regroupe les INSERT plutot que d'en envoyer un
                # par enregistrement.
                if pending_new:
                    session.flush()

                # Passe 2 : mise a jour des champs + tags + sighting, main-
                # tenant que tous les indicateurs du lot ont un id valide.
                for indicator, record, created in to_process:
                    seen_at = record.get("seen_at") or datetime.utcnow()

                    if not indicator.first_seen or seen_at < indicator.first_seen:
                        indicator.first_seen = seen_at
                    if not indicator.last_seen or seen_at > indicator.last_seen:
                        indicator.last_seen = seen_at

                    if record.get("metadata"):
                        indicator.raw_metadata = {
                            **(indicator.raw_metadata or {}),
                            **record["metadata"],
                        }

                    for tag_name in record.get("tag_names") or []:
                        attach_tag(session, indicator, tag_name, tag_cache=tag_cache)

                    session.add(Sighting(
                        indicator_id=indicator.id,
                        seen_at=seen_at,
                        source_ref=source_name,
                        context=record.get("context") or {},
                    ))

                    stats["created" if created else "updated"] += 1
                    stats["sightings"] += 1

            session.commit()
        except Exception as e:
            stats["errors"] += len(chunk)
            logger.error(f"[{source_name}] Erreur sur le lot {chunk_start}-{chunk_start+len(chunk)} : {e}")

        done = min(chunk_start + CHUNK_SIZE, len(records))
        logger.info(f"[{source_name}] {done}/{len(records)} traites...")

    return stats
