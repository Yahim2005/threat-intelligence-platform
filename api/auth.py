# api/auth.py

import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

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