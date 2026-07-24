"""
Mise a jour du referentiel institutionnel Cameroun (v2).

Source : Annuaire_institutionnel_Cameroun_domaines_officiels_v2.xlsx
92 institutions re-verifiees : 87 confirmees (dont plusieurs domaines
corriges suite a une vraie verification manuelle), 5 marquees not_found
(domaine investigue et confirme comme inexistant/inactif).

Idempotent : upsert par acronyme. Preserve les institutions dont
l'acronyme n'apparait pas dans ce fichier (pas de suppression).
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.monitored_asset import MonitoredAsset
from app.models.enums import DomainStatus

REFERENTIEL_V2 = [
    ("PRC", "prc.cm", DomainStatus.confirmed, ""),
    ("SPM", "spm.gov.cm", DomainStatus.confirmed, ""),
    ("AN", "assnat.cm", DomainStatus.confirmed, ""),
    ("SÉNAT", "senat.cm", DomainStatus.confirmed, ""),
    ("CC", "conseilconstitutionnel.cm", DomainStatus.not_found, "L'institution est confirmée par la Présidence, mais aucun site propre actif ne permet de valider conseilconstitutionnel.cm."),
    ("CONAC", "conac.cm", DomainStatus.confirmed, ""),
    ("CONSUPE", "consupe.gov.cm", DomainStatus.not_found, "Le rattachement institutionnel est confirmé par la Présidence ; consupe.gov.cm reste inaccessible et non validé."),
    ("ELECAM", "elecam.cm", DomainStatus.confirmed, "Le portail de contenu est également accessible sur https://portail.elecam.cm/."),
    ("MINAT", "minat.gov.cm", DomainStatus.confirmed, ""),
    ("MINDEF", "mindef.gov.cm", DomainStatus.confirmed, ""),
    ("MINJUSTICE", "minjustice.gov.cm", DomainStatus.confirmed, "Domaine corrigé : minjustice.gov.cm remplace l'adresse justice.gov.cm du fichier initial."),
    ("MINREX", "diplocam.cm", DomainStatus.confirmed, ""),
    ("MINFI", "minfi.gov.cm", DomainStatus.confirmed, ""),
    ("MINDCAF", "mindcaf.gov.cm", DomainStatus.confirmed, ""),
    ("MINEPAT", "minepat.gov.cm", DomainStatus.confirmed, ""),
    ("MINCOMMERCE", "mincommerce.gov.cm", DomainStatus.confirmed, ""),
    ("MINMIDT", "minmidt.cm", DomainStatus.confirmed, "Un ancien domaine minmidt.net existe encore"),
    ("MINPMEESA", "minpmeesa.cm", DomainStatus.confirmed, ""),
    ("MINMAP", "minmap.cm", DomainStatus.confirmed, ""),
    ("MINFOPRA", "minfopra.gov.cm", DomainStatus.confirmed, ""),
    ("MINEDUB", "minedub.cm", DomainStatus.confirmed, ""),
    ("MINESEC", "minesec.gov.cm", DomainStatus.confirmed, ""),
    ("MINESUP", "minesup.gov.cm", DomainStatus.confirmed, ""),
    ("MINEFOP", "minefop.cm", DomainStatus.confirmed, "Domaine institutionnel actuel corrigé : minefop.cm."),
    ("MINRESI", "minresi.gov.cm", DomainStatus.confirmed, ""),
    ("MINSANTE", "minsante.cm", DomainStatus.confirmed, ""),
    ("MINAS", "minas.cm", DomainStatus.confirmed, "Domaine confirmé par la page officielle du MINAS ; le serveur web affiche actuellement une page XAMPP mal configurée."),
    ("MINPROFF", "minproff.gov.cm", DomainStatus.confirmed, "Domaine corrigé : minproff.gov.cm remplace minproff.cm."),
    ("MINJEC", "minjec.gov.cm", DomainStatus.confirmed, ""),
    ("MINSEP", "minsep.cm", DomainStatus.confirmed, ""),
    ("MINAC", "minac.gov.cm", DomainStatus.confirmed, ""),
    ("MINCOM", "mincom.gov.cm", DomainStatus.confirmed, ""),
    ("MINPOSTEL", "minpostel.gov.cm", DomainStatus.confirmed, ""),
    ("MINT", "mintransports.cm", DomainStatus.confirmed, "Domaine institutionnel actuel corrigé : mintransports.cm."),
    ("MINTP", "mintp.cm", DomainStatus.confirmed, ""),
    ("MINEE", "minee.cm", DomainStatus.confirmed, ""),
    ("MINHDU", "minhdu.gov.cm", DomainStatus.confirmed, "Ancien sigle/domaine MINDUH parfois encore référencé"),
    ("MINDDEVEL", "minddevel.gov.cm", DomainStatus.confirmed, ""),
    ("MINADER", "minader.cm", DomainStatus.confirmed, ""),
    ("MINEPIA", "minepia.cm", DomainStatus.confirmed, ""),
    ("MINFOF", "minfof.gov.cm", DomainStatus.confirmed, ""),
    ("MINEPDED", "minepded.gov.cm", DomainStatus.confirmed, ""),
    ("MINTOUL", "mintoul.gov.cm", DomainStatus.confirmed, ""),
    ("MINTSS", "mintss.cm", DomainStatus.confirmed, "Domaine corrigé : mintss.cm remplace mintss.gov.cm."),
    ("CAMTEL", "camtel.cm", DomainStatus.confirmed, ""),
    ("CAMPOST", "campost.cm", DomainStatus.confirmed, ""),
    ("CAMWATER", "camwater.cm", DomainStatus.confirmed, ""),
    ("SONATREL", "sonatrel-cm.cm", DomainStatus.confirmed, "Domaine confirmé dans la liste publique des états financiers ; le site est actuellement en maintenance."),
    ("EDC", "edc.cm", DomainStatus.confirmed, ""),
    ("SNH", "snh.cm", DomainStatus.confirmed, ""),
    ("SONARA", "sonara-cm.cm", DomainStatus.confirmed, ""),
    ("SCDP", "scdp.cm", DomainStatus.confirmed, ""),
    ("SONAMINES", "sonamines.cm", DomainStatus.confirmed, ""),
    ("SODECOTON", "sodecoton.cm", DomainStatus.confirmed, ""),
    ("CDC", "cdc-cameroon.net", DomainStatus.confirmed, "Le domaine .com du fichier initial redirige vers le domaine institutionnel cdc-cameroon.net."),
    ("SEMRY", "semry.cm", DomainStatus.not_found, "Aucun site officiel actif ni source institutionnelle récente ne permet de confirmer semry.cm."),
    ("SODEPA", "sodepa.cm", DomainStatus.confirmed, ""),
    ("CICAM", "cicam.cm", DomainStatus.confirmed, ""),
    ("CAMAIR-CO", "camair-co.cm", DomainStatus.confirmed, "Acronyme corrigé usuellement : CAMAIR-CO"),
    ("ADC", "adcsa.info", DomainStatus.confirmed, "Le domaine adcsa.aero redirige vers l'adresse institutionnelle actuelle adcsa.info."),
    ("PAD", "pad.cm", DomainStatus.confirmed, ""),
    ("PAK", "pak.cm", DomainStatus.confirmed, ""),
    ("SIC", "sic.cm", DomainStatus.confirmed, "Le domaine identifie bien la SIC, malgré une réponse serveur intermittente lors du contrôle."),
    ("MAETUR", "maetur-cameroun.com", DomainStatus.confirmed, "Domaine institutionnel actuel corrigé : maetur-cameroun.com."),
    ("MAGZI", "magzicameroun.com", DomainStatus.confirmed, ""),
    ("LABOGENIE", "labogenie.cm", DomainStatus.confirmed, ""),
    ("MATGENIE", "matgenie.cm", DomainStatus.confirmed, ""),
    ("CFC", "creditfoncier.cm", DomainStatus.confirmed, ""),
    ("BC-PME", "bcpme.cm", DomainStatus.not_found, "La banque publique est confirmée, mais bcpme.cm ne résout pas et aucun domaine de remplacement officiel n'a été trouvé."),
    ("SNI", "sni.cm", DomainStatus.confirmed, ""),
    ("SRC", "src.cm", DomainStatus.confirmed, ""),
    ("ANTIC", "antic.cm", DomainStatus.confirmed, ""),
    ("ART", "art.cm", DomainStatus.confirmed, ""),
    ("ARMP", "armp.cm", DomainStatus.confirmed, ""),
    ("ARSEL", "arsel-cm.org", DomainStatus.confirmed, "Domaine institutionnel actuel corrigé : arsel-cm.org."),
    ("AER", "aer.cm", DomainStatus.not_found, "aer.cm est cité par une source publique, mais affiche actuellement une page sans lien avec l'AER ; validation conservée en attente."),
    ("CCAA", "ccaa.aero", DomainStatus.confirmed, ""),
    ("FEICOM", "feicom.cm", DomainStatus.confirmed, ""),
    ("CNPS", "cnps.cm", DomainStatus.confirmed, ""),
    ("CAA", "caa.cm", DomainStatus.confirmed, ""),
    ("FNE", "fnecm.org", DomainStatus.confirmed, "Le portail opérationnel officiel est hébergé sur le sous-domaine emploi.fnecm.org."),
    ("INS", "ins-cameroun.cm", DomainStatus.confirmed, ""),
    ("IRAD", "irad.cm", DomainStatus.confirmed, ""),
    ("ONCC", "oncc.cm", DomainStatus.confirmed, ""),
    ("CENAME", "cename.org", DomainStatus.confirmed, "Domaine corrigé : cename.org remplace cename.cm."),
    ("OBC", "officedubac.cm", DomainStatus.confirmed, "Domaine institutionnel actuel retenu : officedubac.cm. Le domaine obc.cm reste mentionné dans certains documents."),
    ("GCE BOARD", "camgceb.org", DomainStatus.confirmed, "Le domaine officiel est confirmé ; une protection anti-robot peut limiter l'accès automatisé."),
    ("MIPROMALO", "mipromalo.cm", DomainStatus.confirmed, ""),
    ("API", "investincameroon.cm", DomainStatus.confirmed, "Domaine corrigé : investincameroon.cm remplace investincameroon.net."),
    ("APME", "apme.cm", DomainStatus.confirmed, ""),
    ("ANAFOR", "anafor.cm", DomainStatus.confirmed, ""),
    ("ONACC", "onacc.cm", DomainStatus.confirmed, ""),
]


def run() -> None:
    session = SessionLocal()
    updated_domain, updated_status, updated_note, unchanged, not_found_asset = 0, 0, 0, 0, 0
    domain_corrections = []

    try:
        for acronym, domain, status, observation in REFERENTIEL_V2:
            asset = session.query(MonitoredAsset).filter_by(acronym=acronym).first()
            if not asset:
                not_found_asset += 1
                print(f"  institution introuvable en base (acronyme={acronym}), ignoree")
                continue

            changed = False

            if domain and asset.domain != domain:
                if asset.domain and asset.domain != domain:
                    domain_corrections.append((acronym, asset.domain, domain))
                asset.domain = domain
                updated_domain += 1
                changed = True

            if asset.domain_status != status:
                asset.domain_status = status
                updated_status += 1
                changed = True

            if observation and asset.verification_note != observation:
                asset.verification_note = observation
                updated_note += 1
                changed = True

            if not changed:
                unchanged += 1

        session.commit()

        print(f"\n{updated_domain} domaines mis a jour, {updated_status} statuts changes, "
              f"{updated_note} notes ajoutees, {unchanged} inchanges, "
              f"{not_found_asset} introuvables en base")

        if domain_corrections:
            print("\nCorrections de domaine reelles (ancien != nouveau) :")
            for acr, old, new in domain_corrections:
                print(f"  {acr} : {old} -> {new}")

        total_not_found = session.query(MonitoredAsset).filter_by(domain_status=DomainStatus.not_found).count()
        total_confirmed = session.query(MonitoredAsset).filter_by(domain_status=DomainStatus.confirmed).count()
        print(f"\nTotal en base : {total_confirmed} confirmes, {total_not_found} not_found")
    finally:
        session.close()


if __name__ == "__main__":
    run()
