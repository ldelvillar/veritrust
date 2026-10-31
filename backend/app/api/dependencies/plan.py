"""Dependencies on the user's Plan: its limits, the features a route needs and its History window."""

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
    """Read the user's Plan on every request, uncached, so a webhook takes effect on the next one."""
    try:
        subscription = await get_user_subscription(user["sub"])
    except DatabaseError as exc:
        raise HTTPException(
            status_code=500, detail=make_error_detail(ErrorCode.BILLING_FETCH_FAILED)
        ) from exc
    return limits_for(subscription)


def plan_required() -> HTTPException:
    """Refusal of a feature the user's Plan does not include."""
    return HTTPException(
        status_code=403, detail=make_error_detail(ErrorCode.PLAN_REQUIRED)
    )


def require(feature: Feature) -> Callable[..., Awaitable[PlanLimits]]:
    """Create a dependency that answers 403 PLAN_REQUIRED when the Plan lacks ``feature``."""

    async def dependency(limits: PlanLimits = Depends(current_plan)) -> PlanLimits:
        if not getattr(limits, feature):
            raise plan_required()
        return limits

    return dependency


async def history_window(
    limits: PlanLimits = Depends(current_plan),
) -> datetime | None:
    """Return the oldest instant of the History the Plan sees, or None when it sees all of it."""
    return history_floor(limits, datetime.now(UTC))
