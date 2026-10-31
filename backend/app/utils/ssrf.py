"""SSRF validation primitives that validate the URL, resolve the host and pin the connection."""

import ipaddress
import socket
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from requests.utils import select_proxy
from urllib3.exceptions import LocationParseError
from urllib3.util import parse_url


class SSRFValidationError(Exception):
    """The URL points at a forbidden destination (invalid scheme or internal network)."""


class PinnedIPAdapter(HTTPAdapter):
    """Connect to an already validated IP, keeping the real host's Host header and SNI/certificate."""

    def __init__(self, host: str, ip: str, **kwargs):
        self._host = host.lower()
        self._ip = ip
        super().__init__(**kwargs)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        # With a proxy, the proxy resolves the name, so pinning the IP makes no sense.
        if select_proxy(request.url, proxies):
            return super().get_connection_with_tls_context(
                request, verify, proxies, cert
            )

        host_params, pool_kwargs = self.build_connection_pool_key_attributes(
            request, verify, cert
        )
        if host_params["host"].lower() == self._host:
            host_params["host"] = self._ip
            if host_params["scheme"] == "https":
                # TLS verification still uses the real host, not the IP.
                pool_kwargs["server_hostname"] = self._host
                pool_kwargs["assert_hostname"] = self._host

        return self.poolmanager.connection_from_host(
            **host_params, pool_kwargs=pool_kwargs
        )


def is_public_ip(ip_str: str) -> bool:
    """Return True if the IP is public and fit for outbound connections."""
    ip = ipaddress.ip_address(ip_str)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def resolve_public_host(url: str) -> tuple[str, str]:
    """Validate the URL and return ``(host, public_ip)`` to pin the connection."""
    # urlparse raises ValueError on characters invalid under NFKC, so the URL is treated as invalid.
    try:
        parsed = urlparse(url)
    except ValueError as e:
        raise SSRFValidationError("La URL no contiene un host válido") from e

    if parsed.scheme not in {"http", "https"}:
        raise SSRFValidationError("La URL debe comenzar con http:// o https://")

    if not parsed.hostname:
        raise SSRFValidationError("La URL no contiene un host válido")

    host = parsed.hostname.strip().lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise SSRFValidationError(
            "No se permite extraer contenido desde URLs locales o de red interna"
        )

    # requests connects using urllib3's parsing, so the URL is refused if it differs from the validated host (e.g. a backslash in the authority).
    try:
        connect_host = (parse_url(url).host or "").strip().lower().strip("[]")
    except LocationParseError as e:
        raise SSRFValidationError("La URL no contiene un host válido") from e
    if connect_host != host.strip("[]"):
        raise SSRFValidationError(
            "No se permite extraer contenido desde URLs locales o de red interna"
        )

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addrinfo = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SSRFValidationError(f"No se pudo resolver el host de la URL: {e}") from e

    resolved_ips = [
        str(entry[4][0]) for entry in addrinfo if isinstance(entry[4][0], str)
    ]
    if not resolved_ips:
        raise SSRFValidationError(
            "No se pudo resolver ninguna IP para el host indicado"
        )

    if not all(is_public_ip(ip) for ip in resolved_ips):
        raise SSRFValidationError(
            "No se permite extraer contenido desde URLs locales o de red interna"
        )

    return host, resolved_ips[0]


def build_pinned_session(host: str, ip: str) -> requests.Session:
    """Create a session that connects to ``ip`` for any request to ``host``."""
    session = requests.Session()
    adapter = PinnedIPAdapter(host, ip)
    session.mount(f"http://{host}", adapter)
    session.mount(f"https://{host}", adapter)
    return session
