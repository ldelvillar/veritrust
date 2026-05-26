"""Dependencia para comprobar el límite de tasa del usuario."""

import time
from collections import defaultdict

from fastapi import Depends, HTTPException

from app.api.dependencies.get_current_user import get_current_user

rate_limit: defaultdict[str, list[float]] = defaultdict(list)


def check_rate_limit(user: dict = Depends(get_current_user)) -> dict:
    """Dependencia que verifica el rate limit del usuario autenticado."""
    user_id = user["sub"]
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")

    now = time.time()
    window = 60
    max_requests = 5

    requests = [r for r in rate_limit[user_id] if now - r < window]

    if len(requests) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail="Has superado el límite de peticiones. Intenta de nuevo en un minuto.",
        )

    requests.append(now)
    rate_limit[user_id] = requests

    return user
