"""La credibilidad que ordena y agrega el SQL es la misma que publica ``credibility_of``."""

import pytest

from app.core.verdict import CREDIBILITY_SQL, credibility_of, kind_of
from app.schemas.analysis import AnalysisRequest
from tests.db.seed import seed_done, seed_pending

pytestmark = pytest.mark.db

USER = "user-a"


async def _analysis(text: str) -> str:
    return await seed_pending(user_id=USER, request=AnalysisRequest(text=text))


async def test_sql_credibility_matches_the_python_rule_row_by_row(db_pool):
    expected: dict[str, int | None] = {}
    for label in ("verdadera", "falsa", "incierta"):
        for confidence in (0.0, 0.25, 0.5, 0.555, 0.75, 1.0):
            analysis_id = await _analysis(f"Afirmación {label} {confidence}")
            await seed_done(
                analysis_id=analysis_id,
                label=label,
                confidence=confidence,
                explanation=None,
            )
            expected[analysis_id] = credibility_of(kind_of(label), confidence)
    # Una fila pendiente aún no tiene veredicto ni confianza.
    expected[await _analysis("Análisis aún pendiente")] = None

    async with db_pool.connection() as conn:
        cur = await conn.execute(
            f"SELECT id::text, {CREDIBILITY_SQL} FROM public.analysis_history"
        )
        rows = await cur.fetchall()

    actual = {
        analysis_id: None if value is None else round(value * 100)
        for analysis_id, value in rows
    }
    assert actual == expected
