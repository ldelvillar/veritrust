"""Tests del registro de afirmación: construcción, búsqueda, juicio y lo que se guarda de ella."""

import pytest

from app.core.claim import (
    Claim,
    Evidence,
    EvidenceSearch,
    evidence_report,
    evidence_search,
    extract_claims,
    keep_shown_sources,
    source_records,
    translate_claims,
    with_hits,
    with_stances,
)


@pytest.mark.parametrize(
    ("queries", "drug_terms", "expected"),
    [
        # Listas completas: cada afirmación recibe lo suyo.
        (['"a"', '"b"'], ["ibuprofeno", ""], [('"a"', "ibuprofeno"), ('"b"', "")]),
        # Listas cortas: lo que falta queda vacío.
        (['"a"'], ["ibuprofeno"], [('"a"', "ibuprofeno"), ("", "")]),
        # Listas largas: lo que sobra se descarta.
        (['"a"', '"b"', '"c"'], ["x", "y", "z"], [('"a"', "x"), ('"b"', "y")]),
    ],
)
def test_extract_claims_aligns_queries_and_drug_terms_with_the_statements(
    queries, drug_terms, expected
):
    claims = extract_claims(["A", "B"], queries, drug_terms)

    assert [(c.index, c.text) for c in claims] == [(0, "A"), (1, "B")]
    assert [(c.query, c.drug_term) for c in claims] == expected


def test_extract_claims_trims_the_drug_term():
    (claim,) = extract_claims(["A"], ['"a"'], ["  ibuprofeno "])

    assert claim.drug_term == "ibuprofeno"


def test_extract_claims_without_statements_is_empty():
    assert extract_claims([], ['"a"'], ["x"]) == []


@pytest.mark.parametrize(
    ("translations", "expected"),
    [
        (["A-en", "B-en"], ["A-en", "B-en"]),
        (["A-en"], ["A-en", ""]),
        (["A-en", "B-en", "extra"], ["A-en", "B-en"]),
        ([], ["", ""]),
    ],
)
def test_translate_claims_aligns_translations_with_the_claims(translations, expected):
    claims = translate_claims(extract_claims(["A", "B"], [], []), translations)

    assert [c.text_en for c in claims] == expected
    # La traducción no altera el resto del registro.
    assert [(c.index, c.text) for c in claims] == [(0, "A"), (1, "B")]


@pytest.mark.parametrize(
    ("query", "text_en", "expected"),
    [
        # La consulta enfocada del extractor manda sobre la traducción.
        ('"vitamin C" AND "cold"', "Vitamin C cures colds", '"vitamin C" AND "cold"'),
        # Sin consulta, o con una sin letras ni cifras, se busca con la traducción.
        ("", "Vitamin C cures colds", "Vitamin C cures colds"),
        ('"" ()', "Vitamin C cures colds", "Vitamin C cures colds"),
        # Sin ninguna de las dos no hay nada que buscar.
        ("", "", ""),
        ("  ", "  ", ""),
    ],
)
def test_search_query_prefers_the_extractor_query_over_the_translation(
    query, text_en, expected
):
    claim = Claim(index=0, text="La vitamina C cura", text_en=text_en, query=query)

    assert claim.search_query == expected


def _hit(key: str, url: str | None = None) -> dict:
    return {
        "title": f"Estudio {key}",
        "url": f"https://e.org/{key}" if url is None else url,
        "source": "BMJ",
        "year": "2021",
        "abstract": f"Resumen {key}.",
    }


def _found(index: int, *keys: str, text: str | None = None) -> Claim:
    """Afirmación buscada cuyas fuentes devolvieron los resultados indicados, aún sin juzgar."""
    claim = Claim(index=index, text=text or f"Afirmación {index}", query=f'"q{index}"')
    return with_hits(claim, [_hit(key) for key in keys])


def _judged(index: int, *pairs: tuple[str, str], text: str | None = None) -> Claim:
    """Afirmación buscada y juzgada con una postura por fuente."""
    claim = _found(index, *(key for key, _ in pairs), text=text)
    return with_stances(claim, [stance for _, stance in pairs])


def test_a_claim_without_a_search_query_is_unsearchable_until_translated():
    claim = extract_claims(["A"], [""], [])[0]

    assert claim.outcome == "unsearchable"
    # La traducción le da consulta: pasa a estar pendiente de buscar.
    assert translate_claims([claim], ["A-en"])[0].outcome == "unsearched"


def test_with_hits_marks_a_claim_whose_sources_all_failed_as_unavailable():
    claim = with_hits(Claim(index=0, text="A", query='"a"'), None)

    assert (claim.outcome, claim.evidence) == ("unavailable", ())


def test_with_hits_keeps_the_first_result_of_each_url():
    claim = _found(0, "A", "B", "A")

    assert claim.outcome == "unjudged"
    assert [item.url for item in claim.evidence] == [
        "https://e.org/A",
        "https://e.org/B",
    ]
    assert claim.evidence[0] == Evidence(
        title="Estudio A",
        url="https://e.org/A",
        source="BMJ",
        year="2021",
        abstract="Resumen A.",
    )


def test_a_claim_with_no_results_has_nothing_left_to_judge():
    assert _found(0).outcome == "judged"


def test_with_stances_drops_unrelated_sources_and_records_the_stance():
    claim = _judged(0, ("A", "supports"), ("B", "unrelated"), ("C", "inconclusive"))

    assert claim.outcome == "judged"
    assert [(item.url, item.stance) for item in claim.evidence] == [
        ("https://e.org/A", "supports"),
        ("https://e.org/C", "inconclusive"),
    ]


def test_with_stances_without_an_answer_leaves_the_evidence_unjudged():
    claim = _found(0, "A")

    assert with_stances(claim, None) == claim


@pytest.mark.parametrize(
    ("claims", "expected"),
    [
        # Sin afirmaciones no hay nada que medir ni corte que declarar.
        ([], EvidenceSearch(total=0, searched=0, covered=0, outage=False)),
        # La que no tiene consulta no cuenta; la que la cota dejó fuera sí.
        (
            [
                Claim(index=0, text="A"),
                Claim(index=1, text="B", query='"b"'),
                _found(2, "X"),
            ],
            EvidenceSearch(total=2, searched=1, covered=1, outage=False),
        ),
        # Cubre quien tiene evidencia, juzgada o no; no quien no halló nada.
        (
            [_found(0, "X"), _judged(1, ("Y", "supports")), _found(2)],
            EvidenceSearch(total=3, searched=3, covered=2, outage=False),
        ),
        # El juez descartó todas sus fuentes: buscada pero sin cubrir.
        (
            [_judged(0, ("Y", "unrelated"))],
            EvidenceSearch(total=1, searched=1, covered=0, outage=False),
        ),
        # Corte solo si todas las buscadas toparon con fuentes caídas.
        (
            [
                with_hits(Claim(index=0, text="A", query='"a"'), None),
                Claim(index=1, text="B", query='"b"'),
            ],
            EvidenceSearch(total=2, searched=1, covered=0, outage=True),
        ),
        (
            [with_hits(Claim(index=0, text="A", query='"a"'), None), _found(1, "X")],
            EvidenceSearch(total=2, searched=2, covered=1, outage=False),
        ),
    ],
)
def test_evidence_search_counts_the_claims_by_outcome(claims, expected):
    assert evidence_search(claims) == expected


def test_keep_shown_sources_keeps_the_first_distinct_sources_in_claim_order():
    claims = [
        _judged(0, ("A", "supports"), ("S", "supports")),
        _judged(1, ("S", "contradicts"), ("B", "supports"), ("C", "supports")),
        _judged(2, ("D", "supports")),
    ]

    shown = keep_shown_sources(claims, 3)

    # A, S y B llenan el cupo; S cuenta una vez aunque la citen dos afirmaciones.
    assert [[item.url[-1] for item in claim.evidence] for claim in shown] == [
        ["A", "S"],
        ["S", "B"],
        [],
    ]
    # Recortar la evidencia no cambia hasta dónde llegó la búsqueda.
    assert [claim.outcome for claim in shown] == ["judged"] * 3


def test_keep_shown_sources_changes_nothing_under_the_limit():
    claims = [_judged(0, ("A", "supports")), _found(1, "B")]

    assert keep_shown_sources(claims, 12) == claims


def test_source_records_merge_a_shared_url_and_link_each_claim_by_index():
    claims = [
        _judged(0, ("A", "supports"), ("S", "supports"), text="Misma frase"),
        _judged(1, ("S", "contradicts"), text="Misma frase"),
        _found(2, "U"),
    ]

    # Casar por texto fundiría las dos primeras; por índice quedan ambas, cada una con su postura.
    assert source_records(claims) == [
        {
            "title": "Estudio A",
            "url": "https://e.org/A",
            "source": "BMJ",
            "year": "2021",
            "statements": [
                {"claim_index": 0, "text": "Misma frase", "stance": "supports"}
            ],
        },
        {
            "title": "Estudio S",
            "url": "https://e.org/S",
            "source": "BMJ",
            "year": "2021",
            "statements": [
                {"claim_index": 0, "text": "Misma frase", "stance": "supports"},
                {"claim_index": 1, "text": "Misma frase", "stance": "contradicts"},
            ],
        },
        {
            "title": "Estudio U",
            "url": "https://e.org/U",
            "source": "BMJ",
            "year": "2021",
            "statements": [{"claim_index": 2, "text": "Afirmación 2", "stance": None}],
        },
    ]


def test_evidence_report_lists_each_searched_claim_with_its_sources():
    claims = [
        Claim(index=0, text="A"),
        _judged(1, ("J", "supports")),
        _found(2, "U"),
        with_hits(Claim(index=3, text="Afirmación 3", query='"q3"'), None),
        Claim(index=4, text="E", query='"q4"'),
    ]

    # La fuente sin juzgar no lleva postura; la afirmación sin fuentes alcanzables no lleva lista.
    assert evidence_report(claims) == {
        "claims": [
            {
                "claim_index": 1,
                "query": '"q1"',
                "claim": "",
                "original": "Afirmación 1",
                "hits": [{**_hit("J"), "stance": "supports"}],
                "judged": True,
            },
            {
                "claim_index": 2,
                "query": '"q2"',
                "claim": "",
                "original": "Afirmación 2",
                "hits": [_hit("U")],
                "judged": False,
            },
            {
                "claim_index": 3,
                "query": '"q3"',
                "claim": "",
                "original": "Afirmación 3",
                "hits": None,
                "judged": False,
            },
        ],
        "unsearched_claims": 1,
    }
