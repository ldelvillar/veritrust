"""Hooks shared by the app and evaluation test suites."""

import os

from hypothesis import settings

from app.core.config import get_settings

# No per-example deadline, since a busy machine would otherwise fail a correct property on timing alone.
settings.register_profile("local", deadline=None)
# CI replays the same examples every run, so a property fails there only on a change, never on a fresh draw.
settings.register_profile("ci", parent=settings.get_profile("local"), derandomize=True)
settings.load_profile("ci" if os.environ.get("CI") else "local")


def pytest_configure(config):
    """Turn Langfuse off before any test imports the tracing client or an @observe'd function."""
    os.environ["LANGFUSE_PUBLIC_KEY"] = ""
    os.environ["LANGFUSE_SECRET_KEY"] = ""
    os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
    get_settings.cache_clear()
