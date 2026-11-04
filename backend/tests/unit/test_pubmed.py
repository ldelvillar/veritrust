"""Tests of the PubMed (NCBI E-utilities) client with the network mocked."""

import pytest
import requests

from app.core.config import get_settings
from app.utils import pubmed
from app.utils.evidence import EvidenceRetrievalError
from app.utils.pubmed import search_evidence

_EFETCH_XML = b"""<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>123</PMID>
      <Article>
        <Journal>
          <Title>BMJ</Title>
          <JournalIssue><PubDate><Year>2021</Year></PubDate></JournalIssue>
        </Journal>
        <ArticleTitle>Vitamin C and the common cold</ArticleTitle>
        <Abstract>
          <AbstractText>Vitamin C does not prevent the common cold.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">123</ArticleId>
        <ArticleId IdType="doi">10.1000/abc</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""

_EFETCH_XML_NO_DOI = b"""<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>456</PMID>
      <Article>
        <Journal><Title>MED</Title></Journal>
        <ArticleTitle>A study</ArticleTitle>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""

_EFETCH_XML_NO_TITLE = b"""<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>789</PMID>
      <Article><Journal><Title>MED</Title></Journal></Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


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


def _patch_get(monkeypatch, *, esearch=None, efetch=None, exc=None):
    def fake_get(url, **kwargs):
        if exc:
            raise exc
        return esearch if "esearch" in url else efetch

    monkeypatch.setattr(pubmed.requests, "get", fake_get)


def _esearch(ids):
    return _FakeResponse(payload={"esearchresult": {"idlist": ids}})


class _Clock:
    """Clock for the request pacing, where sleeping only moves time forward."""

    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    """Pace the requests on a fake clock, so no test waits in real time."""
    fake = _Clock()
    monkeypatch.setattr(pubmed, "monotonic", fake.monotonic)
    monkeypatch.setattr(pubmed, "sleep", fake.sleep)
    monkeypatch.setattr(pubmed, "_next_slot", 0.0)
    return fake


def test_search_evidence_maps_article_with_doi_url(monkeypatch):
    _patch_get(
        monkeypatch,
        esearch=_esearch(["123"]),
        efetch=_FakeResponse(content=_EFETCH_XML),
    )

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


def test_search_evidence_builds_pubmed_url_without_doi(monkeypatch):
    _patch_get(
        monkeypatch,
        esearch=_esearch(["456"]),
        efetch=_FakeResponse(content=_EFETCH_XML_NO_DOI),
    )

    results = search_evidence("query", max_results=3)

    assert results[0]["url"] == "https://pubmed.ncbi.nlm.nih.gov/456/"
    assert results[0]["abstract"] is None


def test_search_evidence_drops_articles_without_title(monkeypatch):
    _patch_get(
        monkeypatch,
        esearch=_esearch(["789"]),
        efetch=_FakeResponse(content=_EFETCH_XML_NO_TITLE),
    )

    assert search_evidence("query", max_results=3) == []


def test_search_evidence_returns_empty_when_no_pmids(monkeypatch):
    # Without PMIDs efetch is never reached, so the esearch response is enough.
    _patch_get(monkeypatch, esearch=_esearch([]))

    assert search_evidence("query", max_results=3) == []


def test_search_evidence_returns_empty_for_blank_query(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("no debe llamarse a la red con query vacío")

    monkeypatch.setattr(pubmed.requests, "get", _fail)

    assert search_evidence("   ", max_results=3) == []


def test_search_evidence_raises_on_request_error(monkeypatch):
    _patch_get(monkeypatch, exc=requests.exceptions.Timeout("timeout"))

    with pytest.raises(EvidenceRetrievalError):
        search_evidence("query", max_results=3)


def test_search_evidence_error_gives_the_status_but_not_the_url(monkeypatch):
    # The URL carries the query and the api_key, and the investigator logs this message.
    response = requests.Response()
    response.status_code = 429
    leak = requests.exceptions.HTTPError(
        "429 Client Error: Too Many Requests for url: "
        "https://eutils.test/esearch.fcgi?term=query&api_key=dummy-key",
        response=response,
    )
    _patch_get(monkeypatch, esearch=_FakeResponse(raise_exc=leak))

    with pytest.raises(EvidenceRetrievalError) as raised:
        search_evidence("query", max_results=3)

    assert "HTTPError 429" in str(raised.value)
    assert "dummy-key" not in str(raised.value)


@pytest.mark.parametrize(
    ("api_key", "ncbi_limit"),
    [("", 3), ("dummy-key", 10)],
    ids=["without-key", "with-key"],
)
def test_requests_start_below_the_ncbi_limit(monkeypatch, clock, api_key, ncbi_limit):
    # NCBI allows 3 requests per second per IP without an api_key and 10 with one.
    monkeypatch.setattr(get_settings(), "pubmed_api_key", api_key)
    starts = []

    def fake_get(url, **kwargs):
        starts.append(clock.now)
        if "esearch" in url:
            return _esearch(["123"])
        return _FakeResponse(content=_EFETCH_XML)

    monkeypatch.setattr(pubmed.requests, "get", fake_get)

    for _ in range(3):
        search_evidence("query", max_results=3)

    assert len(starts) == 6
    assert min(b - a for a, b in zip(starts, starts[1:])) >= 1 / ncbi_limit


def test_search_evidence_raises_on_invalid_xml(monkeypatch):
    _patch_get(
        monkeypatch,
        esearch=_esearch(["123"]),
        efetch=_FakeResponse(content=b"<not-valid"),
    )

    with pytest.raises(EvidenceRetrievalError):
        search_evidence("query", max_results=3)
