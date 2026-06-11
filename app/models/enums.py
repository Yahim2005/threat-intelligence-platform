import enum


class IOCType(str, enum.Enum):
    ip = "ip"
    domain = "domain"
    url = "url"
    md5 = "md5"
    sha256 = "sha256"
    sha1 = "sha1"
    email = "email"


class TLPLevel(str, enum.Enum):
    CLEAR = "CLEAR"
    GREEN = "GREEN"
    AMBER = "AMBER"
    AMBER_STRICT = "AMBER_STRICT"
    RED = "RED"


class IndicatorStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    revoked = "revoked"


class SourceType(str, enum.Enum):
    feed = "feed"
    api = "api"
    manual = "manual"


class ThreatType(str, enum.Enum):
    threat_actor = "threat-actor"
    malware = "malware"
    campaign = "campaign"


class RelationshipType(str, enum.Enum):
    indicates = "indicates"
    uses = "uses"
    targets = "targets"
    attributed_to = "attributed-to"
    mitigates = "mitigates"