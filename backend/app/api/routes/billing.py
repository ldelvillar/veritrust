"""Endpoints de facturación: Plan y Usage, Checkout, portal de cliente y webhook de Stripe."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.dependencies.get_current_user import get_current_user
from app.core import billing
from app.core.errors import make_error_detail
from app.core.plans import is_pro, limits_for, month_window, remaining
from app.db.billing import get_user_subscription, usage_this_month
from app.db.pool import DatabaseError
from app.schemas.billing import (
    BillingUrlResponse,
    CheckoutRequest,
    PlanResponse,
    PlanUsage,
    WebhookResponse,
)
from app.schemas.errors import ErrorCode, ErrorResponse

router = APIRouter()
webhook_router = APIRouter()


def _database_failed() -> HTTPException:
    """Responde un fallo de la base de datos de facturación como 500."""
    return HTTPException(
        status_code=500, detail=make_error_detail(ErrorCode.BILLING_FETCH_FAILED)
    )


def _billing_unavailable() -> HTTPException:
    """Responde un fallo de Stripe como 503."""
    return HTTPException(
        status_code=503, detail=make_error_detail(ErrorCode.BILLING_UNAVAILABLE)
    )


@router.get(
    "/plan",
    response_model=PlanResponse,
    responses={500: {"model": ErrorResponse}},
)
async def get_plan(user=Depends(get_current_user)) -> PlanResponse:
    """Devuelve el Plan del usuario, su Subscription y el Usage de este mes."""
    user_id = user["sub"]
    resets_from, resets_at = month_window(datetime.now(UTC))
    try:
        subscription = await get_user_subscription(user_id)
        usage = await usage_this_month(user_id, resets_from, resets_at)
    except DatabaseError as exc:
        raise _database_failed() from exc

    limits = limits_for(subscription)
    return PlanResponse(
        plan=limits.name,
        status=subscription.status if subscription else None,
        interval=subscription.billing_interval if subscription else None,
        current_period_end=subscription.current_period_end if subscription else None,
        cancel_at=subscription.cancel_at if subscription else None,
        limits=limits,
        usage=PlanUsage(
            used=usage.used,
            pending=usage.pending,
            remaining=remaining(limits, usage.used, usage.pending),
            resets_at=resets_at,
        ),
    )


@router.post(
    "/checkout",
    response_model=BillingUrlResponse,
    responses={
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def create_checkout(
    body: CheckoutRequest, user=Depends(get_current_user)
) -> BillingUrlResponse:
    """Abre un Checkout de Stripe para pasar a Pro; rechaza a quien ya es Pro."""
    user_id = user["sub"]
    try:
        if is_pro(await get_user_subscription(user_id)):
            raise HTTPException(
                status_code=409, detail=make_error_detail(ErrorCode.ALREADY_SUBSCRIBED)
            )
        url = await billing.create_checkout_session(
            user_id, user.get("email"), body.interval
        )
    except DatabaseError as exc:
        raise _database_failed() from exc
    except billing.BillingUnavailable as exc:
        raise _billing_unavailable() from exc
    return BillingUrlResponse(url=url)


@router.post(
    "/portal",
    response_model=BillingUrlResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def create_portal(user=Depends(get_current_user)) -> BillingUrlResponse:
    """Abre el portal de cliente de Stripe para gestionar la Subscription."""
    try:
        url = await billing.create_portal_session(user["sub"])
    except billing.BillingAccountNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(ErrorCode.BILLING_ACCOUNT_NOT_FOUND),
        ) from exc
    except DatabaseError as exc:
        raise _database_failed() from exc
    except billing.BillingUnavailable as exc:
        raise _billing_unavailable() from exc
    return BillingUrlResponse(url=url)


@webhook_router.post(
    "/webhook",
    response_model=WebhookResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def stripe_webhook(
    request: Request, stripe_signature: str | None = Header(None)
) -> WebhookResponse:
    """Recibe los eventos de Stripe; sin auth de usuario, solo la firma del cuerpo crudo."""
    try:
        await billing.handle_webhook(await request.body(), stripe_signature)
    except billing.InvalidWebhook as exc:
        raise HTTPException(
            status_code=400, detail=make_error_detail(ErrorCode.INVALID_WEBHOOK)
        ) from exc
    except DatabaseError as exc:
        raise _database_failed() from exc
    except billing.BillingUnavailable as exc:
        raise _billing_unavailable() from exc
    return WebhookResponse(received=True)
