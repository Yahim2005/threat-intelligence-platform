"""
Gestion des clés API par organisme externe (api_clients).

Remplace la TIP_API_KEY unique partagée : chaque partenaire (autre CIRT,
SIEM, pare-feu...) reçoit sa propre clé, révocable indépendamment, avec un
nom/contact associé pour l'audit (voir api/auth.py et le log structuré de
api/main.py).

La clé en clair n'est affichée QU'UNE SEULE FOIS à la création — seul son
hash SHA-256 est stocké en base. Note-la immédiatement.

Usage :
    python -m scripts.manage_api_keys create --name "CIRT Sénégal" --contact "soc@cirt.sn"
    python -m scripts.manage_api_keys list
    python -m scripts.manage_api_keys revoke <id>
"""
from __future__ import annotations
import argparse
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.api_client import ApiClient
from api.auth import _hash_key


def cmd_create(args: argparse.Namespace) -> None:
    raw_key = f"tip_{secrets.token_hex(24)}"
    client = ApiClient(
        name=args.name,
        contact_email=args.contact,
        key_hash=_hash_key(raw_key),
        key_prefix=raw_key[:12],
    )
    with SessionLocal() as db:
        db.add(client)
        db.commit()
        db.refresh(client)

    print(f"✅  Client créé : {client.name}  (id={client.id})")
    print()
    print(f"Clé API (à transmettre au partenaire, ne sera plus jamais affichée) :")
    print(f"  {raw_key}")
    print()
    print("Test rapide :")
    print(f'  curl -H "X-API-Key: {raw_key}" http://localhost:8001/taxii2/')


def cmd_list(args: argparse.Namespace) -> None:
    with SessionLocal() as db:
        clients = db.query(ApiClient).order_by(ApiClient.created_at.desc()).all()

    if not clients:
        print("Aucun client API enregistré.")
        return

    for c in clients:
        status_label = "actif" if c.is_active else "révoqué"
        last_used = c.last_used_at.isoformat() if c.last_used_at else "jamais utilisée"
        print(f"[{status_label}] {c.name}  (id={c.id})")
        print(f"    contact       : {c.contact_email or '—'}")
        print(f"    clé (préfixe) : {c.key_prefix}...")
        print(f"    créée le      : {c.created_at.isoformat()}")
        print(f"    dernier accès : {last_used}")
        print()


def cmd_revoke(args: argparse.Namespace) -> None:
    with SessionLocal() as db:
        client = db.query(ApiClient).filter(ApiClient.id == args.client_id).first()
        if not client:
            sys.exit(f"❌  Aucun client avec l'id {args.client_id}")
        if not client.is_active:
            print(f"⚠️  {client.name} était déjà révoqué.")
            return
        client.is_active = False
        db.commit()

    print(f"✅  Clé révoquée pour {client.name} (id={client.id}). Effet immédiat sur toutes les routes protégées.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gestion des clés API par organisme")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="Créer une nouvelle clé pour un organisme")
    p_create.add_argument("--name", required=True, help="Nom de l'organisme (ex: 'CIRT Sénégal')")
    p_create.add_argument("--contact", default=None, help="Email de contact")
    p_create.set_defaults(func=cmd_create)

    p_list = sub.add_parser("list", help="Lister les clients API et leur statut")
    p_list.set_defaults(func=cmd_list)

    p_revoke = sub.add_parser("revoke", help="Révoquer une clé (irréversible sans en recréer une)")
    p_revoke.add_argument("client_id", help="UUID du client (voir 'list')")
    p_revoke.set_defaults(func=cmd_revoke)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
