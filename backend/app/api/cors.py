"""Configuración y validación de CORS para la API."""

from __future__ import annotations

import os
from typing import TypedDict


class CORSConfig(TypedDict):
    """Configuración tipada para CORSMiddleware."""

    allow_origins: list[str]
    allow_credentials: bool
    allow_methods: list[str]
    allow_headers: list[str]


def _parse_allowed_origins(origins_raw: str) -> list[str]:
    """Parsea CORS_ALLOWED_ORIGINS separada por comas, limpiando espacios."""
    return [origin.strip() for origin in origins_raw.split(",") if origin.strip()]


def _parse_env_bool(name: str, default: bool) -> bool:
    """Parsea una variable de entorno booleana de forma estricta."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False

    raise ValueError(
        f"{name} debe ser un booleano válido (true/false, 1/0, yes/no, on/off)."
    )


def get_cors_config() -> CORSConfig:
    """Construye la configuración CORS a partir del entorno."""
    environment = os.getenv("ENVIRONMENT", "production").strip().lower()
    allow_credentials = _parse_env_bool("CORS_ALLOW_CREDENTIALS", default=True)

    if environment == "development":
        allowed_origins = _parse_allowed_origins(
            os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
        )
    else:
        allowed_origins = _parse_allowed_origins(os.getenv("CORS_ALLOWED_ORIGINS", ""))
        if not allowed_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS no está configurado para producción")

    if allow_credentials and "*" in allowed_origins:
        raise ValueError(
            "CORS_ALLOWED_ORIGINS no puede contener '*' cuando allow_credentials=True"
        )

    return {
        "allow_origins": allowed_origins,
        "allow_credentials": allow_credentials,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
