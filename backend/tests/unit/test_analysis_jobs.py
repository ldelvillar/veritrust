"""Tests unitarios del encolado compartido del pipeline de análisis."""

import inspect

import pytest
from redis.exceptions import RedisError

import app.core.analysis_jobs as jobs_module
from app.core.analysis_jobs import EnqueueError, enqueue_analysis
from app.db.pool import DatabaseError
from app.worker import run_analysis

ANALYSIS_ID = "11111111-1111-1111-1111-111111111111"


class _ArqPool:
    def __init__(self, error: Exception | None = None):
        self.enqueued: list[tuple[str, tuple, dict]] = []
        self._error = error

    async def enqueue_job(self, name, *args, **kwargs):
        if self._error is not None:
            raise self._error
        self.enqueued.append((name, args, kwargs))


async def _enqueue(pool: _ArqPool) -> None:
    await enqueue_analysis(
        pool,
        analysis_id=ANALYSIS_ID,
        source_type="url",
        text=None,
        url="https://ejemplo.com/noticia",
        email="user@example.com",
    )


async def test_enqueued_args_bind_to_the_worker_signature_by_name() -> None:
    """El worker recibe los argumentos por posición: un desorden cambiaría su significado."""
    pool = _ArqPool()

    await _enqueue(pool)

    [(name, args, kwargs)] = pool.enqueued
    bound = inspect.signature(run_analysis).bind({}, *args).arguments
    assert name == run_analysis.__name__
    assert kwargs == {"_job_id": ANALYSIS_ID}
    assert bound["analysis_id"] == ANALYSIS_ID
    assert bound["source_type"] == "url"
    assert bound["text"] is None
    assert bound["url"] == "https://ejemplo.com/noticia"
    assert bound["recipient_email"] == "user@example.com"


@pytest.mark.parametrize("error", [RedisError("down"), ConnectionResetError("reset")])
async def test_enqueue_failure_fails_the_row_and_raises(monkeypatch, error) -> None:
    failed: list[dict] = []

    async def fake_fail_analysis(**kwargs):
        failed.append(kwargs)

    monkeypatch.setattr(jobs_module, "fail_analysis", fake_fail_analysis)

    with pytest.raises(EnqueueError):
        await _enqueue(_ArqPool(error))

    assert failed == [{"analysis_id": ANALYSIS_ID, "error_code": "SERVICE_UNAVAILABLE"}]


async def test_enqueue_failure_still_raises_when_the_rollback_fails(
    monkeypatch,
) -> None:
    async def broken_fail_analysis(**kwargs):
        raise DatabaseError("db down")

    monkeypatch.setattr(jobs_module, "fail_analysis", broken_fail_analysis)

    with pytest.raises(EnqueueError):
        await _enqueue(_ArqPool(RedisError("down")))
