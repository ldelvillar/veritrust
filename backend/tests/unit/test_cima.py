"""Tests del cliente de AEMPS CIMA (fichas técnicas) con la red mockeada."""

import pytest
import requests

from app.utils import cima
from app.utils.cima import search_evidence
from app.utils.evidence import EvidenceRetrievalError

# 1704067200000 ms = 2024-01-01 UTC.
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


def _patch_get(monkeypatch, *, search=None, ft=None, search_exc=None, ft_exc=None):
    def fake_get(url, **kwargs):
        if "/medicamentos" in url:
            if search_exc:
                raise search_exc
            return search
        if ft_exc:
            raise ft_exc
        return ft

    monkeypatch.setattr(cima.requests, "get", fake_get)


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
    # El script se elimina y el texto de la ficha se conserva para el juez.
    assert "Indicaciones: dolor leve." in source["abstract"]
    assert "tracker" not in source["abstract"]


def test_search_evidence_keeps_source_when_ficha_tecnica_fetch_fails(monkeypatch):
    _patch_get(
        monkeypatch,
        search=_FakeResponse(payload={"resultados": [_MED]}),
        ft_exc=requests.exceptions.Timeout("ft down"),
    )

    results = search_evidence("ibuprofeno", max_results=3)

    # Un fallo al descargar la ficha no descarta la fuente: se conserva sin abstract.
    assert len(results) == 1
    assert results[0]["abstract"] is None
    assert results[0]["url"] == "https://cima.aemps.es/ft/12345.html"


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
