"""Tests de la cola arq real sobre fakeredis: despacho por nombre, timeout y jobs desconocidos."""

import asyncio

import fakeredis.aioredis
import pytest
from arq.connections import ArqRedis
from arq.worker import JobExecutionFailed, Worker

import app.worker as worker_module

ANALYSIS_ID = "22222222-2222-2222-2222-222222222222"


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


def _patch_db(monkeypatch):
    """Sustituye las escrituras de BD del worker por espías que registran llamadas."""
    completed = []
    failed = []

    async def fake_complete(**kwargs):
        completed.append(kwargs)

    async def fake_fail(**kwargs):
        failed.append(kwargs)

    async def fake_set_stage(**kwargs):
        pass

    monkeypatch.setattr(worker_module, "complete_analysis", fake_complete)
    monkeypatch.setattr(worker_module, "fail_analysis", fake_fail)
    monkeypatch.setattr(worker_module, "set_analysis_stage", fake_set_stage)
    return completed, failed


def _make_worker(arq_pool, **overrides) -> Worker:
    """Construye un worker de arq en modo burst con las funciones registradas reales."""
    defaults = dict(
        functions=worker_module.WorkerSettings.functions,
        redis_pool=arq_pool,
        burst=True,
        handle_signals=False,
        poll_delay=0.01,
    )
    defaults.update(overrides)
    return Worker(**defaults)


async def test_enqueued_job_round_trips_through_real_arq_worker(monkeypatch, arq_pool):
    """El nombre y los argumentos que encola la ruta llegan intactos a run_analysis."""
    completed, failed = _patch_db(monkeypatch)
    graph_sentinel = object()
    seen = {}

    async def fake_ainvoke(graph, state, on_stage=None):
        seen["graph"] = graph
        seen["input_text"] = state["input_text"]
        return {
            "label": "falsa",
            "confidence": 0.9,
            "medical_explanation": "Informe.",
        }

    monkeypatch.setattr(worker_module, "ainvoke_graph", fake_ainvoke)

    async def startup(ctx):
        ctx["verification_system"] = graph_sentinel

    # Misma forma exacta de encolado que usan las rutas del proceso web.
    await arq_pool.enqueue_job(
        "run_analysis",
        ANALYSIS_ID,
        "text",
        "Bleach cures COVID",
        None,
        _job_id=ANALYSIS_ID,
    )

    worker = _make_worker(arq_pool, on_startup=startup)
    await worker.main()

    assert (worker.jobs_complete, worker.jobs_failed) == (1, 0)
    # El grafo construido en startup llega al job vía ctx["verification_system"].
    assert seen["graph"] is graph_sentinel
    assert seen["input_text"] == "Bleach cures COVID"
    assert failed == []
    assert completed[0]["analysis_id"] == ANALYSIS_ID
    assert completed[0]["label"] == "falsa"


async def test_duplicate_enqueue_with_same_job_id_runs_the_analysis_once(
    monkeypatch, arq_pool
):
    """Dos encolados del mismo analysis_id (p. ej. reaper + retry en carrera) corren una sola vez."""
    completed, failed = _patch_db(monkeypatch)

    async def fake_ainvoke(graph, state, on_stage=None):
        return {
            "label": "falsa",
            "confidence": 0.9,
            "medical_explanation": "Informe.",
        }

    monkeypatch.setattr(worker_module, "ainvoke_graph", fake_ainvoke)

    async def startup(ctx):
        ctx["verification_system"] = object()

    first = await arq_pool.enqueue_job(
        "run_analysis", ANALYSIS_ID, "text", "Texto", None, _job_id=ANALYSIS_ID
    )
    second = await arq_pool.enqueue_job(
        "run_analysis", ANALYSIS_ID, "text", "Texto", None, _job_id=ANALYSIS_ID
    )

    assert first is not None
    assert second is None

    worker = _make_worker(arq_pool, on_startup=startup)
    await worker.main()

    assert (worker.jobs_complete, worker.jobs_failed) == (1, 0)
    assert len(completed) == 1
    assert failed == []


async def test_finished_job_without_kept_result_can_be_reenqueued(
    monkeypatch, arq_pool
):
    """Con keep_result=0 (retry tras un fallo), el mismo _job_id puede reencolarse al acabar."""
    completed, failed = _patch_db(monkeypatch)

    async def fake_ainvoke(graph, state, on_stage=None):
        return {
            "label": "falsa",
            "confidence": 0.9,
            "medical_explanation": "Informe.",
        }

    monkeypatch.setattr(worker_module, "ainvoke_graph", fake_ainvoke)

    async def startup(ctx):
        ctx["verification_system"] = object()

    await arq_pool.enqueue_job(
        "run_analysis", ANALYSIS_ID, "text", "Texto", None, _job_id=ANALYSIS_ID
    )
    worker = _make_worker(
        arq_pool,
        on_startup=startup,
        keep_result=worker_module.WorkerSettings.keep_result,
    )
    await worker.main()

    # Una clave arq:result: residual haría de este segundo encolado un no-op.
    reenqueued = await arq_pool.enqueue_job(
        "run_analysis", ANALYSIS_ID, "text", "Texto", None, _job_id=ANALYSIS_ID
    )

    assert reenqueued is not None
    worker = _make_worker(
        arq_pool,
        on_startup=startup,
        keep_result=worker_module.WorkerSettings.keep_result,
    )
    await worker.main()

    assert len(completed) == 2


async def test_job_exceeding_timeout_is_cancelled_without_writing_a_verdict(
    monkeypatch, arq_pool
):
    """Un job colgado se cancela por timeout y la fila queda pending para el reaper."""
    completed, failed = _patch_db(monkeypatch)

    async def hanging_ainvoke(graph, state, on_stage=None):
        await asyncio.sleep(30)

    monkeypatch.setattr(worker_module, "ainvoke_graph", hanging_ainvoke)

    async def startup(ctx):
        ctx["verification_system"] = object()

    job = await arq_pool.enqueue_job("run_analysis", ANALYSIS_ID, "text", "Texto", None)

    worker = _make_worker(arq_pool, on_startup=startup, job_timeout=0.2)
    await worker.main()

    # La cancelación no debe registrarse como veredicto ni como fallo del análisis:
    # la fila sigue pending y es el cron reap_stale_analyses quien la recoge.
    assert completed == []
    assert failed == []
    assert worker.jobs_failed == 1

    info = await job.result_info()
    assert info is not None
    assert info.success is False
    assert isinstance(info.result, TimeoutError)


async def test_job_with_unknown_function_name_fails_without_touching_db(
    monkeypatch, arq_pool
):
    """Un desfase de nombres web/worker falla el job en arq sin tocar la base de datos."""
    completed, failed = _patch_db(monkeypatch)

    async def startup(ctx):
        ctx["verification_system"] = object()

    # Simula un despliegue desfasado donde la ruta encola un nombre renombrado.
    job = await arq_pool.enqueue_job(
        "run_analysis_v2", ANALYSIS_ID, "text", "Texto", None
    )

    worker = _make_worker(arq_pool, on_startup=startup)
    await worker.main()

    assert worker.jobs_failed == 1
    assert completed == []
    assert failed == []

    info = await job.result_info()
    assert info is not None
    assert isinstance(info.result, JobExecutionFailed)


async def test_worker_survives_a_failing_job_and_processes_the_next_one(
    monkeypatch, arq_pool
):
    """Una excepción inesperada en un job no tumba el worker ni bloquea la cola."""
    completed, failed = _patch_db(monkeypatch)
    calls = []

    async def flaky_ainvoke(graph, state, on_stage=None):
        calls.append(state["input_text"])
        if state["input_text"] == "veneno":
            raise RuntimeError("graph exploded")
        return {
            "label": "verdadera",
            "confidence": 0.8,
            "medical_explanation": "Informe.",
        }

    monkeypatch.setattr(worker_module, "ainvoke_graph", flaky_ainvoke)

    async def startup(ctx):
        ctx["verification_system"] = object()

    await arq_pool.enqueue_job("run_analysis", ANALYSIS_ID, "text", "veneno", None)
    await arq_pool.enqueue_job(
        "run_analysis", "33333333-3333-3333-3333-333333333333", "text", "sano", None
    )

    worker = _make_worker(arq_pool, on_startup=startup)
    await worker.main()

    # arq no garantiza orden ante empate de score; lo que importa es que ambos corran.
    assert sorted(calls) == ["sano", "veneno"]
    assert worker.jobs_complete == 2
    assert [f["error_code"] for f in failed] == ["INTERNAL"]
    assert [c["analysis_id"] for c in completed] == [
        "33333333-3333-3333-3333-333333333333"
    ]
