"""Dependencias del Plan del usuario: sus límites, las funciones que exige una ruta y su History window."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from fastapi import Depends, HTTPException

from app.api.dependencies.get_current_user import get_current_user
from app.core.errors import make_error_detail
from app.core.plans import Feature, PlanLimits, history_floor, limits_for
from app.db.billing import get_user_subscription
from app.db.pool import DatabaseError
from app.schemas.errors import ErrorCode


async def current_plan(user: dict = Depends(get_current_user)) -> PlanLimits:
    """Lee el Plan del usuario en cada petición, sin caché, para que un webhook surta efecto en la siguiente."""
    try:
        subscription = await get_user_subscription(user["sub"])
    except DatabaseError as exc:
        raise HTTPException(
            status_code=500, detail=make_error_detail(ErrorCode.BILLING_FETCH_FAILED)
        ) from exc
    return limits_for(subscription)


def plan_required() -> HTTPException:
    """El rechazo de una función que el Plan del usuario no incluye."""
    return HTTPException(
        status_code=403, detail=make_error_detail(ErrorCode.PLAN_REQUIRED)
    )


def require(feature: Feature) -> Callable[..., Awaitable[PlanLimits]]:
    """Crea una dependencia que responde 403 PLAN_REQUIRED si el Plan no incluye ``feature``."""

    async def dependency(limits: PlanLimits = Depends(current_plan)) -> PlanLimits:
        if not getattr(limits, feature):
            raise plan_required()
        return limits

    return dependency


async def history_window(
    limits: PlanLimits = Depends(current_plan),
) -> datetime | None:
    """Devuelve el instante más antiguo de la History que ve el Plan, o None si la ve entera."""
    return history_floor(limits, datetime.now(UTC))
