"""Tests of the AEMPS CIMA client (summaries of product characteristics) with the network mocked."""

import pytest
import requests

from app.utils import cima
from app.utils.cima import search_evidence
from app.utils.evidence import EvidenceRetrievalError
from app.utils.ssrf import SSRFValidationError

# 1704067200000 ms is 2024-01-01 UTC.
_MED = {
    "nombre": "IBUPROFENO CINFA 600 mg",
    "nregistro": "12345",
    "estado": {"aut": 1704067200000},
    "docs": [{"tipo": 1, "urlHtml": "https://cima.aemps.es/ft/12345.html"}],
}

_FT_HTML = (
    b"<html><body><script>tracker()</script>"
    b"<h1>Ficha</h1><p>Indicaciones: dolor leve.</p></body></html>"
)


class _FakeResponse:
    def __init__(self, *, payload=None, content=b"", raise_exc=None):
        self._payload = payload
        self.content = content
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        return self._payload


def _patch_get(
    monkeypatch, *, search=None, ft=None, search_exc=None, ft_exc=None, resolve_exc=None
):
    def fake_get(url, **kwargs):
        if "/medicamentos" in url:
            if search_exc:
                raise search_exc
            return search
        if ft_exc:
            raise ft_exc
        return ft

    monkeypatch.setattr(cima.requests, "get", fake_get)

    # Avoid real DNS in the summary's SSRF validation, resolving public by default.
    def fake_resolve(url):
        if resolve_exc:
            raise resolve_exc
        return ("cima.aemps.es", "93.184.216.34")

    monkeypatch.setattr(cima, "resolve_public_host", fake_resolve)


def test_search_evidence_maps_med_and_fetches_ficha_tecnica(monkeypatch):
    _patch_get(
        monkeypatch,
        search=_FakeResponse(payload={"resultados": [_MED]}),
        ft=_FakeResponse(content=_FT_HTML),
    )

    results = search_evidence("ibuprofeno", max_results=3)

    assert len(results) == 1
    source = results[0]
    assert source["title"] == "IBUPROFENO CINFA 600 mg"
    assert source["url"] == "https://cima.aemps.es/ft/12345.html"
    assert source["source"] == "AEMPS"
    assert source["year"] == "2024"
    # The script is removed and the summary text is kept for the judge.
    assert "Indicaciones: dolor leve." in source["abstract"]
    assert "tracker" not in source["abstract"]


def test_search_evidence_sends_each_key_section_of_a_numbered_ficha(monkeypatch):
    advertencias = "Riesgo de hemorragia digestiva. " * 40
    html = (
        '<html><body><h1 id="1">1. NOMBRE DEL MEDICAMENTO</h1><p>Ibuprofeno.</p>'
        '<h2 id="4.1">4.1. Indicaciones terapéuticas</h2><p>Dolor leve.</p>'
        '<h2 id="4.2">4.2. Posología</h2><p>Un comprimido cada 8 horas.</p>'
        f'<h2 id="4.4">4.4. Advertencias</h2><p>{advertencias}</p>'
        '<h2 id="4.9">4.9. Sobredosis</h2><p>Puede causar daño renal.</p>'
        "</body></html>"
    ).encode()
    _patch_get(
        monkeypatch,
        search=_FakeResponse(payload={"resultados": [_MED]}),
        ft=_FakeResponse(content=html),
    )

    (source,) = search_evidence("ibuprofeno", max_results=3)

    assert source["abstract"].startswith("4.1. Indicaciones terapéuticas: Dolor leve.")
    # A long section is trimmed and does not push out the overdose one at the end.
    assert source["abstract"].endswith("4.9. Sobredosis: Puede causar daño renal.")
    assert len(source["abstract"]) < len(advertencias)
    assert "Posología" not in source["abstract"]
    assert "NOMBRE" not in source["abstract"]


def test_search_evidence_keeps_source_when_ficha_tecnica_fetch_fails(monkeypatch):
    _patch_get(
        monkeypatch,
        search=_FakeResponse(payload={"resultados": [_MED]}),
        ft_exc=requests.exceptions.Timeout("ft down"),
    )

    results = search_evidence("ibuprofeno", max_results=3)

    # A failure downloading the summary does not drop the Source, which is kept without abstract.
    assert len(results) == 1
    assert results[0]["abstract"] is None
    assert results[0]["url"] == "https://cima.aemps.es/ft/12345.html"


def test_search_evidence_skips_ficha_from_untrusted_host(monkeypatch):
    # urlHtml tampered towards an internal address must not be downloaded.
    med = {
        "nombre": "IBUPROFENO CINFA 600 mg",
        "nregistro": "12345",
        "estado": {"aut": 1704067200000},
        "docs": [{"tipo": 1, "urlHtml": "http://169.254.169.254/latest/meta-data"}],
    }

    def fake_get(url, **kwargs):
        if "/medicamentos" in url:
            return _FakeResponse(payload={"resultados": [med]})
        raise AssertionError("no debe descargarse un urlHtml fuera del host de CIMA")

    monkeypatch.setattr(cima.requests, "get", fake_get)

    results = search_evidence("ibuprofeno", max_results=3)

    # The Source is kept (the off-host URL is still shown) but without abstract.
    assert len(results) == 1
    assert results[0]["abstract"] is None
    assert results[0]["url"] == "http://169.254.169.254/latest/meta-data"


def test_search_evidence_skips_ficha_when_host_resolves_internal(monkeypatch):
    # An allowed host that resolves to an internal IP (rebinding or a backslash parser differential) must be blocked by SSRF validation.
    _patch_get(
        monkeypatch,
        search=_FakeResponse(payload={"resultados": [_MED]}),
        ft=_FakeResponse(content=_FT_HTML),
        resolve_exc=SSRFValidationError("IP no pública"),
    )

    results = search_evidence("ibuprofeno", max_results=3)

    # The summary would be available, but SSRF validation stops the download.
    assert len(results) == 1
    assert results[0]["abstract"] is None
    assert results[0]["url"] == "https://cima.aemps.es/ft/12345.html"


def test_is_trusted_cima_url_rejects_nfkc_invalid_url():
    # urlparse raises ValueError on a fullwidth solidus, which must degrade to False instead of crashing.
    assert cima._is_trusted_cima_url("http://cima.aemps.es／169.254.169.254/") is False


def test_search_evidence_falls_back_to_detalle_url_without_ficha(monkeypatch):
    med = {"nombre": "SIN FICHA", "nregistro": "999", "docs": []}
    _patch_get(monkeypatch, search=_FakeResponse(payload={"resultados": [med]}))

    results = search_evidence("algo", max_results=3)

    assert results[0]["url"] == (
        "https://cima.aemps.es/cima/publico/detalle.html?nregistro=999"
    )
    assert results[0]["abstract"] is None
    assert results[0]["year"] is None


def test_search_evidence_returns_empty_when_no_results(monkeypatch):
    _patch_get(monkeypatch, search=_FakeResponse(payload={"resultados": []}))

    assert search_evidence("desconocido", max_results=3) == []


def test_search_evidence_drops_meds_without_name(monkeypatch):
    _patch_get(
        monkeypatch,
        search=_FakeResponse(payload={"resultados": [{"nregistro": "1"}]}),
    )

    assert search_evidence("algo", max_results=3) == []


def test_search_evidence_returns_empty_for_blank_query(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("no debe llamarse a la red con término vacío")

    monkeypatch.setattr(cima.requests, "get", _fail)

    assert search_evidence("   ", max_results=3) == []


def test_search_evidence_raises_on_search_error(monkeypatch):
    _patch_get(monkeypatch, search_exc=requests.exceptions.Timeout("timeout"))

    with pytest.raises(EvidenceRetrievalError):
        search_evidence("ibuprofeno", max_results=3)
