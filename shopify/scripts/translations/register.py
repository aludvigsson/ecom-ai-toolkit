"""Register Shopify translations from a CSV via translationsRegister.

CSV columns (all required, all non-empty):
  - ``resource_id``: the GID of the translatable resource
  - ``locale``: locale code, e.g. ``sv-SE``
  - ``key``: translatable content key, e.g. ``title``
  - ``value``: the translated value
  - ``translatable_content_digest``: the digest from the source ``translatableContent``

The digest is mandatory: it ensures the translation is attached to the version
of the source the caller actually saw. Rows are grouped by ``resource_id`` and
the mutation is called once per group.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys
from pathlib import Path

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args
from shopify.utils.client import ShopifyClient, check_user_errors
from shopify.utils.csv_io import read_csv_dicts

_REQUIRED_COLUMNS = (
    "resource_id",
    "locale",
    "key",
    "value",
    "translatable_content_digest",
)

_MUTATION = """
mutation TranslationsRegister($resourceId: ID!, $translations: [TranslationInput!]!) {
  translationsRegister(resourceId: $resourceId, translations: $translations) {
    translations { key locale value }
    userErrors { field message code }
  }
}
"""


def _validate_row(row: dict[str, str], row_index: int) -> None:
    """Raise RuntimeError if any required column is missing or empty."""
    for col in _REQUIRED_COLUMNS:
        value = (row.get(col) or "").strip()
        if not value:
            raise RuntimeError(
                f"CSV row {row_index} is missing required column {col!r} (row: {row!r})"
            )


def _group_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for idx, row in enumerate(rows, start=1):
        _validate_row(row, idx)
        grouped.setdefault(row["resource_id"], []).append(row)
    return grouped


def _row_to_translation_input(row: dict[str, str]) -> dict[str, str]:
    return {
        "key": row["key"],
        "locale": row["locale"],
        "value": row["value"],
        "translatableContentDigest": row["translatable_content_digest"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Register translations from a CSV via translationsRegister."
    )
    add_common_flags(parser)
    parser.add_argument(
        "--from-csv",
        dest="from_csv",
        required=True,
        help="Path to CSV with resource_id,locale,key,value,translatable_content_digest",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    csv_path = Path(args.from_csv)
    rows = list(read_csv_dicts(csv_path))
    grouped = _group_rows(rows)

    if args.dry_run:
        for resource_id, group in grouped.items():
            print(f"Would register {len(group)} translations for {resource_id}")
        return 0

    cfg = load_config(args.config)

    with ShopifyClient(config=cfg) as client:
        for resource_id, group in grouped.items():
            translations = [_row_to_translation_input(r) for r in group]
            data = client.graphql(
                _MUTATION,
                {"resourceId": resource_id, "translations": translations},
            )
            check_user_errors(data, mutation="translationsRegister")
    return 0


if __name__ == "__main__":
    sys.exit(main())
