"""Infraestructura de las pruebas 'db': un PostgreSQL real, desechable y aislado.

Resolución del servidor, en orden: la variable ``TEST_DATABASE_URL`` si está
definida; si no, un contenedor efímero ``postgres:16-alpine`` en un puerto
aleatorio de localhost vía Docker. Sin ninguna de las dos opciones, la suite
se omite con un aviso claro en lugar de fallar.
"""

import asyncio
import os
import subprocess
import time
from pathlib import Path

import psycopg
import pytest

import app.db.pool as pool_module


def pytest_asyncio_loop_factories(config, item):
    """psycopg async no funciona sobre ProactorEventLoop; forzamos un selector loop."""
    return {"selector": asyncio.SelectorEventLoop}


_IMAGE = "postgres:16-alpine"
_INIT_SQL = Path(__file__).resolve().parents[2] / "db" / "init.sql"
_SKIP_REASON = (
    "Pruebas 'db' omitidas: define TEST_DATABASE_URL o arranca Docker "
    "para levantar un PostgreSQL efímero."
)


def _wait_for_postgres(dsn: str, timeout_seconds: float) -> None:
    """Espera a que el servidor acepte conexiones dentro del plazo dado."""
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
        # Sin CLI de docker instalada: se trata igual que un daemon apagado.
        return subprocess.CompletedProcess(["docker", *args], 1, "", str(exc))


@pytest.fixture(scope="session")
def postgres_dsn():
    """Devuelve el DSN de un PostgreSQL de pruebas, arrancándolo si hace falta."""
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
    """Aplica el esquema real de despliegue (db/init.sql) una vez por sesión."""
    with psycopg.connect(postgres_dsn) as conn:
        conn.execute(_INIT_SQL.read_text(encoding="utf-8"))
        conn.commit()
    return postgres_dsn


@pytest.fixture
async def db_pool(database_schema, monkeypatch):
    """Abre el pool real de la app contra el PostgreSQL de pruebas, con tabla limpia."""
    monkeypatch.setattr(
        pool_module, "_build_connection_string", lambda: database_schema
    )
    # Cada test corre en su propio event loop: el pool debe nacer y morir con él.
    assert pool_module._pool is None, "Otro test dejó el pool global abierto"
    pool = await pool_module.get_pool()
    try:
        async with pool.connection() as conn:
            await conn.execute("TRUNCATE public.analysis_history")
        yield pool
    finally:
        await pool_module.close_pool()
