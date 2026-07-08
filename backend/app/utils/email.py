"""Envío de notificaciones por email vía la API de Resend (best-effort)."""

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_EMAILS_PATH = "/emails"
_REQUEST_TIMEOUT_SECONDS = 10


def _build_report_url(base_url: str, analysis_id: str) -> str:
    """Construye el enlace al informe del análisis en el frontend."""
    return f"{base_url.rstrip('/')}/app/analisis/{analysis_id}"


async def _send_email(*, to: str | None, subject: str, html: str) -> None:
    """Envía un email por Resend; un fallo aquí nunca debe romper el análisis."""
    settings = get_settings()
    if not (settings.resend_api_key and settings.resend_from_email and to):
        return

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.resend_base_url}{_EMAILS_PATH}",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.resend_from_email,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
            response.raise_for_status()
    except Exception:
        logger.warning("[Email] No se pudo enviar la notificación a %s", to)


async def send_analysis_ready_email(*, to: str | None, analysis_id: str) -> None:
    """Notifica que un análisis terminó y enlaza a su informe."""
    settings = get_settings()
    if not settings.app_base_url:
        return

    report_url = _build_report_url(settings.app_base_url, analysis_id)
    html = (
        "<p>Tu análisis de VeriTrust está listo.</p>"
        f'<p><a href="{report_url}">Ver el informe</a></p>'
    )
    await _send_email(to=to, subject="Tu análisis de VeriTrust está listo", html=html)


async def send_analysis_failed_email(*, to: str | None, analysis_id: str) -> None:
    """Notifica que un análisis no pudo completarse y enlaza a su estado."""
    settings = get_settings()
    if not settings.app_base_url:
        return

    report_url = _build_report_url(settings.app_base_url, analysis_id)
    html = (
        "<p>No pudimos completar tu análisis de VeriTrust.</p>"
        f'<p><a href="{report_url}">Ver los detalles</a></p>'
    )
    await _send_email(
        to=to, subject="Tu análisis de VeriTrust no pudo completarse", html=html
    )
