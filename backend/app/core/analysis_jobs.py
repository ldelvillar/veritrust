"""Adaptador arq de la cola de análisis: el nombre del job y su payload viven solo aquí."""

import logging
from collections.abc import Sequence

from arq.connections import ArqRedis
from arq.constants import abort_jobs_ss, job_key_prefix
from arq.utils import timestamp_ms
from redis.exceptions import RedisError

from app.core.analysis_lifecycle import QueueUnavailable

logger = logging.getLogger(__name__)

# Nombre con el que el worker registra la función que ejecuta cada Run.
ANALYSIS_JOB = "run_analysis"

# arq solo retira un aborto al empezar o terminar su job: apuntarlo para uno ya ido lo dejaría para siempre.
_ABORT_LIVE_JOBS = """
for i = 2, #KEYS do
    if redis.call('EXISTS', KEYS[i]) == 1 then
        redis.call('ZADD', KEYS[1], ARGV[1], ARGV[i])
    end
end
"""


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

    async def cancel(self, analysis_ids: Sequence[str]) -> None:
        """Pide a arq que aborte los jobs de los análisis que aún siguen en cola o en ejecución."""
        job_keys = [job_key_prefix + analysis_id for analysis_id in analysis_ids]
        try:
            await self._redis.register_script(_ABORT_LIVE_JOBS)(
                keys=[abort_jobs_ss, *job_keys],
                args=[timestamp_ms(), *analysis_ids],
            )
        except (OSError, RedisError) as exc:
            raise QueueUnavailable(", ".join(analysis_ids)) from exc
