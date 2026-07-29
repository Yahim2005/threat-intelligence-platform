# api/rate_limit.py
"""
Configuration centralisée du rate limiting (slowapi).

Isolé dans son propre module pour éviter un import circulaire : api/main.py
importe api/exports.py et api/taxii.py au démarrage (app.include_router),
donc ces derniers ne peuvent pas ré-importer `limiter` depuis api/main.py.
api/main.py importe désormais `limiter` d'ici plutôt que de l'instancier
lui-même -- comportement inchangé pour toutes les routes existantes.

Deux instances de Limiter, volontairement séparées :

- `limiter` : celle déjà utilisée par toutes les routes existantes de
  api/main.py (get_remote_address, headers_enabled=False -- comportement
  identique à avant).
- `client_limiter` : dédiée à /export/* et /taxii2/*, avec headers_enabled=True
  pour exposer Retry-After / X-RateLimit-* comme demandé.

Pourquoi deux instances et pas juste `headers_enabled=True` sur `limiter` :
slowapi, quand headers_enabled=True, essaie d'injecter les headers dans
l'objet Response renvoyé par CHAQUE route déjà décorée par cette instance.
Si la route ne renvoie pas explicitement un objet Response (la majorité des
routes de main.py renvoient un modèle pydantic / dict, converti en JSON par
FastAPI) et n'a pas de paramètre `response: Response` que FastAPI peut
peupler, slowapi lève une exception -> 500 sur ces routes (vérifié : casse
GET /monitored-assets et probablement une bonne partie de main.py). Les
routes de /export/* et /taxii2/*, elles, renvoient déjà toutes un objet
Response explicite (JSONResponse / StreamingResponse) -- headers_enabled=True
y est donc sûr, sans toucher aux routes existantes ni à leur instance.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# get_remote_address : clé par défaut (IP), conservée pour les routes
# publiques existantes (ex: /auth/login) qui n'ont pas de notion de client
# identifié. headers_enabled reste à sa valeur par défaut (False) -- aucun
# changement de comportement pour ces routes.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


def api_client_key(request: Request) -> str:
    """
    Clé de rate limiting par organisme (clé API) plutôt que par IP -- pour
    /export/* et /taxii2/*, dont les consommateurs sont des organismes
    externes identifiés (table api_clients, voir api/auth.py).

    Sans ça, deux organismes derrière la même IP/NAT se gêneraient
    mutuellement, et un organisme légitime interrogeant depuis plusieurs
    serveurs sortants serait bridé à tort.

    Fonctionne parce que api.auth.get_api_key (une Depends()) pose
    request.state.api_client_id / api_client_name AVANT que ce key_func ne
    soit appelé : FastAPI résout toutes les dépendances d'une route avant
    d'invoquer le handler, et le décorateur @limiter.limit() n'évalue la
    limite qu'à ce moment-là (juste avant l'exécution du corps de la route).
    """
    client_id = getattr(request.state, "api_client_id", None)
    if client_id:
        return f"apiclient:{client_id}"
    client_name = getattr(request.state, "api_client_name", None)
    if client_name:
        # Clé "legacy-env-key" (TIP_API_KEY) : bucket partagé unique, cohérent
        # avec le fait que cette clé n'identifie pas un organisme précis.
        return f"apiclient:{client_name}"
    # Filet de sécurité : ne devrait pas arriver en pratique, get_api_key
    # renvoie 403 avant d'atteindre la route si la clé est absente/invalide.
    return f"ip:{get_remote_address(request)}"


# Instance dédiée /export/* + /taxii2/* : voir le pourquoi du "headers_enabled"
# dans le docstring du module. key_func par défaut = api_client_key, pas
# besoin de le répéter à chaque décorateur.
client_limiter = Limiter(key_func=api_client_key, headers_enabled=True)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Remplace le handler par défaut de slowapi (qui utilise toujours
    `app.state.limiter`, une seule instance) : ici on choisit la bonne
    instance selon le chemin, pour que les headers Retry-After/X-RateLimit-*
    reflètent la vraie limite qui a été dépassée (`limiter` ou
    `client_limiter`), qu'elle vienne d'une route existante ou de
    /export|/taxii2.
    """
    response = JSONResponse({"error": f"Rate limit exceeded: {exc.detail}"}, status_code=429)
    active = client_limiter if request.url.path.startswith(("/export/", "/taxii2/")) else limiter
    return active._inject_headers(response, request.state.view_rate_limit)
