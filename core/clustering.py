"""
Moteur de clustering des indicateurs en entités Threat.

Deux stratégies complémentaires :

1. Clustering par composantes connexes du graphe (Jour 20)
   Chaque composante connexe de taille >= MIN_CLUSTER_SIZE devient
   une Threat candidate.

2. Nommage par attribut dominant
   Dans chaque cluster, on cherche :
   - Le tag malware:* le plus fréquent → nom "Malware: Emotet"
   - Sinon la source dominante → nom "Campaign: OpenPhish Cluster"
   - Sinon un nom générique → "Unknown Cluster #N"

Principe de prudence :
- On ne supprime jamais une Threat existante
- On met à jour si le cluster évolue (nouveaux indicateurs)
- MIN_CLUSTER_SIZE = 2 (un seul IOC ne fait pas une campagne)
"""
from __future__ import annotations

import logging
from collections import Counter
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.indicator import Indicator
from app.models.threat import Threat
from app.models.enums import ThreatType, TLPLevel
from core.correlation import build_graph

logger = logging.getLogger(__name__)

MIN_CLUSTER_SIZE = 2      # Taille minimale pour former une Threat
MAX_CLUSTER_SIZE = 500    # Garde-fou anti-explosion


# ---------------------------------------------------------------------------
# Nommage des clusters
# ---------------------------------------------------------------------------

def _dominant_malware_tag(indicators: list[Indicator]) -> str | None:
    """
    Retourne le tag malware:* le plus fréquent dans un cluster.
    Ex: si 7/10 IOCs ont malware:emotet → "emotet"
    """
    tag_counts: Counter = Counter()
    for ind in indicators:
        for tag in (ind.tags or []):
            if tag.name.startswith("malware:"):
                family = tag.name.split(":", 1)[1]
                tag_counts[family] += 1
    if tag_counts:
        return tag_counts.most_common(1)[0][0]
    return None


def _dominant_source(indicators: list[Indicator]) -> str | None:
    """Retourne le nom de source le plus fréquent dans un cluster."""
    source_counts: Counter = Counter()
    for ind in indicators:
        if ind.source:
            source_counts[ind.source.name] += 1
    if source_counts:
        return source_counts.most_common(1)[0][0]
    return None


def _name_cluster(indicators: list[Indicator], cluster_index: int) -> tuple[str, ThreatType, str]:
    """
    Retourne (name, threat_type, description) pour un cluster.
    Priorité : malware tag > source > générique
    """
    malware = _dominant_malware_tag(indicators)
    if malware:
        name = f"Malware: {malware.capitalize()}"
        threat_type = ThreatType.malware
        description = (
            f"Cluster de {len(indicators)} indicateurs associés à la famille "
            f"de malware {malware.capitalize()}. "
            f"Généré automatiquement par corrélation de graphe."
        )
        return name, threat_type, description

    source = _dominant_source(indicators)
    if source:
        name = f"Campaign: {source} Cluster #{cluster_index}"
        threat_type = ThreatType.campaign
        description = (
            f"Cluster de {len(indicators)} indicateurs provenant principalement "
            f"de la source {source}. "
            f"Généré automatiquement par corrélation de graphe."
        )
        return name, threat_type, description

    name = f"Unknown Cluster #{cluster_index}"
    threat_type = ThreatType.campaign
    description = (
        f"Cluster de {len(indicators)} indicateurs corrélés sans attribut dominant identifié."
    )
    return name, threat_type, description


# ---------------------------------------------------------------------------
# Récupération des indicateurs d'un cluster
# ---------------------------------------------------------------------------

def _fetch_indicators(
    session: Session,
    indicator_ids: list[str],
) -> list[Indicator]:
    """Charge les Indicator depuis la DB pour une liste d'UUIDs."""
    from app.models.enums import IndicatorStatus
    indicators = (
        session.query(Indicator)
        .filter(
            Indicator.id.in_(indicator_ids),
            Indicator.status == IndicatorStatus.active,
        )
        .all()
    )
    return indicators


# ---------------------------------------------------------------------------
# Création / mise à jour d'une Threat
# ---------------------------------------------------------------------------

def _upsert_threat(
    session: Session,
    name: str,
    threat_type: ThreatType,
    description: str,
    indicators: list[Indicator],
) -> Threat:
    """
    Crée ou met à jour une Threat par son nom.
    Ajoute les indicateurs du cluster à la Threat.
    """
    existing = session.query(Threat).filter_by(name=name).first()

    if existing:
        threat = existing
        logger.debug("Threat existante mise à jour : %s", name)
    else:
        threat = Threat()
        threat.id = uuid4()
        threat.name = name
        threat.threat_type = threat_type
        threat.tlp = TLPLevel.CLEAR
        session.add(threat)
        logger.info("Nouvelle Threat créée : %s (%s)", name, threat_type.value)

    threat.description = description

    # Ajouter les indicateurs sans doublons
    existing_ids = {str(ind.id) for ind in threat.indicators}
    for ind in indicators:
        if str(ind.id) not in existing_ids:
            threat.indicators.append(ind)

    return threat


# ---------------------------------------------------------------------------
# Orchestration principale
# ---------------------------------------------------------------------------

def extract_clusters(session: Session) -> list[dict]:
    """
    Extrait les clusters depuis le graphe de corrélation et
    crée les entités Threat correspondantes.

    Retourne une liste de dicts décrivant chaque cluster créé/mis à jour.
    """
    import networkx as nx

    logger.info("Construction du graphe de corrélation...")
    G = build_graph(session)

    if G.number_of_nodes() == 0:
        logger.warning("Graphe vide — aucun cluster à extraire")
        return []

    components = list(nx.connected_components(G))
    logger.info(
        "%d composantes connexes trouvées (dont %d de taille >= %d)",
        len(components),
        sum(1 for c in components if len(c) >= MIN_CLUSTER_SIZE),
        MIN_CLUSTER_SIZE,
    )

    results = []
    cluster_index = 1

    for component in sorted(components, key=len, reverse=True):
        if len(component) < MIN_CLUSTER_SIZE:
            continue
        if len(component) > MAX_CLUSTER_SIZE:
            logger.warning(
                "Composante de taille %d > MAX_CLUSTER_SIZE=%d, tronquée",
                len(component), MAX_CLUSTER_SIZE,
            )
            component = set(list(component)[:MAX_CLUSTER_SIZE])

        # Charger les indicateurs depuis la DB
        indicator_ids = list(component)
        indicators = _fetch_indicators(session, indicator_ids)

        if len(indicators) < MIN_CLUSTER_SIZE:
            # Les indicateurs peuvent être expirés ou supprimés
            continue

        # Charger les tags pour le nommage
        for ind in indicators:
            _ = ind.tags  # force le chargement lazy

        name, threat_type, description = _name_cluster(indicators, cluster_index)

        threat = _upsert_threat(session, name, threat_type, description, indicators)
        session.flush()  # obtenir l'ID sans commiter

        results.append({
            "threat_id":      str(threat.id),
            "name":           name,
            "threat_type":    threat_type.value,
            "indicator_count": len(indicators),
            "cluster_size":   len(component),
        })

        cluster_index += 1

    session.commit()
    logger.info("%d Threats créées/mises à jour", len(results))
    return results


# ---------------------------------------------------------------------------
# Endpoint interne : get_threat(indicator)
# ---------------------------------------------------------------------------

def get_threats_for_indicator(
    session: Session,
    indicator_id: str,
) -> list[dict]:
    """
    Retourne les Threats associées à un indicateur donné.
    Utilisé par l'API : GET /indicators/{id}/threats
    """
    indicator = session.query(Indicator).filter_by(id=indicator_id).first()
    if not indicator:
        return []

    return [
        {
            "threat_id":      str(t.id),
            "name":           t.name,
            "threat_type":    t.threat_type.value,
            "description":    t.description,
            "indicator_count": len(t.indicators),
        }
        for t in indicator.threats
    ]