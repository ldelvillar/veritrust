"""Endpoint de readiness para load balancers."""

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request

from app.db.pool import get_pool

router = APIRouter()
logger = logging.getLogger(__name__)

_HEALTHCHECK_TIMEOUT_SECONDS = 2.0


async def _check_database() -> None:
    """Comprueba que la base de datos responde con una consulta trivial."""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")


async def _check_redis(redis: object) -> None:
    """Comprueba que Redis responde a un PING."""
    await redis.ping()  # type: ignore[attr-defined]


@router.get("/healthz")
async def healthz(request: Request):
    """
    Comprueba que todos los servicios están activos. Devuelve
    503 salvo que la cola, la base de datos y Redis respondan.
    """
    arq_pool = getattr(request.app.state, "arq_pool", None)
    redis = getattr(request.app.state, "redis", None)
    if arq_pool is None or redis is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        async with asyncio.timeout(_HEALTHCHECK_TIMEOUT_SECONDS):
            await _check_database()
            await _check_redis(redis)
    except Exception:
        logger.warning("Healthcheck falló: base de datos o Redis no responden")
        raise HTTPException(status_code=503, detail="Service not ready") from None

    return {"status": "ready"}
