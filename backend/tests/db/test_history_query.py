"""Tests of the History query on real PostgreSQL: page, total, Facet and Export."""

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


async def _search(
    page: int = 1,
    page_size: int = 100,
    visible_since: datetime | None = None,
    **filters,
) -> HistoryPage:
    return await search_history(
        user_id=USER,
        query=HistoryQuery(**filters),
        page=page,
        page_size=page_size,
        visible_since=visible_since,
    )


async def _export(visible_since: datetime | None = None, **filters):
    return await export_history(
        user_id=USER, query=HistoryQuery(**filters), visible_since=visible_since
    )


async def _seed_mixed_history() -> None:
    """Two false, one partly false, one true and one uncertain finished, plus one pending and one failed."""
    await _done("Texto uno que resulta falso", "falsa")
    await _done("Texto dos que resulta falso", "falsa")
    await _done("Texto que mezcla lo falso con lo cierto", "parcialmente falsa")
    await _done("Texto que resulta verdadero", "verdadera")
    await _done("Texto que queda incierto", "incierta")
    await _pending("Texto que sigue en cola")
    await _failed("Texto que terminó mal")


async def test_the_verdict_facet_keeps_the_status_filter(db_pool):
    """With «Fallido» chosen, each card counts the rows it would show when clicked."""
    await _seed_mixed_history()

    page = await _search(status="failed")

    assert page.total == 1
    assert page.verdict_counts.model_dump() == {
        "total": 1,
        "real": 0,
        "fake": 0,
        "mixed": 0,
        "uncertain": 0,
    }


@pytest.mark.parametrize(
    ("verdict", "expected_total"),
    [("all", 7), ("real", 1), ("fake", 2), ("mixed", 1), ("uncertain", 1)],
)
async def test_the_total_is_the_facet_cell_of_the_verdict_filter(
    db_pool, verdict, expected_total
):
    """The total is not counted separately but is the Facet cell the Verdict filter picks."""
    await _seed_mixed_history()

    page = await _search(verdict=verdict)

    assert page.total == len(page.items) == expected_total
    assert page.verdict_counts.model_dump() == {
        "total": 7,
        "real": 1,
        "fake": 2,
        "mixed": 1,
        "uncertain": 1,
    }


async def test_the_verdict_filter_reads_the_indexed_column(db_pool):
    await _seed_mixed_history()

    page = await _search(verdict="fake")

    assert [item.label for item in page.items] == ["falsa", "falsa"]


async def test_export_keeps_the_status_filter_and_only_done_rows(db_pool):
    """The Export is the History query restricted to done analyses."""
    await _seed_mixed_history()

    assert await _export(status="failed") == []
    assert await _export(status="pending") == []
    done = await _export(status="done")
    assert len(done) == 5
    fake = await _export(verdict="fake")
    assert [record.label for record in fake] == ["falsa", "falsa"]


async def test_search_matches_only_what_the_row_shows_as_its_title(db_pool):
    """The stored words of the Verdict and type do not match, since they are not shown on screen."""
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
    """A file Analysis is searched by its name, the title the user sees."""
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
    """The trim is output only, so the search still looks at the full text."""
    tail = "cloroquina" + "!"
    analysis_id = await _pending(("relleno " * 400) + tail)

    page = await _search(search="CLOROQUINA")

    assert page.total == 1
    assert page.items[0].analysis_id == analysis_id
    # The search term falls outside the trimmed title and the row still matches.
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
    """The date range filters the page, the Facet and the Export alike."""
    recent_id = await _done("Un análisis de esta semana", "falsa")
    old_id = await _done("Un análisis de hace diez días", "falsa")
    await seed_created_at(
        analysis_id=old_id, created_at=datetime.now(timezone.utc) - timedelta(days=10)
    )

    week = await _search(date_range="7d")
    assert [item.analysis_id for item in week.items] == [recent_id]
    assert week.verdict_counts.fake == 1
    exported = await _export(date_range="7d")
    assert [record.analysis_id for record in exported] == [recent_id]

    assert (await _search(date_range="30d")).total == 2
    assert (await _search(date_range="all")).total == 2


async def test_the_history_window_hides_older_analyses_everywhere(db_pool):
    """The window filters the page, the Facet and the Export, and adds to the filters."""
    now = datetime.now(timezone.utc)
    recent_id = await _done("Un análisis de hace diez días", "falsa")
    old_id = await _done("Un análisis de hace cuarenta días", "verdadera")
    await seed_created_at(analysis_id=recent_id, created_at=now - timedelta(days=10))
    await seed_created_at(analysis_id=old_id, created_at=now - timedelta(days=40))
    floor = now - timedelta(days=30)

    page = await _search(visible_since=floor)
    assert [item.analysis_id for item in page.items] == [recent_id]
    assert (page.total, page.verdict_counts.total, page.verdict_counts.real) == (
        1,
        1,
        0,
    )
    exported = await _export(visible_since=floor)
    assert [record.analysis_id for record in exported] == [recent_id]
    assert (await _search(visible_since=floor, verdict="real")).total == 0

    assert (await _search()).total == 2


@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        ("recent", ["pending", "uncertain", "real_60", "real_80", "fake_10"]),
        ("oldest", ["fake_10", "real_80", "real_60", "uncertain", "pending"]),
        # Without Credibility (uncertain, pending) goes last, and among them the newest first.
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
    exported = await _export(sort=sort)

    assert [names[item.analysis_id] for item in page.items] == expected
    # The Export only carries done rows, in the same order.
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
    exported = await _export()

    assert page.total == page.verdict_counts.total == 1
    assert other_id not in {item.analysis_id for item in page.items}
    assert other_id not in {record.analysis_id for record in exported}


async def test_list_truncates_the_input_text_and_omits_the_report(db_pool):
    """The list brings the row the table draws, a trimmed title and no report."""
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
    # The Verdict and coverage do travel, since the table draws them on each row.
    assert (row.verdict, row.credibility, row.evidence_coverage) == ("fake", 10, 0.5)
    assert not hasattr(row, "explanation")
    assert not hasattr(row, "claims")


async def test_list_reports_the_stage_of_a_running_analysis(db_pool):
    """The History's pending row shows how far the pipeline has got."""
    analysis_id = await _pending("Un análisis todavía en marcha")
    await seed_stage(analysis_id=analysis_id, stage="investigator")

    page = await _search()

    assert page.items[0].stage == "investigator"


async def test_export_keeps_the_whole_input_text(db_pool):
    """Exporting means taking the data away, so the CSV does not trim the text as the list does."""
    long_text = "La vitamina C previene el resfriado. " * 200
    await _done(long_text, "falsa", 0.9)

    records = await _export()

    assert records[0].input_text == long_text.strip()
    assert len(records[0].input_text or "") > HISTORY_LIST_TEXT_CHARS


async def test_export_carries_the_verdict_but_not_the_report(db_pool):
    """The CSV only carries each row's Verdict, and the report is not exported."""
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

    records = await _export()

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
    # The Export does not select stage, which is not a CSV column.
    assert record.stage is None
