"""Load and access per-store secrets from .env.local."""

from __future__ import annotations

import os
from pathlib import Path


class MissingSecretError(RuntimeError):
    """Raised when a required secret is not set."""


_env_loaded = False


def load_env_local(path: str | Path = ".env.local") -> None:
    """Parse a simple KEY=value .env file and set into os.environ.

    Lines starting with '#' and blank lines are skipped. Values are not
    quoted/expanded. Subsequent calls are idempotent.
    """
    global _env_loaded
    p = Path(path)
    if not p.exists():
        _env_loaded = True
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        # Don't clobber values already set in the real environment.
        os.environ.setdefault(key, value)
    _env_loaded = True


def _ensure_loaded() -> None:
    if not _env_loaded:
        load_env_local()


def get_secret(name: str) -> str | None:
    """Return a secret from the environment (loading .env.local first), or None."""
    _ensure_loaded()
    return os.environ.get(name) or None


def require_secret(name: str) -> str:
    """Return a secret or raise a clear MissingSecretError pointing at .env.local."""
    value = get_secret(name)
    if not value:
        raise MissingSecretError(
            f"Missing required secret {name!r}. "
            f"Add it to .env.local (see .env.example for the full list)."
        )
    return value
