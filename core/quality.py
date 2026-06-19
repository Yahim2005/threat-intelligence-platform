"""Détection de faux positifs anti-allowlisting.

Empêche la base de se polluer avec des indicateurs légitimes mal classés
par les feeds (IP de DNS publics, plages privées RFC1918, domaines très
populaires...). Les IOC détectés ici ne sont jamais supprimés : ils sont
marqués `whitelisted` pour rester traçables (cf. IndicatorStatus).
"""
from __future__ import annotations

import csv
import ipaddress
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.models.enums import IOCType

# Chemins relatifs à la racine du projet, peu importe d'où le script est lancé.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ALLOWLIST_PATH = _PROJECT_ROOT / "config" / "allowlist.yaml"
_TRANCO_PATH = _PROJECT_ROOT / "data" / "tranco_top10k.csv"

# Caches module-level, remplis paresseusement au premier appel.
_tranco_domains: set[str] | None = None
_allowlist_config: dict | None = None


@dataclass(frozen=True)
class QualityVerdict:
    """Résultat d'une vérification anti-faux-positif.

    is_false_positive : True si l'IOC matche une règle d'allowlisting.
    reason : code court identifiant la règle déclenchée, pour traçabilité
             dans raw_metadata. None si aucun problème détecté.
    """
    is_false_positive: bool
    reason: str | None = None


def _load_tranco() -> set[str]:
    """Charge le set de domaines populaires Tranco en mémoire (une seule fois)."""
    global _tranco_domains
    if _tranco_domains is not None:
        return _tranco_domains

    domains: set[str] = set()
    if _TRANCO_PATH.exists():
        with open(_TRANCO_PATH, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    domains.add(row[1].strip().lower())

    _tranco_domains = domains
    return _tranco_domains


def _load_allowlist() -> dict:
    """Charge config/allowlist.yaml en mémoire (une seule fois)."""
    global _allowlist_config
    if _allowlist_config is not None:
        return _allowlist_config

    if _ALLOWLIST_PATH.exists():
        with open(_ALLOWLIST_PATH, encoding="utf-8") as f:
            _allowlist_config = yaml.safe_load(f) or {}
    else:
        _allowlist_config = {}

    return _allowlist_config


def _check_ip(value: str) -> QualityVerdict:
    """Vérifie si une IP (v4 ou v6) doit être whitelistée."""
    try:
        ip_obj = ipaddress.ip_address(value)
    except ValueError:
        # Valeur malformée : ce n'est pas le rôle de quality.py de la rejeter,
        # normalize.py s'en est déjà chargé en amont. On ne bloque rien ici.
        return QualityVerdict(is_false_positive=False)

    if ip_obj.is_loopback:
        return QualityVerdict(True, "loopback_ip")
    if ip_obj.is_link_local:
        return QualityVerdict(True, "link_local_ip")
    if ip_obj.is_multicast:
        return QualityVerdict(True, "multicast_ip")
    if ip_obj.is_reserved:
        return QualityVerdict(True, "reserved_ip")
    if ip_obj.is_private:
        return QualityVerdict(True, "private_ip_rfc1918")

    allowlist = _load_allowlist()

    public_dns_ips = set(allowlist.get("public_dns_ips") or [])
    if value in public_dns_ips:
        return QualityVerdict(True, "known_public_dns")

    extra_cidrs = allowlist.get("extra_allowed_cidrs") or []
    for cidr in extra_cidrs:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            continue
        if ip_obj in network:
            return QualityVerdict(True, "extra_allowed_cidr")

    return QualityVerdict(is_false_positive=False)


def _check_domain(value: str) -> QualityVerdict:
    """Vérifie si un domaine doit être whitelisté (popularité Tranco ou règle manuelle)."""
    domain = value.strip().lower()

    tranco_domains = _load_tranco()
    if domain in tranco_domains:
        return QualityVerdict(True, "tranco_top10k")

    allowlist = _load_allowlist()
    extra_domains = {d.strip().lower() for d in (allowlist.get("extra_allowed_domains") or [])}
    if domain in extra_domains:
        return QualityVerdict(True, "extra_allowed_domain")

    return QualityVerdict(is_false_positive=False)


def check_quality(value: str, ioc_type: IOCType) -> QualityVerdict:
    """Point d'entrée principal : détermine si un IOC est un faux positif connu.

    Ne vérifie aujourd'hui que les IP (v4/v6) et les domaines — les autres
    types (hash, URL, CVE, ASN...) n'ont pas encore de règle de filtrage et
    retournent toujours is_false_positive=False.
    """
    if ioc_type in (IOCType.ip, IOCType.ipv6):
        return _check_ip(value)
    if ioc_type == IOCType.domain:
        return _check_domain(value)
    return QualityVerdict(is_false_positive=False)