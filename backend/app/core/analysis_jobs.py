"""Adaptador arq de la cola de análisis: el nombre del job y su payload viven solo aquí."""

import logging

from arq.connections import ArqRedis
from arq.constants import job_key_prefix
from redis.exceptions import RedisError

from app.core.analysis_lifecycle import QueueUnavailable

logger = logging.getLogger(__name__)

# Nombre con el que el worker registra la función que ejecuta cada Run.
ANALYSIS_JOB = "run_analysis"


class ArqAnalysisQueue:
    """Cola de análisis sobre arq y Redis."""

    def __init__(self, redis: ArqRedis) -> None:
        self._redis = redis

    async def enqueue(self, analysis_id: str, *, notify_email: str | None) -> None:
        """Encola la Run con ``_job_id=analysis_id`` para que un doble encolado sea un no-op."""
        try:
            job = await self._redis.enqueue_job(
                ANALYSIS_JOB,
                analysis_id=analysis_id,
                notify_email=notify_email,
                _job_id=analysis_id,
            )
        except (OSError, RedisError) as exc:
            raise QueueUnavailable(analysis_id) from exc
        if job is None:
            logger.warning("El análisis %s ya tenía un job vivo en arq", analysis_id)

    async def is_live(self, analysis_id: str) -> bool:
        """Indica si arq guarda aún el job del análisis (en cola o en ejecución)."""
        try:
            return bool(await self._redis.exists(job_key_prefix + analysis_id))
        except (OSError, RedisError) as exc:
            raise QueueUnavailable(analysis_id) from exc
