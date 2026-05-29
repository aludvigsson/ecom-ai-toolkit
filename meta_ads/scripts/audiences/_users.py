"""Shared helpers for audience membership writes (add_users / remove_users).

Meta's customer-file matching requires identifiers to be normalized (trimmed +
lowercased) and SHA-256-hashed before transmission. Both membership scripts send
a Graph ``payload`` object ``{"schema": <SCHEMA>, "data": [[<hash>], ...]}``
JSON-encoded as the ``payload`` form/query param.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

# Map the user-facing identifier kind to the Graph schema name.
_SCHEMAS = {
    "email": "EMAIL_SHA256",
    "phone": "PHONE_SHA256",
}


def schema_for(kind: str) -> str:
    """Return the Graph schema name for an identifier kind ('email'/'phone')."""
    try:
        return _SCHEMAS[kind]
    except KeyError:
        raise ValueError(f"unsupported identifier kind: {kind!r}") from None


def normalize(value: str) -> str:
    """Trim surrounding whitespace and lowercase (Meta's required pre-hash form)."""
    return value.strip().lower()


def hash_value(value: str) -> str:
    """Normalize then SHA-256-hash an identifier, returning the hex digest."""
    return hashlib.sha256(normalize(value).encode("utf-8")).hexdigest()


def build_payload(schema: str, values: list[str]) -> dict:
    """Build the Graph payload object: schema + one single-element row per hash."""
    return {"schema": schema, "data": [[hash_value(v)] for v in values]}


def payload_param(schema: str, values: list[str]) -> str:
    """Return the JSON-encoded payload string for the Graph ``payload`` param."""
    return json.dumps(build_payload(schema, values))


def load_identifiers(args: argparse.Namespace) -> list[str]:
    """Collect identifiers from --value (repeatable) or --value-file (one per line).

    Raises ValueError when neither is given or the result is empty.
    """
    if args.value:
        values = list(args.value)
    elif args.value_file:
        text = Path(args.value_file).read_text(encoding="utf-8")
        values = [line.strip() for line in text.splitlines() if line.strip()]
    else:
        raise ValueError("provide identifiers via --value or --value-file")
    if not values:
        raise ValueError("no identifiers found")
    return values
