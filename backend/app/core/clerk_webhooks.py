"""Webhook de Clerk: verifica la firma Svix y borra la facturación y los análisis de las cuentas eliminadas."""

import json
import logging
from collections.abc import Mapping

from svix.webhooks import Webhook, WebhookVerificationError

from app.core import billing
from app.core.analysis_lifecycle import AnalysisIntake
from app.core.config import get_settings
from app.db.history import delete_all_user_analyses

logger = logging.getLogger(__name__)


class InvalidClerkWebhook(ValueError):
    """La petición al webhook no trae un evento firmado por Clerk."""


async def handle_webhook(
    payload: bytes, headers: Mapping[str, str], intake: AnalysisIntake
) -> None:
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
            # Borrar la cuenta borra sus análisis, como «Eliminar toda la actividad» (RGPD art. 17)
            deleted = await delete_all_user_analyses(user_id=user_id)
            await intake.cancel_runs(deleted.pending_ids)
        else:
            logger.warning("Evento user.deleted de Clerk sin id de usuario")
    logger.info("Evento de Clerk %s (%s) procesado", headers.get("svix-id"), event_type)
