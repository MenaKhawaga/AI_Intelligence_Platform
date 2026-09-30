"""Logging configuration.

Provides a single ``setup_logging()`` entry point that configures the root
logger once (called from ``main.py`` on startup), and a ``get_logger()``
helper other modules can use instead of calling ``logging.getLogger``
directly. This replaces the old project's ``app/utils/logger.py``, which
does not exist in the new architecture — logging now lives in
``app/config`` per the target structure.
"""

from __future__ import annotations

import logging
import sys

from app.core.config import settings

_CONFIGURED = False

_TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_JSON_FORMAT = (
    '{"time": "%(asctime)s", "level": "%(levelname)s", '
    '"logger": "%(name)s", "message": "%(message)s"}'
)


def setup_logging() -> None:
    """Configure the root logger based on application settings.

    Safe to call more than once; only configures handlers on first call.
    """

    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    fmt = _JSON_FORMAT if settings.LOG_FORMAT.lower() == "json" else _TEXT_FORMAT

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger, ensuring logging is configured."""

    setup_logging()
    return logging.getLogger(name)
