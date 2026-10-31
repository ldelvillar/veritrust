"""Tests of the real arq queue on fakeredis: dispatch by name, timeout and unknown jobs."""

import asyncio

import fakeredis.aioredis
import pytest
from arq.connections import ArqRedis
from arq.worker import JobExecutionFailed, Worker

import app.worker as worker_module
from app.core.analysis_jobs import ArqAnalysisQueue

ANALYSIS_ID = "22222222-2222-2222-2222-222222222222"
HEALTHY_ID = "33333333-3333-3333-3333-333333333333"
PIPELINE = {"provider": "test", "models": {}, "prompts": {"judge": "v0"}}


@pytest.fixture(autouse=True)
def _silence_redis_info(monkeypatch):
    """fakeredis does not implement INFO, so arq's startup log is disabled."""

    async def _noop(pool, log):
        pass

    monkeypatch.setattr("arq.worker.log_redis_info", _noop)


@pytest.fixture
def arq_pool():
    """arq pool backed by an in-memory mock Redis server."""
    fake = fakeredis.aioredis.FakeRedis(server=fakeredis.FakeServer())
    return ArqRedis(connection_pool=fake.connection_pool)


class _RecordingRunner:
    """Fake lifecycle runner that records each Run and can hang or fail."""

    def __init__(self, *, hang=False, explode_on=None):
        self.runs: list[tuple] = []
        self.finished: list[str] = []
        self._hang = hang
        self._explode_on = explode_on

    async def run(self, analysis_id, work, *, notify_email=None):
        self.runs.append((analysis_id, work, notify_email))
        if self._hang:
            await asyncio.sleep(30)
        if analysis_id == self._explode_on:
            raise RuntimeError("fallo inesperado fuera del trabajo de la Run")
        self.finished.append(analysis_id)
        return "done"


def _make_worker(arq_pool, runner, **overrides) -> Worker:
    """Build a burst-mode arq worker with the real registered functions."""

    async def startup(ctx):
        ctx["verification_system"] = object()
        ctx["pipeline"] = PIPELINE
        ctx["analysis_runner"] = runner

    defaults = dict(
        functions=worker_module.WorkerSettings.functions,
        redis_pool=arq_pool,
        burst=True,
        handle_signals=False,
        poll_delay=0.01,
        on_startup=startup,
    )
    defaults.update(overrides)
    return Worker(**defaults)


async def test_enqueued_job_round_trips_through_real_arq_worker(arq_pool):
    """The name and arguments the web queue enqueues reach run_analysis intact."""
    runner = _RecordingRunner()

    # The same queue adapter the web process uses.
    await ArqAnalysisQueue(arq_pool).enqueue(
        ANALYSIS_ID, notify_email="user@example.com"
    )
    worker = _make_worker(arq_pool, runner)
    await worker.main()

    assert (worker.jobs_complete, worker.jobs_failed) == (1, 0)
    [(analysis_id, work, notify_email)] = runner.runs
    assert (analysis_id, notify_email) == (ANALYSIS_ID, "user@example.com")
    # The Run's work is analyse, bound to the ctx that startup prepared.
    assert work.func is worker_module.analyse
    assert work.args[0]["pipeline"] is PIPELINE


async def test_duplicate_enqueue_with_same_job_id_runs_the_analysis_once(arq_pool):
    """Two enqueues of the same analysis_id while its job is alive run only once."""
    runner = _RecordingRunner()
    queue = ArqAnalysisQueue(arq_pool)

    await queue.enqueue(ANALYSIS_ID, notify_email=None)
    await queue.enqueue(ANALYSIS_ID, notify_email=None)
    worker = _make_worker(arq_pool, runner)
    await worker.main()

    assert (worker.jobs_complete, worker.jobs_failed) == (1, 0)
    assert runner.finished == [ANALYSIS_ID]


async def test_finished_job_without_kept_result_can_be_reenqueued(arq_pool):
    """With keep_result=0 a finished Run releases its job and the Analysis can be enqueued again."""
    runner = _RecordingRunner()
    queue = ArqAnalysisQueue(arq_pool)
    keep_result = worker_module.WorkerSettings.keep_result

    await queue.enqueue(ANALYSIS_ID, notify_email=None)
    await _make_worker(arq_pool, runner, keep_result=keep_result).main()

    # A leftover arq:result: key would make this second enqueue a no-op.
    assert await queue.is_live(ANALYSIS_ID) is False
    await queue.enqueue(ANALYSIS_ID, notify_email=None)
    assert await queue.is_live(ANALYSIS_ID) is True
    await _make_worker(arq_pool, runner, keep_result=keep_result).main()

    assert runner.finished == [ANALYSIS_ID, ANALYSIS_ID]


async def test_job_exceeding_timeout_is_cancelled_mid_run(arq_pool):
    """A hung job is cancelled by arq's hard cut without closing its Run."""
    runner = _RecordingRunner(hang=True)

    job = await arq_pool.enqueue_job("run_analysis", analysis_id=ANALYSIS_ID)
    worker = _make_worker(arq_pool, runner, job_timeout=0.2)
    await worker.main()

    # The row stays pending and the reap_orphaned_analyses cron collects it.
    assert runner.finished == []
    assert worker.jobs_failed == 1
    info = await job.result_info()
    assert info is not None
    assert info.success is False
    assert isinstance(info.result, TimeoutError)


async def test_cancelling_a_running_job_aborts_its_run(arq_pool):
    """Cancelling a running Run's job cuts it without closing it and releases the job."""
    runner = _RecordingRunner(hang=True)
    queue = ArqAnalysisQueue(arq_pool)

    await queue.enqueue(ANALYSIS_ID, notify_email=None)
    worker = _make_worker(
        arq_pool,
        runner,
        allow_abort_jobs=worker_module.WorkerSettings.allow_abort_jobs,
        keep_result=worker_module.WorkerSettings.keep_result,
    )
    main = asyncio.create_task(worker.main())
    while not runner.runs:
        await asyncio.sleep(0.01)

    await queue.cancel([ANALYSIS_ID])
    await asyncio.wait_for(main, timeout=5)

    assert runner.finished == []
    assert (worker.jobs_complete, worker.jobs_failed) == (0, 1)
    assert await queue.is_live(ANALYSIS_ID) is False


async def test_job_with_unknown_function_name_fails_without_running(arq_pool):
    """A web and worker name mismatch fails the job in arq without opening any Run."""
    runner = _RecordingRunner()

    # Simulate a skewed deploy where the web enqueues a renamed name.
    job = await arq_pool.enqueue_job("run_analysis_v2", analysis_id=ANALYSIS_ID)
    worker = _make_worker(arq_pool, runner)
    await worker.main()

    assert worker.jobs_failed == 1
    assert runner.runs == []
    info = await job.result_info()
    assert info is not None
    assert isinstance(info.result, JobExecutionFailed)


async def test_worker_survives_a_failing_job_and_processes_the_next_one(arq_pool):
    """An exception escaping a job neither kills the worker nor blocks the queue."""
    runner = _RecordingRunner(explode_on=ANALYSIS_ID)
    queue = ArqAnalysisQueue(arq_pool)

    await queue.enqueue(ANALYSIS_ID, notify_email=None)
    await queue.enqueue(HEALTHY_ID, notify_email=None)
    worker = _make_worker(arq_pool, runner)
    await worker.main()

    # arq does not guarantee order on a score tie, and what matters is that both run.
    assert sorted(run[0] for run in runner.runs) == [ANALYSIS_ID, HEALTHY_ID]
    assert (worker.jobs_complete, worker.jobs_failed) == (1, 1)
    assert runner.finished == [HEALTHY_ID]
