import pytest
from unittest.mock import patch, MagicMock
from app.utils.extract_text_from_url import extract_text_from_url, URLExtractionError


# --- _validate_public_url edge cases ---
def test_invalid_scheme():
    with pytest.raises(URLExtractionError, match="comenzar con http:// o https://"):
        extract_text_from_url("ftp://example.com")


def test_no_hostname():
    with pytest.raises(URLExtractionError, match="no contiene un host válido"):
        extract_text_from_url("http://")


def test_localhost():
    with pytest.raises(URLExtractionError, match="URLs locales"):
        extract_text_from_url("http://localhost")


import socket


@patch("socket.getaddrinfo", side_effect=socket.gaierror)
def test_unresolvable_host(mock_getaddrinfo):
    with pytest.raises(URLExtractionError, match="No se pudo resolver el host"):
        extract_text_from_url("http://unresolvable.local")


@patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 80))])
def test_private_ip_rejected(mock_getaddrinfo):
    with pytest.raises(URLExtractionError, match="URLs locales"):
        extract_text_from_url("http://private.local")


# --- extract_text_from_url main logic ---
@patch("app.utils.extract_text_from_url._validate_public_url")
@patch("requests.get")
def test_too_many_redirects(mock_get, mock_validate):
    mock_get.return_value.status_code = 302
    mock_get.return_value.headers = {"Location": "/redir"}
    with pytest.raises(URLExtractionError, match="Demasiadas redirecciones"):
        extract_text_from_url("http://redirect.com")


import requests


@patch("app.utils.extract_text_from_url._validate_public_url")
@patch("requests.get")
def test_request_exception(mock_get, mock_validate):
    mock_get.side_effect = requests.exceptions.RequestException("fail")
    with pytest.raises(URLExtractionError, match="Error al conectar"):
        extract_text_from_url("http://fail.com")


@patch("app.utils.extract_text_from_url._validate_public_url")
@patch("requests.get")
def test_non_200_status_raises(mock_get, mock_validate):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    import requests

    mock_resp.raise_for_status.side_effect = requests.exceptions.RequestException("404")
    mock_get.return_value = mock_resp
    with pytest.raises(URLExtractionError):
        extract_text_from_url("http://notfound.com")


@patch("app.utils.extract_text_from_url._validate_public_url")
@patch("requests.get")
def test_no_text_extracted(mock_get, mock_validate):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><head></head><body></body></html>"
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp
    with pytest.raises(URLExtractionError, match="No se pudo extraer texto"):
        extract_text_from_url("http://empty.com")


@patch("app.utils.extract_text_from_url._validate_public_url")
@patch("requests.get")
def test_successful_extraction(mock_get, mock_validate):
    html = """
    <html><body><h1>Title</h1><script>var x=1;</script><p>Content</p></body></html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp
    text = extract_text_from_url("http://ok.com")
    assert "Title" in text and "Content" in text and "script" not in text
