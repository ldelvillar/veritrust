"""Webhooks de terceros llamados servidor a servidor: el de Clerk avisa de las cuentas eliminadas."""

from fastapi import APIRouter, HTTPException, Request

from app.core import billing, clerk_webhooks
from app.core.errors import make_error_detail
from app.db.pool import DatabaseError
from app.schemas.billing import WebhookResponse
from app.schemas.errors import ErrorCode, ErrorResponse

router = APIRouter()


@router.post(
    "/clerk",
    response_model=WebhookResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def clerk_webhook(request: Request) -> WebhookResponse:
    """Recibe los eventos de Clerk; sin auth de usuario, solo la firma Svix del cuerpo crudo."""
    try:
        await clerk_webhooks.handle_webhook(await request.body(), request.headers)
    except clerk_webhooks.InvalidClerkWebhook as exc:
        raise HTTPException(
            status_code=400, detail=make_error_detail(ErrorCode.INVALID_WEBHOOK)
        ) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=500, detail=make_error_detail(ErrorCode.BILLING_FETCH_FAILED)
        ) from exc
    except billing.BillingUnavailable as exc:
        raise HTTPException(
            status_code=503, detail=make_error_detail(ErrorCode.BILLING_UNAVAILABLE)
        ) from exc
    return WebhookResponse(received=True)
