"""Tests de la sonda de liveness del worker basada en el heartbeat de arq en Redis."""

from arq.connections import RedisSettings

import app.worker_healthcheck as healthcheck
from app.core.config import get_settings


def test_main_returns_zero_when_worker_heartbeat_is_fresh(monkeypatch):
    seen = {}

    async def fake_check(settings):
        seen["settings"] = settings
        return 0

    monkeypatch.setattr(healthcheck, "async_check_health", fake_check)

    assert healthcheck.main() == 0

    # La sonda debe mirar el mismo Redis que usa el worker según Settings.
    expected = RedisSettings.from_dsn(get_settings().redis_url)
    assert (seen["settings"].host, seen["settings"].port) == (
        expected.host,
        expected.port,
    )


def test_main_returns_one_when_worker_heartbeat_is_stale(monkeypatch):
    async def fake_check(settings):
        return 1

    monkeypatch.setattr(healthcheck, "async_check_health", fake_check)

    # Exit code 1 hace que el orquestador reinicie el contenedor del worker.
    assert healthcheck.main() == 1
