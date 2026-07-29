# Intégration TAXII 2.1 — guide pour un organisme partenaire

Ce document explique comment un organisme externe (autre CIRT régional,
SIEM, pare-feu) se connecte au serveur TAXII 2.1 de la plateforme pour
récupérer nos indicateurs de compromission (IOCs) en continu.

Deux façons de consommer nos IOCs :

| Besoin | Endpoint | Usage |
|---|---|---|
| Un export ponctuel (script cron simple, import manuel) | `GET /export/stix`, `/export/csv`, `/export/blocklist` | Un seul appel, snapshot complet trié par confiance |
| Une synchronisation continue (SIEM, MISP, OpenCTI...) | `GET /taxii2/...` | Protocole standard TAXII 2.1, pagination incrémentale |

Ce guide couvre le second cas (TAXII), le plus pertinent pour une intégration
durable entre deux plateformes.

## 1. Obtenir une clé API

Chaque organisme partenaire a sa propre clé, révocable indépendamment (voir
`scripts/manage_api_keys.py`). Contactez l'administrateur de la plateforme
(ANTIC/CIRT Cameroun) pour qu'il en crée une pour vous :

```bash
python -m scripts.manage_api_keys create --name "Nom de votre organisme" --contact "contact@votre-domaine"
```

Vous recevrez une clé au format `tip_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`,
affichée **une seule fois** à la création. Elle se fournit dans chaque appel
via le header `X-API-Key`.

## 2. Parcours TAXII standard (curl)

Un client TAXII 2.1 se connecte toujours dans cet ordre : Discovery → API
Root → Collections → Objects.

```bash
KEY="tip_votre_cle_ici"
BASE="https://<votre-domaine-tip>"   # http://localhost:8001 en local

# 1. Discovery — liste les API roots disponibles
curl -s -H "X-API-Key: $KEY" "$BASE/taxii2/"

# 2. API Root — capacités de cet API root
curl -s -H "X-API-Key: $KEY" "$BASE/taxii2/api"

# 3. Lister les collections disponibles
curl -s -H "X-API-Key: $KEY" "$BASE/taxii2/api/collections"
# -> une seule collection : "365fed99-08fa-4fcd-a1b3-fb247eb41d01" (Indicateurs actifs)

# 4. Récupérer les objets STIX de la collection
curl -s -H "X-API-Key: $KEY" \
  "$BASE/taxii2/api/collections/365fed99-08fa-4fcd-a1b3-fb247eb41d01/objects?limit=100"
```

## 3. Pagination (synchronisation incrémentale)

`/objects` et `/manifest` acceptent :

- `added_after` (ISO 8601, ex. `2026-07-01T00:00:00Z`) : ne renvoie que les
  IOCs créés après cette date — à utiliser pour le **premier** appel d'une
  synchro (ex. "tout ce qui est arrivé depuis mon dernier passage hier").
- `next` : curseur opaque renvoyé dans le champ `next` de la réponse
  précédente — à repasser tel quel pour la page suivante.
- `limit` (défaut 500, max 2000).

La réponse contient toujours `more` (bool) et, si `more` est `true`, `next`
(string). Une page peut contenir moins de `limit` objets si certaines lignes
ne se convertissent pas en objet STIX (ex. les CVE, qui n'ont pas
d'équivalent STIX "indicator") — ce n'est pas une anomalie : continuez à
suivre `next` tant que `more` vaut `true`.

```bash
# Première page depuis une date donnée
curl -s -H "X-API-Key: $KEY" \
  "$BASE/taxii2/api/collections/365fed99-08fa-4fcd-a1b3-fb247eb41d01/objects?added_after=2026-07-01T00:00:00Z&limit=100"

# Page suivante (le "next" vient de la réponse précédente)
curl -s -H "X-API-Key: $KEY" \
  "$BASE/taxii2/api/collections/365fed99-08fa-4fcd-a1b3-fb247eb41d01/objects?next=<valeur_next>&limit=100"
```

## 4. Script Python — synchronisation en continu

Boucle minimale : récupère tout ce qui est nouveau depuis le dernier passage,
en suivant `next` jusqu'à épuisement, puis mémorise la date pour la
prochaine exécution (à lancer par exemple via cron toutes les heures).

```python
#!/usr/bin/env python3
"""Synchronise les IOCs actifs de la TIP ANTIC/CIRT Cameroun en continu."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = os.environ["TIP_BASE_URL"]         # ex: https://tip.antic.cm
API_KEY = os.environ["TIP_API_KEY"]           # clé fournie par l'admin de la TIP
COLLECTION_ID = "365fed99-08fa-4fcd-a1b3-fb247eb41d01"
STATE_FILE = Path("tip_sync_state.json")      # mémorise le dernier point de synchro

HEADERS = {"X-API-Key": API_KEY}


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"added_after": None}  # premier lancement : tout récupérer


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state))


def fetch_all_new_objects(added_after: str | None) -> list[dict]:
    objects = []
    params = {"limit": 500}
    if added_after:
        params["added_after"] = added_after

    url = f"{BASE_URL}/taxii2/api/collections/{COLLECTION_ID}/objects"
    while True:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        objects.extend(data["objects"])

        if not data.get("more"):
            break
        params = {"next": data["next"], "limit": 500}  # 'next' remplace added_after

    return objects


def main() -> None:
    state = load_state()
    sync_start = datetime.now(timezone.utc).isoformat()

    new_objects = fetch_all_new_objects(state["added_after"])
    print(f"{len(new_objects)} nouveaux indicateurs récupérés.")

    for obj in new_objects:
        # TODO : brancher ici votre ingestion (SIEM, pare-feu, MISP...)
        print(f"  - {obj['id']}  {obj.get('pattern', '')}")

    state["added_after"] = sync_start
    save_state(state)


if __name__ == "__main__":
    main()
```

Variables d'environnement attendues :

```bash
export TIP_BASE_URL="https://tip.antic.cm"
export TIP_API_KEY="tip_votre_cle_ici"
python3 sync_tip.py
```

## 5. Erreurs courantes

| Code | Cause | Action |
|---|---|---|
| `403` | Clé API absente, invalide ou révoquée | Vérifier le header `X-API-Key`, contacter l'admin si la clé devrait être active |
| `400` sur `/objects` ou `/manifest` | `added_after` ou `next` mal formé | `added_after` doit être ISO 8601 ; `next` doit être copié tel quel depuis la réponse précédente, jamais construit à la main |
| `404` sur `/collections/{id}` | UUID de collection incorrect | Utiliser l'UUID renvoyé par `GET /taxii2/api/collections`, ne pas le coder en dur sans vérifier |

## 6. Alternative : export ponctuel

Pour un import manuel ou un script cron simple (sans état à maintenir),
`/export/stix`, `/export/csv` et `/export/blocklist` restent disponibles et
protégés par la même clé API :

```bash
curl -s -H "X-API-Key: $KEY" "$BASE/export/stix?confidence_min=70" -o iocs.json
curl -s -H "X-API-Key: $KEY" "$BASE/export/blocklist?confidence_min=70" -o blocklist.txt
```

Contrairement à `/taxii2/*`, ces endpoints n'ont pas de mécanisme de reprise
incrémentale (`added_after`/`next`) — chaque appel renvoie l'état complet
actuel au-dessus du seuil de confiance demandé.
