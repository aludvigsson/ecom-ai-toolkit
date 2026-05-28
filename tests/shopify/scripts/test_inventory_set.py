import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.inventory import set as setcmd
from shopify.utils.client import ShopifyUserError, SkuNotFoundError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.inventory.set.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.inventory.set.ShopifyClient"))
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _sku_lookup_response(variant_id: str, inventory_item_id: str) -> dict:
    return {
        "productVariants": {
            "edges": [
                {
                    "node": {
                        "id": variant_id,
                        "sku": "ABC",
                        "inventoryItem": {"id": inventory_item_id},
                    }
                }
            ]
        }
    }


def _ok_mutation_response() -> dict:
    return {
        "inventorySetOnHandQuantities": {
            "inventoryAdjustmentGroup": {
                "id": "gid://shopify/InventoryAdjustmentGroup/1",
                "reason": "correction",
                "changes": [
                    {
                        "name": "on_hand",
                        "delta": 5,
                        "quantityAfterChange": 12,
                    }
                ],
            },
            "userErrors": [],
        }
    }


def test_set_dry_run_resolves_inputs_and_skips_mutation(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            _sku_lookup_response(
                "gid://shopify/ProductVariant/1",
                "gid://shopify/InventoryItem/100",
            ),
        ]
        with patch.object(
            sys,
            "argv",
            [
                "set.py",
                "--sku",
                "ABC",
                "--location-id",
                "gid://shopify/Location/10",
                "--quantity",
                "12",
                "--dry-run",
            ],
        ):
            assert setcmd.main() == 0
        # Only the SKU lookup, no mutation
        assert client.graphql.call_count == 1
    out = capsys.readouterr().out
    assert "gid://shopify/InventoryItem/100" in out
    assert "gid://shopify/Location/10" in out
    assert "12" in out


def test_set_resolves_location_by_name(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            _sku_lookup_response(
                "gid://shopify/ProductVariant/1",
                "gid://shopify/InventoryItem/100",
            ),
            {
                "locations": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/Location/77",
                                "name": "Warehouse SE",
                            }
                        }
                    ]
                }
            },
            _ok_mutation_response(),
        ]
        with patch.object(
            sys,
            "argv",
            [
                "set.py",
                "--sku",
                "ABC",
                "--location-name",
                "Warehouse SE",
                "--quantity",
                "12",
            ],
        ):
            assert setcmd.main() == 0
        # third call is the mutation
        mut_args = client.graphql.call_args_list[2][0]
        assert "inventorySetOnHandQuantities" in mut_args[0]
        mut_input = mut_args[1]["input"]
        assert mut_input["setQuantities"][0]["locationId"] == "gid://shopify/Location/77"
        assert mut_input["setQuantities"][0]["inventoryItemId"] == "gid://shopify/InventoryItem/100"
        assert mut_input["setQuantities"][0]["quantity"] == 12


def test_set_userErrors_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            _sku_lookup_response(
                "gid://shopify/ProductVariant/1",
                "gid://shopify/InventoryItem/100",
            ),
            {
                "inventorySetOnHandQuantities": {
                    "inventoryAdjustmentGroup": None,
                    "userErrors": [
                        {
                            "field": ["setQuantities", "0", "quantity"],
                            "message": "Quantity must be positive",
                            "code": "INVALID",
                        }
                    ],
                }
            },
        ]
        with (
            patch.object(
                sys,
                "argv",
                [
                    "set.py",
                    "--sku",
                    "ABC",
                    "--location-id",
                    "gid://shopify/Location/10",
                    "--quantity",
                    "-1",
                ],
            ),
            pytest.raises(ShopifyUserError),
        ):
            setcmd.main()


def test_set_missing_sku_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            {"productVariants": {"edges": []}},
        ]
        with (
            patch.object(
                sys,
                "argv",
                [
                    "set.py",
                    "--sku",
                    "MISSING",
                    "--location-id",
                    "gid://shopify/Location/10",
                    "--quantity",
                    "12",
                ],
            ),
            pytest.raises(SkuNotFoundError) as exc_info,
        ):
            setcmd.main()
        assert exc_info.value.sku == "MISSING"


def test_set_ambiguous_location_name_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            _sku_lookup_response(
                "gid://shopify/ProductVariant/1",
                "gid://shopify/InventoryItem/100",
            ),
            {
                "locations": {
                    "edges": [
                        {"node": {"id": "gid://shopify/Location/1", "name": "Main"}},
                        {"node": {"id": "gid://shopify/Location/2", "name": "Main"}},
                    ]
                }
            },
        ]
        with (
            patch.object(
                sys,
                "argv",
                [
                    "set.py",
                    "--sku",
                    "ABC",
                    "--location-name",
                    "Main",
                    "--quantity",
                    "12",
                ],
            ),
            pytest.raises(setcmd.AmbiguousLocationError) as exc_info,
        ):
            setcmd.main()
        assert exc_info.value.name == "Main"


def test_set_location_name_match_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            _sku_lookup_response(
                "gid://shopify/ProductVariant/1",
                "gid://shopify/InventoryItem/100",
            ),
            {
                "locations": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/Location/77",
                                "name": "Stockholm Warehouse",
                            }
                        }
                    ]
                }
            },
            _ok_mutation_response(),
        ]
        with patch.object(
            sys,
            "argv",
            [
                "set.py",
                "--sku",
                "ABC",
                "--location-name",
                "stockholm warehouse",
                "--quantity",
                "12",
            ],
        ):
            assert setcmd.main() == 0
        mut_args = client.graphql.call_args_list[2][0]
        mut_input = mut_args[1]["input"]
        assert mut_input["setQuantities"][0]["locationId"] == "gid://shopify/Location/77"
