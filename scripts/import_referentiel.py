"""
Import du référentiel institutionnel Cameroun.

Source : Annuaire_institutionnel_Cameroun_domaines_officiels_v1.xlsx
92 institutions, domaines vérifiés ou pré-identifiés (à confirmer).

Remplace/complète le seed initial (scripts/seed_monitored_assets.py)
avec des données bien plus fiables. Idempotent : upsert par acronyme.
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

# (acronyme, nom, domaine, categorie, statut, tutelle)
REFERENTIEL = [
    ("PRC", "Présidence de la République du Cameroun", "prc.cm", AssetCategory.institution, DomainStatus.confirmed, "Présidence"),
    ("SPM", "Services du Premier Ministre", "spm.gov.cm", AssetCategory.institution, DomainStatus.confirmed, "Premier Ministre"),
    ("AN", "Assemblée nationale du Cameroun", "assnat.cm", AssetCategory.institution, DomainStatus.unconfirmed, "Pouvoir législatif"),
    ("SÉNAT", "Sénat du Cameroun", "senat.cm", AssetCategory.institution, DomainStatus.unconfirmed, "Pouvoir législatif"),
    ("CC", "Conseil constitutionnel", "conseilconstitutionnel.cm", AssetCategory.institution, DomainStatus.unconfirmed, "Institution constitutionnelle"),
    ("CONAC", "Commission nationale anti-corruption", "conac.cm", AssetCategory.institution, DomainStatus.unconfirmed, "Présidence"),
    ("CONSUPE", "Contrôle supérieur de l'État", "consupe.gov.cm", AssetCategory.institution, DomainStatus.unconfirmed, "Présidence"),
    ("ELECAM", "Elections Cameroon", "elecam.cm", AssetCategory.institution, DomainStatus.unconfirmed, "Institution électorale"),
    ("MINAT", "Ministère de l'Administration territoriale", "minat.gov.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINDEF", "Ministère de la Défense", "mindef.gov.cm", AssetCategory.ministry, DomainStatus.confirmed, "Présidence"),
    ("MINJUSTICE", "Ministère de la Justice", "justice.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINREX", "Ministère des Relations extérieures", "diplocam.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINFI", "Ministère des Finances", "minfi.gov.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINDCAF", "Ministère des Domaines, du Cadastre et des Affaires foncières", "mindcaf.gov.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINEPAT", "Ministère de l'Économie, de la Planification et de l'Aménagement du territoire", "minepat.gov.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINCOMMERCE", "Ministère du Commerce", "mincommerce.gov.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINMIDT", "Ministère des Mines, de l'Industrie et du Développement technologique", "minmidt.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINPMEESA", "Ministère des PME, de l'Économie sociale et de l'Artisanat", "minpmeesa.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINMAP", "Ministère des Marchés publics", "minmap.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Présidence"),
    ("MINFOPRA", "Ministère de la Fonction publique et de la Réforme administrative", "minfopra.gov.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINEDUB", "Ministère de l'Éducation de base", "minedub.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINESEC", "Ministère des Enseignements secondaires", "minesec.gov.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINESUP", "Ministère de l'Enseignement supérieur", "minesup.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINEFOP", "Ministère de l'Emploi et de la Formation professionnelle", "minefop.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINRESI", "Ministère de la Recherche scientifique et de l'Innovation", "minresi.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINSANTE", "Ministère de la Santé publique", "minsante.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINAS", "Ministère des Affaires sociales", "minas.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINPROFF", "Ministère de la Promotion de la Femme et de la Famille", "minproff.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINJEC", "Ministère de la Jeunesse et de l'Éducation civique", "minjec.gov.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINSEP", "Ministère des Sports et de l'Éducation physique", "minsep.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINAC", "Ministère des Arts et de la Culture", "minac.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINCOM", "Ministère de la Communication", "mincom.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINPOSTEL", "Ministère des Postes et Télécommunications", "minpostel.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINT", "Ministère des Transports", "mint.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINTP", "Ministère des Travaux publics", "mintp.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINEE", "Ministère de l'Eau et de l'Énergie", "minee.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINHDU", "Ministère de l'Habitat et du Développement urbain", "minhdu.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINDDEVEL", "Ministère de la Décentralisation et du Développement local", "minddevel.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINADER", "Ministère de l'Agriculture et du Développement rural", "minader.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINEPIA", "Ministère de l'Élevage, des Pêches et des Industries animales", "minepia.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINFOF", "Ministère des Forêts et de la Faune", "minfof.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINEPDED", "Ministère de l'Environnement, de la Protection de la nature et du Développement durable", "minepded.gov.cm", AssetCategory.ministry, DomainStatus.confirmed, "Gouvernement"),
    ("MINTOUL", "Ministère du Tourisme et des Loisirs", "mintoul.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("MINTSS", "Ministère du Travail et de la Sécurité sociale", "mintss.gov.cm", AssetCategory.ministry, DomainStatus.unconfirmed, "Gouvernement"),
    ("CAMTEL", "Cameroon Telecommunications", "camtel.cm", AssetCategory.public_company, DomainStatus.confirmed, "MINPOSTEL"),
    ("CAMPOST", "Cameroon Postal Services", "campost.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINPOSTEL"),
    ("CAMWATER", "Cameroon Water Utilities Corporation", "camwater.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINEE"),
    ("SONATREL", "Société nationale de transport de l'électricité", "sonatrel.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINEE"),
    ("EDC", "Electricity Development Corporation", "edc.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINEE"),
    ("SNH", "Société nationale des hydrocarbures", "snh.cm", AssetCategory.public_company, DomainStatus.confirmed, "Présidence"),
    ("SONARA", "Société nationale de raffinage", "sonara-cm.cm", AssetCategory.public_company, DomainStatus.confirmed, "MINEE / MINMIDT"),
    ("SCDP", "Société camerounaise des dépôts pétroliers", "scdp.cm", AssetCategory.public_company, DomainStatus.confirmed, "MINEE"),
    ("SONAMINES", "Société nationale des mines", "sonamines.cm", AssetCategory.public_company, DomainStatus.confirmed, "MINMIDT"),
    ("SODECOTON", "Société de développement du coton du Cameroun", "sodecoton.cm", AssetCategory.public_company, DomainStatus.confirmed, "MINADER"),
    ("CDC", "Cameroon Development Corporation", "cdc-cameroon.com", AssetCategory.public_company, DomainStatus.unconfirmed, "MINADER"),
    ("SEMRY", "Société d'expansion et de modernisation de la riziculture de Yagoua", "semry.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINADER"),
    ("SODEPA", "Société de développement et d'exploitation des productions animales", "sodepa.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINEPIA"),
    ("CICAM", "Cotonnière industrielle du Cameroun", "cicam.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINMIDT"),
    ("CAMAIR-CO", "Cameroon Airlines Corporation", "camair-co.cm", AssetCategory.public_company, DomainStatus.confirmed, "MINT"),
    ("ADC", "Aéroports du Cameroun", "adcsa.aero", AssetCategory.public_company, DomainStatus.unconfirmed, "MINT"),
    ("PAD", "Port autonome de Douala", "pad.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINT"),
    ("PAK", "Port autonome de Kribi", "pak.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINT"),
    ("SIC", "Société immobilière du Cameroun", "sic.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINHDU"),
    ("MAETUR", "Mission d'aménagement et d'équipement des terrains urbains et ruraux", "maetur.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINHDU"),
    ("MAGZI", "Mission d'aménagement et de gestion des zones industrielles", "magzicameroun.com", AssetCategory.public_company, DomainStatus.unconfirmed, "MINMIDT"),
    ("LABOGENIE", "Laboratoire national de génie civil", "labogenie.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINTP"),
    ("MATGENIE", "Parc national de matériel de génie civil", "matgenie.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINTP"),
    ("CFC", "Crédit foncier du Cameroun", "creditfoncier.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINFI / MINHDU"),
    ("BC-PME", "Banque camerounaise des PME", "bcpme.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINFI / MINPMEESA"),
    ("SNI", "Société nationale d'investissement du Cameroun", "sni.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "Présidence"),
    ("SRC", "Société de recouvrement des créances du Cameroun", "src.cm", AssetCategory.public_company, DomainStatus.unconfirmed, "MINFI"),
    ("ANTIC", "Agence nationale des technologies de l'information et de la communication", "antic.cm", AssetCategory.institution, DomainStatus.confirmed, "MINPOSTEL"),
    ("ART", "Agence de régulation des télécommunications", "art.cm", AssetCategory.institution, DomainStatus.confirmed, "MINPOSTEL"),
    ("ARMP", "Agence de régulation des marchés publics", "armp.cm", AssetCategory.institution, DomainStatus.confirmed, "Présidence / MINMAP"),
    ("ARSEL", "Agence de régulation du secteur de l'électricité", "arsel.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINEE"),
    ("AER", "Agence d'électrification rurale", "aer.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINEE"),
    ("CCAA", "Cameroon Civil Aviation Authority", "ccaa.aero", AssetCategory.institution, DomainStatus.confirmed, "MINT"),
    ("FEICOM", "Fonds spécial d'équipement et d'intervention intercommunale", "feicom.cm", AssetCategory.institution, DomainStatus.confirmed, "MINDDEVEL"),
    ("CNPS", "Caisse nationale de prévoyance sociale", "cnps.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINTSS"),
    ("CAA", "Caisse autonome d'amortissement", "caa.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINFI"),
    ("FNE", "Fonds national de l'emploi", "fnecm.org", AssetCategory.institution, DomainStatus.unconfirmed, "MINEFOP"),
    ("INS", "Institut national de la statistique", "ins-cameroun.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINEPAT"),
    ("IRAD", "Institut de recherche agricole pour le développement", "irad.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINRESI"),
    ("ONCC", "Office national du cacao et du café", "oncc.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINCOMMERCE"),
    ("CENAME", "Centrale nationale d'approvisionnement en médicaments essentiels", "cename.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINSANTE"),
    ("OBC", "Office du baccalauréat du Cameroun", "obc.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINESEC"),
    ("GCE BOARD", "Cameroon General Certificate of Education Board", "camgceb.org", AssetCategory.institution, DomainStatus.unconfirmed, "MINESEC"),
    ("MIPROMALO", "Mission de promotion des matériaux locaux", "mipromalo.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINRESI"),
    ("API", "Agence de promotion des investissements", "investincameroon.net", AssetCategory.institution, DomainStatus.unconfirmed, "MINEPAT"),
    ("APME", "Agence de promotion des PME", "apme.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINPMEESA"),
    ("ANAFOR", "Agence nationale d'appui au développement forestier", "anafor.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINFOF"),
    ("ONACC", "Observatoire national sur les changements climatiques", "onacc.cm", AssetCategory.institution, DomainStatus.unconfirmed, "MINEPDED"),
]


def run() -> None:
    session = SessionLocal()
    added, updated, skipped = 0, 0, 0
    try:
        for acronym, nom, domaine, category, status, tutelle in REFERENTIEL:
            existing = (
                session.query(MonitoredAsset)
                .filter((MonitoredAsset.acronym == acronym) | (MonitoredAsset.name == nom))
                .first()
            )
            if existing:
                changed = False
                if domaine and existing.domain != domaine:
                    existing.domain = domaine
                    changed = True
                if existing.domain_status != status:
                    existing.domain_status = status
                    changed = True
                if not existing.acronym and acronym:
                    existing.acronym = acronym
                    changed = True
                if changed:
                    updated += 1
                else:
                    skipped += 1
                continue
            asset = MonitoredAsset(
                name=nom,
                acronym=acronym or None,
                category=category,
                domain=domaine or None,
                domain_status=status,
            )
            session.add(asset)
            added += 1
        session.commit()
        print(f"{added} ajoutés, {updated} mis à jour, {skipped} déjà à jour")

        total = session.query(MonitoredAsset).count()
        confirmed = session.query(MonitoredAsset).filter_by(domain_status=DomainStatus.confirmed).count()
        with_domain = session.query(MonitoredAsset).filter(MonitoredAsset.domain.isnot(None)).count()
        print(f"Total : {total} | domaines confirmés : {confirmed} | avec domaine renseigné : {with_domain}")
    finally:
        session.close()


if __name__ == "__main__":
    run()
