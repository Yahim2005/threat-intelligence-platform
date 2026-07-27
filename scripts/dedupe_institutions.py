"""
Fusionne les 31 doublons detectes dans monitored_assets (institutions
creees deux fois par les scripts de seed initiaux, avant et sans sigle).
Pour chaque paire : la ligne AVEC sigle est gardee et enrichie des champs
manquants pris sur l'autre ligne ; la ligne redondante est desactivee
(active=False), jamais supprimee.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()
from app.database import SessionLocal
from app.models.monitored_asset import MonitoredAsset

PAIRS = [('ANTIC', "Agence nationale des technologies de l'information et de la communication", 'ANTIC'), ('ADC', 'Aéroports du Cameroun', 'Aéroports du Cameroun (ADC)'), ('BC-PME', 'Banque camerounaise des PME', 'BC-PME'), ('CAMPOST', 'Cameroon Postal Services', 'CAMPOST'), ('CAMAIR-CO', 'Cameroon Airlines Corporation', 'Camair-Co'), ('CDC', 'Cameroon Development Corporation', 'Cameroon Development Corporation (CDC)'), ('CAMTEL', 'Cameroon Telecommunications', 'Camtel'), ('CAMWATER', 'Cameroon Water Utilities Corporation', 'Camwater'), ('CFC', 'Crédit foncier du Cameroun', 'Crédit Foncier du Cameroun'), ('MAETUR', "Mission d'aménagement et d'équipement des terrains urbains et ruraux", 'MAETUR'), ('MAGZI', "Mission d'aménagement et de gestion des zones industrielles", 'MAGZI'), ('MINEFOP', "Ministère de l'Emploi et de la Formation professionnelle", "Ministère de l'Emploi et de la Formation Professionnelle"), ('MINESUP', "Ministère de l'Enseignement supérieur", "Ministère de l'Enseignement Supérieur"), ('MINEPDED', "Ministère de l'Environnement, de la Protection de la nature et du Développement durable", "Ministère de l'Environnement, de la Protection de la Nature et du Développement Durable"), ('MINHDU', "Ministère de l'Habitat et du Développement urbain", "Ministère de l'Habitat et du Développement Urbain"), ('MINEDUB', "Ministère de l'Éducation de base", "Ministère de l'Éducation de Base"), ('MINEPIA', "Ministère de l'Élevage, des Pêches et des Industries animales", "Ministère de l'Élevage, des Pêches et des Industries Animales"), ('MINDDEVEL', 'Ministère de la Décentralisation et du Développement local', 'Ministère de la Décentralisation et du Développement Local'), ('MINFOPRA', 'Ministère de la Fonction publique et de la Réforme administrative', 'Ministère de la Fonction publique et de la Réforme Administrative'), ('MINMAP', 'Ministère des Marchés publics', 'Ministère des Marchés Publics'), ('PAD', 'Port autonome de Douala', 'Port Autonome de Douala'), ('PAK', 'Port autonome de Kribi', 'Port Autonome de Kribi'), ('SCDP', 'Société camerounaise des dépôts pétroliers', 'SCDP'), ('SEMRY', "Société d'expansion et de modernisation de la riziculture de Yagoua", 'SEMRY'), ('SIC', 'Société immobilière du Cameroun', 'SIC (Société Immobilière du Cameroun)'), ('SODEPA', "Société de développement et d'exploitation des productions animales", 'SODEPA'), ('SNI', "Société nationale d'investissement du Cameroun", "Société Nationale d'Investissement"), ('SNH', 'Société nationale des hydrocarbures', 'Société Nationale des Hydrocarbures (SNH)'), ('SRC', 'Société de recouvrement des créances du Cameroun', 'Société de Recouvrement des Créances'), ('SONARA', 'Société nationale de raffinage', 'Sonara'), ('SONATREL', "Société nationale de transport de l'électricité", 'Sonatrel')]

def run():
    session = SessionLocal()
    merged, not_found = 0, 0
    try:
        for acronym, name_keep, name_drop in PAIRS:
            keep = session.query(MonitoredAsset).filter_by(name=name_keep).first()
            drop = session.query(MonitoredAsset).filter_by(name=name_drop).first()

            if not keep or not drop:
                not_found += 1
                print(f"  INTROUVABLE : garder='{name_keep}' (trouve={bool(keep)}) / desactiver='{name_drop}' (trouve={bool(drop)})")
                continue

            if not keep.domain and drop.domain:
                keep.domain = drop.domain
            if not keep.asn and drop.asn:
                keep.asn = drop.asn
            if not keep.verification_note and drop.verification_note:
                keep.verification_note = drop.verification_note
            if drop.known_aliases:
                existing = set(a.lower() for a in (keep.known_aliases or []))
                for alias in drop.known_aliases:
                    if alias.lower() not in existing:
                        keep.known_aliases = list(keep.known_aliases or []) + [alias]
                        existing.add(alias.lower())

            drop.active = False
            merged += 1

        session.commit()
        print(f"\n{merged} paires fusionnees, {not_found} introuvables")

        total_active = session.query(MonitoredAsset).filter_by(active=True).count()
        total_all = session.query(MonitoredAsset).count()
        print(f"Total en base : {total_all} lignes, {total_active} actives")
    finally:
        session.close()

if __name__ == "__main__":
    run()
