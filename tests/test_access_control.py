"""Matrice d'acces JWT/TLP et fermeture de l'inscription publique."""
from __future__ import annotations

from datetime import datetime
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.main import app, limiter
from app.database import DATABASE_URL, SessionLocal
from app.models import Indicator, Source, Threat, User
from app.models.enums import (
    IOCType,
    IndicatorStatus,
    RelationshipType,
    TLPLevel,
    ThreatType,
)
from app.models.relationship import TIPRelationship
from api.taxii import COLLECTION_ID


client = TestClient(app)

GENERAL_READ_ROUTES = [
    "/metrics",
    "/indicators",
    "/indicators/unknown.example/related",
    "/indicators/unknown.example/timeline",
    "/indicators/unknown.example",
    "/sources",
    "/threats",
    f"/threats/{uuid4()}",
    "/alerts",
    "/analytics/top-sources",
    "/analytics/top-tags",
    "/analytics/confidence-distribution",
    "/collection-runs",
    "/stats/trends",
    "/stats",
    "/cameroon/overview",
    "/exposed-assets",
    "/monitored-assets",
    "/cameroon/timeline",
    "/cameroon/institutions/ranked",
    "/cameroon/vuln-severity",
    "/cameroon/sector-breakdown",
    "/cameroon/top-ports",
]


@pytest.fixture(autouse=True)
def reset_limiter():
    limiter.reset()
    yield


@pytest.fixture(scope="module")
def tlp_matrix(seed_api_test_data):
    session = SessionLocal()
    source = session.query(Source).filter_by(name="API Test Source").one()
    indicators = {}
    threats = {}
    relationship_id = uuid4()
    try:
        for level in TLPLevel:
            suffix = level.value.lower().replace("_", "-")
            indicator = Indicator(
                id=uuid4(),
                value=f"tlp-matrix-{suffix}@example.test",
                type=IOCType.email,
                status=IndicatorStatus.active,
                confidence=99,
                tlp=level,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                source_id=source.id,
            )
            threat = Threat(
                id=uuid4(),
                name=f"TLP Matrix {level.value}",
                threat_type=ThreatType.campaign,
                description="Controle de diffusion TLP",
                tlp=level,
            )
            threat.indicators = [indicator]
            session.add_all([indicator, threat])
            indicators[level] = indicator
            threats[level] = threat
        session.flush()
        session.add(TIPRelationship(
            id=relationship_id,
            source_ref=str(indicators[TLPLevel.CLEAR].id),
            target_ref=str(indicators[TLPLevel.RED].id),
            relationship_type=RelationshipType.same_tag,
            confidence=100,
            rule="tlp-isolation-test",
        ))
        session.commit()
        yield {
            "indicator_values": {level: ind.value for level, ind in indicators.items()},
            "threat_ids": {level: str(threat.id) for level, threat in threats.items()},
        }
    finally:
        session.rollback()
        session.query(User).filter(User.email == "created-by-admin@example.com").delete()
        session.query(TIPRelationship).filter(TIPRelationship.id == relationship_id).delete()
        for threat in threats.values():
            stored = session.get(Threat, threat.id)
            if stored:
                session.delete(stored)
        for indicator in indicators.values():
            stored = session.get(Indicator, indicator.id)
            if stored:
                session.delete(stored)
        session.commit()
        session.close()


@pytest.mark.parametrize("path", GENERAL_READ_ROUTES)
def test_general_read_routes_require_authentication(path):
    assert client.get(path).status_code == 401


def test_database_configuration_is_forced_to_local_test_database():
    assert DATABASE_URL == os.environ["DATABASE_URL"]
    assert "127.0.0.1" in DATABASE_URL or "localhost" in DATABASE_URL
    assert "/tip_test" in DATABASE_URL
    assert "production.invalid" not in DATABASE_URL


def test_user_indicator_list_only_contains_clear_and_green(user_headers, tlp_matrix):
    response = client.get("/indicators?search=tlp-matrix-&page_size=20", headers=user_headers)
    assert response.status_code == 200, response.text
    assert {item["tlp"] for item in response.json()["items"]} == {"CLEAR", "GREEN"}


def test_admin_indicator_list_includes_amber_but_never_red(admin_headers, tlp_matrix):
    response = client.get("/indicators?search=tlp-matrix-&page_size=20", headers=admin_headers)
    assert response.status_code == 200
    assert {item["tlp"] for item in response.json()["items"]} == {
        "CLEAR", "GREEN", "AMBER", "AMBER_STRICT"
    }


@pytest.mark.parametrize(
    "role_fixture,level,expected_status",
    [
        ("user_headers", TLPLevel.CLEAR, 200),
        ("user_headers", TLPLevel.GREEN, 200),
        ("user_headers", TLPLevel.AMBER, 404),
        ("user_headers", TLPLevel.AMBER_STRICT, 404),
        ("user_headers", TLPLevel.RED, 404),
        ("admin_headers", TLPLevel.AMBER, 200),
        ("admin_headers", TLPLevel.AMBER_STRICT, 200),
        ("admin_headers", TLPLevel.RED, 404),
    ],
)
def test_direct_indicator_access_obeys_tlp(
    request, role_fixture, level, expected_status, tlp_matrix
):
    headers = request.getfixturevalue(role_fixture)
    value = tlp_matrix["indicator_values"][level]
    assert client.get(f"/indicators/{value}", headers=headers).status_code == expected_status


def test_user_threat_list_only_contains_clear_and_green(user_headers, tlp_matrix):
    response = client.get("/threats?page_size=100", headers=user_headers)
    matrix_names = {item["name"] for item in response.json() if item["name"].startswith("TLP Matrix")}
    assert matrix_names == {"TLP Matrix CLEAR", "TLP Matrix GREEN"}


def test_admin_threat_access_never_returns_red(admin_headers, tlp_matrix):
    for level in (TLPLevel.AMBER, TLPLevel.AMBER_STRICT):
        threat_id = tlp_matrix["threat_ids"][level]
        assert client.get(f"/threats/{threat_id}", headers=admin_headers).status_code == 200
    red_id = tlp_matrix["threat_ids"][TLPLevel.RED]
    assert client.get(f"/threats/{red_id}", headers=admin_headers).status_code == 404


def test_stats_do_not_disclose_forbidden_tlp_levels(user_headers, admin_headers, tlp_matrix):
    user_counts = client.get("/stats", headers=user_headers).json()["indicators_by_tlp"]
    admin_counts = client.get("/stats", headers=admin_headers).json()["indicators_by_tlp"]
    assert set(user_counts) <= {"CLEAR", "GREEN"}
    assert set(admin_counts) <= {"CLEAR", "GREEN", "AMBER", "AMBER_STRICT"}
    assert "RED" not in admin_counts


def test_related_and_timeline_never_disclose_red(user_headers, admin_headers, tlp_matrix):
    clear_value = tlp_matrix["indicator_values"][TLPLevel.CLEAR]
    red_value = tlp_matrix["indicator_values"][TLPLevel.RED]
    for headers in (user_headers, admin_headers):
        related = client.get(f"/indicators/{clear_value}/related", headers=headers)
        assert related.status_code == 200
        assert red_value not in {item["value"] for item in related.json()}
        timeline = client.get(f"/indicators/{red_value}/timeline", headers=headers)
        assert timeline.status_code == 200
        assert timeline.json() == []


def test_partner_exports_only_clear_and_green(tlp_matrix):
    response = client.get(
        "/export/csv?type=email&confidence_min=0",
        headers={"X-API-Key": "tip-secret-dev-key-2024"},
    )
    assert response.status_code == 200
    body = response.text
    assert tlp_matrix["indicator_values"][TLPLevel.CLEAR] in body
    assert tlp_matrix["indicator_values"][TLPLevel.GREEN] in body
    assert tlp_matrix["indicator_values"][TLPLevel.AMBER] not in body
    assert tlp_matrix["indicator_values"][TLPLevel.RED] not in body


def test_taxii_remains_protected_and_only_shares_clear_green(tlp_matrix):
    path = f"/taxii2/api/collections/{COLLECTION_ID}/objects?limit=2000&confidence_min=0"
    assert client.get(path).status_code == 403
    response = client.get(path, headers={"X-API-Key": "tip-secret-dev-key-2024"})
    assert response.status_code == 200
    body = response.text
    assert tlp_matrix["indicator_values"][TLPLevel.CLEAR] in body
    assert tlp_matrix["indicator_values"][TLPLevel.GREEN] in body
    assert tlp_matrix["indicator_values"][TLPLevel.AMBER] not in body
    assert tlp_matrix["indicator_values"][TLPLevel.RED] not in body


def test_register_requires_admin(user_headers, admin_headers, tlp_matrix):
    payload = {
        "email": "created-by-admin@example.com",
        "full_name": "Created by Admin",
        "password": "StrongPassword123!",
    }
    assert client.post("/auth/register", json=payload).status_code == 401
    assert client.post("/auth/register", json=payload, headers=user_headers).status_code == 403
    response = client.post("/auth/register", json=payload, headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["user"]["role"] == "user"


def test_red_manual_submission_is_rejected(admin_headers):
    response = client.post(
        "/indicators",
        headers=admin_headers,
        json={"value": "red-api@example.test", "type": "email", "tlp": "RED"},
    )
    assert response.status_code == 422
