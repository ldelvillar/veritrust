"""Tests of the real SQL of ``app/db/feedback.py``: creation with snapshot and active feedback."""

import pytest

from app.db.feedback import create_analysis_feedback, get_analysis_feedback
from app.db.history import (
    delete_user_analysis,
)
from app.schemas.analysis import AnalysisRequest
from tests.db.seed import (
    seed_done,
    seed_failed,
    seed_pending,
    seed_reopened_done,
)

pytestmark = pytest.mark.db

USER = "user-a"


async def _done(label: str = "falsa") -> str:
    analysis_id = await seed_pending(
        user_id=USER, request=AnalysisRequest(text="La vitamina C cura el resfriado")
    )
    await seed_done(
        analysis_id=analysis_id, label=label, confidence=0.9, explanation="Informe."
    )
    return analysis_id


async def _feedback_rows(pool, analysis_id: str) -> list:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT verdict_snapshot, label_snapshot FROM public.analysis_feedback "
            "WHERE analysis_id = %s ORDER BY created_at",
            (analysis_id,),
        )
        return await cur.fetchall()


async def test_feedback_round_trips_with_verdict_snapshot(db_pool):
    """Feedback stores a snapshot of what was rated and comes back as sent."""
    analysis_id = await _done(label="falsa")

    saved = await create_analysis_feedback(
        user_id=USER,
        analysis_id=analysis_id,
        is_correct=False,
        suggested_verdict="real",
        comment="La fuente citada desmiente la afirmación.",
    )

    assert saved is not None
    assert saved.is_correct is False
    assert saved.suggested_verdict == "real"
    assert saved.comment == "La fuente citada desmiente la afirmación."

    active = await get_analysis_feedback(user_id=USER, analysis_id=analysis_id)
    assert active is not None
    assert (active.is_correct, active.suggested_verdict, active.comment) == (
        False,
        "real",
        "La fuente citada desmiente la afirmación.",
    )
    # The snapshot freezes the rated Verdict and label, not the row's current ones.
    assert await _feedback_rows(db_pool, analysis_id) == [("fake", "falsa")]


async def test_feedback_allows_single_active_submission(db_pool):
    """The second feedback on the same result is filtered in the INSERT itself."""
    analysis_id = await _done()

    first = await create_analysis_feedback(
        user_id=USER,
        analysis_id=analysis_id,
        is_correct=True,
        suggested_verdict=None,
        comment=None,
    )
    assert first is not None

    duplicate = await create_analysis_feedback(
        user_id=USER,
        analysis_id=analysis_id,
        is_correct=False,
        suggested_verdict="real",
        comment=None,
    )
    assert duplicate is None

    active = await get_analysis_feedback(user_id=USER, analysis_id=analysis_id)
    assert active is not None
    assert active.is_correct is True


async def test_feedback_requires_done_own_row(db_pool):
    """Only an own done row can be rated, and the rest neither inserts nor reads."""
    pending_id = await seed_pending(
        user_id=USER, request=AnalysisRequest(text="sigue en cola")
    )
    assert (
        await create_analysis_feedback(
            user_id=USER,
            analysis_id=pending_id,
            is_correct=True,
            suggested_verdict=None,
            comment=None,
        )
        is None
    )

    failed_id = await seed_pending(
        user_id=USER, request=AnalysisRequest(text="terminó mal")
    )
    await seed_failed(analysis_id=failed_id, error_code="CONNECTION")
    assert (
        await create_analysis_feedback(
            user_id=USER,
            analysis_id=failed_id,
            is_correct=True,
            suggested_verdict=None,
            comment=None,
        )
        is None
    )

    done_id = await _done()
    assert (
        await create_analysis_feedback(
            user_id="otro-usuario",
            analysis_id=done_id,
            is_correct=True,
            suggested_verdict=None,
            comment=None,
        )
        is None
    )

    assert (
        await create_analysis_feedback(
            user_id=USER,
            analysis_id=done_id,
            is_correct=True,
            suggested_verdict=None,
            comment=None,
        )
        is not None
    )
    assert (
        await get_analysis_feedback(user_id="otro-usuario", analysis_id=done_id) is None
    )


async def test_reanalysis_deactivates_previous_feedback(db_pool):
    """Reanalyzing restarts created_at, leaving the old feedback as historical data."""
    analysis_id = await _done(label="falsa")
    assert await create_analysis_feedback(
        user_id=USER,
        analysis_id=analysis_id,
        is_correct=False,
        suggested_verdict="real",
        comment=None,
    )

    assert await seed_reopened_done(user_id=USER, analysis_id=analysis_id)
    await seed_done(
        analysis_id=analysis_id, label="verdadera", confidence=0.8, explanation="Ok."
    )

    # The new result starts without active feedback and accepts a new one.
    assert await get_analysis_feedback(user_id=USER, analysis_id=analysis_id) is None
    fresh = await create_analysis_feedback(
        user_id=USER,
        analysis_id=analysis_id,
        is_correct=True,
        suggested_verdict=None,
        comment=None,
    )
    assert fresh is not None

    active = await get_analysis_feedback(user_id=USER, analysis_id=analysis_id)
    assert active is not None
    assert active.is_correct is True
    # Both generations are kept with their snapshot for retraining.
    assert await _feedback_rows(db_pool, analysis_id) == [
        ("fake", "falsa"),
        ("real", "verdadera"),
    ]


async def test_feedback_keeps_the_pipeline_it_rated_across_reanalysis(db_pool):
    """Feedback keeps the rated configuration even when the row is reanalyzed with another."""
    v1 = {"provider": "ollama", "models": {}, "prompts": {"judge": "v3"}}
    v2 = {"provider": "ollama", "models": {}, "prompts": {"judge": "v4"}}
    analysis_id = await seed_pending(
        user_id=USER, request=AnalysisRequest(text="La vitamina C cura el resfriado")
    )
    await seed_done(
        analysis_id=analysis_id,
        label="falsa",
        confidence=0.9,
        explanation="Informe.",
        pipeline=v1,
    )
    assert await create_analysis_feedback(
        user_id=USER,
        analysis_id=analysis_id,
        is_correct=False,
        suggested_verdict="real",
        comment=None,
    )

    assert await seed_reopened_done(user_id=USER, analysis_id=analysis_id)
    await seed_done(
        analysis_id=analysis_id,
        label="verdadera",
        confidence=0.8,
        explanation="Ok.",
        pipeline=v2,
    )
    assert await create_analysis_feedback(
        user_id=USER,
        analysis_id=analysis_id,
        is_correct=True,
        suggested_verdict=None,
        comment=None,
    )

    async with db_pool.connection() as conn:
        cur = await conn.execute(
            "SELECT pipeline_snapshot FROM public.analysis_feedback "
            "WHERE analysis_id = %s ORDER BY created_at",
            (analysis_id,),
        )
        snapshots = [row[0] for row in await cur.fetchall()]
    assert snapshots == [v1, v2]


async def test_deleting_analysis_cascades_feedback(db_pool):
    """Deleting the Analysis takes its feedback along (ON DELETE CASCADE)."""
    analysis_id = await _done()
    assert await create_analysis_feedback(
        user_id=USER,
        analysis_id=analysis_id,
        is_correct=True,
        suggested_verdict=None,
        comment=None,
    )

    assert await delete_user_analysis(user_id=USER, analysis_id=analysis_id)

    assert await _feedback_rows(db_pool, analysis_id) == []
