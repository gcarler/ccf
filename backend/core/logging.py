import json
import logging
import uuid
from contextvars import ContextVar
from logging.config import dictConfig

from fastapi import Request

# Context variable to hold the current request ID
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        ctx_request_id = request_id_ctx.get()
        if ctx_request_id:
            log_entry["request_id"] = ctx_request_id
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging for production."""

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": JSONFormatter,
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


async def request_id_middleware(request: Request, call_next):
    """Inject a unique request ID into every request context and response header."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    token = request_id_ctx.set(request_id)

    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)

    response.headers["X-Request-ID"] = request_id
    return response


configure_logging()
