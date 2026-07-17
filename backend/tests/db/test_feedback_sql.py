"""Pruebas del SQL real de ``app/db/feedback.py``: alta con snapshot y valoración activa."""

import pytest

from app.db.feedback import create_analysis_feedback, get_analysis_feedback
from app.db.history import (
    complete_analysis,
    create_pending_analysis,
    delete_user_analysis,
    fail_analysis,
    reset_done_analysis_to_pending,
)
from app.schemas.analysis import AnalysisRequest

pytestmark = pytest.mark.db

USER = "user-a"


async def _done(label: str = "falsa") -> str:
    analysis_id = await create_pending_analysis(
        user_id=USER, request=AnalysisRequest(text="La vitamina C cura el resfriado")
    )
    await complete_analysis(
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
    """La valoración guarda un snapshot de lo valorado y vuelve tal cual se envió."""
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
    # El snapshot congela el veredicto/label valorados, no los actuales de la fila.
    assert await _feedback_rows(db_pool, analysis_id) == [("fake", "falsa")]


async def test_feedback_allows_single_active_submission(db_pool):
    """La segunda valoración del mismo resultado se filtra en el propio INSERT."""
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
    """Solo se valora una fila done y propia; el resto no inserta ni se lee."""
    pending_id = await create_pending_analysis(
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

    failed_id = await create_pending_analysis(
        user_id=USER, request=AnalysisRequest(text="terminó mal")
    )
    await fail_analysis(analysis_id=failed_id, error_code="CONNECTION")
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
    """Reanalizar reinicia created_at: la valoración vieja queda como dato histórico."""
    analysis_id = await _done(label="falsa")
    assert await create_analysis_feedback(
        user_id=USER,
        analysis_id=analysis_id,
        is_correct=False,
        suggested_verdict="real",
        comment=None,
    )

    assert await reset_done_analysis_to_pending(user_id=USER, analysis_id=analysis_id)
    await complete_analysis(
        analysis_id=analysis_id, label="verdadera", confidence=0.8, explanation="Ok."
    )

    # El nuevo resultado nace sin valoración activa y admite una nueva.
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
    # Ambas generaciones se conservan con su snapshot para el reentrenamiento.
    assert await _feedback_rows(db_pool, analysis_id) == [
        ("fake", "falsa"),
        ("real", "verdadera"),
    ]


async def test_deleting_analysis_cascades_feedback(db_pool):
    """Borrar el análisis arrastra sus valoraciones (ON DELETE CASCADE)."""
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
