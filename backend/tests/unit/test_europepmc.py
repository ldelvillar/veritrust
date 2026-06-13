"""Tests del cliente de Europe PMC con la red mockeada."""

import pytest
import requests

from app.utils import europepmc
from app.utils.europepmc import EvidenceRetrievalError, search_evidence


class _FakeResponse:
    def __init__(self, payload, *, raise_exc=None, json_exc=None):
        self._payload = payload
        self._raise_exc = raise_exc
        self._json_exc = json_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        if self._json_exc:
            raise self._json_exc
        return self._payload


def _patch_get(monkeypatch, response=None, *, exc=None):
    def fake_get(url, **kwargs):
        if exc:
            raise exc
        return response

    monkeypatch.setattr(europepmc.requests, "get", fake_get)


def test_search_evidence_maps_results_with_doi_url(monkeypatch):
    payload = {
        "resultList": {
            "result": [
                {
                    "title": "Vitamin C and the common cold",
                    "doi": "10.1000/abc",
                    "journalTitle": "BMJ",
                    "pubYear": "2021",
                    "abstractText": "Vitamin C does not prevent the common cold.",
                }
            ]
        }
    }
    _patch_get(monkeypatch, _FakeResponse(payload))

    results = search_evidence("vitamin c cold", max_results=3)

    assert results == [
        {
            "title": "Vitamin C and the common cold",
            "url": "https://doi.org/10.1000/abc",
            "source": "BMJ",
            "year": "2021",
            "abstract": "Vitamin C does not prevent the common cold.",
        }
    ]


def test_search_evidence_builds_europepmc_url_without_doi(monkeypatch):
    payload = {
        "resultList": {
            "result": [
                {"title": "A study", "source": "MED", "id": "123", "pubYear": "2020"}
            ]
        }
    }
    _patch_get(monkeypatch, _FakeResponse(payload))

    results = search_evidence("query", max_results=3)

    assert results[0]["url"] == "https://europepmc.org/article/MED/123"


def test_search_evidence_drops_results_without_title(monkeypatch):
    payload = {"resultList": {"result": [{"doi": "10.1/x"}, {"title": "  "}]}}
    _patch_get(monkeypatch, _FakeResponse(payload))

    assert search_evidence("query", max_results=3) == []


def test_search_evidence_returns_empty_for_blank_query(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("no debe llamarse a la red con query vacío")

    monkeypatch.setattr(europepmc.requests, "get", _fail)

    assert search_evidence("   ", max_results=3) == []


def test_search_evidence_raises_on_request_error(monkeypatch):
    _patch_get(monkeypatch, exc=requests.exceptions.Timeout("timeout"))

    with pytest.raises(EvidenceRetrievalError):
        search_evidence("query", max_results=3)


def test_search_evidence_raises_on_invalid_json(monkeypatch):
    response = _FakeResponse(None, json_exc=ValueError("no json"))
    _patch_get(monkeypatch, response)

    with pytest.raises(EvidenceRetrievalError):
        search_evidence("query", max_results=3)
