"""CORS configuration for the API, derived from the central configuration."""

from __future__ import annotations

from typing import TypedDict

from app.core.config import Settings


class CORSConfig(TypedDict):
    """Typed configuration for CORSMiddleware."""

    allow_origins: list[str]
    allow_credentials: bool
    allow_methods: list[str]
    allow_headers: list[str]


def get_cors_config(settings: Settings) -> CORSConfig:
    """Build the CORS configuration from the central configuration."""
    return {
        "allow_origins": settings.cors_origins(),
        "allow_credentials": settings.cors_allow_credentials,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
