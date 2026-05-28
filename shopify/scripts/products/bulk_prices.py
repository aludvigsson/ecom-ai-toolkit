"""Bulk-update variant prices from a CSV with resumable state.

CSV columns: ``variant_id`` OR ``sku``, ``price``, ``compare_at_price`` (optional).

For each row missing ``variant_id``, looks up the variant by SKU and caches
the result. Variants are grouped by product and pushed through
``productVariantsBulkUpdate`` in chunks of up to 250 per call. A state file
under ``.state/shopify/bulk_prices_<timestamp>.json`` tracks the resolved
SKU→variant map, the variant→product map, and the IDs of variants already
completed. Pass ``--resume <state-file>`` to continue from a prior run.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import load_config
from core.state import save_state
from shopify.utils.cli import add_common_flags
from shopify.utils.client import ShopifyClient, check_user_errors
from shopify.utils.csv_io import read_csv_dicts
from shopify.utils.search import escape_search_value

_CHUNK_SIZE = 250

_LOOKUP_QUERY = """
query VariantLookup($q: String!) {
  productVariants(first: 2, query: $q) {
    edges { node { id product { id } } }
  }
}
"""

_LOOKUP_BY_ID_QUERY = """
query VariantById($q: String!) {
  productVariants(first: 1, query: $q) {
    edges { node { id product { id } } }
  }
}
"""


class AmbiguousSkuError(RuntimeError):
    """Raised when a SKU lookup returns more than one variant."""

    def __init__(self, sku: str, variant_ids: list[str]) -> None:
        self.sku = sku
        self.variant_ids = variant_ids
        super().__init__(
            f"SKU {sku!r} matched {len(variant_ids)} variants: {', '.join(variant_ids)}. "
            f"Refusing to guess — use --csv with explicit variant_id column instead."
        )


class SkuNotFoundError(RuntimeError):
    """Raised when a SKU lookup returns zero variants."""

    def __init__(self, sku: str) -> None:
        self.sku = sku
        super().__init__(f"SKU {sku!r} not found")


_BULK_MUTATION = """
mutation Bulk($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id price compareAtPrice }
    userErrors { field message }
  }
}
"""


def _state_filename(ts: str) -> str:
    return f"bulk_prices_{ts}"


def _utc_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H%M%S")


def _load_resume(path: Path) -> dict:
    state = json.loads(path.read_text(encoding="utf-8"))
    state.setdefault("sku_to_variant_id", {})
    state.setdefault("completed_variant_ids", [])
    state.setdefault("variant_to_product", {})
    return state


def _save_state_to_path(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    return list(read_csv_dicts(csv_path))


def _resolve_variant(
    client: ShopifyClient,
    *,
    sku: str | None,
    variant_id: str | None,
    state: dict,
) -> tuple[str, str] | None:
    """Return (variant_id, product_id) for a row, caching lookups in state.

    Returns None if no variant could be located.
    """
    if variant_id:
        product_id = state["variant_to_product"].get(variant_id)
        if product_id:
            return variant_id, product_id
        data = client.graphql(_LOOKUP_BY_ID_QUERY, {"q": f"id:{variant_id.rsplit('/', 1)[-1]}"})
        edges = data.get("productVariants", {}).get("edges", [])
        if not edges:
            return None
        node = edges[0]["node"]
        product_id = node["product"]["id"]
        state["variant_to_product"][variant_id] = product_id
        return variant_id, product_id

    if sku:
        cached = state["sku_to_variant_id"].get(sku)
        if cached:
            product_id = state["variant_to_product"].get(cached)
            if product_id:
                return cached, product_id
        data = client.graphql(_LOOKUP_QUERY, {"q": f"sku:'{escape_search_value(sku)}'"})
        edges = data.get("productVariants", {}).get("edges", [])
        if not edges:
            raise SkuNotFoundError(sku)
        if len(edges) > 1:
            raise AmbiguousSkuError(sku, [e["node"]["id"] for e in edges])
        node = edges[0]["node"]
        vid = node["id"]
        product_id = node["product"]["id"]
        state["sku_to_variant_id"][sku] = vid
        state["variant_to_product"][vid] = product_id
        return vid, product_id

    return None


def _build_variant_input(row: dict[str, str], variant_id: str) -> dict[str, Any]:
    inp: dict[str, Any] = {"id": variant_id, "price": row["price"]}
    compare = (row.get("compare_at_price") or "").strip()
    if compare:
        inp["compareAtPrice"] = compare
    return inp


def _chunk(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bulk-update variant prices from a CSV with resumable state."
    )
    add_common_flags(parser)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-csv", dest="from_csv", help="Path to CSV of price updates")
    source.add_argument("--resume", help="Path to a prior bulk_prices state file")
    args = parser.parse_args(argv)

    # Build / load state
    if args.resume:
        state_path = Path(args.resume)
        state = _load_resume(state_path)
        csv_path = Path(state["csv_path"])
    else:
        ts = _utc_timestamp()
        csv_path = Path(args.from_csv)
        state = {
            "started_at": ts,
            "csv_path": str(csv_path),
            "sku_to_variant_id": {},
            "completed_variant_ids": [],
            "variant_to_product": {},
        }
        state_path = Path(".state") / "shopify" / f"{_state_filename(ts)}.json"

    rows = _read_rows(csv_path)
    completed = set(state["completed_variant_ids"])

    cfg = load_config(args.config)

    # Group rows per product, skipping anything already completed.
    by_product: dict[str, list[dict[str, Any]]] = {}

    with ShopifyClient(config=cfg) as client:
        for row in rows:
            variant_id = (row.get("variant_id") or "").strip() or None
            sku = (row.get("sku") or "").strip() or None
            if variant_id and variant_id in completed:
                continue
            resolved = _resolve_variant(client, sku=sku, variant_id=variant_id, state=state)
            if not resolved:
                continue
            vid, pid = resolved
            if vid in completed:
                continue
            by_product.setdefault(pid, []).append(_build_variant_input(row, vid))

        # Dry-run: emit chunks and exit. No state file, no mutations.
        if args.dry_run:
            for pid, variants in by_product.items():
                for chunk in _chunk(variants, _CHUNK_SIZE):
                    ids = [v["id"] for v in chunk]
                    print(f"{pid}: {ids}")
            return 0

        # Execute chunks. Save state after each successful chunk so we can resume.
        for pid, variants in by_product.items():
            for chunk in _chunk(variants, _CHUNK_SIZE):
                data = client.graphql(_BULK_MUTATION, {"productId": pid, "variants": chunk})
                check_user_errors(data, mutation="productVariantsBulkUpdate")
                state["completed_variant_ids"].extend(v["id"] for v in chunk)
                _persist_state(state_path, state)

    return 0


def _persist_state(state_path: Path, state: dict) -> None:
    """Persist state. Uses core.state.save_state for the default location;
    otherwise writes to the supplied path (e.g. when resuming from a file
    that lives outside .state/shopify/)."""
    expected_root = Path(".state") / "shopify"
    try:
        if state_path.parent == expected_root and state_path.suffix == ".json":
            save_state("shopify", state_path.stem, state)
            return
    except Exception:
        pass
    _save_state_to_path(state_path, state)


if __name__ == "__main__":
    sys.exit(main())
