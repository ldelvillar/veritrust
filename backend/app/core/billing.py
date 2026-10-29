"""Adaptador de Stripe: Checkout, portal de cliente, webhooks y sincronización de Subscriptions."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import cache
from typing import Any, cast

import stripe

from app.core.config import get_settings
from app.core.plans import BillingInterval, SubscriptionRow
from app.db import billing as billing_db

logger = logging.getLogger(__name__)

# Versión de la API fijada para que respuestas y webhooks no cambien de forma bajo el código
STRIPE_API_VERSION = "2026-09-30.endive"

_SUBSCRIPTION_EVENTS = frozenset(
    {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }
)
_INVOICE_EVENTS = frozenset({"invoice.paid", "invoice.payment_failed"})
# Estados en que una Subscription ya no cobra y Stripe no deja cancelarla
_ENDED_STATUSES = frozenset({"canceled", "incomplete_expired"})

_TERMS_MESSAGE = (
    "Acepto los [Términos y condiciones]({app_url}/terminos-y-condiciones) y pido que "
    "el servicio empiece de inmediato, por lo que pierdo el derecho de desistimiento "
    "sobre el periodo ya disfrutado."
)


class BillingUnavailable(RuntimeError):
    """Stripe no respondió o rechazó la llamada."""


class InvalidWebhook(ValueError):
    """La petición al webhook no trae un evento firmado por Stripe."""


class BillingAccountNotFound(LookupError):
    """El usuario nunca ha tenido un cliente de Stripe."""


@cache
def _client() -> stripe.StripeClient:
    """Cliente de Stripe con la versión de la API fijada y transporte async (httpx)."""
    return stripe.StripeClient(
        get_settings().stripe_secret_key,
        stripe_version=STRIPE_API_VERSION,
        http_client=stripe.HTTPXClient(),
    )


@asynccontextmanager
async def _stripe_errors() -> AsyncIterator[None]:
    """Traduce cualquier error de Stripe (red o API) a BillingUnavailable."""
    try:
        yield
    except stripe.StripeError as exc:
        logger.warning("Stripe rechazó la llamada: %s", type(exc).__name__)
        raise BillingUnavailable(str(exc)) from exc


def _app_url() -> str:
    """Origen público del frontend, sin barra final."""
    return (get_settings().app_base_url or "").rstrip("/")


async def _customer_for(user_id: str, email: str | None) -> str:
    """Devuelve el cliente de Stripe del usuario, creándolo y guardándolo si no lo tiene."""
    existing = await billing_db.get_customer_id(user_id)
    if existing is not None:
        return existing
    customer = await _client().v1.customers.create_async(
        params={
            "metadata": {"clerk_user_id": user_id},
            **({"email": email} if email else {}),
        }
    )
    return await billing_db.insert_customer(user_id, customer.id)


async def create_checkout_session(
    user_id: str, email: str | None, interval: BillingInterval
) -> str:
    """Abre un Checkout de Stripe para suscribirse a Pro y devuelve su URL."""
    settings = get_settings()
    price = (
        settings.stripe_price_pro_monthly
        if interval == "month"
        else settings.stripe_price_pro_yearly
    )
    app_url = _app_url()
    async with _stripe_errors():
        customer_id = await _customer_for(user_id, email)
        # Un Checkout abierto en otra pestaña caduca para no cobrar dos suscripciones
        open_sessions = await _client().v1.checkout.sessions.list_async(
            params={"customer": customer_id, "status": "open"}
        )
        for open_session in open_sessions.data:
            await _client().v1.checkout.sessions.expire_async(open_session.id)
        session = await _client().v1.checkout.sessions.create_async(
            params={
                "mode": "subscription",
                "customer": customer_id,
                "client_reference_id": user_id,
                "line_items": [{"price": price, "quantity": 1}],
                "subscription_data": {"metadata": {"clerk_user_id": user_id}},
                "automatic_tax": {"enabled": True},
                "billing_address_collection": "required",
                "customer_update": {"address": "auto", "name": "auto"},
                "tax_id_collection": {"enabled": True},
                "locale": "es",
                "allow_promotion_codes": False,
                "consent_collection": {"terms_of_service": "required"},
                "custom_text": {
                    "terms_of_service_acceptance": {
                        "message": _TERMS_MESSAGE.format(app_url=app_url)
                    }
                },
                "success_url": f"{app_url}/app/cuenta?checkout=success",
                "cancel_url": f"{app_url}/app/cuenta?checkout=cancelled",
            }
        )
    if not session.url:
        raise BillingUnavailable("Stripe devolvió un Checkout sin URL")
    return session.url


async def create_portal_session(user_id: str) -> str:
    """Abre el portal de cliente de Stripe del usuario y devuelve su URL."""
    customer_id = await billing_db.get_customer_id(user_id)
    if customer_id is None:
        raise BillingAccountNotFound(user_id)
    async with _stripe_errors():
        session = await _client().v1.billing_portal.sessions.create_async(
            params={
                "customer": customer_id,
                "return_url": f"{_app_url()}/app/cuenta",
                "locale": "es",
            }
        )
    return session.url


async def sync_subscription(subscription_id: str) -> None:
    """Vuelve a leer la Subscription de Stripe y guarda su estado actual."""
    # Sin el cerrojo, dos webhooks simultáneos podrían guardar una lectura vieja tras una nueva
    async with billing_db.subscription_lock(subscription_id) as conn:
        async with _stripe_errors():
            subscription = await _client().v1.subscriptions.retrieve_async(
                subscription_id
            )
        customer = subscription.customer
        customer_id = customer if isinstance(customer, str) else customer.id
        user_id = await billing_db.user_id_for_customer(customer_id, conn)
        if user_id is None and subscription.status in _ENDED_STATUSES:
            logger.info(
                "Suscripción %s terminada sin cliente guardado", subscription.id
            )
            return
        user_id = user_id or subscription.metadata.to_dict().get("clerk_user_id")
        item = subscription.items.data[0]
        recurring = item.price.recurring
        if (
            user_id is None
            or recurring is None
            or recurring.interval not in ("month", "year")
        ):
            logger.error(
                "Suscripción %s ajena a los planes de VeriTrust", subscription.id
            )
            return
        period_end = datetime.fromtimestamp(item.current_period_end, UTC)
        if subscription.cancel_at:
            cancel_at: datetime | None = datetime.fromtimestamp(
                subscription.cancel_at, UTC
            )
        else:
            # Una baja al final del periodo puede llegar solo con el flag, sin fecha
            cancel_at = period_end if subscription.cancel_at_period_end else None
        await billing_db.upsert_subscription(
            SubscriptionRow(
                stripe_subscription_id=subscription.id,
                user_id=user_id,
                status=subscription.status,
                price_id=item.price.id,
                billing_interval=cast(BillingInterval, recurring.interval),
                current_period_end=period_end,
                cancel_at=cancel_at,
            ),
            conn,
        )


async def forget_user(user_id: str) -> None:
    """Cancela ya, sin prorrateo, las Subscriptions de un usuario que eliminó su cuenta y borra su facturación."""
    customer_id = await billing_db.get_customer_id(user_id)
    if customer_id is not None:
        async with _stripe_errors():
            subscriptions = await _client().v1.subscriptions.list_async(
                params={"customer": customer_id, "limit": 100}
            )
            for subscription in subscriptions.data:
                if subscription.status not in _ENDED_STATUSES:
                    await _client().v1.subscriptions.cancel_async(subscription.id)
    # El cliente de Stripe y sus facturas se conservan: la ley fiscal obliga a guardarlas.
    await billing_db.delete_user_billing(user_id)
    logger.info("Facturación del usuario eliminado %s dada de baja", user_id)


async def _handle(event_type: str, obj: Any) -> None:
    """Aplica un evento de Stripe ya verificado; los tipos no manejados se ignoran."""
    if event_type == "checkout.session.completed":
        if obj.customer and obj.client_reference_id:
            await billing_db.insert_customer(obj.client_reference_id, obj.customer)
        if obj.subscription:
            await sync_subscription(obj.subscription)
    elif event_type in _SUBSCRIPTION_EVENTS:
        await sync_subscription(obj.id)
    elif event_type in _INVOICE_EVENTS:
        details = obj.parent.subscription_details if obj.parent else None
        if details and details.subscription:
            await sync_subscription(details.subscription)


async def handle_webhook(payload: bytes, signature: str | None) -> None:
    """Verifica la firma del webhook sobre el cuerpo crudo y aplica el evento una sola vez."""
    try:
        event = _client().construct_event(
            payload, signature, get_settings().stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise InvalidWebhook(type(exc).__name__) from exc

    if await billing_db.is_event_processed(event.id):
        logger.info("Evento de Stripe %s (%s) ya procesado", event.id, event.type)
        return
    await _handle(event.type, event.data.object)
    # Se registra solo tras el éxito: un fallo responde 5xx y Stripe lo reintenta
    await billing_db.record_event(event.id, event.type)
    logger.info("Evento de Stripe %s (%s) procesado", event.id, event.type)
