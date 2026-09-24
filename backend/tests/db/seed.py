"""Siembra de filas para las pruebas de lectura con el SQL de transiciones, sin pasar por el ciclo de vida."""

from app.db import analysis_transitions as transitions
from app.schemas.analysis import AnalysisRequest, SourceType


async def seed_pending(
    *, user_id: str, request: AnalysisRequest, origin: str = "web"
) -> str:
    """Inserta un análisis ``pending`` de texto o URL y devuelve su id."""
    is_url = request.source_type == SourceType.URL
    return await transitions.insert_pending(
        user_id=user_id,
        origin=origin,
        source_type=request.source_type.value,
        input_text=None if is_url else request.text,
        input_url=str(request.url) if is_url else None,
    )


async def seed_pending_file(*, user_id: str, filename: str, data: bytes) -> str:
    """Inserta un análisis ``pending`` de archivo y devuelve su id."""
    return await transitions.insert_pending_file(
        user_id=user_id, origin="web", filename=filename, data=data
    )


async def seed_done(
    *,
    analysis_id: str,
    label: str,
    confidence: float,
    explanation: str | None,
    claims: list[dict] | None = None,
    sources: list[dict] | None = None,
    evidence_coverage: float | None = None,
    pipeline: dict | None = None,
) -> None:
    """Cierra un análisis ``pending`` como ``done`` con el veredicto indicado."""
    await transitions.complete(
        analysis_id=analysis_id,
        label=label,
        confidence=confidence,
        explanation=explanation,
        claims=claims or [],
        sources=sources or [],
        evidence_coverage=evidence_coverage,
        pipeline=pipeline or {},
    )


async def seed_failed(*, analysis_id: str, error_code: str) -> None:
    """Cierra un análisis ``pending`` como ``failed``."""
    await transitions.fail(analysis_id=analysis_id, error_code=error_code)


async def seed_stage(*, analysis_id: str, stage: str) -> None:
    """Fija la etapa visible de un análisis ``pending``."""
    await transitions.set_stage(analysis_id=analysis_id, stage=stage)


async def seed_reopened_done(*, user_id: str, analysis_id: str) -> bool:
    """Devuelve a ``pending`` un análisis ``done``, como hace Reanalyze."""
    return await transitions.reopen(
        user_id=user_id, analysis_id=analysis_id, from_status="done"
    )
