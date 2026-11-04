"""Tests of what every evidence client puts in a failure, which the investigator logs."""

import traceback

import pytest
import requests

from app.utils import cima, europepmc, openfda, pubmed
from app.utils.evidence import EvidenceRetrievalError


@pytest.mark.parametrize(
    "client",
    [europepmc, pubmed, openfda, cima],
    ids=["europepmc", "pubmed", "openfda", "cima"],
)
def test_failure_gives_the_status_but_never_the_url(monkeypatch, client):
    # The request URL carries the query and any api_key, so neither the message nor the traceback may show it.
    response = requests.Response()
    response.status_code = 429

    def fake_get(url, **kwargs):
        raise requests.exceptions.HTTPError(
            f"429 Client Error: Too Many Requests for url: {url}?api_key=dummy-key",
            response=response,
        )

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(pubmed, "sleep", lambda seconds: None)

    with pytest.raises(EvidenceRetrievalError) as raised:
        client.search_evidence("query", max_results=3)

    assert "HTTPError 429" in str(raised.value)
    assert "dummy-key" not in "".join(traceback.format_exception(raised.value))
