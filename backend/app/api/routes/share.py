"""Endpoint público (sin autenticación) para ver informes compartidos por token."""

from fastapi import APIRouter, HTTPException

from app.core.errors import make_error_detail
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
    """Devuelve la vista pública de un informe compartido, sin datos de identidad."""
    try:
        report = await get_shared_analysis_by_token(token=token)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_FETCH_FAILED),
        ) from e

    if report is None:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(ErrorCode.SHARED_REPORT_NOT_FOUND),
        )

    return report
