"""Dependencia para comprobar el límite de tasa del usuario."""

import time
from collections import defaultdict

from fastapi import Depends, HTTPException

from app.api.dependencies.get_current_user import get_current_user
from app.core.errors import make_error_detail
from app.schemas.errors import ErrorCode

rate_limit: defaultdict[str, list[float]] = defaultdict(list)


async def check_rate_limit(user: dict = Depends(get_current_user)) -> dict:
    """Dependencia que verifica el rate limit del usuario autenticado."""
    user_id = user["sub"]
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail=make_error_detail(ErrorCode.INVALID_TOKEN),
        )

    now = time.time()
    window = 60
    max_requests = 5

    requests = [r for r in rate_limit[user_id] if now - r < window]

    if len(requests) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail=make_error_detail(ErrorCode.RATE_LIMIT),
        )

    requests.append(now)
    rate_limit[user_id] = requests

    return user
