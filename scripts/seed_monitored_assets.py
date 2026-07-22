"""
Seed initial de la table monitored_assets.

Sources :
- ASN : RIPEstat (country-resource-list, resource=cm) — 21/07/2026
- Ministères : Wikipedia FR "Liste des ministères au Cameroun"
- Banques : APECCAM (apeccam.cm/membres/) — 18 banques + 4 organismes publics
- Entreprises publiques/parapubliques : DGI, Osidimbea, Investir au Cameroun

Statut des domaines :
- confirmed   : domaine vérifié manuellement
- unconfirmed : nom connu, domaine à découvrir (voir scripts/discover_domains.py)
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.monitored_asset import MonitoredAsset
from app.models.enums import AssetCategory, DomainStatus

# (name, category, domain_or_None, domain_status, asn_or_None)
ASSETS = [
    # ─── Télécom / ASN (confirmés via RIPE) ──────────────────────────
    ("Camtel", AssetCategory.telecom, "camtel.cm", DomainStatus.confirmed, 15964),
    ("MTN Cameroon", AssetCategory.telecom, "mtn.cm", DomainStatus.confirmed, 30992),
    ("Orange Cameroun", AssetCategory.telecom, "orange.cm", DomainStatus.confirmed, 36912),
    ("Creolink Communications", AssetCategory.telecom, None, DomainStatus.unconfirmed, 36905),
    ("Matrix Telecoms", AssetCategory.telecom, None, DomainStatus.unconfirmed, 36955),
    ("Sancfis Cameroun", AssetCategory.telecom, None, DomainStatus.unconfirmed, 37089),
    ("GIE Groupe Commercial Bank", AssetCategory.telecom, None, DomainStatus.unconfirmed, 37641),
    ("INQ Digital Cameroon", AssetCategory.telecom, None, DomainStatus.unconfirmed, 37672),
    ("Cameroon Internet Exchange Point (CAMIX)", AssetCategory.telecom, None, DomainStatus.unconfirmed, 37718),
    ("ST Digital", AssetCategory.telecom, None, DomainStatus.unconfirmed, 37790),
    ("INFOGENIE Technologies", AssetCategory.telecom, None, DomainStatus.unconfirmed, 327741),
    ("SWECOM PLC", AssetCategory.telecom, None, DomainStatus.unconfirmed, 327820),
    ("AVS Telecom", AssetCategory.telecom, None, DomainStatus.unconfirmed, 327920),
    ("CAMPASS PLC", AssetCategory.telecom, None, DomainStatus.unconfirmed, 328666),
    ("Newtelnet Cameroun", AssetCategory.telecom, None, DomainStatus.unconfirmed, 328866),
    ("Africa Data Center", AssetCategory.telecom, None, DomainStatus.unconfirmed, 328920),
    ("HTT Telecom", AssetCategory.telecom, None, DomainStatus.unconfirmed, 329375),
    ("Connection Cameroon", AssetCategory.telecom, None, DomainStatus.unconfirmed, 329457),

    # ─── Institutions ─────────────────────────────────────────────
    ("ANTIC", AssetCategory.institution, "antic.cm", DomainStatus.confirmed, 328909),
    ("BEAC", AssetCategory.institution, "beac.int", DomainStatus.confirmed, 328878),
    ("Université de Maroua", AssetCategory.institution, None, DomainStatus.unconfirmed, 328937),
    ("Port Autonome de Kribi", AssetCategory.institution, None, DomainStatus.unconfirmed, 329432),
    ("CAMPOST", AssetCategory.institution, "campost.cm", DomainStatus.confirmed, 329380),
    ("CNSRIC", AssetCategory.institution, None, DomainStatus.unconfirmed, 329607),

    # ─── Ministères ───────────────────────────────────────────────
    ("Ministère de l'Administration territoriale", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Affaires sociales", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de l'Agriculture et du Développement rural", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Arts et de la Culture", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère du Commerce", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de la Communication", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère du Contrôle Supérieur de l'État", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de la Décentralisation et du Développement Local", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de la Défense", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Domaines, du Cadastre et des Affaires foncières", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de l'Eau et de l'Énergie", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de l'Économie, de la Planification et de l'Aménagement du territoire", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de l'Éducation de Base", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de l'Élevage, des Pêches et des Industries Animales", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de l'Emploi et de la Formation Professionnelle", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Enseignements secondaires", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de l'Enseignement Supérieur", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de l'Environnement, de la Protection de la Nature et du Développement Durable", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Finances", AssetCategory.ministry, "minfi.gov.cm", DomainStatus.confirmed, None),
    ("Ministère de la Fonction publique et de la Réforme Administrative", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Forêts et de la Faune", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de l'Habitat et du Développement Urbain", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de la Jeunesse et de l'Éducation civique", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de la Justice", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Marchés Publics", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Mines, de l'Industrie et du Développement technologique", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Petites et Moyennes Entreprises, de l'Économie sociale et de l'Artisanat", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Postes et Télécommunications", AssetCategory.ministry, "minpostel.gov.cm", DomainStatus.confirmed, None),
    ("Ministère de la Promotion de la Femme et de la Famille", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de la Recherche scientifique et de l'Innovation", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère chargé des Relations avec les Assemblées", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Relations extérieures", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère de la Santé publique", AssetCategory.ministry, "minsante.cm", DomainStatus.confirmed, None),
    ("Ministère des Sports et de l'Éducation physique", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère du Tourisme et des Loisirs", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère du Travail et de la Sécurité sociale", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Transports", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Ministère des Travaux publics", AssetCategory.ministry, None, DomainStatus.unconfirmed, None),
    ("Services du Premier Ministre", AssetCategory.ministry, "spm.gov.cm", DomainStatus.confirmed, None),

    # ─── Banques commerciales (18) ────────────────────────────────
    ("Access Bank Cameroon", AssetCategory.bank, None, DomainStatus.unconfirmed, 329469),
    ("Afriland First Bank", AssetCategory.bank, "afrilandfirstbank.com", DomainStatus.confirmed, 329470),
    ("BANGE Bank", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("Banque Atlantique Cameroun", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("BC-PME", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("BGFI Bank Cameroun", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("BICEC", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("CCA Bank", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("Citibank Cameroun", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("Commercial Bank of Cameroon", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("Ecobank Cameroun", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("National Financial Credit Bank", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("Société Générale Cameroun", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("Standard Chartered Bank Cameroun", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("Union Bank Cameroon", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("La Régionale Bank", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("United Bank for Africa Cameroun", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("Crédit Foncier du Cameroun", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("Société de Recouvrement des Créances", AssetCategory.bank, None, DomainStatus.unconfirmed, None),
    ("Société Nationale d'Investissement", AssetCategory.bank, None, DomainStatus.unconfirmed, None),

    # ─── Entreprises publiques ────────────────────────────────────
    ("Aéroports du Cameroun (ADC)", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Camair-Co", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Camwater", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Cameroon Development Corporation (CDC)", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("CRTV", AssetCategory.public_company, "crtv.cm", DomainStatus.confirmed, None),
    ("MAGZI", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("MAETUR", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("MEKIN", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("PAMOL", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Port Autonome de Douala", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("SCDP", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("SEMRY", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Société Nationale des Hydrocarbures (SNH)", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("SODEPA", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("SOPEACM", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Alucam", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Camrail", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Cimencam", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("ENEO Cameroun", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Hevecam", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Hysacam", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Safacam", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("SIC (Société Immobilière du Cameroun)", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Sonatrel", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Sonara", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
    ("Tradex", AssetCategory.public_company, None, DomainStatus.unconfirmed, None),
]


def run() -> None:
    session = SessionLocal()
    added = 0
    skipped = 0
    try:
        for name, category, domain, domain_status, asn in ASSETS:
            existing = session.query(MonitoredAsset).filter_by(name=name).first()
            if existing:
                skipped += 1
                continue
            asset = MonitoredAsset(
                name=name,
                category=category,
                domain=domain,
                domain_status=domain_status,
                asn=asn,
            )
            session.add(asset)
            added += 1
        session.commit()
        print(f"{added} actifs ajoutés, {skipped} déjà existants")

        confirmed = session.query(MonitoredAsset).filter_by(domain_status=DomainStatus.confirmed).count()
        unconfirmed = session.query(MonitoredAsset).filter_by(domain_status=DomainStatus.unconfirmed).count()
        print(f"Domaines confirmés : {confirmed} | à découvrir : {unconfirmed}")
    finally:
        session.close()


if __name__ == "__main__":
    run()
