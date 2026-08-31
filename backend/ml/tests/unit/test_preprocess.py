"""Tests unitarios para el módulo de preprocesamiento de datos."""

import pandas as pd

from ml.utils.preprocess import clean_text, preprocess_data


def test_clean_text_returns_empty_for_non_string_input() -> None:
    assert clean_text(None) == ""
    assert clean_text(123) == ""


def test_clean_text_normalizes_text_url_spaces_and_quotes() -> None:
    # La capitalización se conserva: el modelo base es cased.
    raw = '  ""Hello   https://example.com  WORLD""  '
    assert clean_text(raw) == "Hello WORLD"


def test_preprocess_data_drops_ids_cleans_claims_and_renames_columns() -> None:
    df = pd.DataFrame(
        {
            "claim_id": [1, 2, 3, 4],
            "claim": ["A valid claim", '  ""   ""  ', "Another claim", "Third claim"],
            "label": [0, 0, 1, 2],
        }
    )

    out = preprocess_data(df)

    assert "claim_id" not in out.columns
    assert "claim" not in out.columns
    assert "text" in out.columns

    # Las tres clases de HealthVer se conservan tal cual: 0, 1 y 2.
    assert set(out["label"].unique()) == {0, 1, 2}

    # La fila cuyo claim queda vacío tras la limpieza se descarta.
    assert len(out) == 3
    assert all(text != "" for text in out["text"])
