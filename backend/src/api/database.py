"""Utilidades de persistencia para guardar y consultar el historial de analisis."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from dotenv import load_dotenv
import psycopg2

from src.api.schemas import AnalyzeRequest

load_dotenv()

logger = logging.getLogger(__name__)


class HistoryDatabaseError(RuntimeError):
    """Error base para operaciones de persistencia del historial."""


@dataclass(frozen=True)
class HistoryRecord:
    """Representa una fila de historial de analisis."""

    id: str
    user_id: str
    source_type: str
    input_text: Optional[str]
    input_url: Optional[str]
    label: str
    confidence: float
    explanation: str
    created_at: str


def _build_connection_string() -> str:
    """Obtiene la cadena de conexion desde la variable DATABASE_URL."""

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HistoryDatabaseError(
            "No se encontro la variable de entorno DATABASE_URL."
        )

    return db_url


def _normalize_confidence(confidence: Any) -> float:
    """Convierte confidence a float y valida el rango [0, 1]."""

    try:
        value = float(confidence)
    except (TypeError, ValueError) as exc:
        raise HistoryDatabaseError(
            f"Confidence no es numerico: {confidence!r}."
        ) from exc

    if not 0.0 <= value <= 1.0:
        raise HistoryDatabaseError(f"Confidence fuera de rango [0, 1]: {value}.")

    return value


def save_analysis_history(
    *,
    user_id: str,
    source_type: str,
    input_text: Optional[str],
    input_url: Optional[str],
    label: str,
    confidence: Any,
    explanation: str,
) -> str:
    """Guarda un analisis exitoso en public.analysis_history."""

    conninfo = _build_connection_string()
    confidence_value = _normalize_confidence(confidence)

    query = """
		INSERT INTO public.analysis_history
		(user_id, source_type, input_text, input_url, label, confidence, explanation)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
	"""

    try:
        with psycopg2.connect(conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        user_id,
                        source_type,
                        input_text,
                        input_url,
                        label,
                        confidence_value,
                        explanation,
                    ),
                )
                inserted_row = cur.fetchone()
            conn.commit()

            if not inserted_row:
                raise HistoryDatabaseError(
                    "No se pudo obtener el id del análisis guardado."
                )

            return str(inserted_row[0])
    except psycopg2.Error as exc:
        raise HistoryDatabaseError(
            "No se pudo guardar el analisis en la base de datos. "
            "Revisa DATABASE_URL y, si usas Supabase, prueba el host del pooler IPv4."
        ) from exc


def save_successful_analysis(
    *,
    user_id: str,
    request: AnalyzeRequest,
    label: str,
    confidence: Any,
    explanation: str,
) -> str | None:
    """
    Persistencia de analisis exitoso.
    Devuelve el id del analisis si se guardo correctamente y None en caso de error.
    El objetivo es no romper la respuesta de analisis por fallos temporales de BD.
    """

    source_type = request.source_type.value
    input_text = request.text if source_type in {"text", "file"} else None
    input_url = str(request.url) if source_type == "url" and request.url else None

    try:
        return save_analysis_history(
            user_id=user_id,
            source_type=source_type,
            input_text=input_text,
            input_url=input_url,
            label=label,
            confidence=confidence,
            explanation=explanation,
        )
    except (HistoryDatabaseError, psycopg2.Error) as exc:
        logger.exception("No se pudo guardar el historial de analisis: %s", exc)
        return None


def list_user_analysis_history(
    *,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    search_query: Optional[str] = None,
    source_type: Optional[str] = None,
    created_after: Optional[datetime] = None,
    score_sort_order: str = "desc",
) -> tuple[list[HistoryRecord], int]:
    """Lista historial paginado del usuario y devuelve tambien el total."""

    conninfo = _build_connection_string()

    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    safe_source_type = source_type if source_type in {"text", "file", "url"} else None
    safe_score_sort = "ASC" if score_sort_order.lower() == "asc" else "DESC"

    where_clauses = ["user_id = %s"]
    where_params: list[Any] = [user_id]

    normalized_search = (search_query or "").strip()
    if normalized_search:
        like_pattern = f"%{normalized_search}%"
        where_clauses.append(
            "("
            "COALESCE(input_text, '') ILIKE %s OR "
            "COALESCE(input_url, '') ILIKE %s OR "
            "COALESCE(label, '') ILIKE %s OR "
            "COALESCE(source_type, '') ILIKE %s"
            ")"
        )
        where_params.extend([like_pattern, like_pattern, like_pattern, like_pattern])

    if safe_source_type:
        where_clauses.append("source_type = %s")
        where_params.append(safe_source_type)

    if created_after is not None:
        where_clauses.append("created_at >= %s")
        where_params.append(created_after)

    where_sql = " AND ".join(where_clauses)

    count_query = f"""
        SELECT COUNT(*)
        FROM public.analysis_history
        WHERE {where_sql}
    """

    query = """
		SELECT
			id,
			user_id,
			source_type,
			input_text,
			input_url,
			label,
			confidence,
			explanation,
			created_at
		FROM public.analysis_history
		WHERE {where_sql}
		ORDER BY confidence {safe_score_sort}, created_at DESC
		LIMIT %s OFFSET %s
	""".format(
        where_sql=where_sql, safe_score_sort=safe_score_sort
    )

    try:
        with psycopg2.connect(conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(count_query, tuple(where_params))
                count_row = cur.fetchone()
                total_count = int(count_row[0]) if count_row else 0

                cur.execute(query, (*where_params, safe_limit, safe_offset))
                rows = cur.fetchall()
    except psycopg2.Error as exc:
        raise HistoryDatabaseError(
            "No se pudo consultar el historial en la base de datos. "
            "Revisa DATABASE_URL y, si usas Supabase, prueba el host del pooler IPv4."
        ) from exc

    records = [
        HistoryRecord(
            id=str(row[0]),
            user_id=row[1],
            source_type=row[2],
            input_text=row[3],
            input_url=row[4],
            label=row[5],
            confidence=float(row[6]),
            explanation=row[7],
            created_at=str(row[8]),
        )
        for row in rows
    ]

    return records, total_count


def get_user_analysis_by_id(*, user_id: str, analysis_id: str) -> HistoryRecord | None:
    """Obtiene un analisis por id para un usuario autenticado."""

    conninfo = _build_connection_string()

    query = """
		SELECT
			id,
			user_id,
			source_type,
			input_text,
			input_url,
			label,
			confidence,
			explanation,
			created_at
		FROM public.analysis_history
		WHERE user_id = %s AND id = %s
		LIMIT 1
	"""

    try:
        with psycopg2.connect(conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (user_id, analysis_id))
                row = cur.fetchone()
    except psycopg2.Error as exc:
        raise HistoryDatabaseError(
            "No se pudo consultar el análisis en la base de datos. "
            "Revisa DATABASE_URL y, si usas Supabase, prueba el host del pooler IPv4."
        ) from exc

    if not row:
        return None

    return HistoryRecord(
        id=str(row[0]),
        user_id=row[1],
        source_type=row[2],
        input_text=row[3],
        input_url=row[4],
        label=row[5],
        confidence=float(row[6]),
        explanation=row[7],
        created_at=str(row[8]),
    )
