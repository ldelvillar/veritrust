"""Encolado del pipeline de análisis, compartido por las rutas web y el servidor MCP."""

import logging
from typing import Any

from redis.exceptions import RedisError

from app.db.history import fail_analysis
from app.db.pool import DatabaseError
from app.schemas.errors import ErrorCode

logger = logging.getLogger(__name__)


class EnqueueError(RuntimeError):
    """No se pudo encolar el análisis y su fila ya quedó en ``failed``."""


async def enqueue_analysis(
    arq_pool: Any,
    *,
    analysis_id: str,
    source_type: str,
    text: str | None,
    url: str | None,
    email: str | None,
) -> None:
    """Encola ``run_analysis`` para una fila ``pending`` y, si no puede, la pasa a ``failed`` y lanza EnqueueError."""
    try:
        # Posicionales en el orden de la firma de run_analysis; _job_id hace que un doble encolado sea un no-op.
        await arq_pool.enqueue_job(
            "run_analysis",
            analysis_id,
            source_type,
            text,
            url,
            email,
            _job_id=analysis_id,
        )
    except (OSError, RedisError) as exc:
        logger.exception("No se pudo encolar el análisis %s", analysis_id)
        # Sin encolado, la fila pasa a failed para que el cliente deje de sondear.
        try:
            await fail_analysis(
                analysis_id=analysis_id,
                error_code=ErrorCode.SERVICE_UNAVAILABLE.value,
            )
        except DatabaseError:
            logger.exception(
                "No se pudo marcar como failed el análisis %s", analysis_id
            )
        raise EnqueueError(analysis_id) from exc
