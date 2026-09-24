"""Este módulo contiene los endpoints relacionados con los análisis de noticas."""

from pathlib import Path
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
)

from app.api.dependencies.analysis_intake import analysis_intake, web_submitter
from app.api.dependencies.check_rate_limit import check_rate_limit
from app.api.dependencies.get_current_user import get_current_user
from app.api.dependencies.valid_analysis_id import valid_analysis_id
from app.core.analysis_lifecycle import AnalysisIntake, Submitter
from app.core.errors import make_error_detail
from app.db.feedback import create_analysis_feedback, get_analysis_feedback
from app.db.history import (
    clear_analysis_share_token,
    delete_user_analysis,
    get_analysis_file,
    get_user_analysis_by_id,
    get_user_analysis_status,
    set_analysis_share_token,
)
from app.db.pool import DatabaseError
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatusResponse,
    ShareResponse,
)
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.schemas.history import AnalysisHistoryItem

router = APIRouter()


_POST_ERROR_RESPONSES: dict[int | str, dict] = {
    401: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}

_POST_FILE_ERROR_RESPONSES: dict[int | str, dict] = {
    401: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    415: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}

_GET_FILE_ERROR_RESPONSES: dict[int | str, dict] = {
    200: {
        "content": {"application/octet-stream": {}},
        "description": "Archivo original.",
    },
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}

_GET_ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}

_DELETE_ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}

_RETRY_ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}

_FEEDBACK_ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}

_SHARE_ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}

_UNSHARE_ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@router.post(
    "",
    response_model=AnalysisResponse,
    responses=_POST_ERROR_RESPONSES,
)
async def analyze_news(
    body: AnalysisRequest,
    submitter: Submitter = Depends(web_submitter),
    intake: AnalysisIntake = Depends(analysis_intake),
):
    """Encola el análisis de una noticia y devuelve su id en estado ``pending``."""
    analysis_id = await intake.submit(submitter, body)
    return {"status": "pending", "analysis_id": analysis_id}


@router.post(
    "/{analysis_id}/share",
    response_model=ShareResponse,
    responses=_SHARE_ERROR_RESPONSES,
)
async def share_analysis(
    user=Depends(get_current_user),
    analysis_id: str = Depends(valid_analysis_id),
):
    """Activa el enlace público de un análisis ``done`` propio y devuelve su token."""
    user_id = user["sub"]

    try:
        record = await get_user_analysis_by_id(user_id=user_id, analysis_id=analysis_id)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_FETCH_FAILED),
        ) from e

    if not record:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_FOUND),
        )

    # Solo se comparte un informe terminado; pending/failed no tienen resultado.
    if record.status != "done":
        raise HTTPException(
            status_code=409,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_SHAREABLE),
        )

    try:
        token = await set_analysis_share_token(user_id=user_id, analysis_id=analysis_id)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.SHARE_FAILED),
        ) from e

    if token is None:
        # Perdió la carrera: el estado cambió entre la lectura y el update.
        raise HTTPException(
            status_code=409,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_SHAREABLE),
        )

    return {"status": "shared", "share_token": token}


@router.delete(
    "/{analysis_id}/share",
    response_model=AnalysisResponse,
    responses=_UNSHARE_ERROR_RESPONSES,
)
async def unshare_analysis(
    user=Depends(get_current_user),
    analysis_id: str = Depends(valid_analysis_id),
):
    """Desactiva el enlace público de un análisis propio."""
    user_id = user["sub"]

    try:
        cleared = await clear_analysis_share_token(
            user_id=user_id, analysis_id=analysis_id
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.SHARE_FAILED),
        ) from e

    if not cleared:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_FOUND),
        )

    return {"status": "unshared", "analysis_id": analysis_id}


@router.post(
    "/file",
    response_model=AnalysisResponse,
    responses=_POST_FILE_ERROR_RESPONSES,
)
async def analyze_file(
    file: UploadFile = File(...),
    submitter: Submitter = Depends(web_submitter),
    intake: AnalysisIntake = Depends(analysis_intake),
):
    """Sube un archivo (PDF/TXT/MD), guarda el binario y encola su análisis ``pending``."""
    analysis_id = await intake.submit_file(submitter, file)
    return {"status": "pending", "analysis_id": analysis_id}


@router.get(
    "/{analysis_id}",
    response_model=AnalysisHistoryItem,
    responses=_GET_ERROR_RESPONSES,
)
async def get_analysis_detail(
    user=Depends(get_current_user),
    analysis_id: str = Depends(valid_analysis_id),
):
    """Endpoint para obtener un análisis específico del usuario autenticado."""
    user_id = user["sub"]

    try:
        record = await get_user_analysis_by_id(user_id=user_id, analysis_id=analysis_id)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_FETCH_FAILED),
        ) from e

    if not record:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_FOUND),
        )

    # Solo un informe terminado puede tener valoración; el sondeo pending se ahorra la consulta.
    feedback = None
    if record.status == "done":
        try:
            feedback = await get_analysis_feedback(
                user_id=user_id, analysis_id=analysis_id
            )
        except DatabaseError as e:
            raise HTTPException(
                status_code=500,
                detail=make_error_detail(ErrorCode.ANALYSIS_FETCH_FAILED),
            ) from e

    return AnalysisHistoryItem(
        analysis_id=record.analysis_id,
        user_id=record.user_id,
        source_type=record.source_type,
        origin=record.origin,
        input_text=record.input_text,
        input_url=record.input_url,
        label=record.label,
        confidence=record.confidence,
        evidence_coverage=record.evidence_coverage,
        explanation=record.explanation,
        status=record.status,
        error_code=record.error_code,
        created_at=record.created_at,
        completed_at=record.completed_at,
        claims=record.claims,
        sources=record.sources,
        file_filename=record.file_filename,
        share_token=record.share_token,
        stage=record.stage,
        feedback=feedback,
    )


@router.get(
    "/{analysis_id}/status",
    response_model=AnalysisStatusResponse,
    responses=_GET_ERROR_RESPONSES,
)
async def get_analysis_status(
    user=Depends(get_current_user),
    analysis_id: str = Depends(valid_analysis_id),
):
    """Endpoint ligero que devuelve solo el estado y la etapa para el sondeo del detalle."""
    try:
        record = await get_user_analysis_status(
            user_id=user["sub"], analysis_id=analysis_id
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_FETCH_FAILED),
        ) from e

    if not record:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_FOUND),
        )

    return record


_FILE_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
}


def _content_disposition_inline(filename: str) -> str:
    """Construye un Content-Disposition inline seguro (RFC 6266) para nombres no ASCII."""
    # Cabeceras HTTP se codifican en latin-1: un nombre con em dash, emoji o CJK
    # reventaría la respuesta con UnicodeEncodeError, así que separamos el
    # fallback ASCII (sin comillas ni control) del nombre real percent-encoded.
    ascii_fallback = (
        "".join(c for c in filename if 32 <= ord(c) < 127 and c not in '"\\')
        or "documento"
    )
    # surrogatepass evita un UnicodeEncodeError si el nombre trae surrogates sueltos.
    encoded = quote(filename, safe="", errors="surrogatepass")
    return f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


@router.get("/{analysis_id}/file", responses=_GET_FILE_ERROR_RESPONSES)
async def get_analysis_file_content(
    user=Depends(get_current_user),
    analysis_id: str = Depends(valid_analysis_id),
):
    """Devuelve el archivo original de un análisis para mostrarlo en el informe."""
    user_id = user["sub"]

    try:
        stored = await get_analysis_file(user_id=user_id, analysis_id=analysis_id)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_FETCH_FAILED),
        ) from e

    if stored is None:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_FOUND),
        )

    data, filename = stored
    safe_name = filename or "documento"
    media_type = _FILE_MEDIA_TYPES.get(
        Path(safe_name).suffix.lower(), "application/octet-stream"
    )
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": _content_disposition_inline(safe_name)},
    )


@router.delete(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    responses=_DELETE_ERROR_RESPONSES,
)
async def delete_analysis_detail(
    user=Depends(get_current_user),
    analysis_id: str = Depends(valid_analysis_id),
):
    """Elimina un análisis del usuario autenticado."""
    user_id = user["sub"]

    try:
        deleted = await delete_user_analysis(user_id=user_id, analysis_id=analysis_id)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_DELETE_FAILED),
        ) from e

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_FOUND),
        )

    return {"status": "deleted", "analysis_id": analysis_id}


@router.post(
    "/{analysis_id}/retry",
    response_model=AnalysisResponse,
    responses=_RETRY_ERROR_RESPONSES,
)
async def retry_analysis(
    submitter: Submitter = Depends(web_submitter),
    analysis_id: str = Depends(valid_analysis_id),
    intake: AnalysisIntake = Depends(analysis_intake),
):
    """Reabre un análisis ``failed`` propio y lo reencola reutilizando su entrada."""
    await intake.retry(submitter, analysis_id)
    return {"status": "pending", "analysis_id": analysis_id}


@router.post(
    "/{analysis_id}/feedback",
    response_model=FeedbackResponse,
    responses=_FEEDBACK_ERROR_RESPONSES,
)
async def submit_analysis_feedback(
    body: FeedbackRequest,
    user: dict = Depends(check_rate_limit),
    analysis_id: str = Depends(valid_analysis_id),
):
    """Guarda la valoración del veredicto de un análisis ``done`` propio."""
    user_id = user["sub"]

    try:
        record = await get_user_analysis_by_id(user_id=user_id, analysis_id=analysis_id)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_FETCH_FAILED),
        ) from e

    if not record:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_FOUND),
        )

    # Solo se valora un veredicto existente; pending/failed no tienen resultado.
    if record.status != "done":
        raise HTTPException(
            status_code=409,
            detail=make_error_detail(ErrorCode.FEEDBACK_NOT_ALLOWED),
        )

    try:
        feedback = await create_analysis_feedback(
            user_id=user_id,
            analysis_id=analysis_id,
            is_correct=body.is_correct,
            suggested_verdict=body.suggested_verdict,
            comment=body.comment,
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.FEEDBACK_SAVE_FAILED),
        ) from e

    if feedback is None:
        # El guard del INSERT filtró la fila: ya había valoración activa (o carrera).
        raise HTTPException(
            status_code=409,
            detail=make_error_detail(ErrorCode.FEEDBACK_ALREADY_SUBMITTED),
        )

    return {"status": "saved", "feedback": feedback}


@router.post(
    "/{analysis_id}/reanalyze",
    response_model=AnalysisResponse,
    responses=_RETRY_ERROR_RESPONSES,
)
async def reanalyze_analysis(
    submitter: Submitter = Depends(web_submitter),
    analysis_id: str = Depends(valid_analysis_id),
    intake: AnalysisIntake = Depends(analysis_intake),
):
    """Reabre un análisis ``done`` propio y lo reencola con la misma entrada."""
    await intake.reanalyze(submitter, analysis_id)
    return {"status": "pending", "analysis_id": analysis_id}
