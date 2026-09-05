"""Serialización del historial de análisis al CSV que descarga el usuario."""

import csv
import io
from datetime import datetime

from app.core.config import get_settings
from app.core.credibility import classify_verdict
from app.schemas.history import HistoryExportItem

# BOM para que Excel detecte UTF-8 al abrir el CSV.
_UTF8_BOM = "﻿"

# Caracteres iniciales que Excel/Sheets interpretan como fórmula (inyección CSV).
_CSV_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")

# Vocabulario único del producto: VERDICT_LABEL en analysis-result/format.ts.
_EXPORT_VERDICT_LABELS = {"real": "Verdadero", "fake": "Falso", "uncertain": "Dudoso"}
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
    """Antepone una comilla simple si el texto podría abrirse como fórmula en Excel."""
    if value.startswith(_CSV_FORMULA_TRIGGERS):
        return "'" + value
    return value


def _export_duration_seconds(created_at: str, completed_at: str | None) -> str:
    """Segundos que tardó el análisis; vacío si falta o no se puede leer una marca."""
    if not completed_at:
        return ""
    try:
        started = datetime.fromisoformat(created_at)
        finished = datetime.fromisoformat(completed_at)
    except ValueError:
        return ""
    return str(max(0, round((finished - started).total_seconds())))


def _export_entry(record: HistoryExportItem) -> str:
    """Columna «Entrada»: el mismo título que el historial muestra en pantalla."""
    if record.source_type == "file" and record.file_filename:
        return record.file_filename
    return record.input_url or record.input_text or ""


def _build_report_url(base_url: str | None, analysis_id: str) -> str:
    """Enlace al informe en el frontend; vacío si APP_BASE_URL no está configurado."""
    if not base_url:
        return ""
    return f"{base_url.rstrip('/')}/app/analisis/{analysis_id}"


def build_history_csv(records: list[HistoryExportItem]) -> bytes:
    """Serializa el historial a CSV UTF-8 con BOM (compatible con Excel)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    base_url = get_settings().app_base_url
    writer.writerow(_EXPORT_COLUMNS)
    for record in records:
        entrada = _neutralize_csv_formula(_export_entry(record))
        verdict = _EXPORT_VERDICT_LABELS.get(classify_verdict(record.label), "")
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
