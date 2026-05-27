"""Configuración de CORS para la API, derivada de la configuración central."""

from __future__ import annotations

from typing import TypedDict

from app.core.config import Settings


class CORSConfig(TypedDict):
    """Configuración tipada para CORSMiddleware."""

    allow_origins: list[str]
    allow_credentials: bool
    allow_methods: list[str]
    allow_headers: list[str]


def get_cors_config(settings: Settings) -> CORSConfig:
    """Construye la configuración CORS a partir de la configuración central."""
    return {
        "allow_origins": settings.cors_origins(),
        "allow_credentials": settings.cors_allow_credentials,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
