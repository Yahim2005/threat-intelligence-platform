"""
Moteur de corrélation des indicateurs TIP.

Trois règles de corrélation, ordonnées par précision décroissante :

1. resolves_to    : domaine → IP via enrichissement DNS (confidence 90)
2. same_tag       : IOCs partageant un tag malware:* (confidence 75)
3. same_source_batch : IOCs du même batch de collecte (confidence 50)

Chaque règle produit des TIPRelationship persistées en base.
Un graphe NetworkX est construit en mémoire pour explorer les clusters.

Principe anti-explosion combinatoire :
- Règle 1 : exactement 1 relation par résolution DNS trouvée
- Règle 2 : max MAX_SAME_TAG_PAIRS paires par tag (évite O(n²) sur les gros tags)
- Règle 3 : max MAX_BATCH_PAIRS paires par batch
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

import networkx as nx
from sqlalchemy.orm import Session

from app.models.enrichment import Enrichment
from app.models.indicator import Indicator
from app.models.relationship import TIPRelationship
from app.models.enums import RelationshipType
from app.models.tag import Tag

logger = logging.getLogger(__name__)

# Limites anti-explosion combinatoire
MAX_SAME_TAG_PAIRS = 500    # max paires par tag malware
MAX_BATCH_PAIRS = 200       # max paires par batch source


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_relation(
    source_ref: str,
    target_ref: str,
    rel_type: RelationshipType,
    confidence: int,
    rule: str,
) -> TIPRelationship:
    r = TIPRelationship()
    r.id = uuid4()
    r.source_ref = source_ref
    r.target_ref = target_ref
    r.relationship_type = rel_type
    r.confidence = confidence
    r.rule = rule
    r.created_at = datetime.now(timezone.utc)
    return r


def _relation_exists(
    session: Session,
    source_ref: str,
    target_ref: str,
    rel_type: RelationshipType,
) -> bool:
    """Vérifie si une relation identique existe déjà en base."""
    return (
        session.query(TIPRelationship)
        .filter_by(
            source_ref=source_ref,
            target_ref=target_ref,
            relationship_type=rel_type,
        )
        .first()
    ) is not None


# ---------------------------------------------------------------------------
# Règle 1 : resolves_to (domaine → IP via DNS)
# ---------------------------------------------------------------------------

def rule_resolves_to(session: Session) -> list[TIPRelationship]:
    """
    Pour chaque enrichissement DNS d'un domaine, si l'IP résolue
    est aussi un indicateur en base → crée une relation resolves_to.

    Source des données DNS : table enrichments, provider='dns',
    data contient {'addresses': ['1.2.3.4', ...]}
    """
    created = []

    # Récupérer tous les enrichissements DNS
    dns_enrichments = (
        session.query(Enrichment)
        .filter_by(provider="dns")
        .all()
    )
    logger.info("Règle resolves_to : %d enrichissements DNS trouvés", len(dns_enrichments))

    # Index des IPs en base : value → indicator_id
    from app.models.enums import IOCType
    ip_indicators = (
        session.query(Indicator.value, Indicator.id)
        .filter(Indicator.type.in_([IOCType.ip, IOCType.ipv6]))
        .all()
    )
    ip_index = {row.value: str(row.id) for row in ip_indicators}
    logger.info("Règle resolves_to : %d IPs indexées", len(ip_index))

    for enrichment in dns_enrichments:
        if not enrichment.data:
            continue

        # Extraire les adresses IP depuis les données DNS
        addresses = []
        data = enrichment.data
        if isinstance(data, dict):
            addresses = data.get("addresses", [])
            # Certains enrichisseurs stockent sous 'a_records' ou 'ips'
            if not addresses:
                addresses = data.get("a_records", data.get("ips", []))
        elif isinstance(data, list):
            addresses = data

        source_ref = str(enrichment.indicator_id)

        for ip in addresses:
            if not isinstance(ip, str):
                continue
            ip = ip.strip()
            if ip not in ip_index:
                continue

            target_ref = ip_index[ip]
            if source_ref == target_ref:
                continue

            # Éviter les doublons
            if _relation_exists(session, source_ref, target_ref, RelationshipType.resolves_to):
                continue

            rel = _make_relation(
                source_ref=source_ref,
                target_ref=target_ref,
                rel_type=RelationshipType.resolves_to,
                confidence=90,
                rule="dns_resolution",
            )
            session.add(rel)
            created.append(rel)

    logger.info("Règle resolves_to : %d relations créées", len(created))
    return created


# ---------------------------------------------------------------------------
# Règle 2 : same_tag (co-occurrence par tag malware:*)
# ---------------------------------------------------------------------------

def rule_same_tag(session: Session) -> list[TIPRelationship]:
    """
    Pour chaque tag malware:*, relie les indicateurs qui le partagent.
    Limité à MAX_SAME_TAG_PAIRS paires par tag.
    """
    created = []

    # Récupérer tous les tags malware:*
    malware_tags = (
        session.query(Tag)
        .filter(Tag.name.like("malware:%"))
        .all()
    )
    logger.info("Règle same_tag : %d tags malware trouvés", len(malware_tags))

    for tag in malware_tags:
        # Indicateurs portant ce tag
        indicators = tag.indicators
        if len(indicators) < 2:
            continue

        # Limiter pour éviter O(n²) sur les gros tags
        indicators = indicators[:100]  # max 100 indicateurs par tag
        pairs_created = 0

        for i, ind_a in enumerate(indicators):
            for ind_b in indicators[i + 1:]:
                if pairs_created >= MAX_SAME_TAG_PAIRS:
                    break

                source_ref = str(ind_a.id)
                target_ref = str(ind_b.id)

                if _relation_exists(
                    session, source_ref, target_ref, RelationshipType.same_tag
                ):
                    continue

                rel = _make_relation(
                    source_ref=source_ref,
                    target_ref=target_ref,
                    rel_type=RelationshipType.same_tag,
                    confidence=75,
                    rule=f"shared_tag:{tag.name}",
                )
                session.add(rel)
                created.append(rel)
                pairs_created += 1

            if pairs_created >= MAX_SAME_TAG_PAIRS:
                break

    logger.info("Règle same_tag : %d relations créées", len(created))
    return created


# ---------------------------------------------------------------------------
# Règle 3 : same_source_batch (co-occurrence dans le même batch)
# ---------------------------------------------------------------------------

def rule_same_source_batch(session: Session) -> list[TIPRelationship]:
    """
    Relie les indicateurs collectés dans le même batch (même source,
    même last_seen à la minute près).
    Limité à MAX_BATCH_PAIRS paires par batch.
    """
    from sqlalchemy import func
    from app.models.enums import IndicatorStatus

    created = []

    # Grouper par (source_id, trunc(last_seen, minute))
    # On récupère tous les indicateurs actifs avec source
    indicators = (
        session.query(Indicator)
        .filter(
            Indicator.status == IndicatorStatus.active,
            Indicator.source_id.isnot(None),
        )
        .order_by(Indicator.source_id, Indicator.last_seen)
        .limit(10000)  # garde-fou
        .all()
    )

    # Grouper manuellement par (source_id, minute)
    batches: dict[tuple, list[Indicator]] = {}
    for ind in indicators:
        if ind.last_seen is None:
            continue
        ls = ind.last_seen
        if hasattr(ls, 'tzinfo') and ls.tzinfo is None:
            ls = ls.replace(tzinfo=timezone.utc)
        # Clé = (source_id, année, mois, jour, heure, minute)
        key = (
            str(ind.source_id),
            ls.year, ls.month, ls.day, ls.hour, ls.minute,
        )
        batches.setdefault(key, []).append(ind)

    logger.info("Règle same_source_batch : %d batches identifiés", len(batches))

    for key, batch_indicators in batches.items():
        if len(batch_indicators) < 2:
            continue

        # Limiter la taille du batch
        batch_indicators = batch_indicators[:50]
        pairs_created = 0

        for i, ind_a in enumerate(batch_indicators):
            for ind_b in batch_indicators[i + 1:]:
                if pairs_created >= MAX_BATCH_PAIRS:
                    break

                source_ref = str(ind_a.id)
                target_ref = str(ind_b.id)

                if _relation_exists(
                    session, source_ref, target_ref,
                    RelationshipType.same_source_batch
                ):
                    continue

                rel = _make_relation(
                    source_ref=source_ref,
                    target_ref=target_ref,
                    rel_type=RelationshipType.same_source_batch,
                    confidence=50,
                    rule=f"batch:{key[0]}",
                )
                session.add(rel)
                created.append(rel)
                pairs_created += 1

            if pairs_created >= MAX_BATCH_PAIRS:
                break

    logger.info("Règle same_source_batch : %d relations créées", len(created))
    return created


# ---------------------------------------------------------------------------
# Construction du graphe NetworkX
# ---------------------------------------------------------------------------

def build_graph(session: Session) -> nx.Graph:
    """
    Charge toutes les relations en base et construit un graphe non-orienté.

    Noeuds : indicator_id (str UUID)
    Arêtes : (source_ref, target_ref, type=relationship_type, confidence=...)

    Retourne le graphe NetworkX pour exploration des clusters.
    """
    relations = session.query(TIPRelationship).all()
    G = nx.Graph()

    for rel in relations:
        G.add_edge(
            rel.source_ref,
            rel.target_ref,
            relationship_type=rel.relationship_type.value,
            confidence=rel.confidence,
            rule=rel.rule,
        )

    logger.info(
        "Graphe construit : %d noeuds, %d arêtes, %d composantes connexes",
        G.number_of_nodes(),
        G.number_of_edges(),
        nx.number_connected_components(G),
    )
    return G


def get_related_indicators(
    session: Session,
    indicator_id: str,
    max_hops: int = 2,
) -> list[dict]:
    """
    Retourne les indicateurs reliés à un indicateur donné,
    jusqu'à max_hops sauts dans le graphe.

    Utile pour l'API : GET /indicators/{id}/related
    """
    G = build_graph(session)

    if indicator_id not in G:
        return []

    # BFS limité à max_hops
    related = {}
    for neighbor in nx.single_source_shortest_path_length(
        G, indicator_id, cutoff=max_hops
    ):
        if neighbor == indicator_id:
            continue
        edge_data = G.get_edge_data(indicator_id, neighbor) or {}
        related[neighbor] = {
            "indicator_id": neighbor,
            "hops": nx.shortest_path_length(G, indicator_id, neighbor),
            "relationship_type": edge_data.get("relationship_type"),
            "confidence": edge_data.get("confidence"),
            "rule": edge_data.get("rule"),
        }

    return list(related.values())