"""Tests de la sonda de liveness del worker basada en el heartbeat de arq en Redis."""

from arq.connections import RedisSettings

import app.worker_healthcheck as healthcheck
from app.core.config import get_settings


def test_main_probes_the_configured_redis(monkeypatch):
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
