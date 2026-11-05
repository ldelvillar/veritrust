"""Tests of the report link, which the backend builds only in one place."""

import types

from app.core import report_url
from app.core.report_url import build_report_url


def test_report_url_joins_the_configured_base_and_the_analysis_id(monkeypatch):
    monkeypatch.setattr(
        report_url,
        "get_settings",
        lambda: types.SimpleNamespace(app_base_url="https://veritrust.es"),
    )

    assert build_report_url("abc") == "https://veritrust.es/app/analisis/abc"
