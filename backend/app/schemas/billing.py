"""Esquemas de facturación: el Plan del usuario con su Usage, Checkout y portal de cliente."""

from datetime import datetime

from pydantic import BaseModel

from app.core.plans import BillingInterval, PlanLimits, PlanName


class PlanUsage(BaseModel):
    """Usage del mes en curso (Madrid) y cuándo se renueva la Allowance."""

    used: int
    pending: int
    remaining: int
    resets_at: datetime


class PlanResponse(BaseModel):
    """El Plan del usuario, su Subscription (si la tuvo) y su Usage del mes."""

    plan: PlanName
    status: str | None
    interval: BillingInterval | None
    current_period_end: datetime | None
    cancel_at: datetime | None
    limits: PlanLimits
    usage: PlanUsage


class CheckoutRequest(BaseModel):
    """Periodicidad del plan Pro que se va a contratar."""

    interval: BillingInterval


class BillingUrlResponse(BaseModel):
    """URL de Stripe a la que el frontend redirige al usuario."""

    url: str


class WebhookResponse(BaseModel):
    """Acuse de recibo de un webhook de Stripe."""

    received: bool
