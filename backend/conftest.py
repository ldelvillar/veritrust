"""Hooks shared by the app and evaluation test suites."""

import os

from app.core.config import get_settings


def pytest_configure(config):
    """Turn Langfuse off before any test imports the tracing client or an @observe'd function."""
    os.environ["LANGFUSE_PUBLIC_KEY"] = ""
    os.environ["LANGFUSE_SECRET_KEY"] = ""
    os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
    get_settings.cache_clear()
