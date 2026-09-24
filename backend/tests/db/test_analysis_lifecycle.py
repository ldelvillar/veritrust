"""Pruebas del ciclo de vida de un análisis contra PostgreSQL real, a través de su interfaz."""

import asyncio

import pytest
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.analysis_lifecycle import (
    AnalysisFailure,
    AnalysisIntake,
    AnalysisRefused,
    AnalysisRunner,
    Completion,
    FileContent,
    Submitter,
    TextContent,
    UrlContent,
)
from app.db.history import get_user_analysis_status
from app.db.pool import DatabaseError
from app.schemas.analysis import AnalysisRequest, SourceType
from app.schemas.errors import ErrorCode
from tests.support.lifecycle import InMemoryAnalysisQueue, RecordingNotifier

pytestmark = pytest.mark.db

USER = "user-a"
EMAIL = "user-a@example.com"
WEB = Submitter(user_id=USER, origin="web", notify_email=EMAIL)
MAX_FILE_BYTES = 1024
PDF = b"%PDF-1.4 contenido minimo"


class _Upload:
    """Archivo subido de prueba que cuenta cuántas veces se lee."""

    def __init__(self, filename, data, size=None):
        self.filename = filename
        self.size = size
        self.reads = 0
        self._data = data

    async def read(self):
        self.reads += 1
        return self._data


@pytest.fixture
def queue():
    return InMemoryAnalysisQueue()


@pytest.fixture
def intake(queue):
    return AnalysisIntake(queue, max_file_bytes=MAX_FILE_BYTES)


async def _row(pool, analysis_id: str) -> dict:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT *, created_at > NOW() - interval '1 minute' AS fresh "
                "FROM public.analysis_history WHERE id = %s",
                (analysis_id,),
            )
            row = await cur.fetchone()
    assert row is not None
    return row


async def _count(pool) -> int:
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT COUNT(*) FROM public.analysis_history")
        row = await cur.fetchone()
    return row[0]


async def _arrange(pool, analysis_id: str, **columns) -> None:
    """Fuerza columnas de una fila y la envejece, como si una Run anterior ya hubiera acabado."""
    assignments = ", ".join(f"{column} = %s" for column in columns)
    async with pool.connection() as conn:
        await conn.execute(
            f"UPDATE public.analysis_history SET {assignments}, "
            "created_at = NOW() - interval '1 hour', completed_at = NOW() WHERE id = %s",
            (*columns.values(), analysis_id),
        )


async def _failed(pool, intake, queue, **columns) -> str:
    analysis_id = await intake.submit(
        WEB, AnalysisRequest(text="La lejía cura la COVID")
    )
    queue.finish(analysis_id)
    await _arrange(
        pool,
        analysis_id,
        status="failed",
        error_code="INTERNAL",
        stage="investigator",
        **columns,
    )
    return analysis_id


async def _done(pool, intake, queue) -> str:
    analysis_id = await intake.submit(
        WEB, AnalysisRequest(text="La lejía cura la COVID")
    )
    queue.finish(analysis_id)
    await _arrange(
        pool,
        analysis_id,
        status="done",
        label="falsa",
        verdict="fake",
        confidence=0.9,
        evidence_coverage=0.5,
        explanation="Sin evidencia.",
        claims=Jsonb([{"text": "La lejía cura", "label": "falsa", "confidence": 0.9}]),
        sources=Jsonb([{"title": "Estudio", "url": "https://doi.org/10.1/x"}]),
        pipeline=Jsonb({"provider": "ollama"}),
        share_token="token-publico",
    )
    return analysis_id


async def test_submit_opens_a_pending_text_analysis_and_enqueues_it(
    db_pool, intake, queue
):
    analysis_id = await intake.submit(
        WEB, AnalysisRequest(text="La lejía cura la COVID")
    )

    row = await _row(db_pool, analysis_id)
    assert row["status"] == "pending"
    assert (row["source_type"], row["origin"]) == ("text", "web")
    assert (row["input_text"], row["input_url"]) == ("La lejía cura la COVID", None)
    assert queue.enqueued == [(analysis_id, EMAIL)]


async def test_submit_stores_the_link_of_an_mcp_url_without_an_email(
    db_pool, intake, queue
):
    mcp = Submitter(user_id=USER, origin="mcp")
    request = AnalysisRequest(
        url="https://ejemplo.com/noticia", source_type=SourceType.URL
    )

    analysis_id = await intake.submit(mcp, request)

    row = await _row(db_pool, analysis_id)
    assert (row["source_type"], row["origin"]) == ("url", "mcp")
    assert (row["input_text"], row["input_url"]) == (
        None,
        "https://ejemplo.com/noticia",
    )
    assert queue.enqueued == [(analysis_id, None)]


async def test_submit_without_a_queue_refuses_before_writing(db_pool):
    intake = AnalysisIntake(None, max_file_bytes=MAX_FILE_BYTES)

    with pytest.raises(AnalysisRefused) as refusal:
        await intake.submit(WEB, AnalysisRequest(text="La lejía cura la COVID"))

    assert refusal.value.code == ErrorCode.SERVICE_UNAVAILABLE
    assert await _count(db_pool) == 0


async def test_submit_fails_the_row_when_the_queue_is_down(db_pool, intake, queue):
    queue.down = True

    with pytest.raises(AnalysisRefused) as refusal:
        await intake.submit(WEB, AnalysisRequest(text="La lejía cura la COVID"))

    assert refusal.value.code == ErrorCode.SERVICE_UNAVAILABLE
    async with db_pool.connection() as conn:
        cur = await conn.execute(
            "SELECT status, error_code FROM public.analysis_history"
        )
        assert await cur.fetchall() == [("failed", "SERVICE_UNAVAILABLE")]


async def test_submit_still_refuses_when_failing_the_row_also_fails(
    db_pool, db_faults, intake, queue
):
    queue.down = True
    db_faults.fail_on("SET status = 'failed'")

    with pytest.raises(AnalysisRefused) as refusal:
        await intake.submit(WEB, AnalysisRequest(text="La lejía cura la COVID"))

    assert refusal.value.code == ErrorCode.SERVICE_UNAVAILABLE


async def test_submit_refuses_with_save_failed_when_the_insert_fails(
    db_faults, intake, queue
):
    db_faults.fail_on("INSERT INTO")

    with pytest.raises(AnalysisRefused) as refusal:
        await intake.submit(WEB, AnalysisRequest(text="La lejía cura la COVID"))

    assert refusal.value.code == ErrorCode.ANALYSIS_SAVE_FAILED
    assert queue.enqueued == []


async def test_submit_file_stores_the_bytes_and_enqueues_it(db_pool, intake, queue):
    analysis_id = await intake.submit_file(WEB, _Upload("informe.PDF", PDF))

    row = await _row(db_pool, analysis_id)
    assert (row["status"], row["source_type"], row["origin"]) == (
        "pending",
        "file",
        "web",
    )
    assert row["file_filename"] == "informe.PDF"
    assert bytes(row["file_data"]) == PDF
    assert queue.enqueued == [(analysis_id, EMAIL)]


@pytest.mark.parametrize(
    ("upload", "code"),
    [
        (_Upload("virus.exe", b"MZ"), ErrorCode.INVALID_FILE),
        (_Upload(None, b"texto"), ErrorCode.INVALID_FILE),
        (_Upload("grande.txt", b"x" * (MAX_FILE_BYTES + 1)), ErrorCode.FILE_TOO_LARGE),
        (_Upload("vacio.txt", b""), ErrorCode.INVALID_FILE),
        (_Upload("falso.pdf", b"no soy un pdf"), ErrorCode.INVALID_FILE),
    ],
    ids=["suffix", "no-name", "too-large", "empty", "pdf-signature"],
)
async def test_submit_file_refuses_invalid_uploads_without_writing(
    db_pool, intake, queue, upload, code
):
    with pytest.raises(AnalysisRefused) as refusal:
        await intake.submit_file(WEB, upload)

    assert refusal.value.code == code
    assert await _count(db_pool) == 0
    assert queue.enqueued == []


async def test_submit_file_never_reads_an_upload_declared_too_large(db_pool, intake):
    upload = _Upload("grande.pdf", PDF, size=MAX_FILE_BYTES + 1)

    with pytest.raises(AnalysisRefused) as refusal:
        await intake.submit_file(WEB, upload)

    assert refusal.value.code == ErrorCode.FILE_TOO_LARGE
    assert upload.reads == 0


async def test_submit_file_checks_the_queue_before_the_upload(db_pool):
    intake = AnalysisIntake(None, max_file_bytes=MAX_FILE_BYTES)

    with pytest.raises(AnalysisRefused) as refusal:
        await intake.submit_file(WEB, _Upload("virus.exe", b"MZ"))

    assert refusal.value.code == ErrorCode.SERVICE_UNAVAILABLE


async def test_retry_reopens_a_failed_analysis_and_enqueues_it(db_pool, intake, queue):
    analysis_id = await _failed(db_pool, intake, queue)

    assert await intake.retry(WEB, analysis_id) == analysis_id

    row = await _row(db_pool, analysis_id)
    assert row["status"] == "pending"
    assert (row["error_code"], row["stage"], row["completed_at"]) == (None, None, None)
    # created_at vuelve a NOW(): el reaper concede un periodo de gracia nuevo.
    assert row["fresh"] is True
    assert row["input_text"] == "La lejía cura la COVID"
    assert queue.enqueued[-1] == (analysis_id, EMAIL)


async def test_reanalyze_discards_the_verdict_but_keeps_input_and_share_link(
    db_pool, intake, queue
):
    analysis_id = await _done(db_pool, intake, queue)

    assert await intake.reanalyze(WEB, analysis_id) == analysis_id

    row = await _row(db_pool, analysis_id)
    assert row["status"] == "pending"
    for column in (
        "label",
        "verdict",
        "confidence",
        "evidence_coverage",
        "explanation",
        "claims",
        "sources",
        "pipeline",
        "completed_at",
    ):
        assert row[column] is None, column
    assert row["fresh"] is True
    assert row["input_text"] == "La lejía cura la COVID"
    assert row["share_token"] == "token-publico"
    assert queue.enqueued[-1] == (analysis_id, EMAIL)


@pytest.mark.parametrize(
    ("reopen", "arrange", "code"),
    [
        ("retry", _done, ErrorCode.ANALYSIS_NOT_RETRYABLE),
        ("reanalyze", _failed, ErrorCode.ANALYSIS_NOT_REANALYZABLE),
    ],
)
async def test_reopen_refuses_an_analysis_in_the_wrong_status(
    db_pool, intake, queue, reopen, arrange, code
):
    analysis_id = await arrange(db_pool, intake, queue)
    enqueued = list(queue.enqueued)

    with pytest.raises(AnalysisRefused) as refusal:
        await getattr(intake, reopen)(WEB, analysis_id)

    assert refusal.value.code == code
    assert queue.enqueued == enqueued


@pytest.mark.parametrize(
    ("reopen", "arrange"), [("retry", _failed), ("reanalyze", _done)]
)
async def test_reopen_hides_other_users_analyses(
    db_pool, intake, queue, reopen, arrange
):
    analysis_id = await arrange(db_pool, intake, queue)
    stranger = Submitter(user_id="user-b", origin="web")

    with pytest.raises(AnalysisRefused) as refusal:
        await getattr(intake, reopen)(stranger, analysis_id)

    assert refusal.value.code == ErrorCode.ANALYSIS_NOT_FOUND


@pytest.mark.parametrize(
    ("reopen", "arrange", "code"),
    [
        ("retry", _failed, ErrorCode.ANALYSIS_NOT_RETRYABLE),
        ("reanalyze", _done, ErrorCode.ANALYSIS_NOT_REANALYZABLE),
    ],
)
async def test_reopen_waits_until_the_previous_run_releases_its_job(
    db_pool, intake, queue, reopen, arrange, code
):
    analysis_id = await arrange(db_pool, intake, queue)
    # La Run anterior escribió su estado final pero aún envía el email con el job vivo.
    queue.live.add(analysis_id)
    status_before = (await _row(db_pool, analysis_id))["status"]

    with pytest.raises(AnalysisRefused) as refusal:
        await getattr(intake, reopen)(WEB, analysis_id)

    assert refusal.value.code == code
    assert (await _row(db_pool, analysis_id))["status"] == status_before


@pytest.mark.parametrize(
    ("reopen", "arrange", "marker", "code"),
    [
        ("retry", _failed, "SELECT status, stage", ErrorCode.ANALYSIS_FETCH_FAILED),
        ("retry", _failed, "SET status = 'pending'", ErrorCode.ANALYSIS_RETRY_FAILED),
        ("reanalyze", _done, "SELECT status, stage", ErrorCode.ANALYSIS_FETCH_FAILED),
        (
            "reanalyze",
            _done,
            "SET status = 'pending'",
            ErrorCode.ANALYSIS_REANALYZE_FAILED,
        ),
    ],
)
async def test_reopen_maps_each_database_failure_to_its_contract_code(
    db_pool, db_faults, intake, queue, reopen, arrange, marker, code
):
    analysis_id = await arrange(db_pool, intake, queue)
    db_faults.fail_on(marker)

    with pytest.raises(AnalysisRefused) as refusal:
        await getattr(intake, reopen)(WEB, analysis_id)

    assert refusal.value.code == code


async def test_concurrent_retries_open_a_single_run(db_pool, intake, queue):
    analysis_id = await _failed(db_pool, intake, queue)
    enqueued_before = len(queue.enqueued)

    results = await asyncio.gather(
        intake.retry(WEB, analysis_id),
        intake.retry(WEB, analysis_id),
        return_exceptions=True,
    )

    refusals = [r for r in results if isinstance(r, AnalysisRefused)]
    assert [r.code for r in refusals] == [ErrorCode.ANALYSIS_NOT_RETRYABLE]
    assert len(queue.enqueued) == enqueued_before + 1


async def test_reopen_refuses_without_touching_the_row_when_the_queue_is_down(
    db_pool, intake, queue
):
    analysis_id = await _failed(db_pool, intake, queue)
    queue.down = True

    with pytest.raises(AnalysisRefused) as refusal:
        await intake.retry(WEB, analysis_id)

    assert refusal.value.code == ErrorCode.SERVICE_UNAVAILABLE
    assert (await _row(db_pool, analysis_id))["status"] == "failed"


async def test_reopen_fails_the_row_again_when_enqueueing_fails(db_pool, intake, queue):
    analysis_id = await _done(db_pool, intake, queue)
    queue.fail_enqueue = True

    with pytest.raises(AnalysisRefused) as refusal:
        await intake.reanalyze(WEB, analysis_id)

    assert refusal.value.code == ErrorCode.SERVICE_UNAVAILABLE
    row = await _row(db_pool, analysis_id)
    assert (row["status"], row["error_code"]) == ("failed", "SERVICE_UNAVAILABLE")


PIPELINE = {"provider": "test", "models": {}, "prompts": {"judge": "v0"}}


def _completion(**overrides) -> Completion:
    base: dict = {
        "label": "falsa",
        "confidence": 0.9,
        "explanation": "Sin evidencia.",
        "claims": [{"text": "La lejía cura", "label": "falsa", "confidence": 0.9}],
        "sources": [{"title": "Estudio", "url": "https://doi.org/10.1/x"}],
        "evidence_coverage": 0.5,
        "pipeline": PIPELINE,
    }
    base.update(overrides)
    return Completion(**base)


def _returning(result, seen=None):
    """Trabajo de la Run que anota la Run recibida y devuelve o lanza ``result``."""

    async def work(run):
        if seen is not None:
            seen.append(run)
        if isinstance(result, BaseException):
            raise result
        return result

    return work


@pytest.fixture
def notifier():
    return RecordingNotifier()


@pytest.fixture
def runner(queue, notifier):
    return AnalysisRunner(
        queue=queue,
        notifier=notifier,
        run_timeout_seconds=5,
        stale_after_seconds=300,
    )


async def _submit(intake, request=None) -> str:
    return await intake.submit(
        WEB, request or AnalysisRequest(text="La lejía cura la COVID")
    )


async def _stage(analysis_id: str) -> str | None:
    status = await get_user_analysis_status(user_id=USER, analysis_id=analysis_id)
    assert status is not None
    return status.stage


async def _age(pool, analysis_id: str) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE public.analysis_history "
            "SET created_at = NOW() - interval '1 hour' WHERE id = %s",
            (analysis_id,),
        )


async def test_run_completes_the_analysis_and_notifies_the_submitter(
    db_pool, intake, runner, notifier
):
    analysis_id = await _submit(intake)

    outcome = await runner.run(
        analysis_id, _returning(_completion()), notify_email=EMAIL
    )

    assert outcome == "done"
    row = await _row(db_pool, analysis_id)
    assert (row["status"], row["error_code"]) == ("done", None)
    assert (row["label"], row["verdict"]) == ("falsa", "fake")
    assert (row["confidence"], row["evidence_coverage"]) == (0.9, 0.5)
    assert row["explanation"] == "Sin evidencia."
    assert row["claims"] == [
        {"text": "La lejía cura", "label": "falsa", "confidence": 0.9}
    ]
    assert row["sources"] == [{"title": "Estudio", "url": "https://doi.org/10.1/x"}]
    # El resultado queda atribuido a la configuración con la que arrancó el worker.
    assert row["pipeline"] == PIPELINE
    assert row["completed_at"] is not None
    assert notifier.sent == [(EMAIL, analysis_id, None)]


async def test_run_stores_a_verdict_without_report_or_coverage(db_pool, intake, runner):
    analysis_id = await _submit(intake)

    await runner.run(
        analysis_id,
        _returning(_completion(explanation=None, evidence_coverage=None)),
    )

    row = await _row(db_pool, analysis_id)
    assert (row["status"], row["explanation"]) == ("done", None)
    assert row["evidence_coverage"] is None


@pytest.mark.parametrize(
    ("open_analysis", "expected"),
    [
        (
            lambda intake: _submit(intake),
            TextContent(text="La lejía cura la COVID"),
        ),
        (
            lambda intake: _submit(
                intake,
                AnalysisRequest(
                    url="https://ejemplo.com/noticia", source_type=SourceType.URL
                ),
            ),
            UrlContent(url="https://ejemplo.com/noticia"),
        ),
        (
            lambda intake: intake.submit_file(WEB, _Upload("informe.pdf", PDF)),
            FileContent(data=PDF, filename="informe.pdf"),
        ),
    ],
    ids=["text", "url", "file"],
)
async def test_run_hands_the_work_the_pending_content(
    db_pool, intake, runner, open_analysis, expected
):
    analysis_id = await open_analysis(intake)
    seen: list = []

    await runner.run(analysis_id, _returning(_completion(), seen))

    [run] = seen
    assert run.analysis_id == analysis_id
    assert run.content == expected


async def test_run_shows_preparing_and_then_the_stage_after_each_finished_one(
    db_pool, intake, runner
):
    analysis_id = await _submit(intake)
    stages: list = []

    async def work(run):
        stages.append(await _stage(analysis_id))
        await run.stage_finished("preparing")
        stages.append(await _stage(analysis_id))
        await run.stage_finished("extractor")
        stages.append(await _stage(analysis_id))
        await run.stage_finished("health_expert")
        stages.append(await _stage(analysis_id))
        return _completion()

    await runner.run(analysis_id, work)

    assert stages == ["preparing", "extractor", "translator", "translator"]


async def test_run_keeps_the_extracted_file_text_even_when_it_fails(
    db_pool, intake, runner
):
    analysis_id = await intake.submit_file(WEB, _Upload("informe.pdf", PDF))

    async def work(run):
        await run.keep_input_text("Texto extraído del archivo")
        raise AnalysisFailure(ErrorCode.NO_MEDICAL_CLAIMS)

    await runner.run(analysis_id, work)

    row = await _row(db_pool, analysis_id)
    assert row["status"] == "failed"
    # El historial puede buscar el archivo por su texto aunque la Run fallase.
    assert row["input_text"] == "Texto extraído del archivo"


@pytest.mark.parametrize(
    "code",
    [
        ErrorCode.URL_EXTRACTION,
        ErrorCode.FILE_EXTRACTION,
        ErrorCode.CONNECTION,
        ErrorCode.NO_MEDICAL_CLAIMS,
    ],
)
async def test_run_fails_with_the_reason_the_work_reports(
    db_pool, intake, runner, notifier, code
):
    analysis_id = await _submit(intake)

    outcome = await runner.run(
        analysis_id, _returning(AnalysisFailure(code)), notify_email=EMAIL
    )

    assert outcome == "failed"
    row = await _row(db_pool, analysis_id)
    assert (row["status"], row["error_code"]) == ("failed", code.value)
    assert row["completed_at"] is not None
    assert notifier.sent == [(EMAIL, analysis_id, code)]


async def test_run_fails_as_internal_on_an_unexpected_error(db_pool, intake, runner):
    analysis_id = await _submit(intake)

    outcome = await runner.run(analysis_id, _returning(RuntimeError("grafo roto")))

    assert outcome == "failed"
    assert (await _row(db_pool, analysis_id))["error_code"] == "INTERNAL"


async def test_run_fails_as_service_unavailable_when_it_runs_out_of_time(
    db_pool, intake, queue, notifier
):
    runner = AnalysisRunner(
        queue=queue,
        notifier=notifier,
        run_timeout_seconds=0.05,
        stale_after_seconds=300,
    )
    analysis_id = await _submit(intake)

    async def hanging(run):
        await asyncio.sleep(5)

    outcome = await runner.run(analysis_id, hanging, notify_email=EMAIL)

    assert outcome == "failed"
    assert (await _row(db_pool, analysis_id))["error_code"] == "SERVICE_UNAVAILABLE"
    assert notifier.sent == [(EMAIL, analysis_id, ErrorCode.SERVICE_UNAVAILABLE)]


async def test_a_cancelled_run_leaves_the_analysis_pending_for_the_reaper(
    db_pool, intake, runner, notifier
):
    analysis_id = await _submit(intake)
    started = asyncio.Event()

    async def hanging(run):
        started.set()
        await asyncio.sleep(30)

    task = asyncio.create_task(runner.run(analysis_id, hanging, notify_email=EMAIL))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert (await _row(db_pool, analysis_id))["status"] == "pending"
    assert notifier.sent == []


async def test_run_skips_an_analysis_that_is_no_longer_pending(
    db_pool, intake, queue, runner, notifier
):
    analysis_id = await _failed(db_pool, intake, queue)
    seen: list = []

    outcome = await runner.run(
        analysis_id, _returning(_completion(), seen), notify_email=EMAIL
    )

    assert outcome == "skipped"
    assert seen == []
    assert notifier.sent == []


async def test_run_fails_a_file_analysis_whose_upload_is_gone(db_pool, intake, runner):
    analysis_id = await intake.submit_file(WEB, _Upload("informe.pdf", PDF))
    async with db_pool.connection() as conn:
        await conn.execute(
            "UPDATE public.analysis_history SET file_data = NULL WHERE id = %s",
            (analysis_id,),
        )
    seen: list = []

    outcome = await runner.run(analysis_id, _returning(_completion(), seen))

    assert outcome == "failed"
    assert seen == []
    assert (await _row(db_pool, analysis_id))["error_code"] == "FILE_EXTRACTION"


@pytest.mark.parametrize(
    "result", [_completion(), AnalysisFailure(ErrorCode.CONNECTION)]
)
async def test_a_late_close_is_discarded_without_notifying(
    db_pool, intake, runner, notifier, result
):
    analysis_id = await _submit(intake)

    async def reaped_meanwhile(run):
        # El reaper la dio por huérfana mientras el worker seguía trabajando.
        async with db_pool.connection() as conn:
            await conn.execute(
                "UPDATE public.analysis_history "
                "SET status = 'failed', error_code = 'SERVICE_UNAVAILABLE' WHERE id = %s",
                (analysis_id,),
            )
        return await _returning(result)(run)

    outcome = await runner.run(analysis_id, reaped_meanwhile, notify_email=EMAIL)

    assert outcome == "discarded"
    row = await _row(db_pool, analysis_id)
    assert (row["status"], row["error_code"]) == ("failed", "SERVICE_UNAVAILABLE")
    assert row["label"] is None
    assert notifier.sent == []


async def test_run_without_an_email_notifies_nobody(db_pool, intake, runner, notifier):
    analysis_id = await _submit(intake)

    await runner.run(analysis_id, _returning(_completion()), notify_email=None)

    assert notifier.sent == []


async def test_a_failing_notifier_never_undoes_the_verdict(db_pool, intake, queue):
    runner = AnalysisRunner(
        queue=queue,
        notifier=RecordingNotifier(broken=True),
        run_timeout_seconds=5,
        stale_after_seconds=300,
    )
    analysis_id = await _submit(intake)

    outcome = await runner.run(
        analysis_id, _returning(_completion()), notify_email=EMAIL
    )

    assert outcome == "done"
    assert (await _row(db_pool, analysis_id))["status"] == "done"


async def test_a_stage_that_cannot_be_shown_never_breaks_the_run(
    db_pool, db_faults, intake, runner
):
    analysis_id = await _submit(intake)
    db_faults.fail_on("SET stage")

    async def work(run):
        await run.stage_finished("preparing")
        return _completion()

    assert await runner.run(analysis_id, work) == "done"


@pytest.mark.parametrize(
    ("marker", "completion"),
    [("SET label", _completion()), (None, _completion(confidence=None))],
    ids=["write-fails", "invalid-confidence"],
)
async def test_a_verdict_that_cannot_be_saved_fails_the_run_as_internal(
    db_pool, db_faults, intake, runner, notifier, marker, completion
):
    analysis_id = await _submit(intake)
    if marker:
        db_faults.fail_on(marker)

    outcome = await runner.run(analysis_id, _returning(completion), notify_email=EMAIL)

    assert outcome == "failed"
    row = await _row(db_pool, analysis_id)
    assert (row["status"], row["error_code"]) == ("failed", "INTERNAL")
    assert notifier.sent == [(EMAIL, analysis_id, ErrorCode.INTERNAL)]


async def test_a_failure_that_cannot_be_saved_reaches_arq(
    db_pool, db_faults, intake, runner
):
    analysis_id = await _submit(intake)
    db_faults.fail_on("SET status = 'failed'")

    with pytest.raises(DatabaseError):
        await runner.run(analysis_id, _returning(AnalysisFailure(ErrorCode.CONNECTION)))

    assert (await _row(db_pool, analysis_id))["status"] == "pending"


async def test_a_file_text_that_cannot_be_saved_fails_the_run_as_internal(
    db_pool, db_faults, intake, runner
):
    analysis_id = await intake.submit_file(WEB, _Upload("informe.pdf", PDF))
    db_faults.fail_on("SET input_text")

    async def work(run):
        await run.keep_input_text("Texto extraído del archivo")
        return _completion()

    assert await runner.run(analysis_id, work) == "failed"
    assert (await _row(db_pool, analysis_id))["error_code"] == "INTERNAL"


async def test_reaper_fails_only_orphaned_analyses(db_pool, intake, queue, runner):
    orphaned = await _submit(intake)
    running = await _submit(intake)
    fresh = await _submit(intake)
    for analysis_id in (orphaned, running):
        await _age(db_pool, analysis_id)
    queue.finish(orphaned)
    queue.finish(fresh)

    assert await runner.reap_orphans() == 1

    orphaned_row = await _row(db_pool, orphaned)
    assert (orphaned_row["status"], orphaned_row["error_code"]) == (
        "failed",
        "SERVICE_UNAVAILABLE",
    )
    assert (await _row(db_pool, running))["status"] == "pending"
    assert (await _row(db_pool, fresh))["status"] == "pending"


async def test_reaper_leaves_the_queue_alone_when_nothing_is_stale(
    db_pool, intake, queue, runner
):
    await _submit(intake)
    # Una consulta a la cola fallaría: sin candidatas no debe hacerse.
    queue.down = True

    assert await runner.reap_orphans() == 0


async def test_retry_restarts_the_grace_period_of_the_reaper(
    db_pool, intake, queue, runner
):
    analysis_id = await _failed(db_pool, intake, queue)
    await intake.retry(WEB, analysis_id)
    queue.finish(analysis_id)

    assert await runner.reap_orphans() == 0
    assert (await _row(db_pool, analysis_id))["status"] == "pending"
