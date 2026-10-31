"""Tests of the real SQL of ``app/db/history.py``, the contracts the routes take for granted."""

from datetime import UTC, datetime, timedelta

import pytest

from app.db.history import (
    HiddenAnalysis,
    clear_analysis_share_token,
    delete_all_user_analyses,
    delete_user_analysis,
    get_analysis_file,
    get_pending_analyses_summary,
    get_shared_analysis_by_token,
    get_user_analysis_by_id,
    get_user_analysis_status,
    set_analysis_share_token,
)
from app.db.history_query import search_history
from app.db.pool import DatabaseError
from app.schemas.analysis import AnalysisRequest
from app.schemas.history import HistoryQuery
from tests.db.seed import (
    seed_created_at,
    seed_done,
    seed_failed,
    seed_pending,
    seed_pending_file,
    seed_stage,
)

pytestmark = pytest.mark.db

USER = "user-a"


async def _pending(text: str = "La vitamina C previene el resfriado") -> str:
    return await seed_pending(user_id=USER, request=AnalysisRequest(text=text))


async def test_completed_analysis_round_trips_claims_and_sources(db_pool):
    """The claims and the Sources JSONB come back exactly as the worker stored them."""
    analysis_id = await _pending()
    claims = [
        {
            "text": "Afirmación con eñes y tildes: ñá",
            "label": "falsa",
            "confidence": 0.91,
        }
    ]
    sources = [
        {
            "title": "Vitamin C trial",
            "url": "https://doi.org/10.1/x",
            "source": "BMJ",
            # Every real source (Europe PMC, PubMed, openFDA, CIMA) emits year as str.
            "year": "2021",
            "statements": [
                {"claim_index": 0, "text": "Afirmación", "stance": "contradicts"}
            ],
        }
    ]

    await seed_done(
        analysis_id=analysis_id,
        label="falsa",
        confidence=0.91,
        explanation="Informe médico.",
        claims=claims,
        sources=sources,
        evidence_coverage=0.5,
    )

    record = await get_user_analysis_by_id(
        user_id=USER, analysis_id=analysis_id, visible_since=None
    )
    assert record is not None
    assert record.status == "done"
    assert record.label == "falsa"
    assert record.confidence == pytest.approx(0.91)
    assert record.evidence_coverage == pytest.approx(0.5)
    assert record.error_code is None
    # The JSONB comes back validated as the typed models the frontend consumes.
    assert [(c.text, c.label, c.confidence, c.verdict) for c in record.claims] == [
        ("Afirmación con eñes y tildes: ñá", "falsa", 0.91, "fake")
    ]
    stored_source = record.sources[0]
    assert (stored_source.title, stored_source.url) == (
        "Vitamin C trial",
        "https://doi.org/10.1/x",
    )
    assert (stored_source.source, stored_source.year) == ("BMJ", "2021")
    assert [(s.claim_index, s.text, s.stance) for s in stored_source.statements] == [
        (0, "Afirmación", "contradicts")
    ]


async def test_share_token_issued_only_for_done_rows(db_pool):
    """Sharing needs an own done row, and retrying keeps the same token."""
    analysis_id = await _pending()
    assert await set_analysis_share_token(user_id=USER, analysis_id=analysis_id) is None

    await seed_done(
        analysis_id=analysis_id, label="falsa", confidence=0.9, explanation="Informe."
    )
    assert (
        await set_analysis_share_token(user_id="otro-usuario", analysis_id=analysis_id)
        is None
    )

    token = await set_analysis_share_token(user_id=USER, analysis_id=analysis_id)
    assert token
    # Idempotent, so a second share must not rotate the already published link.
    assert (
        await set_analysis_share_token(user_id=USER, analysis_id=analysis_id) == token
    )

    shared = await get_shared_analysis_by_token(token=token)
    assert shared is not None
    # The owner travels separately so the route decides with their Plan, and the public view does not carry it.
    owner, public = shared
    assert owner == USER
    assert (public.status, public.label) == ("done", "falsa")

    assert await clear_analysis_share_token(user_id=USER, analysis_id=analysis_id)
    assert await get_shared_analysis_by_token(token=token) is None


async def test_readers_hide_analyses_older_than_the_history_window(db_pool):
    """A row older than the window exists but is Pro, so it raises HiddenAnalysis instead of returning None."""
    now = datetime.now(UTC)
    old_id = await seed_pending_file(
        user_id=USER, filename="informe.pdf", data=b"%PDF-1.4 contenido"
    )
    await seed_created_at(analysis_id=old_id, created_at=now - timedelta(days=31))
    floor = now - timedelta(days=30)

    for read in (get_user_analysis_by_id, get_user_analysis_status, get_analysis_file):
        with pytest.raises(HiddenAnalysis):
            await read(user_id=USER, analysis_id=old_id, visible_since=floor)
        assert await read(user_id=USER, analysis_id=old_id, visible_since=None)
        # Someone else's row still does not exist, window or not.
        assert (
            await read(user_id="user-b", analysis_id=old_id, visible_since=floor)
            is None
        )


async def test_status_poll_reads_only_the_owners_status_and_stage(db_pool):
    """The light poll sees the running stage and does not leak other users' rows."""
    analysis_id = await _pending()
    await seed_stage(analysis_id=analysis_id, stage="translator")

    status = await get_user_analysis_status(
        user_id=USER, analysis_id=analysis_id, visible_since=None
    )
    assert (status.status, status.stage) == ("pending", "translator")

    await seed_failed(analysis_id=analysis_id, error_code="CONNECTION")
    failed = await get_user_analysis_status(
        user_id=USER, analysis_id=analysis_id, visible_since=None
    )
    assert failed.status == "failed"

    assert (
        await get_user_analysis_status(
            user_id="user-b", analysis_id=analysis_id, visible_since=None
        )
        is None
    )


async def test_rows_are_isolated_per_user(db_pool):
    analysis_id = await _pending()
    await seed_done(
        analysis_id=analysis_id, label="falsa", confidence=0.9, explanation="Informe."
    )

    assert (
        await get_user_analysis_by_id(
            user_id="user-b", analysis_id=analysis_id, visible_since=None
        )
        is None
    )
    assert await delete_user_analysis(user_id="user-b", analysis_id=analysis_id) is None
    page = await search_history(
        user_id="user-b",
        query=HistoryQuery(),
        page=1,
        page_size=20,
        visible_since=None,
    )
    assert (page.items, page.total) == ([], 0)

    assert await delete_user_analysis(user_id=USER, analysis_id=analysis_id) == "done"


async def test_delete_all_removes_only_own_rows(db_pool):
    """delete_all deletes all the user's rows and leaves other users' alone."""
    await _pending()
    await _pending("El paracetamol reduce la fiebre")
    other_id = await seed_pending(
        user_id="user-b", request=AnalysisRequest(text="Otro usuario")
    )

    deleted = await delete_all_user_analyses(user_id=USER)
    assert deleted.count == 2

    page = await search_history(
        user_id=USER, query=HistoryQuery(), page=1, page_size=20, visible_since=None
    )
    assert (page.items, page.total) == ([], 0)
    assert await get_user_analysis_by_id(
        user_id="user-b", analysis_id=other_id, visible_since=None
    )


async def test_delete_all_returns_zero_when_history_empty(db_pool):
    """With no rows to delete, delete_all returns 0 without error."""
    deleted = await delete_all_user_analyses(user_id="user-sin-actividad")
    assert (deleted.count, deleted.pending_ids) == (0, [])


async def test_delete_all_names_only_the_pending_analyses(db_pool):
    """delete_all points at the pending rows to abort their Runs, not the already closed ones."""
    pending_id = await _pending()
    done_id = await _pending("El paracetamol reduce la fiebre")
    await seed_done(
        analysis_id=done_id, label="falsa", confidence=0.9, explanation=None
    )
    failed_id = await _pending("La lejía cura el resfriado")
    await seed_failed(analysis_id=failed_id, error_code="INTERNAL")

    deleted = await delete_all_user_analyses(user_id=USER)

    assert (deleted.count, deleted.pending_ids) == (3, [pending_id])


async def test_file_bytes_round_trip_exactly(db_pool):
    """The uploaded binary comes back byte for byte in the authenticated download."""
    data = b"%PDF-1.4\x00\xff\x00 binario con nulos"
    analysis_id = await seed_pending_file(
        user_id=USER, filename="informe.pdf", data=data
    )

    # The authenticated download requires the file to belong to the user.
    assert (
        await get_analysis_file(
            user_id="otro-usuario", analysis_id=analysis_id, visible_since=None
        )
        is None
    )
    mine = await get_analysis_file(
        user_id=USER, analysis_id=analysis_id, visible_since=None
    )
    assert mine == (data, "informe.pdf")


async def test_pending_summary_counts_all_and_names_the_newest(db_pool):
    """COUNT(*) OVER () counts every pending row despite the query's LIMIT 1."""
    await _pending("Primera afirmacion medica pendiente")
    await _pending("Segunda afirmacion medica pendiente")
    newest_id = await _pending("Tercera afirmacion medica pendiente")

    summary = await get_pending_analyses_summary(user_id=USER)

    assert summary.count == 3
    assert summary.newest_analysis_id == newest_id


async def test_pending_summary_ignores_finished_rows_and_other_users(db_pool):
    """Only the user's own 'pending' rows count, leaving done, failed and others' out."""
    done_id = await _pending("Afirmacion que termina bien")
    await seed_done(
        analysis_id=done_id,
        label="falsa",
        confidence=0.9,
        explanation="Informe.",
    )
    failed_id = await _pending("Afirmacion que falla")
    await seed_failed(analysis_id=failed_id, error_code="internal_error")
    await seed_pending(
        user_id="user-b", request=AnalysisRequest(text="Pendiente de otro usuario")
    )

    summary = await get_pending_analyses_summary(user_id=USER)

    assert summary.count == 0
    assert summary.newest_analysis_id is None


async def test_origin_rejects_unknown_channels(db_pool):
    """The table's CHECK forbids an Origin other than web or mcp."""
    with pytest.raises(DatabaseError):
        await seed_pending(
            user_id=USER, request=AnalysisRequest(text="Texto de prueba"), origin="api"
        )
