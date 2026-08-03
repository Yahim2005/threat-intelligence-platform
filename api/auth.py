# api/auth.py

import os
from datetime import datetime
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api_clients import hash_api_key as _hash_key
from app.database import SessionLocal
from app.models.api_client import ApiClient
from app.models.user import User
from app.models.enums import TLPLevel, UserRole
from app.security import decode_access_token

# FastAPI lit automatiquement le header X-API-Key dans chaque requête
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


# Politique de diffusion TLP de l'API. RED n'apparait volontairement dans
# aucune liste : ce niveau reste reserve aux traitements internes en base.
USER_VISIBLE_TLPS = (TLPLevel.CLEAR, TLPLevel.GREEN)
ADMIN_VISIBLE_TLPS = (
    TLPLevel.CLEAR,
    TLPLevel.GREEN,
    TLPLevel.AMBER,
    TLPLevel.AMBER_STRICT,
)


def visible_tlp_levels_for(user: User) -> tuple[TLPLevel, ...]:
    """Retourne les niveaux TLP consultables par un utilisateur authentifie."""
    if user.role == UserRole.admin:
        return ADMIN_VISIBLE_TLPS
    return USER_VISIBLE_TLPS


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_api_key(
    request: Request,
    api_key: str = Security(API_KEY_HEADER),
    db: Session = Depends(get_db),
) -> ApiClient | None:
    """
    Dépendance FastAPI : vérifie le header X-API-Key contre les clés
    d'organismes enregistrées en base (table api_clients — voir
    scripts/manage_api_keys.py pour en créer/révoquer).

    Compatibilité : TIP_API_KEY (.env) reste acceptée comme clé de secours
    "legacy" (utile pour tes propres tests), mais n'est plus la seule clé
    valide et n'est associée à aucun organisme identifiable dans l'audit log.
    Les nouveaux partenaires doivent recevoir une clé dédiée via le script.

    Renvoie l'ApiClient correspondant (ou None pour la clé legacy), et pose
    request.state.api_client_name / api_client_id pour que le middleware de
    logging (api/main.py) puisse tracer qui a consulté quoi.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API invalide ou absente. Fournissez X-API-Key dans les headers.",
        )

    legacy_key = os.getenv("TIP_API_KEY")
    if legacy_key and api_key == legacy_key:
        request.state.api_client_name = "legacy-env-key"
        request.state.api_client_id = None
        return None

    client = (
        db.query(ApiClient)
        .filter(ApiClient.key_hash == _hash_key(api_key), ApiClient.is_active.is_(True))
        .first()
    )
    if not client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API invalide ou absente. Fournissez X-API-Key dans les headers.",
        )

    client.last_used_at = datetime.utcnow()
    db.commit()

    request.state.api_client_name = client.name
    request.state.api_client_id = str(client.id)
    return client


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise. Fournissez un token Bearer.",
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
        )

    try:
        user_id = UUID(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformé.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou compte désactivé.",
        )
    return user


def get_current_user_or_api_key(
    request: Request,
    api_key: str = Security(API_KEY_HEADER),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | ApiClient | None:
    """
    Dépendance combinée pour les routes utilisées À LA FOIS par des
    partenaires externes (clé API -- TAXII, scripts) ET par un utilisateur du
    dashboard authentifié par JWT (ex: boutons d'export d'Overview.jsx, qui
    envoyaient auparavant une clé API partagée exposée dans le bundle JS
    public -- voir dashboard/src/api/client.js pour le token déjà utilisé
    par le reste du dashboard).

    Réutilise get_api_key et get_current_user tels quels (mêmes messages
    d'erreur, même comportement) plutôt que de dupliquer leur logique --
    aucun des deux n'est modifié, donc aucun usage existant n'est affecté.

    Ordre : clé API d'abord si fournie (un partenaire qui se trompe de clé
    reçoit un 403 explicite, pas un 401 générique), puis Bearer. Si ni l'un
    ni l'autre n'est fourni, 401 -- cohérent avec get_current_user, qui
    traite déjà l'absence de credentials comme un 401.
    """
    if api_key:
        return get_api_key(request=request, api_key=api_key, db=db)
    if credentials is not None:
        return get_current_user(credentials=credentials, db=db)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise : fournissez un token Bearer (session dashboard) ou une clé API X-API-Key (partenaire).",
    )


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dépendance FastAPI : comme get_current_user, mais exige en plus le rôle admin.
    À utiliser sur les routes réservées (soumission d'IOC, /health, etc).
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action réservée aux administrateurs.",
        )
    return current_user
