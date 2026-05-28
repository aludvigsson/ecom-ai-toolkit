"""List Shopify translations for a single resource or sweep by resource type.

Two modes:
  - ``--resource-id <gid>``: queries one resource's translatable content and its
    existing translations at the supplied locale (``translatableResource``).
  - ``--resource-type <TYPE>``: sweeps all translatable resources of that type
    (``translatableResources``), e.g. PRODUCT, COLLECTION, EMAIL_TEMPLATE.

Both modes require ``--locale``. The result includes the source values + digests
needed to register translations via ``translationsRegister``.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys
from typing import Any

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args, format_output
from shopify.utils.client import ShopifyClient

_SINGLE_QUERY = """
query Translations($resourceId: ID!, $locale: String!) {
  translatableResource(resourceId: $resourceId) {
    resourceId
    translatableContent { key value digest locale }
    translations(locale: $locale) { key locale value }
  }
}
"""

_SWEEP_QUERY = """
query Translations($first: Int!, $resourceType: TranslatableResourceType!, $locale: String!) {
  translatableResources(first: $first, resourceType: $resourceType) {
    edges {
      node {
        resourceId
        translatableContent { key value digest locale }
        translations(locale: $locale) { key locale value }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def _summarize_node(node: dict[str, Any], locale: str) -> dict[str, Any]:
    return {
        "resourceId": node.get("resourceId"),
        "locale": locale,
        "translations": [
            {"key": t.get("key"), "value": t.get("value")} for t in (node.get("translations") or [])
        ],
        "translatable_keys": [
            {"key": c.get("key"), "value": c.get("value"), "digest": c.get("digest")}
            for c in (node.get("translatableContent") or [])
        ],
    }


def _flatten_for_table(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per (resourceId, key, source-value, translated-value)."""
    rows: list[dict[str, Any]] = []
    for summary in summaries:
        resource_id = summary.get("resourceId")
        locale = summary.get("locale")
        translated_by_key = {t["key"]: t.get("value") for t in summary.get("translations") or []}
        for entry in summary.get("translatable_keys") or []:
            rows.append(
                {
                    "resourceId": resource_id,
                    "locale": locale,
                    "key": entry.get("key"),
                    "source_value": entry.get("value"),
                    "translated_value": translated_by_key.get(entry.get("key")),
                }
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List translations for a Shopify resource or sweep by type."
    )
    add_common_flags(parser)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--resource-id", dest="resource_id", help="GID of a single resource")
    source.add_argument(
        "--resource-type",
        dest="resource_type",
        help="TranslatableResourceType (PRODUCT, COLLECTION, EMAIL_TEMPLATE, ...)",
    )
    parser.add_argument("--locale", required=True, help="Locale code, e.g. sv-SE")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)

    with ShopifyClient(config=cfg) as client:
        if args.resource_id:
            data = client.graphql(
                _SINGLE_QUERY,
                {"resourceId": args.resource_id, "locale": args.locale},
            )
            node = data.get("translatableResource") or {}
            summary = _summarize_node(node, args.locale)
            if args.output == "json":
                print(format_output(summary, args.output))
            else:
                print(format_output(_flatten_for_table([summary]), args.output))
            return 0

        data = client.graphql(
            _SWEEP_QUERY,
            {
                "first": args.limit,
                "resourceType": args.resource_type,
                "locale": args.locale,
            },
        )
        edges = (data.get("translatableResources") or {}).get("edges") or []
        summaries = [_summarize_node(edge["node"], args.locale) for edge in edges]
        if args.output == "json":
            print(format_output(summaries, args.output))
        else:
            print(format_output(_flatten_for_table(summaries), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
