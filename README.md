# Threat Intelligence Platform — ANTIC/CIRT Cameroun

Plateforme de threat intelligence combinant :
- un moteur généraliste (collecte, scoring, corrélation d'indicateurs de compromission depuis 15+ sources OSINT publiques) ;
- un module de surveillance nationale dédié au Cameroun (typosquatting, certificats SSL suspects, domaines nouvellement enregistrés, surface d'attaque exposée), construit autour d'un référentiel de 174 institutions camerounaises stratégiques.

Projet réalisé dans le cadre d'un stage, destiné à être repris et exploité en autonomie par l'équipe CIRT de l'ANTIC.

## Par où commencer

**Pour déployer la plateforme sur votre propre infrastructure** (base de données, backend, dashboard, automatisation) :
-> docs/deployment_guide.md — guide complet, testé de bout en bout en reconstruisant l'environnement à partir de zéro.

**Pour comprendre le fonctionnement technique de chaque module** :
-> Chaque page du dashboard intègre un panneau "Comment ça marche" expliquant sa logique.
-> Le rapport de stage (fourni séparément) détaille l'architecture, les choix de conception et les résultats.

**Pour qu'un organisme partenaire consomme les indicateurs via API** (SIEM, autre CIRT, MISP/OpenCTI) :
-> docs/taxii_integration.md — parcours TAXII 2.1, gestion des clés API, script de synchronisation.

**Pour explorer l'API** :
-> docs/openapi.json, ou /docs (Swagger UI) une fois le backend lancé.

## Structure du dépôt

```
api/          Routes FastAPI (indicateurs, menaces, exports, TAXII, administration)
app/          Modèles de données, sécurité, connexion base de données
core/         Scoring, corrélation, clustering, digest email, normalisation
collectors/   Collecteurs OSINT généralistes + modules de surveillance nationale
scripts/      Scripts opérationnels (migrations, référentiel, jobs de post-traitement)
dashboard/    Interface React (analyste + administration)
tests/        Suite de tests (pytest)
docs/         Documentation de déploiement et d'intégration
.github/workflows/   Automatisation (collecte, surveillance nationale, surface d'attaque, digest email, tests)
```

## Administration courante

Une fois déployée, la gestion quotidienne (référentiel des institutions, déclenchement des collectes, clés API partenaires, destinataires du digest email) se fait entièrement depuis l'interface Admin du dashboard, sans ligne de commande.

## Support

Pour toute question sur la reprise en main du projet, se référer en premier lieu au guide de déploiement et à la documentation intégrée aux pages du dashboard, conçus pour permettre une exploitation autonome par l'équipe CIRT.
