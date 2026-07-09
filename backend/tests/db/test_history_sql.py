"""Pruebas del SQL real de ``app/db/history.py``: los contratos que las rutas dan por hechos."""

import pytest

from app.db.history import (
    clear_analysis_share_token,
    complete_analysis,
    count_history_verdict_facets,
    create_pending_analysis,
    create_pending_file_analysis,
    delete_all_user_analyses,
    delete_user_analysis,
    fail_analysis,
    fail_stale_pending_analyses,
    get_analysis_file,
    get_file_data_by_id,
    get_shared_analysis_by_token,
    get_user_analysis_by_id,
    list_stale_pending_analysis_ids,
    list_user_analysis_history,
    reset_failed_analysis_to_pending,
    set_analysis_share_token,
)
from app.schemas.analysis import AnalysisRequest

pytestmark = pytest.mark.db

USER = "user-a"


async def _pending(text: str = "La vitamina C previene el resfriado") -> str:
    return await create_pending_analysis(
        user_id=USER, request=AnalysisRequest(text=text)
    )


async def _age_row(pool, analysis_id: str, seconds: int) -> None:
    """Retrocede created_at para simular una fila antigua sin esperar de verdad."""
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE public.analysis_history "
            "SET created_at = NOW() - make_interval(secs => %s) WHERE id = %s",
            (seconds, analysis_id),
        )


async def test_evidence_coverage_persists_none_and_zero(db_pool):
    """Cobertura None (no medible) y 0.0 (medida sin respaldo) se guardan distintas."""
    outage_id = await _pending()
    await complete_analysis(
        analysis_id=outage_id,
        label="falsa",
        confidence=0.9,
        explanation="Informe.",
        evidence_coverage=None,
    )
    outage = await get_user_analysis_by_id(user_id=USER, analysis_id=outage_id)
    assert outage is not None
    assert outage.evidence_coverage is None

    zero_id = await _pending()
    await complete_analysis(
        analysis_id=zero_id,
        label="falsa",
        confidence=0.9,
        explanation="Informe.",
        evidence_coverage=0.0,
    )
    zero = await get_user_analysis_by_id(user_id=USER, analysis_id=zero_id)
    assert zero is not None
    assert zero.evidence_coverage == pytest.approx(0.0)


async def test_completed_analysis_round_trips_claims_and_sources(db_pool):
    """Los claims y las fuentes JSONB vuelven idénticos a como los guardó el worker."""
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
            # Todas las fuentes reales (Europe PMC, PubMed, openFDA, CIMA) emiten year como str.
            "year": "2021",
            "statements": [{"text": "Afirmación", "stance": "contradicts"}],
        }
    ]

    await complete_analysis(
        analysis_id=analysis_id,
        label="falsa",
        confidence=0.91,
        explanation="Informe médico.",
        claims=claims,
        sources=sources,
        evidence_coverage=0.5,
    )

    record = await get_user_analysis_by_id(user_id=USER, analysis_id=analysis_id)
    assert record is not None
    assert record.status == "done"
    assert record.label == "falsa"
    assert record.confidence == pytest.approx(0.91)
    assert record.evidence_coverage == pytest.approx(0.5)
    assert record.error_code is None
    # El JSONB vuelve validado como los modelos tipados que consume el frontend.
    assert [(c.text, c.label, c.confidence, c.verdict) for c in record.claims] == [
        ("Afirmación con eñes y tildes: ñá", "falsa", 0.91, "fake")
    ]
    stored_source = record.sources[0]
    assert (stored_source.title, stored_source.url) == (
        "Vitamin C trial",
        "https://doi.org/10.1/x",
    )
    assert (stored_source.source, stored_source.year) == ("BMJ", "2021")
    assert [(s.text, s.stance) for s in stored_source.statements] == [
        ("Afirmación", "contradicts")
    ]


async def test_reset_failed_analysis_reopens_and_clears_error(db_pool):
    analysis_id = await _pending()
    await fail_analysis(analysis_id=analysis_id, error_code="CONNECTION")

    assert await reset_failed_analysis_to_pending(user_id=USER, analysis_id=analysis_id)

    record = await get_user_analysis_by_id(user_id=USER, analysis_id=analysis_id)
    assert record is not None
    assert record.status == "pending"
    assert record.error_code is None
    assert record.stage is None


async def test_reset_refuses_non_failed_rows_and_foreign_users(db_pool):
    """La guarda de carrera del retry vive en el WHERE: solo filas failed y propias."""
    pending_id = await _pending()
    assert not await reset_failed_analysis_to_pending(
        user_id=USER, analysis_id=pending_id
    )

    await complete_analysis(
        analysis_id=pending_id, label="verdadera", confidence=0.8, explanation="Ok."
    )
    assert not await reset_failed_analysis_to_pending(
        user_id=USER, analysis_id=pending_id
    )

    failed_id = await _pending()
    await fail_analysis(analysis_id=failed_id, error_code="CONNECTION")
    assert not await reset_failed_analysis_to_pending(
        user_id="otro-usuario", analysis_id=failed_id
    )
    record = await get_user_analysis_by_id(user_id=USER, analysis_id=failed_id)
    assert record is not None
    assert record.status == "failed"


async def test_share_token_issued_only_for_done_rows(db_pool):
    """Compartir exige fila done y propia; reintentarlo conserva el mismo token."""
    analysis_id = await _pending()
    assert await set_analysis_share_token(user_id=USER, analysis_id=analysis_id) is None

    await complete_analysis(
        analysis_id=analysis_id, label="falsa", confidence=0.9, explanation="Informe."
    )
    assert (
        await set_analysis_share_token(user_id="otro-usuario", analysis_id=analysis_id)
        is None
    )

    token = await set_analysis_share_token(user_id=USER, analysis_id=analysis_id)
    assert token
    # Idempotente: un segundo share no debe rotar el enlace ya publicado.
    assert (
        await set_analysis_share_token(user_id=USER, analysis_id=analysis_id) == token
    )

    public = await get_shared_analysis_by_token(token=token)
    assert public is not None
    assert public.status == "done"
    assert public.label == "falsa"

    assert await clear_analysis_share_token(user_id=USER, analysis_id=analysis_id)
    assert await get_shared_analysis_by_token(token=token) is None


async def test_reaper_recycles_only_stale_pending_rows(db_pool):
    """El reaper solo toca filas pending más viejas que el umbral, y nada más."""
    stale_pending = await _pending("atascada")
    await _age_row(db_pool, stale_pending, 1000)

    fresh_pending = await _pending("recién encolada")

    old_done = await _pending("terminada hace tiempo")
    await complete_analysis(
        analysis_id=old_done, label="verdadera", confidence=0.8, explanation="Ok."
    )
    await _age_row(db_pool, old_done, 1000)

    old_failed = await _pending("fallida hace tiempo")
    await fail_analysis(analysis_id=old_failed, error_code="URL_EXTRACTION")
    await _age_row(db_pool, old_failed, 1000)

    stale_ids = await list_stale_pending_analysis_ids(older_than_seconds=900)
    assert stale_pending in stale_ids
    assert fresh_pending not in stale_ids
    assert old_done not in stale_ids
    assert old_failed not in stale_ids

    count = await fail_stale_pending_analyses(
        analysis_ids=[stale_pending],
        older_than_seconds=900,
        error_code="SERVICE_UNAVAILABLE",
    )

    assert count == 1
    reaped = await get_user_analysis_by_id(user_id=USER, analysis_id=stale_pending)
    assert (reaped.status, reaped.error_code) == ("failed", "SERVICE_UNAVAILABLE")
    fresh = await get_user_analysis_by_id(user_id=USER, analysis_id=fresh_pending)
    assert fresh.status == "pending"
    done = await get_user_analysis_by_id(user_id=USER, analysis_id=old_done)
    assert done.status == "done"
    failed = await get_user_analysis_by_id(user_id=USER, analysis_id=old_failed)
    assert (failed.status, failed.error_code) == ("failed", "URL_EXTRACTION")


async def test_retry_restarts_the_reaper_grace_period(db_pool):
    """Reabrir un análisis reinicia created_at: el reaper no debe recogerlo al instante."""
    analysis_id = await _pending()
    await fail_analysis(analysis_id=analysis_id, error_code="CONNECTION")
    await _age_row(db_pool, analysis_id, 1000)

    assert await reset_failed_analysis_to_pending(user_id=USER, analysis_id=analysis_id)

    assert await list_stale_pending_analysis_ids(older_than_seconds=900) == []

    # Aun con una candidata leída antes del retry, la re-verificación de edad la protege.
    count = await fail_stale_pending_analyses(
        analysis_ids=[analysis_id],
        older_than_seconds=900,
        error_code="SERVICE_UNAVAILABLE",
    )

    assert count == 0
    record = await get_user_analysis_by_id(user_id=USER, analysis_id=analysis_id)
    assert record.status == "pending"


async def test_verdict_filter_and_facets_agree_on_indexed_column(db_pool):
    """El filtro de veredicto y los facets leen la columna indexada con el mismo criterio."""
    for label in ("falsa", "falsa", "verdadera", "incierta"):
        analysis_id = await _pending(f"texto {label}")
        await complete_analysis(
            analysis_id=analysis_id, label=label, confidence=0.8, explanation="Informe."
        )
    await _pending("sigue en cola")
    failed_id = await _pending("terminó mal")
    await fail_analysis(analysis_id=failed_id, error_code="CONNECTION")

    rows, total = await list_user_analysis_history(user_id=USER, verdict="fake")
    assert total == 2
    assert [row.label for row in rows] == ["falsa", "falsa"]

    facets = await count_history_verdict_facets(user_id=USER)
    assert (facets.total, facets.real, facets.fake, facets.uncertain) == (6, 1, 2, 1)

    failed_rows, failed_total = await list_user_analysis_history(
        user_id=USER, status="failed"
    )
    assert failed_total == 1
    assert failed_rows[0].error_code == "CONNECTION"


async def test_search_matches_text_and_url_case_insensitively(db_pool):
    text_id = await _pending("Las VACUNAS son seguras")
    await create_pending_analysis(
        user_id=USER,
        request=AnalysisRequest(url="https://ejemplo.com/noticia", source_type="url"),
    )

    rows, total = await list_user_analysis_history(user_id=USER, search_query="vacunas")
    assert total == 1
    assert rows[0].analysis_id == text_id

    rows, total = await list_user_analysis_history(
        user_id=USER, search_query="EJEMPLO.COM"
    )
    assert total == 1
    assert rows[0].input_url == "https://ejemplo.com/noticia"


async def test_rows_are_isolated_per_user(db_pool):
    analysis_id = await _pending()
    await complete_analysis(
        analysis_id=analysis_id, label="falsa", confidence=0.9, explanation="Informe."
    )

    assert (
        await get_user_analysis_by_id(user_id="user-b", analysis_id=analysis_id) is None
    )
    assert not await delete_user_analysis(user_id="user-b", analysis_id=analysis_id)
    rows, total = await list_user_analysis_history(user_id="user-b")
    assert (rows, total) == ([], 0)

    assert await delete_user_analysis(user_id=USER, analysis_id=analysis_id)


async def test_delete_all_removes_only_own_rows(db_pool):
    """delete_all borra todas las filas del usuario y respeta las de otros usuarios."""
    await _pending()
    await _pending("El paracetamol reduce la fiebre")
    other_id = await create_pending_analysis(
        user_id="user-b", request=AnalysisRequest(text="Otro usuario")
    )

    assert await delete_all_user_analyses(user_id=USER) == 2

    rows, total = await list_user_analysis_history(user_id=USER)
    assert (rows, total) == ([], 0)
    assert await get_user_analysis_by_id(user_id="user-b", analysis_id=other_id)


async def test_delete_all_returns_zero_when_history_empty(db_pool):
    """Sin filas que borrar, delete_all devuelve 0 sin error."""
    assert await delete_all_user_analyses(user_id="user-sin-actividad") == 0


async def test_file_bytes_round_trip_exactly(db_pool):
    """El binario subido vuelve byte a byte; sin él no hay extracción en el worker."""
    data = b"%PDF-1.4\x00\xff\x00 binario con nulos"
    analysis_id = await create_pending_file_analysis(
        user_id=USER, filename="informe.pdf", data=data
    )

    stored = await get_file_data_by_id(analysis_id=analysis_id)
    assert stored == (data, "informe.pdf")

    # La descarga autenticada exige que el archivo sea del propio usuario.
    assert (
        await get_analysis_file(user_id="otro-usuario", analysis_id=analysis_id) is None
    )
    mine = await get_analysis_file(user_id=USER, analysis_id=analysis_id)
    assert mine == (data, "informe.pdf")
