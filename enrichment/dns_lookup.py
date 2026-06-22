"""Enrichisseur DNS : résolution A, MX, NS pour IPs et domaines."""
from __future__ import annotations

import logging
import socket

import dns.resolver
import dns.reversename
import dns.exception

from app.models import Indicator
from app.models.enums import IOCType
from enrichment.base import BaseEnricher

logger = logging.getLogger(__name__)

_TIMEOUT = 3  # secondes par requête DNS


def _resolver() -> dns.resolver.Resolver:
    r = dns.resolver.Resolver()
    r.lifetime = _TIMEOUT
    return r


class DNSEnricher(BaseEnricher):
    provider = "dns"
    ioc_types = [IOCType.ip, IOCType.ipv6, IOCType.domain]

    def enrich(self, indicator: Indicator) -> dict:
        result = {}
        value = indicator.value

        if indicator.type in (IOCType.ip, IOCType.ipv6):
            # Reverse DNS : IP → hostname
            try:
                hostname = socket.gethostbyaddr(value)[0]
                result["reverse_dns"] = hostname
            except (socket.herror, socket.gaierror, OSError):
                result["reverse_dns"] = None

        elif indicator.type == IOCType.domain:
            # Forward DNS : domain → IPs (enregistrements A)
            try:
                answers = _resolver().resolve(value, "A")
                result["a_records"] = [r.address for r in answers]
            except (dns.exception.DNSException, Exception):
                result["a_records"] = []

            # MX records
            try:
                answers = _resolver().resolve(value, "MX")
                result["mx_records"] = [str(r.exchange).rstrip(".") for r in answers]
            except (dns.exception.DNSException, Exception):
                result["mx_records"] = []

            # NS records
            try:
                answers = _resolver().resolve(value, "NS")
                result["ns_records"] = [str(r.target).rstrip(".") for r in answers]
            except (dns.exception.DNSException, Exception):
                result["ns_records"] = []

        return result