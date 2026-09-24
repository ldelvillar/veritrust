"""Escrituras de estado y etapa de un análisis; solo las usa ``app.core.analysis_lifecycle``."""

from __future__ import annotations

from typing import Any, Literal

import psycopg
from psycopg.rows import dict_row

from app.db.pool import DatabaseError, _build_database_error, get_pool


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
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id, analysis_id, from_status))
                return cur.rowcount > 0
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error("No se pudo reabrir el análisis en la base de datos.")
        ) from exc


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
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (error_code, analysis_id))
                return cur.rowcount > 0
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error(
                "No se pudo actualizar el analisis en la base de datos."
            )
        ) from exc
