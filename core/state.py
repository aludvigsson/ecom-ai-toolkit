"""Per-domain idempotency / audit state under .state/<domain>/<name>.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

STATE_ROOT = Path(".state")


def _path(domain: str, name: str) -> Path:
    return STATE_ROOT / domain / f"{name}.json"


def load_state(domain: str, name: str) -> dict | None:
    """Return the parsed JSON state file, or None if missing."""
    p = _path(domain, name)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(domain: str, name: str, data: dict) -> None:
    """Atomically write a state file (tmp + os.replace)."""
    p = _path(domain, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, p)
