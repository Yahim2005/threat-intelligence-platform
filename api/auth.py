# api/auth.py

import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from fastapi import Security, HTTPException, status, Depends
# FastAPI lit automatiquement le header X-API-Key dans chaque requête
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    Dépendance FastAPI : vérifie que le header X-API-Key est présent et correct.
    Si absent ou incorrect → 403 Forbidden.
    """
    expected = os.getenv("TIP_API_KEY")
    if not expected:
        raise RuntimeError("TIP_API_KEY non définie dans .env")
    if api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API invalide ou absente. Fournissez X-API-Key dans les headers.",
        )
    return api_key

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.models.enums import UserRole
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from uuid import UUID

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