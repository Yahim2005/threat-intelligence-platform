"""Vocabulaire de tags normalisés pour les indicateurs.

Convention : namespace:valeur, en minuscules, slug-safe (a-z0-9-).
Namespaces réservés :
    kind:*      type de menace (c2, phishing, malware-hosting, exploit, scanner...)
    malware:*   famille de malware (emotet, qakbot, cobaltstrike...)
    source:*    origine logique (tor-exit, kev, allowlist...)
"""
from __future__ import annotations

import re

_SLUG_RE = re.compile(r"[^a-z0-9:-]+")


def normalize_tag(raw: str) -> str:
    """Normalise un tag brut vers la forme canonique namespace:valeur.

    Exemples :
        "Emotet"          -> "malware:emotet"   (impossible à deviner sans namespace -> voir normalize_tag_with_namespace)
        "C2"              -> "c2"               (pas de namespace fourni, reste tel quel slugifié)
        "kind:C2 Server"  -> "kind:c2-server"
    """
    value = raw.strip().lower().replace(" ", "-")
    value = _SLUG_RE.sub("", value)
    value = re.sub(r"-{2,}", "-", value).strip("-:")
    return value


def make_tag(namespace: str, value: str) -> str:
    """Construit un tag namespacé normalisé : make_tag('kind', 'C2 Server') -> 'kind:c2-server'."""
    ns = normalize_tag(namespace)
    val = normalize_tag(value)
    return f"{ns}:{val}"


# Namespaces connus, pour validation optionnelle / documentation.
KNOWN_NAMESPACES = {"kind", "malware", "source"}

# Valeurs `kind` recommandées (non exhaustif, extensible).
KNOWN_KINDS = {
    "c2",
    "phishing",
    "malware-hosting",
    "exploit",
    "scanner",
    "botnet",
    "spam",
    "tor-exit",
    "vulnerability",
}