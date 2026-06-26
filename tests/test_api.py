# tests/test_api.py

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


# ─── Stats ───────────────────────────────────────────────────────────────────

def test_stats_returns_200():
    response = client.get("/stats")
    assert response.status_code == 200


def test_stats_structure():
    data = client.get("/stats").json()
    assert "total_indicators" in data
    assert "active_indicators" in data
    assert "indicators_by_type" in data
    assert "indicators_by_tlp" in data
    assert isinstance(data["total_indicators"], int)
    assert data["total_indicators"] > 0


# ─── Sources ─────────────────────────────────────────────────────────────────

def test_sources_returns_list():
    response = client.get("/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_sources_structure():
    data = client.get("/sources").json()
    source = data[0]
    assert "id" in source
    assert "name" in source
    assert "is_active" in source
    assert "indicator_count" in source


# ─── Indicators ──────────────────────────────────────────────────────────────

def test_indicators_returns_paginated():
    response = client.get("/indicators?page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert len(data["items"]) == 5


def test_indicators_filter_by_type():
    response = client.get("/indicators?type=ip&page_size=10")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["type"] == "ip"


def test_indicators_filter_by_confidence():
    response = client.get("/indicators?confidence_min=80&page_size=10")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["confidence"] >= 80


def test_indicators_pagination():
    page1 = client.get("/indicators?page=1&page_size=5").json()
    page2 = client.get("/indicators?page=2&page_size=5").json()
    ids_page1 = {i["id"] for i in page1["items"]}
    ids_page2 = {i["id"] for i in page2["items"]}
    # Les deux pages ne doivent pas avoir les mêmes indicateurs
    assert ids_page1.isdisjoint(ids_page2)


def test_indicator_by_value_found():
    # Récupère un indicateur existant depuis la liste
    items = client.get("/indicators?type=ip&page_size=1").json()["items"]
    assert len(items) > 0
    value = items[0]["value"]
    response = client.get(f"/indicators/{value}")
    assert response.status_code == 200
    assert response.json()["value"] == value


def test_indicator_by_value_not_found():
    response = client.get("/indicators/999.999.999.999")
    assert response.status_code == 404


def test_indicators_invalid_confidence():
    # confidence_min > 100 doit retourner 422 (validation error)
    response = client.get("/indicators?confidence_min=150")
    assert response.status_code == 422


# ─── Threats ─────────────────────────────────────────────────────────────────

def test_threats_returns_list():
    response = client.get("/threats?page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5


def test_threats_structure():
    data = client.get("/threats?page_size=1").json()
    threat = data[0]
    assert "id" in threat
    assert "name" in threat
    assert "indicator_count" in threat
    assert "avg_confidence" in threat
    assert "top_tags" in threat