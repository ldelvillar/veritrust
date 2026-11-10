"""Tests of the dashboard summary queries on real PostgreSQL."""

from datetime import datetime, timedelta, timezone

import pytest

from app.db.dashboard import get_user_dashboard_summary
from app.schemas.analysis import AnalysisRequest, SourceType
from app.schemas.dashboard import DashboardSummaryResponse
from tests.db.seed import seed_created_at, seed_done, seed_failed, seed_pending

pytestmark = pytest.mark.db

USER = "user-a"
OTHER_USER = "user-b"


async def _pending(
    *, user_id: str = USER, text: str | None = None, url: str | None = None
) -> str:
    request = (
        AnalysisRequest(url=url, source_type=SourceType.URL)
        if url
        else AnalysisRequest(text=text or "La vitamina C previene el resfriado")
    )
    return await seed_pending(user_id=user_id, request=request)


async def _done(
    label: str,
    confidence: float = 0.8,
    *,
    user_id: str = USER,
    text: str | None = None,
    url: str | None = None,
    evidence_coverage: float = 1.0,
    created_at: datetime | None = None,
) -> str:
    analysis_id = await _pending(user_id=user_id, text=text, url=url)
    await seed_done(
        analysis_id=analysis_id,
        label=label,
        confidence=confidence,
        explanation="Informe.",
        evidence_coverage=evidence_coverage,
    )
    if created_at is not None:
        await seed_created_at(analysis_id=analysis_id, created_at=created_at)
    return analysis_id


def _assert_empty(summary: DashboardSummaryResponse) -> None:
    assert summary.kpis.total_analyses == 0
    assert summary.kpis.active_alerts == 0
    assert summary.kpis.average_credibility is None
    assert summary.verdict_distribution.model_dump() == {
        "real": 0,
        "uncertain": 0,
        "mixed": 0,
        "fake": 0,
    }
    assert all(point.total == 0 for point in summary.trend)
    assert summary.source_breakdown == []
    assert summary.domain_breakdown == []
    assert summary.alerts == []


async def test_another_users_analyses_appear_in_no_section(db_pool):
    await _done("falsa", user_id=OTHER_USER, url="https://ajeno.com/bulo")
    await _done("parcialmente falsa", user_id=OTHER_USER, text="Texto de otro usuario")

    _assert_empty(await get_user_dashboard_summary(user_id=USER))


async def test_pending_and_failed_analyses_appear_in_no_section(db_pool):
    await _pending(url="https://encola.com/noticia")
    failed_id = await _pending(url="https://fallido.com/noticia")
    await seed_failed(analysis_id=failed_id, error_code="CONNECTION")

    _assert_empty(await get_user_dashboard_summary(user_id=USER))


async def test_kpis_count_each_verdict_and_average_only_credible_ones(db_pool):
    for index in range(3):
        await _done("verdadera", 0.9, text=f"Texto verdadero {index}")
    for index in range(2):
        await _done("falsa", 0.8, text=f"Texto falso {index}", evidence_coverage=0.5)
    await _done("parcialmente falsa", 0.7, text="Texto mixto", evidence_coverage=0.0)
    await _done("incierta", 0.6, text="Texto incierto", evidence_coverage=0.0)

    summary = await get_user_dashboard_summary(user_id=USER)

    assert summary.verdict_distribution.model_dump() == {
        "real": 3,
        "uncertain": 1,
        "mixed": 1,
        "fake": 2,
    }
    assert summary.kpis.total_analyses == 7
    assert summary.kpis.reliable_rate == 42.9
    assert summary.kpis.active_alerts == 3
    # Mixed and uncertain have no Credibility: (3 * 0.9 + 2 * (1 - 0.8)) / 5.
    assert summary.kpis.average_credibility == 62.0
    # Coverage averages over every Analysis: (3 * 1.0 + 2 * 0.5) / 7.
    assert summary.kpis.average_evidence_coverage == 57.1


async def test_week_over_week_compares_the_last_seven_days_with_the_seven_before(
    db_pool,
):
    now = datetime.now(timezone.utc)
    for index, days_ago in enumerate((0, 2, 6, 8, 13, 20)):
        await _done(
            "verdadera",
            text=f"Texto de hace {days_ago} días {index}",
            created_at=now - timedelta(days=days_ago, hours=1),
        )

    summary = await get_user_dashboard_summary(user_id=USER)

    assert summary.kpis.total_analyses == 6
    # Three this week against two the week before.
    assert summary.kpis.week_over_week_delta == 50.0


async def test_trend_is_a_contiguous_daily_series_ending_today(db_pool):
    today = datetime.now(timezone.utc).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    await _done("verdadera", 0.9, text="Texto de hoy uno", created_at=today)
    await _done("falsa", 0.9, text="Texto de hoy dos", created_at=today)
    await _done("incierta", text="Hace tres días", created_at=today - timedelta(days=3))
    await _done(
        "verdadera", text="Fuera de la ventana", created_at=today - timedelta(days=10)
    )

    summary = await get_user_dashboard_summary(user_id=USER, trend_days=7)

    expected_days = [
        (today - timedelta(days=offset)).date().isoformat()
        for offset in range(6, -1, -1)
    ]
    assert [point.date for point in summary.trend] == expected_days
    by_day = {point.date: point for point in summary.trend}
    assert [point.total for point in summary.trend] == [0, 0, 0, 1, 0, 0, 2]
    # Today averages 0.9 and 1 - 0.9; the uncertain day has no Credibility.
    assert by_day[expected_days[-1]].average_credibility == 50.0
    assert by_day[expected_days[3]].average_credibility is None


async def test_breakdowns_group_by_content_type_and_by_the_five_busiest_hosts(db_pool):
    urls = [
        "https://a.com/1",
        "https://a.com/2",
        "https://a.com/3",
        "https://b.com/1",
        "https://b.com/2",
        "https://c.com/1",
        "https://d.com/1",
        "https://e.com/1",
        "https://f.com/1",
    ]
    for url in urls:
        await _done("verdadera", 0.8, url=url)
    await _done("falsa", 0.9, text="Texto pegado por el usuario")

    summary = await get_user_dashboard_summary(user_id=USER)

    assert [item.model_dump() for item in summary.source_breakdown] == [
        {"source_type": "url", "total": 9, "average_credibility": 80.0},
        {"source_type": "text", "total": 1, "average_credibility": 10.0},
    ]
    domains = summary.domain_breakdown
    assert len(domains) == 5
    assert [(item.domain, item.total) for item in domains[:2]] == [
        ("a.com", 3),
        ("b.com", 2),
    ]
    assert {item.domain for item in domains[2:]} < {"c.com", "d.com", "e.com", "f.com"}
    assert all(item.average_credibility == 80.0 for item in domains)


async def test_alerts_are_the_five_newest_fake_or_mixed_analyses(db_pool):
    now = datetime.now(timezone.utc)
    alert_ids = []
    for hours_ago in range(7):
        label = "falsa" if hours_ago % 2 else "parcialmente falsa"
        alert_ids.append(
            await _done(
                label,
                0.7,
                text=f"Alerta de hace {hours_ago} horas",
                created_at=now - timedelta(hours=hours_ago + 1),
            )
        )
    await _done("verdadera", text="Verdadero más reciente", created_at=now)
    await _done("incierta", text="Incierto más reciente", created_at=now)

    summary = await get_user_dashboard_summary(user_id=USER)

    assert [alert.id for alert in summary.alerts] == alert_ids[:5]
    assert [alert.label for alert in summary.alerts] == [
        "parcialmente falsa",
        "falsa",
        "parcialmente falsa",
        "falsa",
        "parcialmente falsa",
    ]
    assert summary.alerts[1].input_text == "Alerta de hace 1 horas"
    assert summary.alerts[1].source_type == "text"
    assert summary.alerts[1].confidence == 0.7
