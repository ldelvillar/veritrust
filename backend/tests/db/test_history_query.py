"""Pruebas del History query sobre PostgreSQL real: página, total, facet y exportación."""

from datetime import datetime, timedelta, timezone

import pytest

from app.db.history_query import (
    HISTORY_LIST_TEXT_CHARS,
    HistoryPage,
    export_history,
    search_history,
)
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


async def _done(text: str, label: str, confidence: float = 0.8) -> str:
    analysis_id = await _pending(text)
    await seed_done(
        analysis_id=analysis_id,
        label=label,
        confidence=confidence,
        explanation="Informe.",
    )
    return analysis_id


async def _failed(text: str) -> str:
    analysis_id = await _pending(text)
    await seed_failed(analysis_id=analysis_id, error_code="CONNECTION")
    return analysis_id


async def _search(page: int = 1, page_size: int = 100, **filters) -> HistoryPage:
    return await search_history(
        user_id=USER, query=HistoryQuery(**filters), page=page, page_size=page_size
    )


async def _seed_mixed_history() -> None:
    """Dos falsas, una verdadera y una incierta terminadas, más una en curso y una fallida."""
    await _done("Texto uno que resulta falso", "falsa")
    await _done("Texto dos que resulta falso", "falsa")
    await _done("Texto que resulta verdadero", "verdadera")
    await _done("Texto que queda incierto", "incierta")
    await _pending("Texto que sigue en cola")
    await _failed("Texto que terminó mal")


async def test_the_verdict_facet_keeps_the_status_filter(db_pool):
    """Con «Fallido» elegido, cada tarjeta cuenta las filas que mostraría al pulsarla."""
    await _seed_mixed_history()

    page = await _search(status="failed")

    assert page.total == 1
    assert page.verdict_counts.model_dump() == {
        "total": 1,
        "real": 0,
        "fake": 0,
        "uncertain": 0,
    }


@pytest.mark.parametrize(
    ("verdict", "expected_total"),
    [("all", 6), ("real", 1), ("fake", 2), ("uncertain", 1)],
)
async def test_the_total_is_the_facet_cell_of_the_verdict_filter(
    db_pool, verdict, expected_total
):
    """El total no se cuenta aparte: es la celda del facet que el filtro de veredicto elige."""
    await _seed_mixed_history()

    page = await _search(verdict=verdict)

    assert page.total == len(page.items) == expected_total
    assert page.verdict_counts.model_dump() == {
        "total": 6,
        "real": 1,
        "fake": 2,
        "uncertain": 1,
    }


async def test_the_verdict_filter_reads_the_indexed_column(db_pool):
    await _seed_mixed_history()

    page = await _search(verdict="fake")

    assert [item.label for item in page.items] == ["falsa", "falsa"]


async def test_export_keeps_the_status_filter_and_only_done_rows(db_pool):
    """La exportación es la consulta del historial restringida a análisis done."""
    await _seed_mixed_history()

    assert await export_history(user_id=USER, query=HistoryQuery(status="failed")) == []
    assert (
        await export_history(user_id=USER, query=HistoryQuery(status="pending")) == []
    )
    done = await export_history(user_id=USER, query=HistoryQuery(status="done"))
    assert len(done) == 4
    fake = await export_history(user_id=USER, query=HistoryQuery(verdict="fake"))
    assert [record.label for record in fake] == ["falsa", "falsa"]


async def test_search_matches_only_what_the_row_shows_as_its_title(db_pool):
    """Las palabras guardadas del veredicto y del tipo no coinciden: no se ven en pantalla."""
    await _done("La vitamina C previene el resfriado", "falsa")
    await seed_pending(
        user_id=USER,
        request=AnalysisRequest(url="https://ejemplo.com/nota", source_type="url"),
    )

    assert (await _search(search="falsa")).total == 0
    assert (await _search(search="url")).total == 0
    assert (await _search(search="VITAMINA")).total == 1


async def test_search_matches_text_and_url_case_insensitively(db_pool):
    text_id = await _pending("Las VACUNAS son seguras")
    await seed_pending(
        user_id=USER,
        request=AnalysisRequest(url="https://ejemplo.com/noticia", source_type="url"),
    )

    page = await _search(search="vacunas")
    assert page.total == 1
    assert page.items[0].analysis_id == text_id

    page = await _search(search="EJEMPLO.COM")
    assert page.total == 1
    assert page.items[0].input_url == "https://ejemplo.com/noticia"


async def test_search_matches_the_file_name(db_pool):
    """Un análisis de archivo se busca por su nombre: es el título que ve el usuario."""
    file_id = await seed_pending_file(
        user_id=USER, filename="bulos-vitamina-d.pdf", data=b"%PDF-1.4 contenido"
    )
    await _pending("Un texto sin relación con el archivo")

    page = await _search(search="VITAMINA-D.PDF")

    assert page.total == 1
    assert page.items[0].analysis_id == file_id


async def test_a_blank_search_matches_everything(db_pool):
    await _pending("Primera afirmación médica")
    await _pending("Segunda afirmación médica")

    assert (await _search(search="   ")).total == 2


async def test_search_still_matches_beyond_the_truncated_title(db_pool):
    """El recorte es solo de salida: la búsqueda sigue mirando el texto completo."""
    tail = "cloroquina" + "!"
    analysis_id = await _pending(("relleno " * 400) + tail)

    page = await _search(search="CLOROQUINA")

    assert page.total == 1
    assert page.items[0].analysis_id == analysis_id
    # El término buscado cae fuera del título recortado y aun así la fila coincide.
    title = page.items[0].input_text
    assert title is not None and "cloroquina" not in title


async def test_the_content_type_filter_keeps_only_that_type(db_pool):
    await _pending("Un texto pegado por el usuario")
    await seed_pending(
        user_id=USER,
        request=AnalysisRequest(url="https://ejemplo.com/nota", source_type="url"),
    )
    file_id = await seed_pending_file(
        user_id=USER, filename="informe.pdf", data=b"%PDF-1.4 contenido"
    )

    page = await _search(source_type="file")

    assert [item.analysis_id for item in page.items] == [file_id]
    assert page.verdict_counts.total == 1


async def test_the_date_range_leaves_out_older_analyses(db_pool):
    """El rango de fechas filtra la página, el facet y la exportación por igual."""
    recent_id = await _done("Un análisis de esta semana", "falsa")
    old_id = await _done("Un análisis de hace diez días", "falsa")
    await seed_created_at(
        analysis_id=old_id, created_at=datetime.now(timezone.utc) - timedelta(days=10)
    )

    week = await _search(date_range="7d")
    assert [item.analysis_id for item in week.items] == [recent_id]
    assert week.verdict_counts.fake == 1
    exported = await export_history(user_id=USER, query=HistoryQuery(date_range="7d"))
    assert [record.analysis_id for record in exported] == [recent_id]

    assert (await _search(date_range="30d")).total == 2
    assert (await _search(date_range="all")).total == 2


@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        ("recent", ["pending", "uncertain", "real_60", "real_80", "fake_10"]),
        ("oldest", ["fake_10", "real_80", "real_60", "uncertain", "pending"]),
        # Sin credibilidad (incierto, en curso) va al final, y entre ellos el más reciente.
        ("credibility_high", ["real_80", "real_60", "fake_10", "pending", "uncertain"]),
        ("credibility_low", ["fake_10", "real_60", "real_80", "pending", "uncertain"]),
    ],
)
async def test_each_sort_orders_the_page_and_the_export(db_pool, sort, expected):
    now = datetime.now(timezone.utc)
    ids = {
        "fake_10": await _done("Falso con credibilidad diez", "falsa", 0.9),
        "real_80": await _done("Verdadero con credibilidad ochenta", "verdadera", 0.8),
        "real_60": await _done("Verdadero con credibilidad sesenta", "verdadera", 0.6),
        "uncertain": await _done("Incierto sin credibilidad", "incierta", 0.5),
        "pending": await _pending("En curso sin credibilidad"),
    }
    for days_ago, name in enumerate(reversed(list(ids)), start=1):
        await seed_created_at(
            analysis_id=ids[name], created_at=now - timedelta(days=days_ago)
        )
    names = {analysis_id: name for name, analysis_id in ids.items()}

    page = await _search(sort=sort)
    exported = await export_history(user_id=USER, query=HistoryQuery(sort=sort))

    assert [names[item.analysis_id] for item in page.items] == expected
    # La exportación solo lleva filas done, en el mismo orden.
    assert [names[record.analysis_id] for record in exported] == [
        name for name in expected if name != "pending"
    ]


async def test_pages_share_the_total(db_pool):
    for number in range(3):
        await _pending(f"Afirmación médica número {number}")

    first = await _search(page=1, page_size=2)
    second = await _search(page=2, page_size=2)

    assert (len(first.items), first.total) == (2, 3)
    assert (len(second.items), second.total) == (1, 3)
    assert not {item.analysis_id for item in first.items} & {
        item.analysis_id for item in second.items
    }


async def test_other_users_rows_never_appear(db_pool):
    await _done("Un análisis propio", "falsa")
    other_id = await seed_pending(
        user_id="user-b", request=AnalysisRequest(text="De otro usuario")
    )
    await seed_done(
        analysis_id=other_id, label="verdadera", confidence=0.7, explanation="Informe."
    )

    page = await _search()
    exported = await export_history(user_id=USER, query=HistoryQuery())

    assert page.total == page.verdict_counts.total == 1
    assert other_id not in {item.analysis_id for item in page.items}
    assert other_id not in {record.analysis_id for record in exported}


async def test_list_truncates_the_input_text_and_omits_the_report(db_pool):
    """El listado trae la fila que pinta la tabla: título recortado y sin informe."""
    long_text = "La vitamina C previene el resfriado. " * 200
    analysis_id = await _pending(long_text)
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

    page = await _search()

    assert page.total == 1
    row = page.items[0]
    assert row.input_text is not None
    assert len(row.input_text) == HISTORY_LIST_TEXT_CHARS
    # El veredicto y la cobertura sí viajan: la tabla los pinta en cada fila.
    assert (row.verdict, row.credibility, row.evidence_coverage) == ("fake", 10, 0.5)
    # El cuerpo del informe no forma parte del ítem de listado.
    assert not hasattr(row, "explanation")
    assert not hasattr(row, "claims")


async def test_list_reports_the_stage_of_a_running_analysis(db_pool):
    """La fila 'en curso' del historial muestra por dónde va el pipeline."""
    analysis_id = await _pending("Un análisis todavía en marcha")
    await seed_stage(analysis_id=analysis_id, stage="investigator")

    page = await _search()

    assert page.items[0].stage == "investigator"


async def test_export_keeps_the_whole_input_text(db_pool):
    """Exportar es llevarse los datos: el CSV no recorta el texto como sí hace el listado."""
    long_text = "La vitamina C previene el resfriado. " * 200
    await _done(long_text, "falsa", 0.9)

    records = await export_history(user_id=USER, query=HistoryQuery())

    assert records[0].input_text == long_text.strip()
    assert len(records[0].input_text or "") > HISTORY_LIST_TEXT_CHARS


async def test_export_carries_the_verdict_but_not_the_report(db_pool):
    """El CSV solo lleva el veredicto de cada fila; el informe no se exporta."""
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

    records = await export_history(user_id=USER, query=HistoryQuery())

    assert [record.analysis_id for record in records] == [done_id]
    record = records[0]
    assert (record.label, record.confidence, record.evidence_coverage) == (
        "falsa",
        0.9,
        0.5,
    )
    assert not hasattr(record, "explanation")
    assert not hasattr(record, "claims")
    assert not hasattr(record, "sources")
    # La exportación no selecciona stage: no es una columna del CSV.
    assert record.stage is None
