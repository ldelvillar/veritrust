"""Disposable PostgreSQL for the 'db' tests, from ``TEST_DATABASE_URL`` or Docker, skipping the suite when neither is available."""

import asyncio
import os
import subprocess
import time
from contextlib import asynccontextmanager

import psycopg
import pytest

import app.db.pool as pool_module
from app.db.migrate import apply_migrations


def pytest_asyncio_loop_factories(config, item):
    """Async psycopg does not work on ProactorEventLoop, so a selector loop is forced."""
    return {"selector": asyncio.SelectorEventLoop}


_IMAGE = "postgres:16-alpine"
_SKIP_REASON = (
    "Pruebas 'db' omitidas: define TEST_DATABASE_URL o arranca Docker "
    "para levantar un PostgreSQL efímero."
)


def _wait_for_postgres(dsn: str, timeout_seconds: float) -> None:
    """Wait for the server to accept connections within the given time."""
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(dsn, connect_timeout=3):
                return
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"PostgreSQL no respondió a tiempo: {last_error}")


def _docker(*args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["docker", *args], capture_output=True, text=True)
    except OSError as exc:
        # Without the docker CLI installed, treat it like a stopped daemon.
        return subprocess.CompletedProcess(["docker", *args], 1, "", str(exc))


@pytest.fixture(scope="session")
def postgres_dsn():
    """Return the DSN of a test PostgreSQL, starting one if needed."""
    configured = os.environ.get("TEST_DATABASE_URL")
    if configured:
        _wait_for_postgres(configured, timeout_seconds=10)
        yield configured
        return

    if _docker("info").returncode != 0:
        pytest.skip(_SKIP_REASON)

    started = _docker(
        "run",
        "--detach",
        "--rm",
        "--env",
        "POSTGRES_USER=veritrust",
        "--env",
        "POSTGRES_PASSWORD=veritrust-test",
        "--env",
        "POSTGRES_DB=veritrust_test",
        "--publish",
        "127.0.0.1:0:5432",
        _IMAGE,
    )
    if started.returncode != 0:
        pytest.skip(f"No se pudo arrancar PostgreSQL: {started.stderr.strip()}")

    container_id = started.stdout.strip()
    try:
        port_output = _docker("port", container_id, "5432/tcp").stdout
        host_port = port_output.strip().splitlines()[0].rsplit(":", 1)[1]
        dsn = (
            "postgresql://veritrust:veritrust-test"
            f"@127.0.0.1:{host_port}/veritrust_test"
        )
        _wait_for_postgres(dsn, timeout_seconds=90)
        yield dsn
    finally:
        _docker("stop", container_id)


@pytest.fixture(scope="session")
def database_schema(postgres_dsn):
    """Apply the real deployment migrations once per session."""
    apply_migrations(postgres_dsn)
    return postgres_dsn


@pytest.fixture
async def db_pool(database_schema, monkeypatch):
    """Open the app's real pool against the test PostgreSQL, with a clean table."""
    monkeypatch.setattr(
        pool_module, "_build_connection_string", lambda: database_schema
    )
    # Each test runs in its own event loop, so the pool must be born and die with it.
    assert pool_module._pool is None, "Otro test dejó el pool global abierto"
    pool = await pool_module.get_pool()
    try:
        async with pool.connection() as conn:
            # CASCADE takes analysis_feedback and usage_events along, which reference the History.
            await conn.execute(
                "TRUNCATE public.analysis_history, public.billing_customers, "
                "public.subscriptions, public.stripe_events CASCADE"
            )
        yield pool
    finally:
        await pool_module.close_pool()


class _FaultyCursor:
    """Real cursor that raises a psycopg error on the marked statements."""

    def __init__(self, cursor, faults):
        self._cursor = cursor
        self._faults = faults

    async def __aenter__(self):
        await self._cursor.__aenter__()
        return self

    async def __aexit__(self, *exc_info):
        return await self._cursor.__aexit__(*exc_info)

    async def execute(self, query, params=None):
        if any(marker in query for marker in self._faults.markers):
            raise psycopg.OperationalError("fallo inyectado por la prueba")
        return await self._cursor.execute(query, params)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _FaultyConnection:
    """Real connection whose cursors fail on the marked statements."""

    def __init__(self, conn, faults):
        self._conn = conn
        self._faults = faults

    def cursor(self, *args, **kwargs):
        return _FaultyCursor(self._conn.cursor(*args, **kwargs), self._faults)

    def __getattr__(self, name):
        return getattr(self._conn, name)


class DatabaseFaults:
    """Real pool that only fails the statements containing a marker."""

    def __init__(self, pool):
        self._pool = pool
        self.markers: list[str] = []

    def fail_on(self, marker: str) -> None:
        """Fail from now on every SQL statement containing ``marker``."""
        self.markers.append(marker)

    @asynccontextmanager
    async def connection(self):
        async with self._pool.connection() as conn:
            yield _FaultyConnection(conn, self)


@pytest.fixture
async def db_faults(db_pool):
    """Replace the app's pool with one that fails on the marked statements."""
    faults = DatabaseFaults(db_pool)
    pool_module._pool = faults
    try:
        yield faults
    finally:
        # Restored before db_pool closes the real pool.
        pool_module._pool = db_pool
