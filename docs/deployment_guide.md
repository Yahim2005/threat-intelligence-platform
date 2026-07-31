# Guide de déploiement — TIP ANTIC/CIRT Cameroun

Ce guide couvre un déploiement complet de zéro, sur une infrastructure neuve,
sans connaissance préalable du projet. Il a été testé réellement (voir la
section « Validation » en fin de document) sur une base PostgreSQL locale
vidée puis reconstruite en suivant exactement les étapes ci-dessous.

Suivre les étapes **dans l'ordre**. Chaque section indique ce qui casse si on
saute une étape.

---

## 1. Prérequis

- **Python 3.11** — précisément cette version mineure, pas plus récent.
  `requirements.txt` contient des paquets (notamment `pydantic-core`, via
  FastAPI/Pydantic) qui ne compilent pas ou se comportent différemment sous
  Python 3.13/3.14. Certaines plateformes d'hébergement (Render, entre
  autres) utilisent une version Python récente par défaut si on ne la fixe
  pas explicitement — **c'est un piège déjà rencontré sur ce projet**. Le
  fichier `render.yaml` du dépôt fixe déjà `PYTHON_VERSION: 3.11.0` ; sur
  toute autre plateforme, fixer explicitement 3.11.x (fichier
  `runtime.txt`, variable d'env `PYTHON_VERSION`, ou équivalent selon
  l'hébergeur).
- **PostgreSQL 14+** (développé et testé avec PostgreSQL 16 en local).
- **Node.js 20+** pour construire le dashboard (Vite 8 + React 19 — aucune
  version n'est figée dans le dépôt via `.nvmrc`, mais une version récente
  est nécessaire).
- **git**, **pip**, **npm**.

---

## 2. Récupérer le code

```bash
git clone <url-du-depot>
cd tip
```

---

## 3. Provisionner une base de données PostgreSQL

Trois options possibles, à choisir selon les contraintes de l'équipe ANTIC — ce
guide reste neutre, n'en préconise aucune en particulier :

- **PostgreSQL auto-hébergé** (VM ANTIC, conteneur Docker, etc.) — contrôle
  total, aucun coût récurrent, mais maintenance (sauvegardes, mises à jour) à
  la charge de l'équipe.
- **Fournisseur managé payant** (Neon, RDS, Supabase, etc.) — voir la section
  « Limitations connues » plus bas concernant le dimensionnement du stockage
  si un plan gratuit est envisagé.
- **Fournisseur managé de l'hébergeur choisi** (ex : base PostgreSQL Render,
  déjà déclarée dans `render.yaml` si ce chemin est retenu).

Dans tous les cas, il faut obtenir une URL de connexion au format :

```
postgresql+psycopg2://<user>:<password>@<host>:<port>/<database>
```

C'est la valeur de `DATABASE_URL` (section suivante).

---

## 4. Variables d'environnement

Copier `.env.example` en `.env` à la racine du dépôt et renseigner les
valeurs réelles. **Ne jamais committer `.env`** (déjà dans `.gitignore`).

### Backend (`.env`)

| Variable | Obligatoire | Rôle |
|---|---|---|
| `DATABASE_URL` | **Oui** | Connexion PostgreSQL (voir section 3). Lue par l'app, Alembic, et tous les scripts. |
| `JWT_SECRET_KEY` | **Oui** | Signature des tokens JWT (login dashboard). Aucune valeur par défaut : l'app refuse de démarrer une opération d'auth si absente. Générer une valeur aléatoire forte, ex : `openssl rand -hex 32`. **Ne jamais réutiliser une valeur d'exemple/dev en production.** |
| `CORS_ORIGINS` | Non (défaut `*`) | Origines autorisées pour le dashboard. En production, restreindre au(x) domaine(s) réel(s) du dashboard, ex : `https://dashboard.antic.cm`. |
| `TIP_API_KEY` | Non | Clé API "legacy" de secours (le système courant est les clés par organisme, table `api_clients`, gérées depuis Admin → Partenaires API). Peut rester vide. |
| `ABUSECH_AUTH_KEY` | Recommandé | Clé abuse.ch (URLhaus/Feodo/ThreatFox/MalwareBazaar) — gratuite sur https://auth.abuse.ch/. Sans elle, ces collecteurs échouent ou sont fortement limités. |
| `OTX_API_KEY` | Recommandé | Clé AlienVault OTX (compte gratuit). |
| `NVD_API_KEY` | Recommandé | Clé NVD (National Vulnerability Database, compte gratuit) — sans elle, le rate limit NVD est beaucoup plus bas. |
| `SMTP_HOST` | Requis si digest email utilisé | Serveur SMTP sortant (ex : `smtp.gmail.com` avec un mot de passe d'application, ou tout relais SMTP). |
| `SMTP_PORT` | Non (défaut 587) | Port SMTP. |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | Requis si le serveur SMTP exige une auth | Identifiants SMTP. |
| `SMTP_FROM_EMAIL` | Recommandé | Adresse d'expéditeur affichée. |
| `SMTP_USE_TLS` | Non (défaut `true`) | Mettre à `false` uniquement contre un relais de test sans TLS. |
| `EMAIL_DIGEST_MIN_RELEVANCE` | Non (défaut 3) | Seuil `cameroon_relevance` minimum pour qu'un IOC entre dans le digest. |
| `EMAIL_DIGEST_MAX_IOCS` | Non (défaut 30) | Nombre max d'IOCs par digest (les plus récents en priorité). |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_FULL_NAME` | Requis **une seule fois**, au moment de créer le premier compte admin (section 8) | Jamais en argument de ligne de commande ni en dur dans le code — uniquement via l'environnement, et seulement le temps de l'exécution de `scripts/create_admin.py`. |

`.env.example` contient aussi `DATABASE_URL_LOCAL`, `SHODAN_API_KEY`, `TOKEN`,
`NEON_API_KEY` : ces trois derniers ne sont lus par **aucun** script du code
actuel (vérifié par recherche exhaustive) — des variables historiques,
pas nécessaires pour un déploiement neuf. `DATABASE_URL_LOCAL` est une
simple convention de confort pour le développement local, jamais lue par le
code (on exporte `DATABASE_URL` directement quand on veut pointer sur une
base locale).

### Frontend (`dashboard/.env`)

Une seule variable, lue par `dashboard/src/api/client.js` :

| Variable | Obligatoire | Rôle |
|---|---|---|
| `VITE_API_BASE_URL` | Non (défaut `/api`, adapté à un reverse-proxy) | URL complète du backend si le frontend et le backend ne sont pas derrière le même reverse-proxy, ex : `https://api.tip-antic.cm`. |

**Ne jamais** y mettre de clé API ou de secret : tout ce qui commence par
`VITE_` est compilé en clair dans le bundle JavaScript public (incident déjà
rencontré et corrigé sur ce projet — voir l'historique du dépôt).

---

## 5. Installer les dépendances

```bash
python3.11 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

```bash
cd dashboard
npm install
cd ..
```

---

## 6. Appliquer les migrations

```bash
alembic upgrade head
```

Doit se terminer sans erreur et créer l'intégralité du schéma (tables
`indicators`, `sources`, `threats`, `monitored_assets`, `users`,
`api_clients`, `email_recipients`, `admin_job_runs`, etc.). C'est la seule
étape qui crée les tables — tout ce qui suit dépend d'un schéma déjà en
place.

---

## 7. Reconstruire le référentiel institutionnel

Le référentiel des institutions camerounaises surveillées
(`monitored_assets`) n'est pas dans les migrations : il est peuplé par une
séquence de scripts Python, **à exécuter dans cet ordre précis** — chaque
script dépend d'un état laissé par le précédent :

```bash
python -m scripts.seeds
python -m scripts.seed_monitored_assets
python -m scripts.import_referentiel
python -m scripts.update_referentiel_v2
python -m scripts.dedupe_institutions
python -m scripts.import_recherche_74
```

Pourquoi cet ordre précis (dépendances réelles, pas une convention) :

1. **`scripts.seeds`** — peuple la table `sources` (les flux OSINT :
   URLhaus, Feodo, ThreatFox, etc.). Indépendant du reste, mais nécessaire
   avant tout collecteur.
2. **`scripts.seed_monitored_assets`** — première liste d'institutions
   (télécoms via ASN RIPE, ministères, banques, entreprises publiques),
   **sans sigle renseigné**. Idempotent (upsert par nom).
3. **`scripts.import_referentiel`** — importe un référentiel plus fiable
   (92 institutions, avec sigle). Fait un upsert par `acronyme OU nom` :
   pour les institutions déjà créées à l'étape 2 sous un nom identique, il
   les complète (ajoute le sigle) ; sinon il en crée de nouvelles — **c'est
   cette étape qui crée les doublons que `dedupe_institutions` corrige plus
   loin**, quand le nom de l'étape 2 diffère légèrement de celui de
   l'étape 3 (ex: "Aéroports du Cameroun (ADC)" vs "Aéroports du
   Cameroun").
4. **`scripts.update_referentiel_v2`** — corrections de domaines
   post-vérification manuelle. Recherche **strictement par sigle**
   (`acronym`) : ne peut donc s'exécuter qu'**après** l'étape 3, seule à
   renseigner ce champ. Lancé avant cette étape, il ne trouve aucune ligne
   et ne fait rien (pas d'erreur, mais silencieusement inutile).
5. **`scripts.dedupe_institutions`** — fusionne les paires de doublons
   créées à l'étape 3 (garde la ligne avec sigle, désactive `active=False`
   l'autre — jamais de suppression physique).
6. **`scripts.import_recherche_74`** — dernière passe de correction sur 74
   institutions restantes, recherche par **nom complet** et `active=True`
   uniquement — d'où l'intérêt d'avoir dédupliqué juste avant, pour ne
   cibler que la ligne canonique.

Chaque script affiche un résumé (`ajoutés`/`mis à jour`/`inchangés`) et est
**idempotent** : relancer toute la séquence sur une base déjà peuplée est
sans danger.

---

## 8. Télécharger les bases GeoIP MaxMind

Utilisées par `scripts/score_cameroon.py` pour la géolocalisation IP et
l'association ASN → Cameroun. Volumineuses (~75 Mo au total) et exclues du
dépôt (`.gitignore` : `data/*.mmdb`).

1. Créer un compte gratuit sur https://www.maxmind.com/en/geolite2/signup
   (licence GeoLite2 — gratuite mais nécessite un compte et l'acceptation
   des conditions).
2. Générer une clé de licence, puis télécharger les deux bases :
   `GeoLite2-City` et `GeoLite2-ASN` (format `.mmdb`).
3. Les placer dans :
   ```
   data/GeoLite2-City.mmdb
   data/GeoLite2-ASN.mmdb
   ```
   (chemins en dur dans `scripts/score_cameroon.py`, ne pas renommer).

Sans ces fichiers, `score_cameroon.py` échoue à l'exécution — tout le reste
de la plateforme (API, dashboard, collecteurs) fonctionne normalement sans
elles ; seul le calcul de `cameroon_relevance` en dépend.

---

## 9. Créer le premier compte administrateur

```bash
ADMIN_EMAIL=admin@antic.cm ADMIN_PASSWORD='<mot-de-passe-fort>' ADMIN_FULL_NAME="ANTIC CIRT Admin" \
  python scripts/create_admin.py
```

Toujours en variables d'environnement, jamais en argument ni en dur (le
script refuse de s'exécuter sans `ADMIN_EMAIL`/`ADMIN_PASSWORD`). Relancer
ce script sur un email déjà existant met à jour son mot de passe et son
rôle vers `admin` plutôt que d'échouer.

---

## 10. Démarrer le backend

**Le point d'entrée est `api.main:app`, pas `app.main:app`** — un piège déjà
rencontré sur ce projet (il existe un module `app/` distinct pour les
modèles/logique métier, mais l'application FastAPI est assemblée dans
`api/main.py`).

En développement :
```bash
uvicorn api.main:app --reload --port 8001
```

En production, le dépôt inclut un `render.yaml` fonctionnel qui utilise :
```bash
gunicorn api.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```
Cette commande fonctionne telle quelle sur n'importe quelle plateforme qui
fournit un `$PORT` (Render, Railway, un conteneur Docker, un service
systemd avec `Environment=PORT=...`, etc.) — le projet ne dépend pas
structurellement de Render, `render.yaml` est un blueprint pour ceux qui
choisissent cette plateforme, pas une contrainte du code.

---

## 11. Construire et déployer le frontend

```bash
cd dashboard
npm run build
```

Produit un dossier `dashboard/dist/` statique, déployable sur n'importe quel
hébergeur de fichiers statiques (Render `runtime: static`, Netlify, Vercel,
un simple Nginx, etc.) — configurer `VITE_API_BASE_URL` **avant** le build
(c'est une variable de build-time Vite, pas runtime : elle doit être définie
dans l'environnement au moment où `npm run build` s'exécute).

---

## 12. Secrets GitHub Actions

Le dépôt contient 4 workflows (`.github/workflows/`), chacun avec ses
propres secrets à définir dans **Settings → Secrets and variables →
Actions** du dépôt GitHub :

| Workflow | Rôle | Secrets requis |
|---|---|---|
| `collect.yml` | Collecte OSINT généraliste (toutes les 6h) + corrélation/clustering/scores/décroissance | `DATABASE_URL`, `ABUSECH_AUTH_KEY`, `OTX_API_KEY`, `NVD_API_KEY`, `TIP_API_KEY` |
| `cameroon-monitors.yml` | Surveillance nationale (typosquat, domaines récents, certificats) + scoring Cameroun (quotidien) | `DATABASE_URL`, `TIP_API_KEY` |
| `attack-surface-scan.yml` | Scan de surface d'attaque des institutions (RIPEstat + Shodan InternetDB, toutes les 6h) | `DATABASE_URL` |
| `email-digest.yml` | Digest IOC par email (quotidien, envoi réel espacé de 3 jours par logique interne) | `DATABASE_URL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` |

Note : `TIP_API_KEY` est déclaré dans l'environnement de `collect.yml` et
`cameroon-monitors.yml` mais n'est en réalité lu par **aucun** collecteur
actuel (vérifié dans le code) — ces deux workflows fonctionnent même si ce
secret est laissé vide. Il est conservé par cohérence avec le reste de la
configuration ; ne pas perdre de temps à le renseigner si l'objectif est
uniquement de faire fonctionner la collecte.

---

## 13. Vérification post-déploiement

Checklist simple, dans l'ordre :

1. **Backend en vie** : `curl https://<domaine-api>/health` → doit répondre
   (200 si vous êtes authentifié en admin, 401 sinon — dans les deux cas,
   une réponse JSON du serveur, pas une erreur de connexion, confirme que
   le processus tourne et parle à la base).
2. **Migrations appliquées** : `alembic current` doit afficher la révision
   la plus récente du dossier `alembic/versions/`.
3. **Référentiel peuplé** : requête directe ou, une fois un compte admin
   créé, `GET /monitored-assets` (authentifié) doit renvoyer un nombre
   d'institutions cohérent (voir section Validation ci-dessous pour le
   chiffre exact obtenu lors du test de ce guide).
4. **Login admin fonctionnel** : `POST /auth/login` avec l'email/mot de
   passe créés en section 9 doit renvoyer un token JWT.
5. **Dashboard accessible** : ouvrir l'URL du frontend déployé, se
   connecter avec le compte admin, vérifier que la page Overview affiche
   des statistiques (même à zéro avant la première collecte) sans erreur
   console.
6. **Un collecteur fonctionne** : depuis Admin → Collecte & traitement,
   lancer manuellement un collecteur rapide (ex : `feodo`) et vérifier que
   son statut passe à `succès` après quelques secondes.
7. **GitHub Actions** : après avoir renseigné les secrets (section 12),
   déclencher chaque workflow manuellement (`workflow_dispatch`, bouton
   "Run workflow" dans l'onglet Actions de GitHub) une première fois plutôt
   que d'attendre le prochain cron, pour confirmer que les secrets sont
   correctement configurés.

---

## Validation

Ce guide a été suivi littéralement, étape par étape, sans raccourci, sur la
base locale de développement
(`postgresql+psycopg2://tip:tip_secret@localhost:5433/tip_db`) après un
`DROP SCHEMA public CASCADE ; CREATE SCHEMA public` complet (jamais fait sur
une base de production). Résultat, chaque étape a réussi sans erreur ni
avertissement inattendu, dans l'ordre exact documenté :

| Étape | Résultat obtenu |
|---|---|
| `alembic upgrade head` | Chaîne complète appliquée jusqu'à `d4f8b2a1c9e3` sans erreur |
| `scripts.seeds` | 14 sources ajoutées |
| `scripts.seed_monitored_assets` | 109 institutions ajoutées |
| `scripts.import_referentiel` | 65 ajoutées, 27 mises à jour — 174 au total |
| `scripts.update_referentiel_v2` | 0 "introuvable en base" (confirme la dépendance sur l'étape précédente) |
| `scripts.dedupe_institutions` | 31 paires fusionnées, 0 introuvable |
| `scripts.import_recherche_74` | 0 introuvable |
| GeoIP (`.mmdb` déjà présents) | Les deux bases s'ouvrent correctement via `geoip2.database.Reader` |
| `scripts/create_admin.py` | Compte admin créé |
| `uvicorn api.main:app` | Démarre, `Application startup complete` |
| `GET /health` (authentifié) | `{"status": "ok", "db": "ok", "version": "1.0.0"}` |
| `POST /auth/login` | Token JWT émis |
| `GET /monitored-assets` | 143 institutions actives renvoyées |
| Déclenchement manuel du collecteur `feodo` | Passe à `succès` en ~1 seconde |

**État final de la base après ce test** : 14 sources, 174 lignes dans
`monitored_assets` (143 actives : 129 `confirmed`, 3 `unconfirmed`,
11 `not_found` — 31 lignes désactivées par la déduplication, jamais
supprimées), 1 compte utilisateur (l'admin créé pendant ce test), migrations
à jour sur la révision `d4f8b2a1c9e3`.

Aucune étape du guide n'a dû être corrigée après coup : l'ordre de la
séquence de reconstruction du référentiel (section 7) était déjà correct
avant ce test, la dépendance de `update_referentiel_v2` sur l'acronyme posé
par `import_referentiel` était le seul point réellement bloquant si l'ordre
n'est pas respecté (testé implicitement : 0 "introuvable" confirme que
l'ordre documenté est le bon).

---

## Limitations connues

- **Dimensionnement du stockage (retour d'expérience Neon gratuit)** : en
  cours de développement, le plan gratuit Neon utilisé pour la base de
  développement s'est rempli, provoquant un **échec silencieux à 100 %**
  des écritures des collecteurs (268 enregistrements sur 268 en erreur) —
  invisible sur GitHub Actions, qui affichait un run "vert" alors qu'aucune
  donnée n'était réellement persistée. Un garde-fou a depuis été ajouté
  (`collectors/base.py`) : un run à 0 % de succès sur des enregistrements
  traités fait maintenant échouer explicitement le job (`sys.exit(1)`,
  croix rouge visible). Ce garde-fou protège contre le symptôme, pas la
  cause : **dimensionner la base de production avec une marge de stockage
  réelle**, pas un plan gratuit minimal, si le volume de collecte est
  significatif (voir point suivant).
- **`crt.sh` externe et peu fiable** : le module de surveillance des
  certificats SSL (`collectors/ct_monitor.py`) dépend de `crt.sh`, un
  service tiers gratuit sans garantie de disponibilité, régulièrement lent
  ou temporairement indisponible. Le workflow `cameroon-monitors.yml` borne
  déjà cette étape (`timeout-minutes: 20`, `continue-on-error: true`) pour
  ne pas bloquer les autres monitors en cas d'indisponibilité — mais cela
  signifie que la surveillance des certificats peut avoir des trous
  temporels si `crt.sh` est indisponible plusieurs jours de suite.
- **Volume généré par le typosquat monitor** : le dictionnaire de mots-clés
  (`data/dnstwist_dictionary.txt`) et la liste de TLD
  (`data/dnstwist_tlds.txt`) utilisés par `collectors/typosquat_monitor.py`
  génèrent, combinés aux permutations dnstwist, un volume de candidats
  significatif — mesuré à environ **1200 candidats pour ~130 institutions**
  lors du développement. À multiplier par le nombre d'institutions
  effectivement surveillées pour dimensionner le stockage et le temps
  d'exécution (ce collecteur est aussi le plus lent de la plateforme,
  jusqu'à ~40 minutes selon la configuration).
