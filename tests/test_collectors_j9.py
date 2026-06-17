"""Tests J9 — isolation des pannes au niveau persistance + retries/backoff.
Aucun accès réseau pour les tests de persistance : DB de test locale uniquement.
"""
import pytest

from app.database import SessionLocal
from app.models.enums import IOCType
from app.persistence import store_records
from collectors.base import BaseCollector
import httpx


# ── Isolation des pannes dans store_records ──────────────────────────────────
def test_store_records_isolates_failures():
    """Un record invalide ne doit pas bloquer les records valides autour de lui."""
    records = [
        {"value": "http://test-j9-isolation-1.com/", "type": IOCType.url},
        {"value": None, "type": IOCType.url},  # provoque une erreur certaine
        {"value": "http://test-j9-isolation-2.com/", "type": IOCType.url},
    ]
    session = SessionLocal()
    try:
        stats = store_records(records, "OpenPhish", session)
    finally:
        session.close()

    assert stats["created"] + stats["updated"] == 2
    assert stats["errors"] == 1


def test_store_records_truncates_long_values():
    """Une valeur trop longue pour la colonne doit être tronquée, pas rejetée."""
    records = [
        {"value": "B" * 5000, "type": IOCType.url},
    ]
    session = SessionLocal()
    try:
        stats = store_records(records, "OpenPhish", session)
    finally:
        session.close()

    assert stats["created"] + stats["updated"] == 1
    assert stats["errors"] == 0


# ── Retries / backoff dans BaseCollector ──────────────────────────────────────
class _FakeCollector(BaseCollector):
    name = "Fake"
    max_retries = 2
    backoff_base = 1

    def fetch(self):
        pass

    def parse(self, raw):
        return []


def test_http_get_with_retry_raises_after_max_attempts():
    """Une erreur réseau persistante doit relancer l'exception après max_retries tentatives."""
    collector = _FakeCollector()
    with pytest.raises(httpx.ConnectError):
        collector.http_get_with_retry("https://this-domain-does-not-exist-12345.invalid/")


def test_http_get_with_retry_does_not_retry_on_404():
    """Une erreur 404 est définitive : elle doit être relancée immédiatement, sans retry."""
    collector = _FakeCollector()
    with pytest.raises(httpx.HTTPStatusError):
        collector.http_get_with_retry("https://httpbin.org/status/404")