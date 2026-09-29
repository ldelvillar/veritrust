"""Tests del registro de afirmación: alineación, traducción y consulta de búsqueda."""

import pytest

from app.core.claim import Claim, extract_claims, translate_claims


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
