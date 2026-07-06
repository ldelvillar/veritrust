"""Configuración de logging centralizada para la API."""

import json
import logging
from datetime import datetime, timezone
from logging.config import dictConfig

from app.core.config import get_settings

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


class JsonFormatter(logging.Formatter):
    """Emite cada registro como una línea JSON con severity, apta para Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Configura el root logger con un único handler a stdout (texto o JSON según LOG_FORMAT)."""
    use_json = get_settings().log_format.strip().lower() == "json"
    formatter: dict = {"()": JsonFormatter} if use_json else {"format": _LOG_FORMAT}
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": formatter,
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
