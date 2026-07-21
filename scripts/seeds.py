import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        "name": "abuse.ch - Feodo",
        "url": "https://feodotracker.abuse.ch/downloads/ipblocklist.json",
        "source_type": SourceType.feed,
        "tlp": TLPLevel.CLEAR,
    },
    {
        "name": "abuse.ch - ThreatFox",
        "url": "https://threatfox-api.abuse.ch/api/v1/",
        "source_type": SourceType.api,
        "tlp": TLPLevel.CLEAR,
    },
    {
        "name": "Spamhaus - DROP",
        "url": "https://www.spamhaus.org/drop/drop.txt",
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
    {
        "name": "AlienVault OTX Africa",
        "url": "https://otx.alienvault.com/api/v1/search/pulses",
        "source_type": SourceType.api,
        "tlp": TLPLevel.GREEN,
    },
    {
        "name": "OpenPhish",
        "url": "https://openphish.com/feed.txt",
        "source_type": SourceType.feed,
        "tlp": TLPLevel.CLEAR,
    },
    {
        "name": "Tor Project - Exit List",
        "url": "https://check.torproject.org/torbulkexitlist",
        "source_type": SourceType.feed,
        "tlp": TLPLevel.CLEAR,
    },
    {
        "name": "NVD",
        "url": "https://services.nvd.nist.gov/rest/json/cves/2.0",
        "source_type": SourceType.api,
        "tlp": TLPLevel.CLEAR,
    },
    {
        "name": "abuse.ch - MalwareBazaar",
        "url": "https://mb-api.abuse.ch/api/v1/",
        "source_type": SourceType.api,
        "tlp": TLPLevel.CLEAR,
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