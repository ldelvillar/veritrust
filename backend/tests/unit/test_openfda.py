"""Tests del cliente de openFDA (fichas de medicamentos) con la red mockeada."""

import pytest
import requests

from app.utils import openfda
from app.utils.evidence import EvidenceRetrievalError
from app.utils.openfda import search_evidence

_LABEL = {
    "openfda": {"brand_name": ["Advil"], "generic_name": ["IBUPROFEN"]},
    "purpose": ["Pain reliever/fever reducer"],
    "indications_and_usage": ["For the temporary relief of minor aches."],
    "warnings": ["Stomach bleeding warning."],
    "set_id": "abc-123",
    "effective_time": "20240115",
}


class _FakeResponse:
    def __init__(self, *, status_code=200, payload=None, raise_exc=None):
        self.status_code = status_code
        self._payload = payload
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        return self._payload


def _patch_get(monkeypatch, response=None, *, exc=None):
    def fake_get(url, **kwargs):
        if exc:
            raise exc
        return response

    monkeypatch.setattr(openfda.requests, "get", fake_get)


def test_search_evidence_maps_label_to_dailymed_source(monkeypatch):
    _patch_get(monkeypatch, _FakeResponse(payload={"results": [_LABEL]}))

    results = search_evidence("ibuprofen pain", max_results=3)

    assert results == [
        {
            "title": "Advil",
            "url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=abc-123",
            "source": "FDA",
            "year": "2024",
            "abstract": (
                "Pain reliever/fever reducer For the temporary relief of minor "
                "aches. Stomach bleeding warning."
            ),
        }
    ]


def test_search_evidence_falls_back_to_generic_name(monkeypatch):
    label = {**_LABEL, "openfda": {"generic_name": ["IBUPROFEN"]}}
    _patch_get(monkeypatch, _FakeResponse(payload={"results": [label]}))

    results = search_evidence("query", max_results=3)

    assert results[0]["title"] == "IBUPROFEN"


def test_search_evidence_treats_404_as_no_results(monkeypatch):
    # openFDA responde 404 cuando no hay coincidencias: no es un fallo.
    _patch_get(monkeypatch, _FakeResponse(status_code=404))

    assert search_evidence("nonexistent drug", max_results=3) == []


def test_search_evidence_drops_labels_without_title(monkeypatch):
    label = {"openfda": {}, "set_id": "x", "effective_time": "20200101"}
    _patch_get(monkeypatch, _FakeResponse(payload={"results": [label]}))

    assert search_evidence("query", max_results=3) == []


def test_search_evidence_returns_empty_for_blank_query(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("no debe llamarse a la red con query vacío")

    monkeypatch.setattr(openfda.requests, "get", _fail)

    assert search_evidence("   ", max_results=3) == []


def test_search_evidence_raises_on_request_error(monkeypatch):
    _patch_get(monkeypatch, exc=requests.exceptions.Timeout("timeout"))

    with pytest.raises(EvidenceRetrievalError):
        search_evidence("query", max_results=3)


def test_search_evidence_raises_on_http_error(monkeypatch):
    _patch_get(
        monkeypatch,
        _FakeResponse(status_code=500, raise_exc=requests.exceptions.HTTPError("boom")),
    )

    with pytest.raises(EvidenceRetrievalError):
        search_evidence("query", max_results=3)
