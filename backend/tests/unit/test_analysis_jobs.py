"""Tests del adaptador arq de la cola de análisis sobre un Redis simulado."""

import inspect

import fakeredis.aioredis
import pytest
from arq.connections import ArqRedis
from arq.constants import abort_jobs_ss
from arq.jobs import Job
from redis.exceptions import RedisError

from app.core.analysis_jobs import ANALYSIS_JOB, ArqAnalysisQueue
from app.core.analysis_lifecycle import QueueUnavailable
from app.worker import run_analysis

ANALYSIS_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def redis():
    fake = fakeredis.aioredis.FakeRedis(server=fakeredis.FakeServer())
    return ArqRedis(connection_pool=fake.connection_pool)


async def test_enqueued_job_binds_to_the_worker_signature_by_name(redis) -> None:
    await ArqAnalysisQueue(redis).enqueue(ANALYSIS_ID, notify_email="user@example.com")

    job = await Job(ANALYSIS_ID, redis).info()
    assert job is not None
    assert job.function == ANALYSIS_JOB == run_analysis.__name__
    bound = inspect.signature(run_analysis).bind({}, *job.args, **job.kwargs)
    assert bound.arguments["analysis_id"] == ANALYSIS_ID
    assert bound.arguments["notify_email"] == "user@example.com"


async def test_a_queued_job_is_live_until_arq_drops_it(redis) -> None:
    queue = ArqAnalysisQueue(redis)

    assert await queue.is_live(ANALYSIS_ID) is False
    await queue.enqueue(ANALYSIS_ID, notify_email=None)

    assert await queue.is_live(ANALYSIS_ID) is True


async def test_enqueueing_a_live_analysis_again_keeps_a_single_job(redis) -> None:
    queue = ArqAnalysisQueue(redis)

    await queue.enqueue(ANALYSIS_ID, notify_email="first@example.com")
    await queue.enqueue(ANALYSIS_ID, notify_email="second@example.com")

    job = await Job(ANALYSIS_ID, redis).info()
    assert job is not None
    assert job.kwargs["notify_email"] == "first@example.com"
    assert await redis.zcard("arq:queue") == 1


async def test_cancelling_asks_arq_to_abort_only_the_live_jobs(redis) -> None:
    queue = ArqAnalysisQueue(redis)
    await queue.enqueue(ANALYSIS_ID, notify_email=None)

    # El segundo id no tiene job: arq nunca retiraría su aborto.
    await queue.cancel([ANALYSIS_ID, "22222222-2222-2222-2222-222222222222"])

    assert await redis.zrange(abort_jobs_ss, 0, -1) == [ANALYSIS_ID.encode()]


class _BrokenRedis:
    def __init__(self, error: Exception):
        self._error = error

    async def enqueue_job(self, *args, **kwargs):
        raise self._error

    async def exists(self, *keys):
        raise self._error

    def register_script(self, script):
        return self._fail

    async def _fail(self, **kwargs):
        raise self._error


@pytest.mark.parametrize("error", [RedisError("down"), ConnectionResetError("reset")])
async def test_transport_failures_surface_as_queue_unavailable(error) -> None:
    queue = ArqAnalysisQueue(_BrokenRedis(error))

    with pytest.raises(QueueUnavailable):
        await queue.enqueue(ANALYSIS_ID, notify_email=None)
    with pytest.raises(QueueUnavailable):
        await queue.is_live(ANALYSIS_ID)
    with pytest.raises(QueueUnavailable):
        await queue.cancel([ANALYSIS_ID])
