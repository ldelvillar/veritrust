"""Endpoint público (sin autenticación) para ver informes compartidos por token."""

from fastapi import APIRouter, HTTPException

from app.core.errors import make_error_detail
from app.core.plans import limits_for
from app.db.billing import get_user_subscription
from app.db.history import get_shared_analysis_by_token
from app.db.pool import DatabaseError
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.history import PublicAnalysisReport

router = APIRouter()


_GET_SHARED_ERROR_RESPONSES: dict[int | str, dict] = {
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@router.get(
    "/{token}",
    response_model=PublicAnalysisReport,
    responses=_GET_SHARED_ERROR_RESPONSES,
)
async def get_shared_report(token: str):
    """Devuelve la vista pública de un informe compartido mientras su dueño pueda compartir, sin datos de identidad."""
    try:
        shared = await get_shared_analysis_by_token(token=token)
        # El token se conserva: el enlace vuelve a responder si el dueño recupera el Plan.
        if (
            shared is not None
            and not limits_for(await get_user_subscription(shared[0])).share
        ):
            shared = None
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_FETCH_FAILED),
        ) from e

    if shared is None:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(ErrorCode.SHARED_REPORT_NOT_FOUND),
        )

    return shared[1]
