"""
Logique partagée de gestion des clés API par organisme (api_clients).

Utilisé à la fois par scripts/manage_api_keys.py (CLI) et
api/api_clients_routes.py (interface admin du dashboard) -- pour que les deux
chemins de création génèrent/hashent une clé exactement de la même façon.

La clé en clair n'est jamais stockée : seul son hash SHA-256 l'est
(voir app/models/api_client.py). Elle n'est renvoyée qu'au moment de la
création, par l'appelant (CLI ou route API), jamais relue ensuite.
"""
from __future__ import annotations

import hashlib
import secrets

from sqlalchemy.orm import Session

from app.models.api_client import ApiClient


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    return f"tip_{secrets.token_hex(24)}"


def create_api_client(db: Session, name: str, contact_email: str | None) -> tuple[ApiClient, str]:
    """Crée un client API et renvoie (client, clé_en_clair). La clé en clair
    n'existe que dans cette valeur de retour -- à afficher/transmettre
    immédiatement à l'appelant, elle n'est jamais récupérable ensuite."""
    raw_key = generate_api_key()
    client = ApiClient(
        name=name,
        contact_email=contact_email,
        key_hash=hash_api_key(raw_key),
        key_prefix=raw_key[:12],
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client, raw_key


def regenerate_api_client(db: Session, client: ApiClient) -> str:
    """Génère une nouvelle clé pour un client EXISTANT (même id/name/
    contact_email) et invalide l'ancienne immédiatement -- seul moyen de
    "réafficher" une clé, puisque seul le hash est stocké (voir
    app/models/api_client.py). Renvoie la nouvelle clé en clair, une seule
    fois, comme create_api_client."""
    raw_key = generate_api_key()
    client.key_hash = hash_api_key(raw_key)
    client.key_prefix = raw_key[:12]
    client.last_used_at = None
    db.commit()
    db.refresh(client)
    return raw_key
