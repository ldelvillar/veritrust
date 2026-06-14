"""Tests del cliente de PubMed (NCBI E-utilities) con la red mockeada."""

import pytest
import requests

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
    # Sin PMIDs no se llega a efetch; basta con la respuesta de esearch.
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


def test_search_evidence_raises_on_invalid_xml(monkeypatch):
    _patch_get(
        monkeypatch,
        esearch=_esearch(["123"]),
        efetch=_FakeResponse(content=b"<not-valid"),
    )

    with pytest.raises(EvidenceRetrievalError):
        search_evidence("query", max_results=3)
