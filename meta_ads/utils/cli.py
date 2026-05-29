"""Shared argparse + output helpers for meta_ads/scripts/.

A near-copy of klaviyo/utils/cli.py (duplicated rather than imported to avoid
coupling domains; promoting to core/cli.py is a deferred follow-up — spec
§3.2). Adds add_meta_flags for the domain-specific --api-version/--yes flags.
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any


def add_common_flags(parser: argparse.ArgumentParser) -> None:
    """Register the conventions every meta_ads/scripts/* script supports."""
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip writes; print the Graph request and exit 0",
    )
    parser.add_argument(
        "--output",
        choices=("table", "json", "markdown"),
        default="table",
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--config", default="store-config.yaml")
    parser.add_argument("--verbose", action="store_true")


def add_meta_flags(parser: argparse.ArgumentParser) -> None:
    """Register Meta-specific flags.

    --api-version overrides the Graph API version the client otherwise reads
    from domains.meta_ads.api_version. --yes confirms high-stakes operations
    (gated writes land in Plan M2/M3; the flag surface is registered now so it
    is stable across the domain).
    """
    parser.add_argument(
        "--api-version",
        dest="api_version",
        default=None,
        help="Override the Graph API version (default: config api_version)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm a high-stakes operation (required for live execution)",
    )


def configure_logging_from_args(args: argparse.Namespace) -> None:
    """Honor --verbose by raising the ecom.* logger to DEBUG."""
    if getattr(args, "verbose", False):
        logging.getLogger("ecom").setLevel(logging.DEBUG)


def format_output(data: Any, fmt: str) -> str:
    """Format data as a table (default), JSON, or Markdown table."""
    if fmt == "json":
        return json.dumps(data, indent=2, default=str)
    if fmt == "markdown":
        if isinstance(data, list):
            return _markdown_table(data)
        return f"```json\n{json.dumps(data, indent=2, default=str)}\n```"
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
