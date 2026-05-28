"""Unified diff helper used by theme/update_asset.py.

Thin wrapper around stdlib difflib so future scripts (e.g. metafield
audit reports) can produce consistent diff output.
"""

from __future__ import annotations

import difflib


def make_diff(old: str, new: str, path: str = "asset") -> str:
    """Return a unified diff string for old → new.

    Empty string when there's no change.
    """
    return "\n".join(
        difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        )
    )
