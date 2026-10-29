"""Webhook de Clerk: verifica la firma Svix y da de baja la facturación de las cuentas eliminadas."""

import json
import logging
from collections.abc import Mapping

from svix.webhooks import Webhook, WebhookVerificationError

from app.core import billing
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class InvalidClerkWebhook(ValueError):
    """La petición al webhook no trae un evento firmado por Clerk."""


async def handle_webhook(payload: bytes, headers: Mapping[str, str]) -> None:
    """Verifica la firma sobre el cuerpo crudo y aplica el evento; repetirlo no tiene efecto."""
    webhook = Webhook(get_settings().clerk_webhook_secret)
    try:
        webhook.verify(payload, dict(headers))
        event = json.loads(payload)
    except (WebhookVerificationError, ValueError) as exc:
        raise InvalidClerkWebhook(type(exc).__name__) from exc

    event_type = event.get("type")
    if event_type == "user.deleted":
        user_id = (event.get("data") or {}).get("id")
        if user_id:
            await billing.forget_user(user_id)
        else:
            logger.warning("Evento user.deleted de Clerk sin id de usuario")
    logger.info("Evento de Clerk %s (%s) procesado", headers.get("svix-id"), event_type)
