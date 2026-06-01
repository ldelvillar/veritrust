import http.server
import socket
import threading
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.schemas.analysis import MAX_INPUT_TEXT_LENGTH
from app.utils.extract_text_from_url import (
    MAX_DOWNLOAD_BYTES,
    URLExtractionError,
    _read_capped_body,
    extract_text_from_url,
)


# --- _resolve_public_host edge cases ---
def test_invalid_scheme():
    with pytest.raises(URLExtractionError, match="comenzar con http:// o https://"):
        extract_text_from_url("ftp://example.com")


def test_no_hostname():
    with pytest.raises(URLExtractionError, match="no contiene un host válido"):
        extract_text_from_url("http://")


def test_localhost():
    with pytest.raises(URLExtractionError, match="URLs locales"):
        extract_text_from_url("http://localhost")


@patch("socket.getaddrinfo", side_effect=socket.gaierror)
def test_unresolvable_host(mock_getaddrinfo):
    with pytest.raises(URLExtractionError, match="No se pudo resolver el host"):
        extract_text_from_url("http://unresolvable.local")


@patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 80))])
def test_private_ip_rejected(mock_getaddrinfo):
    with pytest.raises(URLExtractionError, match="URLs locales"):
        extract_text_from_url("http://private.local")


@patch(
    "socket.getaddrinfo",
    return_value=[(2, 1, 6, "", ("93.184.216.34", 80))],
)
def test_mixed_public_private_rejected(mock_getaddrinfo):
    # Si cualquiera de las IPs resueltas no es pública, se rechaza el conjunto.
    mock_getaddrinfo.return_value = [
        (2, 1, 6, "", ("93.184.216.34", 80)),
        (2, 1, 6, "", ("10.0.0.5", 80)),
    ]
    with pytest.raises(URLExtractionError, match="URLs locales"):
        extract_text_from_url("http://mixed.example.com")


# --- extract_text_from_url main logic ---
@patch(
    "app.utils.extract_text_from_url._resolve_public_host",
    return_value=("redirect.com", "1.2.3.4"),
)
@patch("requests.Session.get")
def test_too_many_redirects(mock_get, mock_resolve):
    mock_get.return_value.status_code = 302
    mock_get.return_value.headers = {"Location": "/redir"}
    with pytest.raises(URLExtractionError, match="Demasiadas redirecciones"):
        extract_text_from_url("http://redirect.com")


@patch(
    "app.utils.extract_text_from_url._resolve_public_host",
    return_value=("fail.com", "1.2.3.4"),
)
@patch("requests.Session.get")
def test_request_exception(mock_get, mock_resolve):
    mock_get.side_effect = requests.exceptions.RequestException("fail")
    with pytest.raises(URLExtractionError, match="Error al conectar"):
        extract_text_from_url("http://fail.com")


@patch(
    "app.utils.extract_text_from_url._resolve_public_host",
    return_value=("redirect.com", "1.2.3.4"),
)
@patch("requests.Session.get")
def test_redirect_without_location_raises(mock_get, mock_resolve):
    mock_get.return_value.status_code = 301
    mock_get.return_value.headers = {}
    with pytest.raises(URLExtractionError, match="redirección inválida"):
        extract_text_from_url("http://redirect.com")


@patch(
    "app.utils.extract_text_from_url._resolve_public_host",
    return_value=("notfound.com", "1.2.3.4"),
)
@patch("requests.Session.get")
def test_non_200_status_raises(mock_get, mock_resolve):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.raise_for_status.side_effect = requests.exceptions.RequestException("404")
    mock_get.return_value = mock_resp
    with pytest.raises(URLExtractionError):
        extract_text_from_url("http://notfound.com")


@patch(
    "app.utils.extract_text_from_url._resolve_public_host",
    return_value=("empty.com", "1.2.3.4"),
)
@patch("requests.Session.get")
def test_no_text_extracted(mock_get, mock_resolve):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_content.return_value = [b"<html><head></head><body></body></html>"]
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp
    with pytest.raises(URLExtractionError, match="No se pudo extraer texto"):
        extract_text_from_url("http://empty.com")


@patch(
    "app.utils.extract_text_from_url._resolve_public_host",
    return_value=("ok.com", "1.2.3.4"),
)
@patch("requests.Session.get")
def test_successful_extraction(mock_get, mock_resolve):
    html = (
        b"<html><body><h1>Title</h1><script>var x=1;</script>"
        b"<p>Content</p></body></html>"
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_content.return_value = [html]
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp
    text = extract_text_from_url("http://ok.com")
    assert "Title" in text and "Content" in text and "script" not in text


@patch(
    "app.utils.extract_text_from_url._resolve_public_host",
    return_value=("big.com", "1.2.3.4"),
)
@patch("requests.Session.get")
def test_extracted_text_is_truncated(mock_get, mock_resolve):
    # Una página enorme no puede convertirse en un prompt sin límite.
    body = "a" * (MAX_INPUT_TEXT_LENGTH * 3)
    html = f"<html><body><p>{body}</p></body></html>".encode()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_content.return_value = [html]
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    text = extract_text_from_url("http://big.com")

    assert len(text) == MAX_INPUT_TEXT_LENGTH


def test_read_capped_body_stops_at_limit():
    """Un cuerpo gigante (o infinito) se corta en MAX_DOWNLOAD_BYTES."""
    produced = {"n": 0}

    def _endless(chunk_size=8192):
        chunk = b"x" * 8192
        while True:
            produced["n"] += len(chunk)
            yield chunk

    mock_resp = MagicMock()
    mock_resp.iter_content.side_effect = _endless

    body = _read_capped_body(mock_resp)

    assert len(body) == MAX_DOWNLOAD_BYTES
    # Deja de leer en cuanto alcanza el tope (a lo sumo un chunk de margen).
    assert produced["n"] <= MAX_DOWNLOAD_BYTES + 8192


# --- DNS-rebinding / IP-pinning regression ---
def test_connection_pinned_to_validated_ip():
    """La conexión usa la IP validada y conserva el Host real (anti DNS rebinding)."""
    seen: dict[str, str | None] = {}

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            seen["host"] = self.headers.get("Host")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<html><body><p>Contenido fijado</p></body></html>")

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    threading.Thread(target=server.handle_request, daemon=True).start()

    # El host nunca se resuelve por DNS: forzamos la IP validada a loopback, que
    # es justo a donde debe conectar pese a que el host de la URL sea otro.
    with patch(
        "app.utils.extract_text_from_url._resolve_public_host",
        return_value=("example.test", "127.0.0.1"),
    ):
        text = extract_text_from_url(f"http://example.test:{port}/articulo")

    server.server_close()
    assert "Contenido fijado" in text
    assert seen["host"] == f"example.test:{port}"
