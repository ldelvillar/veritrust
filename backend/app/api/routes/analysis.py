"""Este módulo contiene los endpoints relacionados con los análisis de noticas."""

import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from redis.exceptions import RedisError

from app.api.dependencies.check_rate_limit import check_rate_limit
from app.api.dependencies.get_current_user import get_current_user
from app.core.config import get_settings
from app.core.errors import make_error_detail
from app.db.history import (
    create_pending_analysis,
    create_pending_pdf_analysis,
    delete_user_analysis,
    fail_analysis,
    get_analysis_pdf,
    get_user_analysis_by_id,
    reset_failed_analysis_to_pending,
)
from app.db.pool import DatabaseError
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.history import AnalysisHistoryItem

router = APIRouter()
logger = logging.getLogger(__name__)


_POST_ERROR_RESPONSES: dict[int | str, dict] = {
    401: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}

_POST_PDF_ERROR_RESPONSES: dict[int | str, dict] = {
    401: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    415: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}

_GET_PDF_ERROR_RESPONSES: dict[int | str, dict] = {
    200: {"content": {"application/pdf": {}}, "description": "PDF original."},
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


@router.post(
    "",
    response_model=AnalysisResponse,
    responses=_POST_ERROR_RESPONSES,
)
async def analyze_news(
    body: AnalysisRequest,
    request: Request,
    user: dict = Depends(check_rate_limit),
):
    """Encola el análisis de una noticia y devuelve su id en estado ``pending``."""
    user_id = user["sub"]

    arq_pool = getattr(request.app.state, "arq_pool", None)
    if arq_pool is None:
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        )

    try:
        analysis_id = await create_pending_analysis(user_id=user_id, request=body)
    except DatabaseError as e:
        logger.exception("No se pudo crear el análisis pendiente")
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_SAVE_FAILED),
        ) from e

    try:
        await arq_pool.enqueue_job(
            "run_analysis",
            analysis_id,
            body.source_type.value,
            body.text,
            str(body.url) if body.url else None,
        )
    except (OSError, RedisError) as e:
        # Sin encolado, marcamos la fila como failed para que no quede pending indefinidamente
        logger.exception("No se pudo encolar el análisis %s", analysis_id)
        try:
            await fail_analysis(
                analysis_id=analysis_id,
                error_code=ErrorCode.SERVICE_UNAVAILABLE.value,
            )
        except DatabaseError:
            logger.exception(
                "No se pudo marcar como failed el análisis %s", analysis_id
            )
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        ) from e

    return {"status": "pending", "analysis_id": analysis_id}


@router.post(
    "/pdf",
    response_model=AnalysisResponse,
    responses=_POST_PDF_ERROR_RESPONSES,
)
async def analyze_pdf(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(check_rate_limit),
):
    """Sube un PDF, guarda el binario y encola su análisis en estado ``pending``."""
    user_id = user["sub"]
    settings = get_settings()

    arq_pool = getattr(request.app.state, "arq_pool", None)
    if arq_pool is None:
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        )

    # Rechaza por tamaño antes de leer todo el cuerpo en memoria cuando es posible.
    if file.size is not None and file.size > settings.max_pdf_bytes:
        raise HTTPException(
            status_code=413,
            detail=make_error_detail(ErrorCode.PDF_TOO_LARGE),
        )

    data = await file.read()
    if len(data) > settings.max_pdf_bytes:
        raise HTTPException(
            status_code=413,
            detail=make_error_detail(ErrorCode.PDF_TOO_LARGE),
        )

    if not data or not data.startswith(b"%PDF"):
        raise HTTPException(
            status_code=415,
            detail=make_error_detail(ErrorCode.INVALID_PDF),
        )

    filename = (file.filename or "documento.pdf")[:255]

    try:
        analysis_id = await create_pending_pdf_analysis(
            user_id=user_id, filename=filename, data=data
        )
    except DatabaseError as e:
        logger.exception("No se pudo crear el análisis de PDF pendiente")
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_SAVE_FAILED),
        ) from e

    try:
        await arq_pool.enqueue_job("run_analysis", analysis_id, "pdf", None, None)
    except (OSError, RedisError) as e:
        logger.exception("No se pudo encolar el análisis %s", analysis_id)
        try:
            await fail_analysis(
                analysis_id=analysis_id,
                error_code=ErrorCode.SERVICE_UNAVAILABLE.value,
            )
        except DatabaseError:
            logger.exception(
                "No se pudo marcar como failed el análisis %s", analysis_id
            )
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        ) from e

    return {"status": "pending", "analysis_id": analysis_id}


@router.get(
    "/{analysis_id}",
    response_model=AnalysisHistoryItem,
    responses=_GET_ERROR_RESPONSES,
)
async def get_analysis_detail(analysis_id: str, user=Depends(get_current_user)):
    """Endpoint para obtener un análisis específico del usuario autenticado."""
    user_id = user["sub"]

    try:
        # Validación rápida para evitar consultas con ids inválidos.
        UUID(analysis_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=make_error_detail(ErrorCode.INVALID_ANALYSIS_ID),
        ) from e

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

    return AnalysisHistoryItem(
        analysis_id=record.analysis_id,
        user_id=record.user_id,
        source_type=record.source_type,
        input_text=record.input_text,
        input_url=record.input_url,
        label=record.label,
        confidence=record.confidence,
        explanation=record.explanation,
        status=record.status,
        error_code=record.error_code,
        created_at=record.created_at,
        claims=record.claims,
        sources=record.sources,
        pdf_filename=record.pdf_filename,
    )


@router.get("/{analysis_id}/pdf", responses=_GET_PDF_ERROR_RESPONSES)
async def get_analysis_pdf_file(analysis_id: str, user=Depends(get_current_user)):
    """Devuelve el PDF original de un análisis para mostrarlo en el informe."""
    user_id = user["sub"]

    try:
        UUID(analysis_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=make_error_detail(ErrorCode.INVALID_ANALYSIS_ID),
        ) from e

    try:
        pdf = await get_analysis_pdf(user_id=user_id, analysis_id=analysis_id)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_FETCH_FAILED),
        ) from e

    if pdf is None:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_FOUND),
        )

    data, filename = pdf
    safe_name = filename or "documento.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'},
    )


@router.delete(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    responses=_DELETE_ERROR_RESPONSES,
)
async def delete_analysis_detail(analysis_id: str, user=Depends(get_current_user)):
    """Elimina un análisis del usuario autenticado."""
    user_id = user["sub"]

    try:
        # Validación rápida para evitar consultas con ids inválidos.
        UUID(analysis_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=make_error_detail(ErrorCode.INVALID_ANALYSIS_ID),
        ) from e

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
    analysis_id: str,
    request: Request,
    user: dict = Depends(check_rate_limit),
):
    """Reabre un análisis ``failed`` propio y lo reencola reutilizando su entrada."""
    user_id = user["sub"]

    try:
        # Validación rápida para evitar consultas con ids inválidos.
        UUID(analysis_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=make_error_detail(ErrorCode.INVALID_ANALYSIS_ID),
        ) from e

    arq_pool = getattr(request.app.state, "arq_pool", None)
    if arq_pool is None:
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        )

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

    # Solo tiene sentido reintentar lo que falló; un 'pending'/'done' no se toca.
    if record.status != "failed":
        raise HTTPException(
            status_code=409,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_RETRYABLE),
        )

    try:
        reopened = await reset_failed_analysis_to_pending(
            user_id=user_id, analysis_id=analysis_id
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.ANALYSIS_RETRY_FAILED),
        ) from e

    if not reopened:
        # Perdió la carrera: el estado cambió entre la lectura y el reinicio.
        raise HTTPException(
            status_code=409,
            detail=make_error_detail(ErrorCode.ANALYSIS_NOT_RETRYABLE),
        )

    if record.source_type == "url":
        text_arg, url_arg = None, record.input_url
    else:
        text_arg, url_arg = record.input_text, None

    try:
        await arq_pool.enqueue_job(
            "run_analysis",
            analysis_id,
            record.source_type,
            text_arg,
            url_arg,
        )
    except (OSError, RedisError) as e:
        # Sin encolado, se devuelve la fila a failed para que no quede pending.
        logger.exception("No se pudo reencolar el análisis %s", analysis_id)
        try:
            await fail_analysis(
                analysis_id=analysis_id,
                error_code=ErrorCode.SERVICE_UNAVAILABLE.value,
            )
        except DatabaseError:
            logger.exception(
                "No se pudo marcar como failed el análisis %s", analysis_id
            )
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        ) from e

    return {"status": "pending", "analysis_id": analysis_id}
