import logging
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    """Configure JSON-style structured logging."""

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": "{asctime} | {levelname} | {name} | {message}",
                    "style": "{",
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "level": level,
                }
            },
            "root": {
                "handlers": ["default"],
                "level": level,
            },
        }
    )


configure_logging()
