"""Per-domain idempotency / audit state under .state/<domain>/<name>.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

STATE_ROOT = Path(".state")


class StateSchemaError(RuntimeError):
    """Raised when a state file's schema_version doesn't match what the loader expects."""


def _path(domain: str, name: str) -> Path:
    return STATE_ROOT / domain / f"{name}.json"


def load_state(domain: str, name: str) -> dict | None:
    """Return the parsed JSON state file, or None if missing."""
    p = _path(domain, name)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_state_v(domain: str, name: str, *, expected_version: int) -> dict | None:
    """Load state and verify its ``schema_version`` matches ``expected_version``.

    Returns ``None`` if the file is missing.

    Raises ``StateSchemaError`` if the file exists but its ``schema_version`` field
    is absent or does not match ``expected_version``. This makes resume loaders
    fail loudly on stale-shape files instead of silently misinterpreting them.
    """
    data = load_state(domain, name)
    if data is None:
        return None
    actual = data.get("schema_version")
    if actual != expected_version:
        raise StateSchemaError(
            f"State file .state/{domain}/{name}.json has schema_version={actual!r}; "
            f"expected {expected_version}. Migrate or delete the file before resuming."
        )
    return data


def save_state(domain: str, name: str, data: dict, *, schema_version: int = 1) -> None:
    """Atomically write a state file (tmp + os.replace).

    Writes a ``schema_version`` key (default 1) as the first field of the payload
    so future loaders can fail loudly on shape changes via ``load_state_v``.
    Any ``schema_version`` already present in ``data`` is overridden by the
    keyword argument.
    """
    p = _path(domain, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": schema_version,
        **{k: v for k, v in data.items() if k != "schema_version"},
    }
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, p)
