"""Tests de la cola arq real sobre fakeredis: despacho por nombre, timeout y jobs desconocidos."""

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
    """fakeredis no implementa INFO, así que se anula el log de arranque de arq."""

    async def _noop(pool, log):
        pass

    monkeypatch.setattr("arq.worker.log_redis_info", _noop)


@pytest.fixture
def arq_pool():
    """Pool de arq respaldado por un servidor Redis simulado en memoria."""
    fake = fakeredis.aioredis.FakeRedis(server=fakeredis.FakeServer())
    return ArqRedis(connection_pool=fake.connection_pool)


class _RecordingRunner:
    """Runner del ciclo de vida de mentira: registra cada Run y puede colgarse o fallar."""

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
    """Construye un worker de arq en modo burst con las funciones registradas reales."""

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
    """El nombre y los argumentos que encola la cola de la web llegan intactos a run_analysis."""
    runner = _RecordingRunner()

    # El mismo adaptador de cola que usa el proceso web.
    await ArqAnalysisQueue(arq_pool).enqueue(
        ANALYSIS_ID, notify_email="user@example.com"
    )
    worker = _make_worker(arq_pool, runner)
    await worker.main()

    assert (worker.jobs_complete, worker.jobs_failed) == (1, 0)
    [(analysis_id, work, notify_email)] = runner.runs
    assert (analysis_id, notify_email) == (ANALYSIS_ID, "user@example.com")
    # El trabajo de la Run es analyse sobre el ctx que preparó startup.
    assert work.func is worker_module.analyse
    assert work.args[0]["pipeline"] is PIPELINE


async def test_duplicate_enqueue_with_same_job_id_runs_the_analysis_once(arq_pool):
    """Dos encolados del mismo analysis_id mientras su job sigue vivo corren una sola vez."""
    runner = _RecordingRunner()
    queue = ArqAnalysisQueue(arq_pool)

    await queue.enqueue(ANALYSIS_ID, notify_email=None)
    await queue.enqueue(ANALYSIS_ID, notify_email=None)
    worker = _make_worker(arq_pool, runner)
    await worker.main()

    assert (worker.jobs_complete, worker.jobs_failed) == (1, 0)
    assert runner.finished == [ANALYSIS_ID]


async def test_finished_job_without_kept_result_can_be_reenqueued(arq_pool):
    """Con keep_result=0, una Run terminada suelta su job y el análisis puede reencolarse."""
    runner = _RecordingRunner()
    queue = ArqAnalysisQueue(arq_pool)
    keep_result = worker_module.WorkerSettings.keep_result

    await queue.enqueue(ANALYSIS_ID, notify_email=None)
    await _make_worker(arq_pool, runner, keep_result=keep_result).main()

    # Una clave arq:result: residual haría de este segundo encolado un no-op.
    assert await queue.is_live(ANALYSIS_ID) is False
    await queue.enqueue(ANALYSIS_ID, notify_email=None)
    assert await queue.is_live(ANALYSIS_ID) is True
    await _make_worker(arq_pool, runner, keep_result=keep_result).main()

    assert runner.finished == [ANALYSIS_ID, ANALYSIS_ID]


async def test_job_exceeding_timeout_is_cancelled_mid_run(arq_pool):
    """Un job colgado se cancela por el corte duro de arq sin llegar a cerrar su Run."""
    runner = _RecordingRunner(hang=True)

    job = await arq_pool.enqueue_job("run_analysis", analysis_id=ANALYSIS_ID)
    worker = _make_worker(arq_pool, runner, job_timeout=0.2)
    await worker.main()

    # La fila sigue pending y es el cron reap_orphaned_analyses quien la recoge.
    assert runner.finished == []
    assert worker.jobs_failed == 1
    info = await job.result_info()
    assert info is not None
    assert info.success is False
    assert isinstance(info.result, TimeoutError)


async def test_job_with_unknown_function_name_fails_without_running(arq_pool):
    """Un desfase de nombres web/worker falla el job en arq sin abrir ninguna Run."""
    runner = _RecordingRunner()

    # Simula un despliegue desfasado donde la web encola un nombre renombrado.
    job = await arq_pool.enqueue_job("run_analysis_v2", analysis_id=ANALYSIS_ID)
    worker = _make_worker(arq_pool, runner)
    await worker.main()

    assert worker.jobs_failed == 1
    assert runner.runs == []
    info = await job.result_info()
    assert info is not None
    assert isinstance(info.result, JobExecutionFailed)


async def test_worker_survives_a_failing_job_and_processes_the_next_one(arq_pool):
    """Una excepción que escapa de un job no tumba el worker ni bloquea la cola."""
    runner = _RecordingRunner(explode_on=ANALYSIS_ID)
    queue = ArqAnalysisQueue(arq_pool)

    await queue.enqueue(ANALYSIS_ID, notify_email=None)
    await queue.enqueue(HEALTHY_ID, notify_email=None)
    worker = _make_worker(arq_pool, runner)
    await worker.main()

    # arq no garantiza orden ante empate de score; lo que importa es que ambos corran.
    assert sorted(run[0] for run in runner.runs) == [ANALYSIS_ID, HEALTHY_ID]
    assert (worker.jobs_complete, worker.jobs_failed) == (1, 1)
    assert runner.finished == [HEALTHY_ID]
