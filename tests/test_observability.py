# tests/test_observability.py

import pytest
from fastapi.testclient import TestClient
from api.main import app, limiter, _metrics

client = TestClient(app)


# ─── Fixture : reset rate limiter + métriques entre chaque test ───────────────

@pytest.fixture(autouse=True)
def reset_state():
    """
    Réinitialise le rate limiter et les métriques avant chaque test.
    Sans ça, les compteurs du limiter persistent et cassent les tests suivants.
    """
    limiter.reset()
    _metrics["requests_total"] = 0
    _metrics["requests_4xx"] = 0
    _metrics["requests_5xx"] = 0
    _metrics["requests_by_path"].clear()
    _metrics["latency_total_ms"] = 0.0
    yield


# ─── /health ─────────────────────────────────────────────────────────────────

def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_structure():
    data = client.get("/health").json()
    assert "status" in data
    assert "db" in data
    assert "version" in data


def test_health_status_ok():
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"


def test_health_version():
    data = client.get("/health").json()
    assert data["version"] == "1.0.0"


# ─── /metrics ────────────────────────────────────────────────────────────────

def test_metrics_returns_200():
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_structure():
    data = client.get("/metrics").json()
    assert "requests_total" in data
    assert "requests_4xx" in data
    assert "requests_5xx" in data
    assert "avg_latency_ms" in data
    assert "requests_by_path" in data


def test_metrics_counts_requests():
    # On fait 3 requêtes sur /health puis on vérifie les compteurs
    client.get("/health")
    client.get("/health")
    client.get("/health")
    data = client.get("/metrics").json()
    # 3 /health comptés + la requête /metrics elle-même
    # n'est pas encore comptée au moment où la réponse est lue
    assert data["requests_total"] == 3
    assert data["requests_by_path"].get("/health") == 3


def test_metrics_counts_4xx():
    # Une requête 404 doit incrémenter requests_4xx
    client.get("/indicators/cette-ip-nexiste-vraiment-pas-du-tout")
    data = client.get("/metrics").json()
    assert data["requests_4xx"] >= 1


def test_metrics_avg_latency_positive():
    client.get("/health")
    data = client.get("/metrics").json()
    assert data["avg_latency_ms"] >= 0


# ─── Rate limiting ────────────────────────────────────────────────────────────

def test_rate_limit_allows_under_limit():
    """60 requêtes doivent toutes passer."""
    for _ in range(60):
        r = client.get("/indicators?page_size=1")
        assert r.status_code == 200


def test_rate_limit_blocks_over_limit():
    """La 61ème requête doit recevoir un 429."""
    for _ in range(60):
        client.get("/indicators?page_size=1")
    response = client.get("/indicators?page_size=1")
    assert response.status_code == 429


def test_rate_limit_response_body():
    """Le corps du 429 doit contenir un message d'erreur."""
    for _ in range(61):
        r = client.get("/indicators?page_size=1")
    last = r
    assert last.status_code == 429
    # slowapi retourne un JSON avec "error"
    assert "error" in last.json()


def test_rate_limit_does_not_affect_health():
    """Le rate limiting sur /indicators ne doit pas bloquer /health."""
    for _ in range(65):
        client.get("/indicators?page_size=1")
    # /health n'a pas de décorateur @limiter.limit() → toujours accessible
    response = client.get("/health")
    assert response.status_code == 200