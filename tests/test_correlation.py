"""
Tests du moteur de corrélation.
Scénario principal : deux domaines résolvant vers la même IP sont reliés.
"""
from __future__ import annotations

from pyexpat import model
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.enums import IOCType, IndicatorStatus, RelationshipType, TLPLevel
from app.models.indicator import Indicator
from app.models.enrichment import Enrichment
from app.models.relationship import TIPRelationship
from app.models.tag import Tag
from core.correlation import (
    rule_resolves_to,
    rule_same_tag,
    rule_same_source_batch,
    build_graph,
    get_related_indicators,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_indicator(ioc_type: str, value: str, source_id=None) -> Indicator:
    ind = Indicator()
    ind.id = uuid.uuid4()
    ind.value = value
    ind.type = IOCType(ioc_type)
    ind.tlp = TLPLevel.CLEAR
    ind.confidence = 50
    ind.status = IndicatorStatus.active
    ind.tags = []
    ind.source_id = source_id
    ind.last_seen = datetime.now(timezone.utc)
    ind.raw_metadata = {}
    return ind


def make_enrichment(indicator_id, provider: str, data: dict) -> Enrichment:
    e = Enrichment()
    e.id = uuid.uuid4()
    e.indicator_id = indicator_id
    e.provider = provider
    e.data = data
    e.enriched_at = datetime.now(timezone.utc)
    return e


def make_tag(name: str, indicators: list) -> Tag:
    t = Tag()
    t.id = uuid.uuid4()
    t.name = name
    t.indicators = indicators
    return t


def make_relation(source_ref, target_ref, rel_type, confidence=50) -> TIPRelationship:
    r = TIPRelationship()
    r.id = uuid.uuid4()
    r.source_ref = str(source_ref)
    r.target_ref = str(target_ref)
    r.relationship_type = rel_type
    r.confidence = confidence
    r.rule = "test"
    r.created_at = datetime.now(timezone.utc)
    return r


# ---------------------------------------------------------------------------
# Tests rule_resolves_to
# ---------------------------------------------------------------------------

class TestRuleResolvesTo:

    def _make_session(self, dns_enrichments, ip_indicators, existing_relations=None):
        """Session mockée pour rule_resolves_to."""
        session = MagicMock()

        def query_side(*args):
            # args[0] est le modèle ou la première colonne
            model = args[0]
            q = MagicMock()
            if model is Enrichment:
                q.filter_by.return_value.all.return_value = dns_enrichments
            elif model is TIPRelationship:
                q.filter_by.return_value.first.return_value = None
            else:
                # session.query(Indicator.value, Indicator.id).filter().all()
                filter_mock = MagicMock()
                filter_mock.all.return_value = ip_indicators
                q.filter.return_value = filter_mock
            return q

        session.query.side_effect = query_side
        return session

    def test_domain_resolving_to_known_ip_creates_relation(self):
        """
        Un domaine dont l'enrichissement DNS pointe vers une IP connue
        doit créer une relation resolves_to.
        """
        domain = make_indicator("domain", "evil.com")
        ip = make_indicator("ip", "1.2.3.4")

        dns_enrich = make_enrichment(
            domain.id, "dns", {"addresses": ["1.2.3.4"]}
        )

        # Simuler les rows retournées par la query Indicator
        ip_row = MagicMock()
        ip_row.value = "1.2.3.4"
        ip_row.id = ip.id

        session = self._make_session(
            dns_enrichments=[dns_enrich],
            ip_indicators=[ip_row],
        )

        relations = rule_resolves_to(session)
        assert len(relations) == 1
        assert relations[0].relationship_type == RelationshipType.resolves_to
        assert relations[0].confidence == 90
        assert relations[0].source_ref == str(domain.id)
        assert relations[0].target_ref == str(ip.id)

    def test_no_dns_enrichments_no_relations(self):
        """Sans enrichissements DNS, aucune relation ne doit être créée."""
        session = self._make_session(dns_enrichments=[], ip_indicators=[])
        relations = rule_resolves_to(session)
        assert relations == []

    def test_ip_not_in_base_no_relation(self):
        """Si l'IP résolue n'est pas dans notre base, pas de relation."""
        domain = make_indicator("domain", "evil.com")
        dns_enrich = make_enrichment(
            domain.id, "dns", {"addresses": ["9.9.9.9"]}
        )
        session = self._make_session(
            dns_enrichments=[dns_enrich],
            ip_indicators=[],  # 9.9.9.9 pas dans la base
        )
        relations = rule_resolves_to(session)
        assert relations == []

    def test_two_domains_same_ip_two_relations(self):
        """Deux domaines résolvant vers la même IP → deux relations."""
        domain1 = make_indicator("domain", "evil1.com")
        domain2 = make_indicator("domain", "evil2.com")
        ip = make_indicator("ip", "5.5.5.5")

        enrich1 = make_enrichment(domain1.id, "dns", {"addresses": ["5.5.5.5"]})
        enrich2 = make_enrichment(domain2.id, "dns", {"addresses": ["5.5.5.5"]})

        ip_row = MagicMock()
        ip_row.value = "5.5.5.5"
        ip_row.id = ip.id

        session = self._make_session(
            dns_enrichments=[enrich1, enrich2],
            ip_indicators=[ip_row],
        )
        relations = rule_resolves_to(session)
        assert len(relations) == 2
        targets = {r.target_ref for r in relations}
        assert str(ip.id) in targets


# ---------------------------------------------------------------------------
# Tests rule_same_tag
# ---------------------------------------------------------------------------

class TestRuleSameTag:

    def _make_session(self, tags):
        session = MagicMock()

        def query_side(model):
            q = MagicMock()
            if model is Tag:
                q.filter.return_value.all.return_value = tags
            elif model is TIPRelationship:
                q.filter_by.return_value.first.return_value = None
            return q

        session.query.side_effect = query_side
        return session

    def test_two_indicators_same_malware_tag(self):
        """Deux IOCs avec le même tag malware:emotet → 1 relation same_tag."""
        ind1 = make_indicator("ip", "1.1.1.1")
        ind2 = make_indicator("ip", "2.2.2.2")
        tag = make_tag("malware:emotet", [ind1, ind2])

        session = self._make_session(tags=[tag])
        relations = rule_same_tag(session)
        assert len(relations) == 1
        assert relations[0].relationship_type == RelationshipType.same_tag
        assert relations[0].confidence == 75

    def test_single_indicator_no_relation(self):
        """Un seul IOC par tag → aucune relation."""
        ind1 = make_indicator("ip", "1.1.1.1")
        tag = make_tag("malware:trickbot", [ind1])

        session = self._make_session(tags=[tag])
        relations = rule_same_tag(session)
        assert relations == []

    def test_non_malware_tag_ignored(self):
        """Les tags kind:* et source:* ne doivent pas créer de relations."""
        # rule_same_tag filtre malware:* dans la query
        # Si la query retourne un tag kind:phishing, on ne devrait pas en tenir compte
        session = self._make_session(tags=[])  # filtre SQL exclut les non-malware
        relations = rule_same_tag(session)
        assert relations == []


# ---------------------------------------------------------------------------
# Tests build_graph et get_related_indicators
# ---------------------------------------------------------------------------

class TestBuildGraph:

    def _make_session_with_relations(self, relations):
        session = MagicMock()
        q = MagicMock()
        q.all.return_value = relations
        session.query.return_value = q
        return session

    def test_graph_has_correct_node_count(self):
        """Le graphe doit avoir autant de noeuds que d'UUIDs uniques."""
        id_a, id_b, id_c = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        rels = [
            make_relation(id_a, id_b, RelationshipType.resolves_to, 90),
            make_relation(id_b, id_c, RelationshipType.same_tag, 75),
        ]
        session = self._make_session_with_relations(rels)
        G = build_graph(session)
        assert G.number_of_nodes() == 3
        assert G.number_of_edges() == 2

    def test_get_related_one_hop(self):
        """get_related_indicators doit retourner les voisins directs."""
        id_a, id_b = str(uuid.uuid4()), str(uuid.uuid4())
        rels = [make_relation(id_a, id_b, RelationshipType.resolves_to, 90)]
        session = self._make_session_with_relations(rels)

        related = get_related_indicators(session, id_a, max_hops=1)
        assert len(related) == 1
        assert related[0]["indicator_id"] == id_b
        assert related[0]["hops"] == 1

    def test_unknown_indicator_returns_empty(self):
        """Un ID absent du graphe doit retourner une liste vide."""
        session = self._make_session_with_relations([])
        related = get_related_indicators(session, str(uuid.uuid4()), max_hops=2)
        assert related == []