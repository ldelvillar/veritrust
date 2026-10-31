"""arq adapter of the analysis queue, the only place that knows the job name and its payload."""

import logging
from collections.abc import Sequence

from arq.connections import ArqRedis
from arq.constants import abort_jobs_ss, job_key_prefix
from arq.utils import timestamp_ms
from redis.exceptions import RedisError

from app.core.analysis_lifecycle import QueueUnavailable

logger = logging.getLogger(__name__)

# Name under which the worker registers the function that runs each Run.
ANALYSIS_JOB = "run_analysis"

# arq only clears an abort when its job starts or ends, so marking one already gone would leave it forever.
_ABORT_LIVE_JOBS = """
for i = 2, #KEYS do
    if redis.call('EXISTS', KEYS[i]) == 1 then
        redis.call('ZADD', KEYS[1], ARGV[1], ARGV[i])
    end
end
"""


class ArqAnalysisQueue:
    """Analysis queue on arq and Redis."""

    def __init__(self, redis: ArqRedis) -> None:
        self._redis = redis
        self._abort_live_jobs = redis.register_script(_ABORT_LIVE_JOBS)

    async def enqueue(self, analysis_id: str, *, notify_email: str | None) -> None:
        """Enqueue the Run with ``_job_id=analysis_id`` so a double enqueue is a no-op."""
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
        """Tell whether arq still holds the analysis job, queued or running."""
        try:
            return bool(await self._redis.exists(job_key_prefix + analysis_id))
        except (OSError, RedisError) as exc:
            raise QueueUnavailable(analysis_id) from exc

    async def cancel(self, analysis_ids: Sequence[str]) -> None:
        """Ask arq to abort the jobs of the analyses still queued or running."""
        job_keys = [job_key_prefix + analysis_id for analysis_id in analysis_ids]
        try:
            await self._abort_live_jobs(
                keys=[abort_jobs_ss, *job_keys],
                args=[timestamp_ms(), *analysis_ids],
            )
        except (OSError, RedisError) as exc:
            raise QueueUnavailable(", ".join(analysis_ids)) from exc
