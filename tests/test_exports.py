# tests/test_exports.py

import json
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
API_KEY = "tip-secret-dev-key-2024"
HEADERS = {"X-API-Key": API_KEY}


# ─── Auth ────────────────────────────────────────────────────────────────────

def test_export_without_credentials_returns_401():
    # /export/* accepte désormais soit une clé API (partenaire), soit un
    # token Bearer (utilisateur dashboard) -- voir get_current_user_or_api_key
    # dans api/auth.py. Sans AUCUN des deux, l'identité n'est pas établie :
    # 401, cohérent avec get_current_user qui traite déjà ce cas ainsi.
    # Une clé API présente mais invalide reste un 403 (test ci-dessous).
    assert client.get("/export/blocklist").status_code == 401

def test_export_with_wrong_key_returns_403():
    assert client.get("/export/blocklist", headers={"X-API-Key": "mauvaise-cle"}).status_code == 403

def test_export_with_valid_key_returns_200():
    assert client.get("/export/blocklist", headers=HEADERS).status_code == 200


# ─── Blocklist ───────────────────────────────────────────────────────────────

def test_blocklist_returns_plain_text():
    response = client.get("/export/blocklist", headers=HEADERS)
    assert "text/plain" in response.headers["content-type"]

def test_blocklist_contains_values():
    response = client.get("/export/blocklist?type=ip", headers=HEADERS)
    lines = [l for l in response.text.strip().split("\n") if l]
    assert len(lines) > 0

def test_blocklist_confidence_filter():
    high = client.get("/export/blocklist?confidence_min=90", headers=HEADERS).text.strip().split("\n")
    low = client.get("/export/blocklist?confidence_min=10", headers=HEADERS).text.strip().split("\n")
    # Seuil plus bas → plus de résultats
    assert len(low) >= len(high)


# ─── CSV ─────────────────────────────────────────────────────────────────────

def test_csv_returns_200():
    response = client.get("/export/csv", headers=HEADERS)
    assert response.status_code == 200

def test_csv_has_header():
    response = client.get("/export/csv?type=ip&confidence_min=70", headers=HEADERS)
    first_line = response.text.strip().split("\n")[0]
    assert "value" in first_line
    assert "type" in first_line
    assert "confidence" in first_line

def test_csv_rows_match_type_filter():
    response = client.get("/export/csv?type=ip&confidence_min=50", headers=HEADERS)
    lines = response.text.strip().split("\n")
    # Ignore l'en-tête
    for line in lines[1:]:
        cols = line.split(",")
        assert cols[1] == "ip"


# ─── STIX ────────────────────────────────────────────────────────────────────

def test_stix_returns_200():
    response = client.get("/export/stix?type=sha256&confidence_min=70", headers=HEADERS)
    assert response.status_code == 200

def test_stix_is_valid_bundle():
    response = client.get("/export/stix?type=sha256&confidence_min=70", headers=HEADERS)
    data = response.json()
    assert data["type"] == "bundle"
    assert "objects" in data
    assert isinstance(data["objects"], list)

def test_stix_objects_are_indicators():
    response = client.get("/export/stix?type=sha256&confidence_min=70", headers=HEADERS)
    data = response.json()
    for obj in data["objects"]:
        assert obj["type"] == "indicator"
        assert obj["spec_version"] == "2.1"
        assert "pattern" in obj

def test_stix_pattern_format():
    response = client.get("/export/stix?type=sha256&confidence_min=70", headers=HEADERS)
    data = response.json()
    for obj in data["objects"]:
        # Pattern doit commencer par [ et finir par ]
        assert obj["pattern"].startswith("[")
        assert obj["pattern"].endswith("]")

def test_stix_tlp_marking():
    response = client.get("/export/stix?type=sha256&confidence_min=70", headers=HEADERS)
    data = response.json()
    for obj in data["objects"]:
        assert "object_marking_refs" in obj
        assert len(obj["object_marking_refs"]) > 0