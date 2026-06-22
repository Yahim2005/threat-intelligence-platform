"""Fixtures partagées pour les tests d'intégration.

La fixture `db_session` crée le schéma complet dans tip_test au début
de la session pytest, puis le détruit à la fin. Chaque test reçoit une
transaction qui est rollbackée après le test — la base reste propre
entre chaque test sans avoir à recréer le schéma à chaque fois.
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.enums import (
    IOCType, IndicatorStatus, TLPLevel, SourceType, RunStatus
)

TEST_DATABASE_URL = "postgresql+psycopg2://tip:tip_secret@localhost:5433/tip_test"


@pytest.fixture(scope="session")
def test_engine():
    """Crée le schéma une fois pour toute la session pytest."""
    engine = create_engine(TEST_DATABASE_URL)

    # Crée tous les types enum PostgreSQL + toutes les tables
    Base.metadata.create_all(engine)
    yield engine

    # Détruit tout après la session
    Base.metadata.drop_all(engine)
    engine.dispose()


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