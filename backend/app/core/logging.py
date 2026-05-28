"""Configuración de logging centralizada para la API."""

from logging.config import dictConfig

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configura el root logger con un único handler a stdout."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": _LOG_FORMAT},
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "root": {"level": level, "handlers": ["stdout"]},
            "loggers": {
                "app": {"level": level, "propagate": True},
            },
        }
    )
