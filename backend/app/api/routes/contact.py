"""Endpoint público (sin autenticación) que envía por email los formularios de contacto/demo."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.check_rate_limit import check_public_rate_limit
from app.core.errors import make_error_detail
from app.schemas.contact import ContactRequest, ContactResponse
from app.schemas.errors import ErrorCode, ErrorResponse
from app.utils.email import (
    ContactEmailError,
    ContactEmailNotConfigured,
    send_contact_email,
)

router = APIRouter()


_POST_CONTACT_ERROR_RESPONSES: dict[int | str, dict] = {
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


@router.post(
    "",
    response_model=ContactResponse,
    responses=_POST_CONTACT_ERROR_RESPONSES,
)
async def submit_contact(
    body: ContactRequest,
    _: None = Depends(check_public_rate_limit),
) -> ContactResponse:
    """Entrega el mensaje del formulario al buzón del equipo; sin persistencia, best-effort no vale."""
    try:
        await send_contact_email(
            name=body.name,
            email=body.email,
            subject=body.subject,
            message=body.message,
            metadata=body.metadata,
            contact_type=body.type.value,
        )
    except ContactEmailNotConfigured as e:
        raise HTTPException(
            status_code=503,
            detail=make_error_detail(ErrorCode.SERVICE_UNAVAILABLE),
        ) from e
    except ContactEmailError as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(ErrorCode.CONTACT_SEND_FAILED),
        ) from e

    return ContactResponse(status="sent")
