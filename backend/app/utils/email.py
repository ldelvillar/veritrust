"""Envío de notificaciones por email vía la API de Resend (best-effort)."""

import logging
from html import escape

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_EMAILS_PATH = "/emails"
_REQUEST_TIMEOUT_SECONDS = 10
# Logo de marca sobre fondo transparente, servido por el frontend.
_LOGO_PATH = "/images/logo-1316x1316-no-bg.png"
# Prefijo del asunto según el tipo de formulario que originó el mensaje.
_CONTACT_SUBJECT_PREFIX = {
    "contact": "Nuevo mensaje de contacto",
    "demo": "Nueva solicitud de demo",
}


class ContactEmailNotConfigured(RuntimeError):
    """El envío de mensajes de contacto no está configurado (falta Resend o el buzón)."""


class ContactEmailError(RuntimeError):
    """El mensaje de contacto no se pudo entregar a través de Resend."""


def _build_report_url(base_url: str, analysis_id: str) -> str:
    """Construye el enlace al informe del análisis en el frontend."""
    return f"{base_url.rstrip('/')}/app/analisis/{analysis_id}"


def _render_email_html(
    *, base_url: str, report_url: str, heading: str, body_text: str, cta_label: str
) -> str:
    """Compone el HTML del email con tablas y estilos inline compatibles con clientes de correo."""
    logo_url = f"{base_url.rstrip('/')}{_LOGO_PATH}"
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="background:#f4f4f7;padding:32px 0;'
        'font-family:Helvetica,Arial,sans-serif;">'
        '<tr><td align="center">'
        '<table role="presentation" width="480" cellpadding="0" cellspacing="0" '
        'style="max-width:480px;background:#ffffff;border:1px solid #ececf1;'
        'border-radius:12px;">'
        '<tr><td style="padding:32px 40px 0;text-align:center;">'
        f'<img src="{logo_url}" alt="VeriTrust" width="64" height="64" '
        'style="display:inline-block;border:0;">'
        "</td></tr>"
        '<tr><td style="padding:20px 40px 8px;text-align:center;">'
        f'<h1 style="margin:0;font-size:20px;color:#15162c;">{heading}</h1>'
        "</td></tr>"
        '<tr><td style="padding:0 40px 24px;text-align:center;">'
        f'<p style="margin:0;font-size:15px;line-height:1.6;color:#4b4b5a;">{body_text}</p>'
        "</td></tr>"
        '<tr><td style="padding:0 40px 32px;text-align:center;">'
        f'<a href="{report_url}" style="display:inline-block;background:#432dd7;'
        "color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;"
        f'padding:13px 30px;border-radius:8px;">{cta_label}</a>'
        "</td></tr>"
        '<tr><td style="padding:20px 40px;background:#fafafc;'
        'border-top:1px solid #ececf1;border-radius:0 0 12px 12px;text-align:center;">'
        '<p style="margin:0;font-size:12px;color:#9a9aa8;">'
        "VeriTrust · Verificación de información médica con IA</p>"
        "</td></tr>"
        "</table></td></tr></table>"
    )


async def _send_email(
    *, to: str | None, subject: str, html: str, text: str | None = None
) -> None:
    """Envía un email por Resend; un fallo aquí nunca debe romper el análisis."""
    settings = get_settings()
    if not (settings.resend_api_key and settings.resend_from_email and to):
        return

    payload: dict[str, object] = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.resend_base_url}{_EMAILS_PATH}",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json=payload,
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
    html = _render_email_html(
        base_url=settings.app_base_url,
        report_url=report_url,
        heading="Tu análisis está listo",
        body_text=(
            "Hemos terminado de verificar tu contenido. Ya puedes consultar el "
            "veredicto, las fuentes y la explicación."
        ),
        cta_label="Ver el informe",
    )
    text = f"Tu análisis de VeriTrust está listo. Consúltalo aquí: {report_url}"
    await _send_email(
        to=to,
        subject="Tu análisis de VeriTrust está listo",
        html=html,
        text=text,
    )


async def send_analysis_no_claims_email(*, to: str | None, analysis_id: str) -> None:
    """Notifica, en tono neutro, que el texto no contenía afirmaciones médicas verificables."""
    settings = get_settings()
    if not settings.app_base_url:
        return

    report_url = _build_report_url(settings.app_base_url, analysis_id)
    html = _render_email_html(
        base_url=settings.app_base_url,
        report_url=report_url,
        heading="No encontramos afirmaciones médicas",
        body_text=(
            "Hemos revisado tu contenido, pero no contenía afirmaciones médicas "
            "que pudiéramos verificar. Prueba con otro texto o enlace."
        ),
        cta_label="Ver el análisis",
    )
    text = (
        "Revisamos tu contenido, pero no encontramos afirmaciones médicas "
        f"verificables. Consúltalo aquí: {report_url}"
    )
    await _send_email(
        to=to,
        subject="No encontramos afirmaciones médicas en tu contenido",
        html=html,
        text=text,
    )


async def send_analysis_failed_email(*, to: str | None, analysis_id: str) -> None:
    """Notifica que un análisis no pudo completarse y enlaza a su estado."""
    settings = get_settings()
    if not settings.app_base_url:
        return

    report_url = _build_report_url(settings.app_base_url, analysis_id)
    html = _render_email_html(
        base_url=settings.app_base_url,
        report_url=report_url,
        heading="No pudimos completar tu análisis",
        body_text=(
            "Ha surgido un problema al verificar tu contenido. Abre el informe "
            "para ver los detalles o volver a intentarlo."
        ),
        cta_label="Ver los detalles",
    )
    text = f"Tu análisis de VeriTrust no pudo completarse. Más detalles: {report_url}"
    await _send_email(
        to=to,
        subject="Tu análisis de VeriTrust no pudo completarse",
        html=html,
        text=text,
    )


def _render_contact_html(
    *,
    name: str,
    email: str,
    subject: str,
    message: str | None,
    metadata: dict[str, str] | None,
) -> str:
    """Compone un email plano con los datos del formulario, para lectura del equipo."""
    rows = [("Nombre", name), ("Email", email), ("Asunto", subject)]
    if metadata:
        rows.extend(metadata.items())
    fields = "".join(
        "<tr>"
        '<td style="padding:4px 12px 4px 0;color:#6b6b7a;font-weight:600;'
        f'white-space:nowrap;vertical-align:top;">{escape(label)}</td>'
        f'<td style="padding:4px 0;color:#15162c;">{escape(value)}</td>'
        "</tr>"
        for label, value in rows
    )
    body = escape(message or "(sin mensaje)").replace("\n", "<br>")
    return (
        '<div style="font-family:Helvetica,Arial,sans-serif;max-width:560px;">'
        '<table role="presentation" cellpadding="0" cellspacing="0" '
        f'style="font-size:14px;line-height:1.5;">{fields}</table>'
        '<p style="margin:16px 0 4px;color:#6b6b7a;font-weight:600;font-size:14px;">'
        "Mensaje</p>"
        f'<p style="margin:0;color:#15162c;font-size:14px;line-height:1.6;">{body}</p>'
        "</div>"
    )


async def send_contact_email(
    *,
    name: str,
    email: str,
    subject: str,
    message: str | None,
    metadata: dict[str, str] | None,
    contact_type: str,
) -> None:
    """Envía un mensaje de formulario al buzón del equipo; propaga fallos para poder reintentar."""
    settings = get_settings()
    if not (
        settings.resend_api_key
        and settings.resend_from_email
        and settings.contact_to_email
    ):
        raise ContactEmailNotConfigured

    prefix = _CONTACT_SUBJECT_PREFIX.get(
        contact_type, _CONTACT_SUBJECT_PREFIX["contact"]
    )
    payload = {
        "from": settings.resend_from_email,
        "to": [settings.contact_to_email],
        "reply_to": [email],
        "subject": f"[VeriTrust] {prefix} — {subject}",
        "html": _render_contact_html(
            name=name,
            email=email,
            subject=subject,
            message=message,
            metadata=metadata,
        ),
    }

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.resend_base_url}{_EMAILS_PATH}",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json=payload,
            )
            response.raise_for_status()
    except Exception as exc:
        logger.warning("[Email] No se pudo enviar el mensaje de contacto")
        raise ContactEmailError from exc
