"""Pruebas del SQL real de ``app/db/history.py``: los contratos que las rutas dan por hechos."""

import pytest

from app.db.history import (
    HISTORY_LIST_TEXT_CHARS,
    clear_analysis_share_token,
    count_history_verdict_facets,
    delete_all_user_analyses,
    delete_user_analysis,
    export_user_analysis_history,
    get_analysis_file,
    get_pending_analyses_summary,
    get_shared_analysis_by_token,
    get_user_analysis_by_id,
    get_user_analysis_status,
    list_user_analysis_history,
    set_analysis_share_token,
)
from app.db.pool import DatabaseError
from app.schemas.analysis import AnalysisRequest
from tests.db.seed import (
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
    assert [(s.claim_index, s.text, s.stance) for s in stored_source.statements] == [
        (0, "Afirmación", "contradicts")
    ]


async def test_share_token_issued_only_for_done_rows(db_pool):
    """Compartir exige fila done y propia; reintentarlo conserva el mismo token."""
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


async def test_verdict_filter_and_facets_agree_on_indexed_column(db_pool):
    """El filtro de veredicto y los facets leen la columna indexada con el mismo criterio."""
    for label in ("falsa", "falsa", "verdadera", "incierta"):
        analysis_id = await _pending(f"texto {label}")
        await seed_done(
            analysis_id=analysis_id, label=label, confidence=0.8, explanation="Informe."
        )
    await _pending("sigue en cola")
    failed_id = await _pending("terminó mal")
    await seed_failed(analysis_id=failed_id, error_code="CONNECTION")

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
    await seed_pending(
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


async def test_search_matches_the_file_name(db_pool):
    """Un análisis de archivo se busca por su nombre: es el título que ve el usuario."""
    file_id = await seed_pending_file(
        user_id=USER, filename="bulos-vitamina-d.pdf", data=b"%PDF-1.4 contenido"
    )
    await _pending("Un texto sin relación con el archivo")

    rows, total = await list_user_analysis_history(
        user_id=USER, search_query="VITAMINA-D.PDF"
    )
    assert total == 1
    assert rows[0].analysis_id == file_id


async def test_list_truncates_the_input_text_and_omits_the_report(db_pool):
    """El listado trae la fila que pinta la tabla: título recortado y sin informe."""
    long_text = "La vitamina C previene el resfriado. " * 200
    analysis_id = await seed_pending(
        user_id=USER, request=AnalysisRequest(text=long_text)
    )
    await seed_done(
        analysis_id=analysis_id,
        label="falsa",
        confidence=0.9,
        explanation="Un informe médico largo.",
        claims=[{"text": "Afirmación", "label": "falsa", "confidence": 0.9}],
        sources=[
            {"title": "Estudio", "url": "https://doi.org/10.1/x", "source": "BMJ"}
        ],
        evidence_coverage=0.5,
    )

    rows, total = await list_user_analysis_history(user_id=USER)

    assert total == 1
    row = rows[0]
    assert row.input_text is not None
    assert len(row.input_text) == HISTORY_LIST_TEXT_CHARS
    # El veredicto y la cobertura sí viajan: la tabla los pinta en cada fila.
    assert (row.verdict, row.credibility, row.evidence_coverage) == ("fake", 10, 0.5)
    # El cuerpo del informe no forma parte del ítem de listado.
    assert not hasattr(row, "explanation")
    assert not hasattr(row, "claims")


async def test_export_keeps_the_whole_input_text(db_pool):
    """Exportar es llevarse los datos: el CSV no recorta el texto como sí hace el listado."""
    long_text = "La vitamina C previene el resfriado. " * 200
    analysis_id = await seed_pending(
        user_id=USER, request=AnalysisRequest(text=long_text)
    )
    await seed_done(
        analysis_id=analysis_id, label="falsa", confidence=0.9, explanation="Informe."
    )

    records = await export_user_analysis_history(user_id=USER)

    assert records[0].input_text == long_text.strip()
    assert len(records[0].input_text or "") > HISTORY_LIST_TEXT_CHARS


async def test_list_reports_the_stage_of_a_running_analysis(db_pool):
    """La fila 'en curso' del historial muestra por dónde va el pipeline."""
    analysis_id = await _pending("Un análisis todavía en marcha")
    await seed_stage(analysis_id=analysis_id, stage="investigator")

    rows, _ = await list_user_analysis_history(user_id=USER)

    assert rows[0].stage == "investigator"


async def test_status_poll_reads_only_the_owners_status_and_stage(db_pool):
    """El sondeo ligero ve la etapa en curso y no filtra filas de otro usuario."""
    analysis_id = await _pending()
    await seed_stage(analysis_id=analysis_id, stage="translator")

    status = await get_user_analysis_status(user_id=USER, analysis_id=analysis_id)
    assert (status.status, status.stage) == ("pending", "translator")

    await seed_failed(analysis_id=analysis_id, error_code="CONNECTION")
    failed = await get_user_analysis_status(user_id=USER, analysis_id=analysis_id)
    assert failed.status == "failed"

    assert (
        await get_user_analysis_status(user_id="user-b", analysis_id=analysis_id)
        is None
    )


async def test_search_still_matches_beyond_the_truncated_title(db_pool):
    """El recorte es solo de salida: la búsqueda sigue mirando el texto completo."""
    tail = "cloroquina" + "!"
    analysis_id = await seed_pending(
        user_id=USER,
        request=AnalysisRequest(text=("relleno " * 400) + tail),
    )

    rows, total = await list_user_analysis_history(
        user_id=USER, search_query="CLOROQUINA"
    )

    assert total == 1
    assert rows[0].analysis_id == analysis_id
    # El término buscado cae fuera del título recortado y aun así la fila coincide.
    assert rows[0].input_text is not None and "cloroquina" not in rows[0].input_text


async def test_export_returns_only_finished_rows_of_the_user(db_pool):
    """La exportación saca el veredicto, pero solo de filas propias y terminadas."""
    done_id = await _pending("La vitamina C previene el resfriado")
    await seed_done(
        analysis_id=done_id,
        label="falsa",
        confidence=0.9,
        explanation="Informe.",
        claims=[{"text": "Afirmación", "label": "falsa", "confidence": 0.9}],
        sources=[
            {"title": "Estudio", "url": "https://doi.org/10.1/x", "source": "BMJ"}
        ],
        evidence_coverage=0.5,
    )
    await _pending("sigue en cola")
    failed_id = await _pending("terminó mal")
    await seed_failed(analysis_id=failed_id, error_code="CONNECTION")
    other_id = await seed_pending(
        user_id="user-b", request=AnalysisRequest(text="De otro usuario")
    )
    await seed_done(
        analysis_id=other_id, label="verdadera", confidence=0.7, explanation="Informe."
    )

    records = await export_user_analysis_history(user_id=USER)

    assert [record.analysis_id for record in records] == [done_id]
    record = records[0]
    assert (record.label, record.confidence, record.evidence_coverage) == (
        "falsa",
        0.9,
        0.5,
    )
    # El CSV solo lleva el veredicto de cada fila; el informe no se exporta.
    assert not hasattr(record, "explanation")
    assert not hasattr(record, "claims")
    assert not hasattr(record, "sources")
    # La exportación no selecciona stage: no es una columna del CSV.
    assert record.stage is None


async def test_rows_are_isolated_per_user(db_pool):
    analysis_id = await _pending()
    await seed_done(
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
    other_id = await seed_pending(
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
    """El binario subido vuelve byte a byte en la descarga autenticada."""
    data = b"%PDF-1.4\x00\xff\x00 binario con nulos"
    analysis_id = await seed_pending_file(
        user_id=USER, filename="informe.pdf", data=data
    )

    # La descarga autenticada exige que el archivo sea del propio usuario.
    assert (
        await get_analysis_file(user_id="otro-usuario", analysis_id=analysis_id) is None
    )
    mine = await get_analysis_file(user_id=USER, analysis_id=analysis_id)
    assert mine == (data, "informe.pdf")


async def test_pending_summary_counts_all_and_names_the_newest(db_pool):
    """COUNT(*) OVER () cuenta todas las pendientes pese al LIMIT 1 de la consulta."""
    await _pending("Primera afirmacion medica pendiente")
    await _pending("Segunda afirmacion medica pendiente")
    newest_id = await _pending("Tercera afirmacion medica pendiente")

    summary = await get_pending_analyses_summary(user_id=USER)

    assert summary.count == 3
    assert summary.newest_analysis_id == newest_id


async def test_pending_summary_ignores_finished_rows_and_other_users(db_pool):
    """Solo cuentan las filas 'pending' propias; done/failed y ajenas quedan fuera."""
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
    """El CHECK de la tabla impide canales fuera de web/mcp."""
    with pytest.raises(DatabaseError):
        await seed_pending(
            user_id=USER, request=AnalysisRequest(text="Texto de prueba"), origin="api"
        )
