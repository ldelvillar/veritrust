"""Pruebas del ciclo de vida de un análisis contra PostgreSQL real, a través de su interfaz."""

import asyncio

import pytest
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.analysis_lifecycle import AnalysisIntake, AnalysisRefused, Submitter
from app.schemas.analysis import AnalysisRequest, SourceType
from app.schemas.errors import ErrorCode
from tests.support.lifecycle import InMemoryAnalysisQueue

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
