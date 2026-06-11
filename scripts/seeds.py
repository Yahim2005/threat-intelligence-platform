import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cet import unique charge TOUS les modèles d'un coup via __init__.py
from app.models import Source
from app.database import SessionLocal
from app.models.enums import SourceType, TLPLevel
SOURCES = [
    {
        "name": "abuse.ch - URLhaus",
        "url": "https://urlhaus-api.abuse.ch/v1/",
        "source_type": SourceType.feed,
        "tlp": TLPLevel.CLEAR,
    },
    {
        "name": "CISA KEV",
        "url": "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        "source_type": SourceType.feed,
        "tlp": TLPLevel.CLEAR,
    },
    {
        "name": "AlienVault OTX",
        "url": "https://otx.alienvault.com/api/v1/",
        "source_type": SourceType.api,
        "tlp": TLPLevel.GREEN,
    },
]


def seed():
    session = SessionLocal()
    try:
        inserted = 0
        for data in SOURCES:
            exists = session.query(Source).filter_by(name=data["name"]).first()
            if not exists:
                source = Source(**data)
                session.add(source)
                inserted += 1
                print(f"  ✓ Source ajoutée : {data['name']}")
            else:
                print(f"  - Déjà existante : {data['name']}")
        session.commit()
        print(f"\n{inserted} source(s) insérée(s).")
    finally:
        session.close()


if __name__ == "__main__":
    seed()