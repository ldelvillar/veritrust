"""Row seeding for the read tests with the transitions SQL, bypassing the lifecycle."""

from datetime import datetime

from app.core.plans import PRO
from app.core.verdict import ClaimVerdict, Verdict, kind_of
from app.db import analysis_transitions as transitions
from app.db.pool import get_pool
from app.schemas.analysis import AnalysisRequest, SourceType


async def seed_pending(
    *, user_id: str, request: AnalysisRequest, origin: str = "web"
) -> str:
    """Insert a ``pending`` text or URL Analysis with the Pro Plan and return its id."""
    is_url = request.source_type == SourceType.URL
    return await transitions.insert_pending(
        user_id=user_id,
        origin=origin,
        source_type=request.source_type.value,
        input_text=None if is_url else request.text,
        input_url=str(request.url) if is_url else None,
        limits=PRO,
    )


async def seed_pending_file(*, user_id: str, filename: str, data: bytes) -> str:
    """Insert a ``pending`` file Analysis with the Pro Plan and return its id."""
    return await transitions.insert_pending_file(
        user_id=user_id,
        origin="web",
        filename=filename,
        data=data,
        limits=PRO,
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
    """Close a ``pending`` Analysis as ``done`` with the given Verdict."""
    verdict = Verdict(
        kind=kind_of(label),
        confidence=confidence,
        # The falsehood is not stored, so its value does not matter when seeding.
        falsehood=0.5,
        evidence_coverage=evidence_coverage,
        claims=tuple(
            ClaimVerdict(
                text=claim["text"],
                kind=kind_of(claim["label"]),
                confidence=claim["confidence"],
            )
            for claim in claims or []
        ),
    )
    await transitions.complete(
        analysis_id=analysis_id,
        verdict=verdict,
        explanation=explanation,
        sources=sources or [],
        pipeline=pipeline or {},
    )


async def seed_failed(*, analysis_id: str, error_code: str) -> None:
    """Close a ``pending`` Analysis as ``failed``."""
    await transitions.fail(analysis_id=analysis_id, error_code=error_code)


async def seed_stage(*, analysis_id: str, stage: str) -> None:
    """Set the visible stage of a ``pending`` Analysis."""
    await transitions.set_stage(analysis_id=analysis_id, stage=stage)


async def seed_reopened_done(*, user_id: str, analysis_id: str) -> bool:
    """Return a ``done`` Analysis to ``pending``, as Reanalyze does."""
    return await transitions.reopen(
        user_id=user_id,
        analysis_id=analysis_id,
        from_status="done",
        limits=PRO,
    )


async def seed_created_at(*, analysis_id: str, created_at: datetime) -> None:
    """Set an Analysis's creation instant, to test date ranges and sorting."""
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE public.analysis_history SET created_at = %s WHERE id = %s",
            (created_at, analysis_id),
        )


async def seed_usage(
    *, user_id: str, occurred_at: datetime, analysis_id: str | None = None
) -> None:
    """Record one unit of the user's Usage at the given instant, without a Run."""
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO public.usage_events (user_id, kind, analysis_id, occurred_at) "
            "VALUES (%s, 'analysis', %s, %s)",
            (user_id, analysis_id, occurred_at),
        )
