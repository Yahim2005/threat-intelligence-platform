"""
Import de la recherche ciblee du 24/07/2026 sur les domaines des
institutions restantes (74 entrees, toutes deja presentes dans le
referentiel -- aucune nouvelle institution a creer).

Correspondance par NOM COMPLET (pas par sigle) : de nombreuses
institutions existantes n'ont pas de sigle renseigne en base, le nom
est la seule cle fiable pour toutes les cibler correctement.

Cas particulier SONATREL : le domaine sonatrel-cm.cm est officiellement
attribue a l'entreprise mais son contenu observe est actuellement sans
rapport avec elle (detournement possible). Statut volontairement
retrograde a 'unconfirmed' malgre l'attribution officielle du domaine.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()
from app.database import SessionLocal
from app.models.monitored_asset import MonitoredAsset
from app.models.enums import DomainStatus

# (nom_complet_exact_en_base, domaine, statut, note)
ENTRIES = [('AVS Telecom', None, 'not_found', 'L’opérateur est répertorié par l’ART, mais la fiche officielle ne publie aucun site web.'), ('Africa Data Center', 'adac.cm', 'confirmed', 'Le site s’identifie comme ADAC — Africa Data Center ; le domaine est aussi utilisé par les contacts techniques de l’opérateur.'), ('CAMPASS PLC', 'campass.org', 'confirmed', 'Site institutionnel propre de CAMPASS PLC.'), ('Cameroon Internet Exchange Point (CAMIX)', 'camix.cm', 'confirmed', 'Portail officiel du point d’échange Internet camerounais.'), ('Connection Cameroon', 'connectioncameroon.com', 'confirmed', 'Le site présente explicitement l’entreprise Connection Cameroon et ses coordonnées à Douala.'), ('Creolink Communications', 'creolink.com', 'confirmed', 'Domaine propre, également attribué à l’entreprise par le NIC Cameroun.'), ('GIE Groupe Commercial Bank', None, 'not_found', 'Le GIE est cité comme structure informatique du Groupe Commercial Bank ; aucun portail autonome n’a été trouvé.'), ('HTT Telecom', 'yoomeemobile.cm', 'confirmed', '[marque d’exploitation] HTT Telecom exploite la marque YooMee. Le domaine historique yoomee.cm est remplacé dans la présence web actuelle par yoomeemobile.cm.'), ('INFOGENIE Technologies', 'infogenie.cm', 'confirmed', 'Le site identifie clairement INFOGENIE Technologies.'), ('INQ Digital Cameroon', 'inq.inc', 'confirmed', '[domaine groupe] Le domaine panafricain d’INQ répertorie une présence au Cameroun (Douala et Yaoundé).'), ('Matrix Telecoms', 'matrixtelecoms.com', 'confirmed', 'Site propre de MATRIX TELECOMS S.A.'), ('Newtelnet Cameroun', 'newtelnet.net', 'confirmed', 'Le site s’identifie comme NEWTELNET CAMEROUN SAS.'), ('ST Digital', 'st.digital', 'confirmed', 'Page officielle dédiée au Cameroun.'), ('SWECOM PLC', 'swecom.cm', 'confirmed', 'Le domaine est déclaré par l’opérateur et associé à son réseau autonome ; l’accès web peut être intermittent.'), ('Sancfis Cameroun', 'sancfis.net', 'confirmed', '[domaine groupe] La documentation du groupe SANCFIS confirme sa présence au Cameroun et le domaine sancfis.net.'), ('Ministère chargé des Relations avec les Assemblées', 'spm.gov.cm', 'not_found', 'Le service est présenté sur le portail des Services du Premier Ministre ; aucun site autonome n’a été identifié.'), ("Ministère de l'Emploi et de la Formation professionnelle", 'minefop.cm', 'confirmed', ''), ("Ministère de l'Enseignement supérieur", 'minesup.gov.cm', 'confirmed', ''), ("Ministère de l'Environnement, de la Protection de la nature et du Développement durable", 'minepded.gov.cm', 'confirmed', ''), ("Ministère de l'Habitat et du Développement urbain", 'minhdu.gov.cm', 'confirmed', ''), ("Ministère de l'Éducation de base", 'minedub.cm', 'confirmed', ''), ("Ministère de l'Élevage, des Pêches et des Industries animales", 'minepia.cm', 'confirmed', ''), ('Ministère de la Décentralisation et du Développement local', 'minddevel.gov.cm', 'confirmed', ''), ('Ministère de la Fonction publique et de la Réforme administrative', 'minfopra.gov.cm', 'confirmed', ''), ('Ministère des Marchés publics', 'minmap.cm', 'confirmed', ''), ("Ministère des PME, de l'Économie sociale et de l'Artisanat", 'minpmeesa.cm', 'confirmed', ''), ("Contrôle supérieur de l'État", None, 'not_found', 'Un appel d’offres de juillet 2026 prévoit précisément la création d’un site et l’acquisition d’un nom de domaine ; consupe.gov.cm n’est donc pas retenu comme confirmé.'), ('Access Bank Cameroon', 'cameroon.accessbankplc.com', 'confirmed', ''), ('BANGE Bank', 'bangecmr.com', 'confirmed', ''), ('Banque camerounaise des PME', None, 'not_found', 'L’ancien domaine bc-pme.cm est cité historiquement mais n’est pas retenu faute de site actif et de confirmation récente.'), ('BGFI Bank Cameroun', 'bgfi.com', 'confirmed', '[domaine groupe] La plateforme officielle camerounaise est hébergée sur un sous-domaine de bgfi.com.'), ('BICEC', 'bicec.com', 'confirmed', ''), ('Banque Atlantique Cameroun', 'afgbank.cm', 'confirmed', '[nouvelle identité] Banque Atlantique Cameroun communique désormais sous l’identité AFG Bank Cameroun.'), ('CCA Bank', 'cca-bank.com', 'confirmed', ''), ('Citibank Cameroun', 'citigroup.com', 'confirmed', '[domaine groupe] Page pays officielle de Citi.'), ('Commercial Bank of Cameroon', 'cbc-bank.com', 'confirmed', 'Le portail bancaire s’identifie comme propriété de Commercial Bank of Cameroon.'), ('Crédit foncier du Cameroun', 'creditfoncier.cm', 'confirmed', ''), ('Ecobank Cameroun', 'ecobank.com', 'confirmed', '[domaine groupe] Page pays officielle d’Ecobank.'), ('La Régionale Bank', 'laregionalebank.com', 'confirmed', ''), ('National Financial Credit Bank', 'nfcbank.com', 'confirmed', ''), ('Société Générale Cameroun', 'societegenerale.cm', 'confirmed', 'Le site reste officiel, mais l’institution annonce opérer désormais sous le nom « General Bank of Cameroon » ; surveiller la publication d’un nouveau domaine.'), ("Société nationale d'investissement du Cameroun", 'sni.cm', 'confirmed', ''), ('Société de recouvrement des créances du Cameroun', 'src.cm', 'confirmed', ''), ('Standard Chartered Bank Cameroun', 'sc.com', 'not_found', 'Standard Chartered indique ne plus avoir de bureaux au Cameroun et renvoie vers Access Bank Cameroon.'), ('Union Bank Cameroon', 'unionbankcameroon.com', 'confirmed', ''), ('United Bank for Africa Cameroun', 'ubacameroon.com', 'confirmed', ''), ('Alucam', 'alucam.cm', 'confirmed', ''), ('Aéroports du Cameroun', 'adcsa.info', 'confirmed', 'Le domaine historique adcsa.aero reste utilisé pour les courriels ; le portail web actuel est adcsa.info.'), ('Cameroon Airlines Corporation', 'camair-co.net', 'confirmed', '[portail actuel] Le portail actif en 2026 utilise .net ; camair-co.cm reste encore cité par l’IATA et certains documents.'), ('Cameroon Development Corporation', 'cdc-cameroon.net', 'confirmed', ''), ('Camrail', 'camrail.cm', 'confirmed', '[portail actuel] Le domaine camrail.net correspond à l’ancien portail ; camrail.cm est le site institutionnel actuel.'), ('Cameroon Water Utilities Corporation', 'camwater.cm', 'confirmed', ''), ('Cimencam', 'cimencam.com', 'confirmed', ''), ('ENEO Cameroun', 'eneocameroon.cm', 'confirmed', ''), ('Hevecam', 'corrie-maccoll.com', 'confirmed', '[domaine maison mère] Aucun portail propre récent n’a été trouvé ; HEVECAM est exploitée par Corrie MacColl. Ne pas traiter ce domaine groupe comme un site institutionnel autonome.'), ('Hysacam', 'hysacam-proprete.com', 'confirmed', ''), ("Mission d'aménagement et d'équipement des terrains urbains et ruraux", 'maetur-cameroun.com', 'confirmed', ''), ("Mission d'aménagement et de gestion des zones industrielles", 'magzicameroun.com', 'confirmed', ''), ('MEKIN', None, 'not_found', 'L’entreprise est confirmée par des sources publiques, mais aucun portail officiel autonome n’a été trouvé.'), ('PAMOL', 'pamol.net', 'confirmed', ''), ('Port autonome de Douala', 'pad.cm', 'confirmed', ''), ('Société camerounaise des dépôts pétroliers', 'scdp.cm', 'confirmed', ''), ("Société d'expansion et de modernisation de la riziculture de Yagoua", None, 'not_found', 'L’entité publique est confirmée, mais aucun domaine officiel actif n’a été trouvé ; semry.cm n’est pas retenu.'), ('Société immobilière du Cameroun', 'sic.cm', 'confirmed', ''), ("Société de développement et d'exploitation des productions animales", 'sodepa.cm', 'confirmed', ''), ('SOPEACM', 'sopecam.cm', 'confirmed', '[nom corrigé] Le libellé « SOPEACM » semble être une coquille ; l’institution officielle est la SOPECAM.'), ('Safacam', 'socfin.com', 'confirmed', '[domaine groupe] La SNI attribue à SAFACAM une page du groupe Socfin ; aucun domaine autonome SAFACAM n’a été identifié.'), ('Société nationale des hydrocarbures', 'snh.cm', 'confirmed', ''), ('Société nationale de raffinage', 'sonara-cm.cm', 'confirmed', ''), ("Société nationale de transport de l'électricité", 'sonatrel-cm.cm', 'unconfirmed', 'Le domaine est attribué officiellement à SONATREL, mais le contenu observé en 2026 est sans rapport avec l’entreprise. Ne pas le considérer comme fiable tant que le site n’est pas assaini.'), ('Tradex', 'tradexsa.co', 'confirmed', ''), ('CNSRIC', None, 'not_found', 'Le sigle apparaît dans des ressources réseau liées au Cameroun, mais son identité complète et un domaine propre n’ont pas pu être confirmés.'), ('Port autonome de Kribi', 'pak.cm', 'confirmed', ''), ('Université de Maroua', 'univ-maroua.cm', 'confirmed', '')]

def run():
    session = SessionLocal()
    updated_domain, updated_status, updated_note, unchanged, not_found = 0, 0, 0, 0, 0
    try:
        for name, domain, status_str, note in ENTRIES:
            asset = session.query(MonitoredAsset).filter_by(name=name, active=True).first()
            if not asset:
                not_found += 1
                print(f"  introuvable (actif) : {name}")
                continue

            status = DomainStatus(status_str)
            changed = False

            if domain and asset.domain != domain:
                asset.domain = domain
                updated_domain += 1
                changed = True

            if asset.domain_status != status:
                asset.domain_status = status
                updated_status += 1
                changed = True

            if note and asset.verification_note != note:
                asset.verification_note = note
                updated_note += 1
                changed = True

            if not changed:
                unchanged += 1

        session.commit()
        print(f"\n{updated_domain} domaines mis a jour, {updated_status} statuts changes, "
              f"{updated_note} notes ajoutees, {unchanged} inchanges, {not_found} introuvables")

        total_confirmed = session.query(MonitoredAsset).filter_by(domain_status=DomainStatus.confirmed, active=True).count()
        total_unconfirmed = session.query(MonitoredAsset).filter_by(domain_status=DomainStatus.unconfirmed, active=True).count()
        total_not_found = session.query(MonitoredAsset).filter_by(domain_status=DomainStatus.not_found, active=True).count()
        print(f"\nTotal actif : {total_confirmed} confirmes, {total_unconfirmed} unconfirmed, {total_not_found} not_found")
    finally:
        session.close()

if __name__ == "__main__":
    run()
