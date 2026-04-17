"""Este módulo contiene funciones de utilidad para la API."""

import time
from collections import defaultdict

from fastapi import HTTPException

rate_limit = defaultdict(list)


def check_rate_limit(user_id: str) -> None:
    """Función para limitar la cantidad de solicitudes por usuario."""
    now = time.time()
    window = 60
    max_requests = 5

    requests = rate_limit[user_id]
    requests = [r for r in requests if now - r < window]

    if len(requests) >= max_requests:
        raise HTTPException(status_code=429, detail="Too many requests")

    requests.append(now)
    rate_limit[user_id] = requests
