"""Escrituras de estado y etapa de un análisis; solo las usa ``app.core.analysis_lifecycle``."""

from __future__ import annotations

from typing import Any, Literal, Sequence

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.verdict import Verdict
from app.db.pool import DatabaseError, _build_database_error, get_pool


def _normalize_confidence(confidence: Any) -> float:
    """Convierte confidence a float y valida el rango [0, 1]."""
    try:
        value = float(confidence)
    except (TypeError, ValueError) as exc:
        raise DatabaseError(f"Confidence no es numerico: {confidence!r}.") from exc

    if not 0.0 <= value <= 1.0:
        raise DatabaseError(f"Confidence fuera de rango [0, 1]: {value}.")

    return value


def _coerce_optional_fraction(value: Any) -> float | None:
    """Convierte una fracción opcional a float validando [0, 1]; ``None`` pasa tal cual."""
    if value is None:
        return None
    try:
        fraction = float(value)
    except (TypeError, ValueError) as exc:
        raise DatabaseError(f"Fraccion no es numerica: {value!r}.") from exc

    if not 0.0 <= fraction <= 1.0:
        raise DatabaseError(f"Fraccion fuera de rango [0, 1]: {fraction}.")

    return fraction


async def insert_pending(
    *,
    user_id: str,
    origin: str,
    source_type: str,
    input_text: str | None,
    input_url: str | None,
) -> str:
    """Inserta un análisis de texto o URL en estado ``pending`` y devuelve su id."""
    query = """
        INSERT INTO public.analysis_history
        (user_id, source_type, origin, input_text, input_url, status)
        VALUES (%s, %s, %s, %s, %s, 'pending')
        RETURNING id
    """
    return await _insert(
        query,
        (user_id, source_type, origin, input_text, input_url),
        "No se pudo guardar el analisis en la base de datos.",
    )


async def insert_pending_file(
    *, user_id: str, origin: str, filename: str, data: bytes
) -> str:
    """Inserta un análisis de archivo en estado ``pending`` con su binario y devuelve su id."""
    query = """
        INSERT INTO public.analysis_history
        (user_id, source_type, origin, file_data, file_filename, status)
        VALUES (%s, 'file', %s, %s, %s, 'pending')
        RETURNING id
    """
    return await _insert(
        query,
        (user_id, origin, data, filename),
        "No se pudo guardar el archivo en la base de datos.",
    )


async def _insert(query: str, params: tuple[Any, ...], context: str) -> str:
    """Ejecuta un INSERT … RETURNING id y devuelve el id creado."""
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                inserted_row = await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(_build_database_error(context)) from exc

    if not inserted_row:
        raise DatabaseError("No se pudo obtener el id del análisis guardado.")

    return str(inserted_row[0])


async def reopen(
    *, user_id: str, analysis_id: str, from_status: Literal["failed", "done"]
) -> bool:
    """Devuelve a ``pending`` un análisis propio que sigue en ``from_status``; True si cambió."""
    # created_at se reinicia para el reaper; el resultado anterior se borra para no seguir sumando en agregados.
    query = """
        UPDATE public.analysis_history
        SET status = 'pending',
            label = NULL,
            verdict = NULL,
            confidence = NULL,
            evidence_coverage = NULL,
            explanation = NULL,
            claims = NULL,
            sources = NULL,
            pipeline = NULL,
            error_code = NULL,
            stage = NULL,
            created_at = NOW(),
            completed_at = NULL
        WHERE user_id = %s AND id = %s AND status = %s
    """
    return await _update(
        query,
        (user_id, analysis_id, from_status),
        "No se pudo reabrir el análisis en la base de datos.",
    )


async def load_pending_content(analysis_id: str) -> dict[str, Any] | None:
    """Devuelve la entrada de un análisis ``pending`` (tipo, texto, URL y archivo), o None."""
    query = """
        SELECT source_type, input_text, input_url, file_data, file_filename
        FROM public.analysis_history
        WHERE id = %s AND status = 'pending'
    """
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (analysis_id,))
                return await cur.fetchone()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo cargar la entrada del análisis en la base de datos."
            )
        ) from exc


async def fail(*, analysis_id: str, error_code: str) -> bool:
    """Pasa a ``failed`` un análisis que sigue ``pending``; True si cambió."""
    query = """
        UPDATE public.analysis_history
        SET status = 'failed', error_code = %s, completed_at = NOW()
        WHERE id = %s AND status = 'pending'
    """
    return await _update(
        query,
        (error_code, analysis_id),
        "No se pudo actualizar el analisis en la base de datos.",
    )


async def set_stage(*, analysis_id: str, stage: str) -> None:
    """Registra la etapa activa de un análisis mientras sigue ``pending``."""
    query = (
        "UPDATE public.analysis_history SET stage = %s "
        "WHERE id = %s AND status = 'pending'"
    )
    await _update(
        query,
        (stage, analysis_id),
        "No se pudo actualizar la etapa del análisis en la base de datos.",
    )


async def set_input_text(*, analysis_id: str, input_text: str) -> None:
    """Guarda el texto extraído de un archivo mientras el análisis sigue ``pending``."""
    query = (
        "UPDATE public.analysis_history SET input_text = %s "
        "WHERE id = %s AND status = 'pending'"
    )
    await _update(
        query,
        (input_text, analysis_id),
        "No se pudo actualizar el texto del análisis en la base de datos.",
    )


async def complete(
    *,
    analysis_id: str,
    verdict: Verdict,
    explanation: str | None,
    sources: list[dict],
    pipeline: dict,
) -> bool:
    """Pasa a ``done`` con su veredicto un análisis que sigue ``pending``; True si cambió."""
    confidence_value = _normalize_confidence(verdict.confidence)
    coverage_value = _coerce_optional_fraction(verdict.evidence_coverage)
    claims = [
        {"text": claim.text, "label": claim.label, "confidence": claim.confidence}
        for claim in verdict.claims
    ]
    query = """
        UPDATE public.analysis_history
        SET label = %s,
            verdict = %s,
            confidence = %s,
            evidence_coverage = %s,
            explanation = %s,
            claims = %s,
            sources = %s,
            pipeline = %s,
            status = 'done',
            error_code = NULL,
            completed_at = NOW()
        WHERE id = %s AND status = 'pending'
    """
    return await _update(
        query,
        (
            verdict.label,
            verdict.kind,
            confidence_value,
            coverage_value,
            explanation,
            Jsonb(claims) if claims else None,
            Jsonb(sources) if sources else None,
            Jsonb(pipeline) if pipeline else None,
            analysis_id,
        ),
        "No se pudo guardar el analisis en la base de datos.",
    )


async def list_stale_pending_ids(*, older_than_seconds: int) -> list[str]:
    """Lista los ids ``pending`` más antiguos que el umbral, candidatos a huérfanos."""
    query = """
        SELECT id::text
        FROM public.analysis_history
        WHERE status = 'pending'
          AND created_at < NOW() - make_interval(secs => %s)
    """
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (older_than_seconds,))
                rows = await cur.fetchall()
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo consultar análisis atascados en la base de datos."
            )
        ) from exc

    return [str(row[0]) for row in rows]


async def fail_stale(
    *, analysis_ids: Sequence[str], older_than_seconds: int, error_code: str
) -> int:
    """Pasa a ``failed`` los ids indicados si siguen ``pending`` y estancados; devuelve cuántos."""
    # Re-verifica estado y antigüedad: un Retry entre la lectura y esta escritura reinicia created_at.
    query = """
        UPDATE public.analysis_history
        SET status = 'failed', error_code = %s, completed_at = NOW()
        WHERE id::text = ANY(%s)
          AND status = 'pending'
          AND created_at < NOW() - make_interval(secs => %s)
    """
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    query, (error_code, list(analysis_ids), older_than_seconds)
                )
                return cur.rowcount
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo reciclar análisis atascados en la base de datos."
            )
        ) from exc


async def _update(query: str, params: tuple[Any, ...], context: str) -> bool:
    """Ejecuta un UPDATE y devuelve si cambió alguna fila."""
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return cur.rowcount > 0
    except psycopg.Error as exc:
        raise DatabaseError(_build_database_error(context)) from exc
