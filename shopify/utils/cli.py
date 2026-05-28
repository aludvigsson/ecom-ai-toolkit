"""Shared argparse + output helpers for shopify/scripts/.

Every Plan 2+ script uses these to keep CLI conventions identical:
--market, --dry-run, --output, --limit, --config, --verbose.
"""

from __future__ import annotations

import argparse
import json
from typing import Any


def add_common_flags(parser: argparse.ArgumentParser) -> None:
    """Register the six conventions every shopify/scripts/* script supports."""
    parser.add_argument("--market", help="Market code from store-config.yaml")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip writes; exercise read path",
    )
    parser.add_argument(
        "--output",
        choices=("table", "json", "markdown"),
        default="table",
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--config", default="store-config.yaml")
    parser.add_argument("--verbose", action="store_true")


def format_output(data: Any, fmt: str) -> str:
    """Format data as a table (default), JSON, or Markdown table.

    Lists of dicts render as tables; everything else renders as JSON.
    """
    if fmt == "json":
        return json.dumps(data, indent=2, default=str)
    if fmt == "markdown":
        if isinstance(data, list):
            return _markdown_table(data)
        return f"```json\n{json.dumps(data, indent=2, default=str)}\n```"
    # default: table
    if isinstance(data, list):
        return _plain_table(data)
    return json.dumps(data, indent=2, default=str)


def _plain_table(rows: list[dict]) -> str:
    if not rows:
        return "(no rows)"
    cols = list(rows[0].keys())
    widths = {c: max(len(c), max((len(str(r.get(c, ""))) for r in rows), default=0)) for c in cols}
    header = " | ".join(c.ljust(widths[c]) for c in cols)
    sep = "-+-".join("-" * widths[c] for c in cols)
    body = "\n".join(" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols) for r in rows)
    return f"{header}\n{sep}\n{body}"


def _markdown_table(rows: list[dict]) -> str:
    if not rows:
        return "_(no rows)_"
    cols = list(rows[0].keys())
    head = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = "\n".join("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in rows)
    return f"{head}\n{sep}\n{body}"
