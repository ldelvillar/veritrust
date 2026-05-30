"""Pool de conexiones compartido y utilidades base de persistencia."""

from __future__ import annotations

import logging

from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_DATABASE_CONFIGURATION_HINT = (
    "Revisa DATABASE_URL y que el servicio de PostgreSQL esté accesible."
)


class DatabaseError(RuntimeError):
    """Error base para operaciones de persistencia."""


def _build_connection_string() -> str:
    """Obtiene la cadena de conexion desde la configuracion central."""
    db_url = get_settings().database_url
    if not db_url:
        raise DatabaseError("No se encontro la variable de entorno DATABASE_URL.")

    return db_url


def _build_database_error(context_message: str) -> str:
    """Construye mensajes de error de BD consistentes para todas las operaciones."""
    return f"{context_message} {_DATABASE_CONFIGURATION_HINT}"


_pool: AsyncConnectionPool | None = None


async def get_pool() -> AsyncConnectionPool:
    """Devuelve un pool async compartido, abriéndolo bajo demanda."""
    global _pool
    if _pool is None:
        conninfo = _build_connection_string()
        pool = AsyncConnectionPool(conninfo, min_size=1, max_size=10, open=False)
        await pool.open()
        _pool = pool
    return _pool


async def close_pool() -> None:
    """Cierra el pool si está abierto. Llamado desde el lifespan."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
