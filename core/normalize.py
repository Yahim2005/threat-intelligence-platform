"""Moteur central de normalisation et détection de type d'IOC.

Toute donnée brute provenant d'un collecteur doit passer par detect_and_normalize()
avant d'entrer dans la base — plus aucun collecteur ne devine son propre type.

Principe de détection : une regex repère un CANDIDAT, une validation stricte
confirme le type (longueur exacte, charset, sémantique via des bibliothèques
dédiées comme `ipaddress` plutôt que des regex maison pour les IP).
"""
import ipaddress
import re

from app.models.enums import IOCType

# ------------------------------------------------------------------ #
#  Defang / Refang                                                    #
# ------------------------------------------------------------------ #
# Les feeds CTI "défangent" volontairement les indicateurs dangereux
# (hxxp://, [.]，[@]) pour éviter qu'un clic accidentel ne déclenche
# une vraie requête réseau. On "refang" pour stocker la forme propre,
# et on pourra "defang" à l'affichage si besoin plus tard.

_REFANG_RULES = [
    (re.compile(r"hxxp://", re.IGNORECASE), "http://"),
    (re.compile(r"hxxps://", re.IGNORECASE), "https://"),
    (re.compile(r"\[\.\]"), "."),
    (re.compile(r"\[@\]"), "@"),
    (re.compile(r"\[:\]"), ":"),
]

_DEFANG_RULES = [
    (re.compile(r"http://", re.IGNORECASE), "hxxp://"),
    (re.compile(r"https://", re.IGNORECASE), "hxxps://"),
    (re.compile(r"\."), "[.]"),
]


def refang(value: str) -> str:
    """Transforme une valeur défangée (hxxp://, 1.2.3[.]4) en forme propre."""
    result = value
    for pattern, replacement in _REFANG_RULES:
        result = pattern.sub(replacement, result)
    return result


def defang(value: str) -> str:
    """Transforme une valeur propre en forme défangée, pour affichage sans danger."""
    result = value
    for pattern, replacement in _DEFANG_RULES:
        result = pattern.sub(replacement, result)
    return result


# ------------------------------------------------------------------ #
#  Détection de type — chaque fonction valide STRICTEMENT, pas juste  #
#  un pattern approximatif.                                           #
# ------------------------------------------------------------------ #

_MD5_RE = re.compile(r"^[a-fA-F0-9]{32}$")
_SHA1_RE = re.compile(r"^[a-fA-F0-9]{40}$")
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
_ASN_RE = re.compile(r"^AS\d+$", re.IGNORECASE)
# Numéro de téléphone : E.164 international ou camerounais local
_PHONE_RE = re.compile(
    r"^\+\d{7,15}$"       # E.164 strict  : +237699123456
    r"|^00\d{7,15}$"       # Avec 00       : 00237699123456
    r"|^[26]\d{8}$"        # Local CM 9ch  : 699123456
)
_DOMAIN_LABEL_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


def _is_hash(value: str) -> IOCType | None:
    """Valide un hash par longueur ET charset exact — pas juste 'ça ressemble à de l'hexa'."""
    if _MD5_RE.match(value):
        return IOCType.md5
    if _SHA1_RE.match(value):
        return IOCType.sha1
    if _SHA256_RE.match(value):
        return IOCType.sha256
    return None


def _is_ip(value: str) -> IOCType | None:
    """Utilise ipaddress (validation sémantique réelle) plutôt qu'une regex maison."""
    try:
        ip_obj = ipaddress.ip_address(value)
    except ValueError:
        return None
    return IOCType.ipv6 if isinstance(ip_obj, ipaddress.IPv6Address) else IOCType.ip


def _is_cidr(value: str) -> bool:
    try:
        ipaddress.ip_network(value, strict=False)
        return "/" in value  # ip_network accepte aussi une IP seule ; on exige le préfixe
    except ValueError:
        return False


def _is_domain(value: str) -> bool:
    """Valide chaque label du domaine (entre points), gère le punycode (IDNA)."""
    if len(value) > 253 or "." not in value:
        return False
    try:
        # encode('idna') normalise et valide les domaines internationalisés (punycode).
        ascii_form = value.encode("idna").decode("ascii")
    except (UnicodeError, UnicodeDecodeError):
        ascii_form = value  # déjà en ASCII pur, idna peut échouer sur des cas triviaux

    labels = ascii_form.rstrip(".").split(".")
    if len(labels) < 2:
        return False
    return all(_DOMAIN_LABEL_RE.match(label) for label in labels)


def _is_url(value: str) -> bool:
    return bool(re.match(r"^(https?|ftp|tftp|file)://", value, re.IGNORECASE))


def detect_type(value: str) -> IOCType | None:
    """Détecte le type d'un IOC à partir de sa valeur déjà refangée.
    Retourne None si aucun type ne correspond (le collecteur doit alors
    décider quoi faire : ignorer le record, logger un avertissement, etc.).
    Ordre de vérification volontaire : du plus spécifique au plus général,
    pour éviter qu'un type plus large n'avale un cas qui appartient à un
    type plus précis (ex: une URL ne doit jamais être prise pour un domaine).
    """
    value = value.strip()
    if not value:
        return None

    if _CVE_RE.match(value):
        return IOCType.cve

    if _ASN_RE.match(value):
        return IOCType.asn

    hash_type = _is_hash(value)
    if hash_type:
        return hash_type

    if _EMAIL_RE.match(value):
        return IOCType.email
    if _PHONE_RE.match(value):
        return IOCType.phone

    if _is_url(value):
        return IOCType.url

    if _is_cidr(value):
        return IOCType.cidr

    ip_type = _is_ip(value)
    if ip_type:
        return ip_type

    if _is_domain(value):
        return IOCType.domain

    return None


# ------------------------------------------------------------------ #
#  Canonicalisation — forme unique et cohérente par type              #
# ------------------------------------------------------------------ #

def canonicalize(value: str, ioc_type: IOCType) -> str:
    """Ramène une valeur à sa forme canonique unique pour son type,
    pour éviter les doublons silencieux (EVIL.COM vs evil.com)."""
    value = value.strip()

    if ioc_type in (IOCType.domain, IOCType.md5, IOCType.sha1, IOCType.sha256, IOCType.email):
        return value.lower()

    if ioc_type == IOCType.ip:
        return str(ipaddress.IPv4Address(value))

    if ioc_type == IOCType.ipv6:
        return str(ipaddress.IPv6Address(value))

    if ioc_type == IOCType.cidr:
        return str(ipaddress.ip_network(value, strict=False))

    if ioc_type == IOCType.url:
        # Schéma et host en minuscules, le reste (path, query) inchangé : sensible à la casse.
        match = re.match(r"^((?:https?|ftp|tftp|file)://)([^/]+)(.*)$", value, re.IGNORECASE)
        if match:
            scheme, host, rest = match.groups()
            return f"{scheme.lower()}{host.lower()}{rest}"
        return value

    if ioc_type == IOCType.cve:
        return value.upper()

    if ioc_type == IOCType.phone:
        # Normalise en E.164 : supprime espaces/tirets, ajoute + si absent
        digits = re.sub(r"[\s\-\.\(\)]", "", value)
        if digits.startswith("00"):
            digits = "+" + digits[2:]
        elif not digits.startswith("+"):
            digits = "+237" + digits   # numéro local → préfixe Cameroun
        return digits
    if ioc_type == IOCType.asn:
        return value.upper()

    return value


def detect_and_normalize(raw_value: str) -> tuple[str, IOCType] | None:
    """Point d'entrée unique pour les collecteurs : refang, détecte le type,
    canonicalise. Retourne (valeur_normalisée, type) ou None si non détecté.
    """
    refanged = refang(raw_value.strip())
    ioc_type = detect_type(refanged)
    if ioc_type is None:
        return None
    return canonicalize(refanged, ioc_type), ioc_type