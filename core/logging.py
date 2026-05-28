"""Stdlib logging wrapper. One consistent format across the toolkit."""

from __future__ import annotations

import logging
import os
import sys

_LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"
_configured = False


def _configure_once() -> None:
    global _configured
    if _configured:
        return
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger. Configures stdlib logging on first call."""
    _configure_once()
    return logging.getLogger(name)
