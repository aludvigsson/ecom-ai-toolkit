"""Shared CSV helpers for bulk scripts."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path


def read_csv_dicts(path: str | Path) -> Iterator[dict[str, str]]:
    """Yield each row of a CSV file as a dict keyed by the header row."""
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)
