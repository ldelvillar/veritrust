"""Clerk webhook that verifies the Svix signature and erases the billing and analyses of deleted accounts."""

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
    """The webhook request does not carry an event signed by Clerk."""


async def handle_webhook(
    payload: bytes, headers: Mapping[str, str], intake: AnalysisIntake
) -> None:
    """Verify the signature over the raw body and apply the event, where repeating it has no effect."""
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
            # Analyses go first, so a Run that closes later has no row and records no Usage.
            deleted = await delete_all_user_analyses(user_id=user_id)
            await intake.cancel_runs(deleted.pending_ids)
            await billing.forget_user(user_id)
        else:
            logger.warning("Evento user.deleted de Clerk sin id de usuario")
    logger.info("Evento de Clerk %s (%s) procesado", headers.get("svix-id"), event_type)
