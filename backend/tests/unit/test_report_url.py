"""Tests of the report link, which the backend builds only in one place."""

from app.core.report_url import build_report_url


def test_report_url_drops_the_trailing_slash_of_the_base():
    assert (
        build_report_url("https://veritrust.es/", "abc")
        == "https://veritrust.es/app/analisis/abc"
    )
