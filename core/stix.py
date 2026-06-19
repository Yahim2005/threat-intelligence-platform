"""Conversion Indicator (interne) -> objet STIX 2.1.

Construit des objets stix2.v21.Indicator avec un pattern correct par type
d'IOC, en s'appuyant sur la bibliothèque stix2 (pas de construction de
chaînes à la main) pour garantir une syntaxe de pattern valide.
"""
from __future__ import annotations

from stix2 import v21
from stix2.exceptions import STIXError

from app.models.enums import IOCType, TLPLevel

# Markings TLP standards OASIS — IDs fixes, à réutiliser tels quels.
# Source : https://github.com/oasis-open/cti-stix-common-objects
TLP_MARKING_IDS = {
    TLPLevel.CLEAR: "marking-definition--613f2e26-407d-48c7-9eca-b8e91df99dc9",
    TLPLevel.GREEN: "marking-definition--34098fce-860f-48ae-8e50-ebd3cc5e41da",
    TLPLevel.AMBER: "marking-definition--f88d31f6-486f-44da-b317-01333bde0b82",
    TLPLevel.AMBER_STRICT: "marking-definition--826578e1-40ad-459f-bc73-ede076f81f37",
    TLPLevel.RED: "marking-definition--5e57f73f-3cab-4dd5-9c41-2c5d7c5cdb15",
}


def _build_pattern(value: str, ioc_type: IOCType) -> str:
    """Construit la chaîne de pattern STIX pour une valeur+type donnés.

    On laisse la lib stix2 valider/sérialiser l'objet Indicator complet ;
    ici on ne fait que choisir le bon chemin de propriété cyber-observable
    par type, ce qui est la seule partie spécifique à notre domaine.
    """
    if ioc_type == IOCType.ip:
        return f"[ipv4-addr:value = '{value}']"
    if ioc_type == IOCType.ipv6:
        return f"[ipv6-addr:value = '{value}']"
    if ioc_type == IOCType.cidr:
        return f"[ipv4-addr:value = '{value}']"
    if ioc_type == IOCType.domain:
        return f"[domain-name:value = '{value}']"
    if ioc_type == IOCType.url:
        return f"[url:value = '{value}']"
    if ioc_type == IOCType.md5:
        return f"[file:hashes.MD5 = '{value}']"
    if ioc_type == IOCType.sha1:
        return f"[file:hashes.'SHA-1' = '{value}']"
    if ioc_type == IOCType.sha256:
        return f"[file:hashes.'SHA-256' = '{value}']"
    if ioc_type == IOCType.email:
        return f"[email-addr:value = '{value}']"
    if ioc_type == IOCType.asn:
        number = value[2:] if value.upper().startswith("AS") else value
        return f"[autonomous-system:number = {number}]"

    raise ValueError(f"Type {ioc_type!r} non supporté pour la conversion STIX (cve non mappable en indicator)")


def to_stix(indicator) -> v21.Indicator:
    """Convertit un Indicator interne en objet stix2.v21.Indicator.

    `indicator` est un objet ORM app.models.Indicator (ou tout objet exposant
    .value, .type, .tlp, .first_seen, .confidence, .tags).
    Lève ValueError si le type n'est pas mappable en pattern STIX,
    STIXError si la construction de l'objet échoue (pattern malformé...).
    """
    pattern = _build_pattern(indicator.value, indicator.type)

    labels = ["malicious-activity"]
    if indicator.tags:
        labels += [tag.name for tag in indicator.tags]

    marking_id = TLP_MARKING_IDS.get(indicator.tlp, TLP_MARKING_IDS[TLPLevel.CLEAR])

    kwargs = dict(
        id=f"indicator--{indicator.id}",
        name=f"{indicator.type.value}: {indicator.value}",
        pattern=pattern,
        pattern_type="stix",
        valid_from=indicator.first_seen or indicator.created_at,
        labels=labels,
        confidence=indicator.confidence,
        object_marking_refs=[marking_id],
    )

    try:
        return v21.Indicator(**kwargs)
    except STIXError as e:
        raise STIXError(f"Échec de conversion STIX pour {indicator.value!r} : {e}") from e