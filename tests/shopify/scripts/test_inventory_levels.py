import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.inventory import levels
from shopify.utils.client import AmbiguousSkuError, SkuNotFoundError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.inventory.levels.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.inventory.levels.ShopifyClient"))
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _variant_with_levels(variant_id: str, sku: str, locations: list[dict]) -> dict:
    """Build a productVariants edge with the given inventoryLevels."""
    return {
        "node": {
            "id": variant_id,
            "sku": sku,
            "inventoryItem": {
                "id": f"gid://shopify/InventoryItem/{variant_id.rsplit('/', 1)[-1]}",
                "tracked": True,
                "inventoryLevels": {
                    "edges": [{"node": loc} for loc in locations],
                },
            },
        }
    }


def _location_quantities(
    location_id: str,
    location_name: str,
    available: int,
    on_hand: int,
    committed: int = 0,
    reserved: int = 0,
) -> dict:
    return {
        "quantities": [
            {"name": "available", "quantity": available},
            {"name": "on_hand", "quantity": on_hand},
            {"name": "committed", "quantity": committed},
            {"name": "reserved", "quantity": reserved},
        ],
        "location": {"id": location_id, "name": location_name},
    }


def test_levels_single_sku_returns_one_row_per_location(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            {
                "productVariants": {
                    "edges": [
                        _variant_with_levels(
                            "gid://shopify/ProductVariant/1",
                            "ABC",
                            [
                                _location_quantities(
                                    "gid://shopify/Location/10", "Warehouse SE", 12, 15, 3, 0
                                ),
                                _location_quantities(
                                    "gid://shopify/Location/20", "Warehouse NO", 5, 5
                                ),
                            ],
                        )
                    ]
                }
            }
        ]
        with patch.object(sys, "argv", ["levels.py", "--sku", "ABC", "--output", "json"]):
            assert levels.main() == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 2
    skus = [r["sku"] for r in parsed]
    assert skus == ["ABC", "ABC"]
    se = next(r for r in parsed if r["location_name"] == "Warehouse SE")
    assert se["available"] == 12
    assert se["on_hand"] == 15
    assert se["committed"] == 3
    assert se["reserved"] == 0
    assert se["tracked"] is True
    assert se["variant_id"] == "gid://shopify/ProductVariant/1"
    assert se["location_id"] == "gid://shopify/Location/10"


def test_levels_repeatable_sku_flag(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            {
                "productVariants": {
                    "edges": [
                        _variant_with_levels(
                            "gid://shopify/ProductVariant/1",
                            "A",
                            [_location_quantities("gid://shopify/Location/10", "Main", 7, 7)],
                        )
                    ]
                }
            },
            {
                "productVariants": {
                    "edges": [
                        _variant_with_levels(
                            "gid://shopify/ProductVariant/2",
                            "B",
                            [_location_quantities("gid://shopify/Location/10", "Main", 4, 4)],
                        )
                    ]
                }
            },
        ]
        with patch.object(
            sys,
            "argv",
            ["levels.py", "--sku", "A", "--sku", "B", "--output", "json"],
        ):
            assert levels.main() == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 2
    skus = sorted(r["sku"] for r in parsed)
    assert skus == ["A", "B"]
    assert client.graphql.call_count == 2


def test_levels_ambiguous_sku_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            {
                "productVariants": {
                    "edges": [
                        _variant_with_levels("gid://shopify/ProductVariant/1", "DUP", []),
                        _variant_with_levels("gid://shopify/ProductVariant/2", "DUP", []),
                    ]
                }
            }
        ]
        with (
            patch.object(sys, "argv", ["levels.py", "--sku", "DUP"]),
            pytest.raises(AmbiguousSkuError) as exc_info,
        ):
            levels.main()
        assert exc_info.value.sku == "DUP"


def test_levels_missing_sku_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            {"productVariants": {"edges": []}},
        ]
        with (
            patch.object(sys, "argv", ["levels.py", "--sku", "MISSING"]),
            pytest.raises(SkuNotFoundError) as exc_info,
        ):
            levels.main()
        assert exc_info.value.sku == "MISSING"
