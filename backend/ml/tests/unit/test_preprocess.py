"""Tests unitarios para el módulo de preprocesamiento de datos."""

import pandas as pd

from ml.utils.preprocess import clean_list_string, clean_text, preprocess_data


def test_clean_text_returns_empty_for_non_string_input() -> None:
    assert clean_text(None) == ""
    assert clean_text(123) == ""


def test_clean_text_normalizes_text_url_spaces_and_quotes() -> None:
    raw = '  ""HELLO   https://example.com  WORLD""  '
    assert clean_text(raw) == "hello world"


def test_clean_list_string_normalizes_separators() -> None:
    raw = "David Biller And Mauricio Savarese & Ana, Bob"
    assert clean_list_string(raw) == "David Biller, Mauricio Savarese, Ana, Bob"


def test_clean_list_string_returns_empty_for_non_string_input() -> None:
    assert clean_list_string(None) == ""
    assert clean_list_string(42) == ""


def test_preprocess_data_filters_maps_and_renames_columns() -> None:
    df = pd.DataFrame(
        {
            "claim_id": [1, 2, 3, 4],
            "subjects": ["a", "b", "c", "d"],
            "label": [0, 3, 2, 1],
            "explanation": ["EXPLANATION", None, "x", "ok"],
            "main_text": ["MAIN", "text", "y", "z"],
            "claim": ["A valid claim", '  ""   ""  ', "drop me", "Another claim"],
            "date_published": [
                "January 01, 2020",
                "February 10, 2021",
                "March 20, 2022",
                "April 05, 2023",
            ],
            "fact_checkers": ["Alice and Bob", "Carol & Dan", "Eve", "Frank"],
            "sources": ["Src1 and Src2", "Src3 & Src4", "Src5", "Src6"],
        }
    )

    out = preprocess_data(df)

    assert "claim_id" not in out.columns
    assert "subjects" not in out.columns
    assert "claim" not in out.columns
    assert "text" in out.columns

    assert set(out["label"].unique()).issubset({0, 1})
    assert (out["label"] == 3).sum() == 0

    assert all(text != "" for text in out["text"])
    assert pd.api.types.is_datetime64_any_dtype(out["date_published"])

    assert "Alice, Bob" in out["fact_checkers"].values
    assert "Src1, Src2" in out["sources"].values
