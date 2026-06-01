"""Este módulo contiene la función para extraer el texto de una URL."""

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.utils import select_proxy

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)


class URLExtractionError(Exception):
    """Excepción lanzada cuando ocurre un error al extraer el texto de la URL."""


class _PinnedIPAdapter(HTTPAdapter):
    """Conecta a un IP ya validado, preservando Host y SNI/certificado del host real."""

    def __init__(self, host: str, ip: str, **kwargs):
        self._host = host.lower()
        self._ip = ip
        super().__init__(**kwargs)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        # Con proxy la resolución la hace el proxy; no tiene sentido fijar la IP.
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
                # La verificación TLS sigue usando el host real, no la IP.
                pool_kwargs["server_hostname"] = self._host
                pool_kwargs["assert_hostname"] = self._host

        return self.poolmanager.connection_from_host(
            **host_params, pool_kwargs=pool_kwargs
        )


def _is_public_ip(ip_str: str) -> bool:
    """Devuelve True si la IP es pública y apta para conexiones salientes."""
    ip = ipaddress.ip_address(ip_str)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_public_host(url: str) -> tuple[str, str]:
    """Valida la URL y devuelve ``(host, ip_pública)`` para fijar la conexión."""
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise URLExtractionError("La URL debe comenzar con http:// o https://")

    if not parsed.hostname:
        raise URLExtractionError("La URL no contiene un host válido")

    host = parsed.hostname.strip().lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise URLExtractionError(
            "No se permite extraer contenido desde URLs locales o de red interna"
        )

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addrinfo = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise URLExtractionError(f"No se pudo resolver el host de la URL: {e}") from e

    resolved_ips = [
        str(entry[4][0]) for entry in addrinfo if isinstance(entry[4][0], str)
    ]
    if not resolved_ips:
        raise URLExtractionError("No se pudo resolver ninguna IP para el host indicado")

    if not all(_is_public_ip(ip) for ip in resolved_ips):
        raise URLExtractionError(
            "No se permite extraer contenido desde URLs locales o de red interna"
        )

    return host, resolved_ips[0]


def _build_pinned_session(host: str, ip: str) -> requests.Session:
    """Crea una sesión que conecta a ``ip`` para cualquier petición a ``host``."""
    session = requests.Session()
    adapter = _PinnedIPAdapter(host, ip)
    session.mount(f"http://{host}", adapter)
    session.mount(f"https://{host}", adapter)
    return session


def extract_text_from_url(url: str) -> str:
    """Extrae el texto de una página web dada su URL."""
    current_url = url
    max_redirects = 5
    response = None

    try:
        for _ in range(max_redirects + 1):
            # Validar y resolver en el mismo paso; la conexión se fija a esta IP.
            host, pinned_ip = _resolve_public_host(current_url)
            parsed = urlparse(current_url)
            host_header = f"{host}:{parsed.port}" if parsed.port else host

            with _build_pinned_session(host, pinned_ip) as session:
                response = session.get(
                    current_url,
                    headers={"User-Agent": _USER_AGENT, "Host": host_header},
                    timeout=10,
                    allow_redirects=False,
                )

            if 300 <= response.status_code < 400:
                location = response.headers.get("Location")
                if not location:
                    raise URLExtractionError(
                        "La URL devolvió una redirección inválida sin cabecera Location"
                    )
                current_url = urljoin(current_url, location)
                continue

            response.raise_for_status()
            break
        else:
            raise URLExtractionError(
                "Demasiadas redirecciones al intentar acceder a la URL"
            )
    except requests.exceptions.RequestException as e:
        raise URLExtractionError(f"Error al conectar con la URL: {e}") from e

    soup = BeautifulSoup(response.text, "html.parser")

    # Eliminar etiquetas que aportan ruido
    for tag in soup(
        ["script", "style", "noscript", "header", "footer", "nav", "aside", "iframe"]
    ):
        tag.extract()

    text = soup.get_text(separator="\n", strip=True)
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

    if not text:
        raise URLExtractionError(
            "No se pudo extraer texto relevante de la URL proporcionada."
        )

    return text
