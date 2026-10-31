"""Dependency that validates the route's analysis id before querying the database."""

from uuid import UUID

from fastapi import HTTPException

from app.core.errors import make_error_detail
from app.schemas.errors import ErrorCode


async def valid_analysis_id(analysis_id: str) -> str:
    """Return the route id in canonical form if it is a UUID, or answer 400 with INVALID_ANALYSIS_ID."""
    try:
        canonical = UUID(analysis_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=make_error_detail(ErrorCode.INVALID_ANALYSIS_ID),
        ) from e

    # arq keys use the canonical form, so an uppercase or dashless variant would not find them.
    return str(canonical)
