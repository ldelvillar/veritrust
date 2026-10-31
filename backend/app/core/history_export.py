"""Serialisation of the analysis History to the CSV the user downloads."""

import csv
import io
from datetime import datetime

from app.core.config import get_settings
from app.schemas.history import HistoryExportItem

# BOM so Excel detects UTF-8 when opening the CSV.
_UTF8_BOM = "﻿"

# Leading characters Excel and Sheets read as a formula (CSV injection).
_CSV_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")

# Mirrors VERDICT_LABEL in analysis-result/format.ts, so the CSV uses the UI's words.
_EXPORT_VERDICT_LABELS = {
    "real": "Verdadero",
    "fake": "Falso",
    "mixed": "Parcialmente falso",
    "uncertain": "Dudoso",
}
_EXPORT_SOURCE_LABELS = {
    "text": "Texto pegado",
    "file": "Carga de archivo",
    "url": "Enlace",
}

_EXPORT_COLUMNS = [
    "Fecha",
    "Tipo",
    "Entrada",
    "Veredicto",
    "Credibilidad",
    "Cobertura de evidencia (%)",
    "Duración (s)",
    "Informe",
]


def _neutralize_csv_formula(value: str) -> str:
    """Prepend a single quote if the text could open as a formula in Excel."""
    if value.startswith(_CSV_FORMULA_TRIGGERS):
        return "'" + value
    return value


def _export_duration_seconds(created_at: str, completed_at: str | None) -> str:
    """Seconds the Analysis took, empty if a timestamp is missing or unreadable."""
    if not completed_at:
        return ""
    try:
        started = datetime.fromisoformat(created_at)
        finished = datetime.fromisoformat(completed_at)
    except ValueError:
        return ""
    return str(max(0, round((finished - started).total_seconds())))


def _export_entry(record: HistoryExportItem) -> str:
    """«Entrada» column, the same title the History shows on screen."""
    if record.source_type == "file" and record.file_filename:
        return record.file_filename
    return record.input_url or record.input_text or ""


def _build_report_url(base_url: str | None, analysis_id: str) -> str:
    """Link to the report in the frontend, empty if APP_BASE_URL is not configured."""
    if not base_url:
        return ""
    return f"{base_url.rstrip('/')}/app/analisis/{analysis_id}"


def build_history_csv(records: list[HistoryExportItem]) -> bytes:
    """Serialise the History to UTF-8 CSV with a BOM (Excel compatible)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    base_url = get_settings().app_base_url
    writer.writerow(_EXPORT_COLUMNS)
    for record in records:
        entrada = _neutralize_csv_formula(_export_entry(record))
        verdict = _EXPORT_VERDICT_LABELS.get(record.verdict, "")
        credibility = "" if record.credibility is None else str(record.credibility)
        coverage = (
            ""
            if record.evidence_coverage is None
            else str(round(record.evidence_coverage * 100))
        )
        writer.writerow(
            [
                record.created_at,
                _EXPORT_SOURCE_LABELS.get(record.source_type, record.source_type),
                entrada,
                verdict,
                credibility,
                coverage,
                _export_duration_seconds(record.created_at, record.completed_at),
                _build_report_url(base_url, record.analysis_id),
            ]
        )
    return (_UTF8_BOM + buffer.getvalue()).encode("utf-8")
