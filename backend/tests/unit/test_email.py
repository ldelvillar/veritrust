"""Tests del envío de notificaciones por email vía Resend con la red mockeada."""

import types

import httpx

from app.utils import email

ANALYSIS_ID = "11111111-1111-1111-1111-111111111111"


class _FakeResponse:
    def __init__(self, *, raise_exc=None):
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc


class _FakeAsyncClient:
    def __init__(self, recorder, *, post_exc=None, response=None):
        self._recorder = recorder
        self._post_exc = post_exc
        self._response = response or _FakeResponse()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, *, headers=None, json=None):
        self._recorder.append({"url": url, "headers": headers, "json": json})
        if self._post_exc:
            raise self._post_exc
        return self._response


def _configure(
    monkeypatch,
    *,
    api_key="test-key",
    from_email="VeriTrust <noreply@veritrust.test>",
    base_url="https://api.resend.com",
    app_base_url="https://veritrust.test",
):
    settings = types.SimpleNamespace(
        resend_api_key=api_key,
        resend_from_email=from_email,
        resend_base_url=base_url,
        app_base_url=app_base_url,
    )
    monkeypatch.setattr(email, "get_settings", lambda: settings)


def _patch_client(monkeypatch, recorder, *, post_exc=None, response=None):
    def factory(**kwargs):
        return _FakeAsyncClient(recorder, post_exc=post_exc, response=response)

    monkeypatch.setattr(email.httpx, "AsyncClient", factory)


async def test_ready_email_posts_to_resend(monkeypatch):
    _configure(monkeypatch)
    recorder: list[dict] = []
    _patch_client(monkeypatch, recorder)

    await email.send_analysis_ready_email(
        to="user@example.com", analysis_id=ANALYSIS_ID
    )

    assert len(recorder) == 1
    req = recorder[0]
    assert req["url"] == "https://api.resend.com/emails"
    assert req["headers"]["Authorization"] == "Bearer test-key"
    assert req["json"]["from"] == "VeriTrust <noreply@veritrust.test>"
    assert req["json"]["to"] == ["user@example.com"]
    assert req["json"]["subject"]
    assert f"https://veritrust.test/app/analisis/{ANALYSIS_ID}" in req["json"]["html"]
    assert f"https://veritrust.test/app/analisis/{ANALYSIS_ID}" in req["json"]["text"]


async def test_failed_email_uses_failure_subject(monkeypatch):
    _configure(monkeypatch)
    recorder: list[dict] = []
    _patch_client(monkeypatch, recorder)

    await email.send_analysis_failed_email(
        to="user@example.com", analysis_id=ANALYSIS_ID
    )

    assert len(recorder) == 1
    assert "no pudo" in recorder[0]["json"]["subject"].lower()
    assert f"/app/analisis/{ANALYSIS_ID}" in recorder[0]["json"]["html"]


async def test_no_claims_email_uses_neutral_subject(monkeypatch):
    _configure(monkeypatch)
    recorder: list[dict] = []
    _patch_client(monkeypatch, recorder)

    await email.send_analysis_no_claims_email(
        to="user@example.com", analysis_id=ANALYSIS_ID
    )

    assert len(recorder) == 1
    subject = recorder[0]["json"]["subject"].lower()
    assert "afirmaciones médicas" in subject
    assert "no pudo" not in subject
    assert f"/app/analisis/{ANALYSIS_ID}" in recorder[0]["json"]["html"]


async def test_no_send_without_api_key(monkeypatch):
    _configure(monkeypatch, api_key=None)
    recorder: list[dict] = []
    _patch_client(monkeypatch, recorder)

    await email.send_analysis_ready_email(
        to="user@example.com", analysis_id=ANALYSIS_ID
    )

    assert recorder == []


async def test_no_send_without_recipient(monkeypatch):
    _configure(monkeypatch)
    recorder: list[dict] = []
    _patch_client(monkeypatch, recorder)

    await email.send_analysis_ready_email(to=None, analysis_id=ANALYSIS_ID)

    assert recorder == []


async def test_no_send_without_app_base_url(monkeypatch):
    _configure(monkeypatch, app_base_url=None)
    recorder: list[dict] = []
    _patch_client(monkeypatch, recorder)

    await email.send_analysis_ready_email(
        to="user@example.com", analysis_id=ANALYSIS_ID
    )
    await email.send_analysis_failed_email(
        to="user@example.com", analysis_id=ANALYSIS_ID
    )

    assert recorder == []


async def test_send_swallows_http_errors(monkeypatch):
    _configure(monkeypatch)
    recorder: list[dict] = []
    _patch_client(monkeypatch, recorder, post_exc=httpx.ConnectError("boom"))

    # No debe propagar: el envío es best-effort y nunca rompe el análisis.
    await email.send_analysis_ready_email(
        to="user@example.com", analysis_id=ANALYSIS_ID
    )

    assert len(recorder) == 1
