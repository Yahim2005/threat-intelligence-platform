"""Fixtures partagées pour les tests d'intégration.

La fixture `db_session` crée le schéma complet dans tip_test au début
de la session pytest, puis le détruit à la fin. Chaque test reçoit une
transaction qui est rollbackée après le test — la base reste propre
entre chaque test sans avoir à recréer le schéma à chaque fois.
"""
import os
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


# GARDE-FOU CRITIQUE : cette valeur est fixee AVANT tout import de app.*.
# app.database appelle load_dotenv() a l'import ; sans cet ordre, la suite peut
# reutiliser DATABASE_URL depuis le .env de production. TEST_DATABASE_URL est
# le seul override accepte, et uniquement vers une base PostgreSQL locale dont
# le nom commence par "tip_test". Une erreur de CI doit faire echouer les tests,
# jamais les rediriger silencieusement vers une base distante.
DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg2://tip:tip_secret@127.0.0.1:5433/tip_test"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
_test_url = make_url(TEST_DATABASE_URL)

if not _test_url.drivername.startswith("postgresql"):
    raise RuntimeError("TEST_DATABASE_URL doit utiliser PostgreSQL.")
if _test_url.host not in {"localhost", "127.0.0.1", "::1"}:
    raise RuntimeError("TEST_DATABASE_URL doit cibler exclusivement une base locale.")
if not (_test_url.database or "").startswith("tip_test"):
    raise RuntimeError("Le nom de la base de test doit commencer par 'tip_test'.")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET_KEY", "pytest-only-jwt-secret-never-use-in-production")
os.environ.setdefault("TIP_API_KEY", "tip-secret-dev-key-2024")

from app.models.base import Base
from app.models.enums import (
    IOCType, IndicatorStatus, TLPLevel, SourceType, RunStatus
)


TEST_USER_ID = UUID("10000000-0000-0000-0000-000000000001")
TEST_ADMIN_ID = UUID("10000000-0000-0000-0000-000000000002")


@pytest.fixture(scope="session", autouse=True)
def test_engine():
    """Recrée le schéma dans la base locale dédiée, puis le détruit."""
    engine = create_engine(TEST_DATABASE_URL)

    # Cette suppression est sûre grâce aux contrôles stricts ci-dessus.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine

    # Détruit tout après la session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def seed_api_test_data(test_engine):
    """Jeu minimal déterministe pour les tests API historiques."""
    from app.database import SessionLocal
    from app.models import Indicator, Source, Threat, User
    from app.models.enums import ThreatType, UserRole
    from app.security import hash_password

    session = SessionLocal()
    try:
        user = User(
            id=TEST_USER_ID,
            email="user@tip.test",
            full_name="Test User",
            hashed_password=hash_password("TestPassword123!"),
            role=UserRole.user,
            is_active=True,
        )
        admin = User(
            id=TEST_ADMIN_ID,
            email="admin@tip.test",
            full_name="Test Admin",
            hashed_password=hash_password("TestPassword123!"),
            role=UserRole.admin,
            is_active=True,
        )
        source = Source(
            id=uuid4(),
            name="API Test Source",
            url="https://example.test/feed",
            source_type=SourceType.feed,
            tlp=TLPLevel.CLEAR,
            is_active=True,
        )
        collector_sources = [
            Source(name=name, source_type=SourceType.feed, tlp=TLPLevel.CLEAR, is_active=True)
            for name in (
                "OpenPhish",
                "abuse.ch - Feodo",
                "abuse.ch - ThreatFox",
                "Spamhaus - DROP",
            )
        ]
        session.add_all([user, admin, source, *collector_sources])
        session.flush()

        indicators = []
        for index in range(12):
            indicator = Indicator(
                id=uuid4(),
                value=f"198.51.100.{index + 1}",
                type=IOCType.ip,
                status=IndicatorStatus.active,
                confidence=80 + (index % 10),
                tlp=TLPLevel.CLEAR,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                source_id=source.id,
            )
            indicators.append(indicator)
        indicators.append(Indicator(
            id=uuid4(),
            value="a" * 64,
            type=IOCType.sha256,
            status=IndicatorStatus.active,
            confidence=90,
            tlp=TLPLevel.CLEAR,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            source_id=source.id,
        ))
        session.add_all(indicators)
        session.flush()

        for index in range(5):
            threat = Threat(
                id=uuid4(),
                name=f"API Test Threat {index + 1}",
                threat_type=ThreatType.campaign,
                description="Threat de test",
                tlp=TLPLevel.CLEAR,
            )
            threat.indicators = [indicators[index]]
            session.add(threat)
        session.commit()
        yield
    finally:
        session.close()


@pytest.fixture(scope="session")
def user_headers(seed_api_test_data):
    from app.security import create_access_token
    token = create_access_token({"sub": str(TEST_USER_ID), "role": "user"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_headers(seed_api_test_data):
    from app.security import create_access_token
    token = create_access_token({"sub": str(TEST_ADMIN_ID), "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Fournit une session DB propre par test via rollback automatique.

    Pattern transaction-savepoint : on ouvre une transaction externe
    qui ne sera jamais committée — tout ce que le test écrit est
    annulé automatiquement à la fin, sans recréer le schéma.
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_source(db_session):
    """Insère une Source de test réutilisable dans les tests d'intégration."""
    from app.models import Source
    source = Source(
        name="Test Source",
        url="https://example.com/feed",
        source_type=SourceType.feed,
        tlp=TLPLevel.CLEAR,
        is_active=True,
    )
    db_session.add(source)
    db_session.flush()
    return source
