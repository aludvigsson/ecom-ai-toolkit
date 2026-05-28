import json
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from shopify.scripts.products import bulk_prices as bp
from shopify.utils.client import AmbiguousSkuError, SkuNotFoundError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.products.bulk_prices.load_config"))
    mock_client_class = stack.enter_context(
        patch("shopify.scripts.products.bulk_prices.ShopifyClient")
    )
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _write_csv(path: Path, rows: list[dict]) -> None:
    headers = list(rows[0].keys())
    lines = [",".join(headers)]
    for r in rows:
        lines.append(",".join(str(r.get(h, "")) for h in headers))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_bulk_prices_dry_run_prints_chunks_and_writes_no_state(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "prices.csv"
    _write_csv(
        csv_path,
        [
            {"variant_id": "gid://shopify/ProductVariant/1", "price": "10.00"},
            {"variant_id": "gid://shopify/ProductVariant/2", "price": "20.00"},
        ],
    )
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        # Need to pre-resolve product_id for variant_id rows; this requires a graphql lookup.
        # Simulate the variant->product lookup returning matching products.
        client.graphql.side_effect = [
            {
                "productVariants": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/ProductVariant/1",
                                "product": {"id": "gid://shopify/Product/100"},
                            }
                        }
                    ]
                }
            },
            {
                "productVariants": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/ProductVariant/2",
                                "product": {"id": "gid://shopify/Product/100"},
                            }
                        }
                    ]
                }
            },
        ]
        with patch.object(
            sys, "argv", ["bulk_prices.py", "--from-csv", str(csv_path), "--dry-run"]
        ):
            assert bp.main() == 0
    # No state directory should be written
    assert not (tmp_path / ".state").exists()
    out = capsys.readouterr().out
    assert "gid://shopify/Product/100" in out


def test_bulk_prices_resolves_skus_via_lookup(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "prices.csv"
    _write_csv(csv_path, [{"sku": "ABC", "price": "10.00"}])
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            # SKU lookup
            {
                "productVariants": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/ProductVariant/9",
                                "product": {"id": "gid://shopify/Product/77"},
                            }
                        }
                    ]
                }
            },
            # Mutation
            {
                "productVariantsBulkUpdate": {
                    "productVariants": [
                        {
                            "id": "gid://shopify/ProductVariant/9",
                            "price": "10.00",
                            "compareAtPrice": None,
                        }
                    ],
                    "userErrors": [],
                }
            },
        ]
        with patch.object(sys, "argv", ["bulk_prices.py", "--from-csv", str(csv_path)]):
            assert bp.main() == 0
        # First call is SKU lookup
        first_call = client.graphql.call_args_list[0]
        lookup_query = first_call[0][0]
        assert "productVariants" in lookup_query
        # Second call is the mutation
        mut_args = client.graphql.call_args_list[1][0]
        assert "productVariantsBulkUpdate" in mut_args[0]
        mut_vars = mut_args[1]
        assert mut_vars["productId"] == "gid://shopify/Product/77"
        assert mut_vars["variants"][0]["id"] == "gid://shopify/ProductVariant/9"
        assert mut_vars["variants"][0]["price"] == "10.00"
        # compareAtPrice should be omitted because CSV didn't have it
        assert "compareAtPrice" not in mut_vars["variants"][0]


def test_bulk_prices_writes_state_with_completed_ids(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "prices.csv"
    _write_csv(
        csv_path,
        [
            {"variant_id": "gid://shopify/ProductVariant/1", "price": "10.00"},
        ],
    )
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            {
                "productVariants": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/ProductVariant/1",
                                "product": {"id": "gid://shopify/Product/100"},
                            }
                        }
                    ]
                }
            },
            {
                "productVariantsBulkUpdate": {
                    "productVariants": [
                        {
                            "id": "gid://shopify/ProductVariant/1",
                            "price": "10.00",
                            "compareAtPrice": None,
                        }
                    ],
                    "userErrors": [],
                }
            },
        ]
        with patch.object(sys, "argv", ["bulk_prices.py", "--from-csv", str(csv_path)]):
            assert bp.main() == 0
    # Should have created .state/shopify/bulk_prices_*.json
    state_dir = tmp_path / ".state" / "shopify"
    assert state_dir.exists()
    files = list(state_dir.glob("bulk_prices_*.json"))
    assert len(files) == 1
    state = json.loads(files[0].read_text(encoding="utf-8"))
    assert "gid://shopify/ProductVariant/1" in state["completed_variant_ids"]


def test_bulk_prices_resume_skips_completed_variants(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "prices.csv"
    _write_csv(
        csv_path,
        [
            {"variant_id": "gid://shopify/ProductVariant/1", "price": "10.00"},
            {"variant_id": "gid://shopify/ProductVariant/2", "price": "20.00"},
        ],
    )
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "started_at": "2026-01-01T000000",
                "csv_path": str(csv_path),
                "sku_to_variant_id": {},
                "completed_variant_ids": ["gid://shopify/ProductVariant/1"],
                "variant_to_product": {
                    "gid://shopify/ProductVariant/1": "gid://shopify/Product/100",
                    "gid://shopify/ProductVariant/2": "gid://shopify/Product/100",
                },
            }
        ),
        encoding="utf-8",
    )
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        # Only ProductVariant/2 should be processed: one mutation call, no lookups needed.
        client.graphql.side_effect = [
            {
                "productVariantsBulkUpdate": {
                    "productVariants": [
                        {
                            "id": "gid://shopify/ProductVariant/2",
                            "price": "20.00",
                            "compareAtPrice": None,
                        }
                    ],
                    "userErrors": [],
                }
            },
        ]
        with patch.object(sys, "argv", ["bulk_prices.py", "--resume", str(state_path)]):
            assert bp.main() == 0
        # Exactly 1 graphql call (the mutation)
        assert client.graphql.call_count == 1
        call_args = client.graphql.call_args_list[0][0]
        variant_ids = [v["id"] for v in call_args[1]["variants"]]
        assert variant_ids == ["gid://shopify/ProductVariant/2"]


def test_bulk_prices_chunks_at_250(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "prices.csv"
    rows = [
        {"variant_id": f"gid://shopify/ProductVariant/{i}", "price": "10.00"} for i in range(260)
    ]
    _write_csv(csv_path, rows)
    state_path = tmp_path / "preseed.json"
    # Pre-seed product mapping so we don't need 260 lookup calls in the test
    state_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "started_at": "2026-01-01T000000",
                "csv_path": str(csv_path),
                "sku_to_variant_id": {},
                "completed_variant_ids": [],
                "variant_to_product": {
                    f"gid://shopify/ProductVariant/{i}": "gid://shopify/Product/1"
                    for i in range(260)
                },
            }
        ),
        encoding="utf-8",
    )
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        # Two mutation calls expected: chunk of 250 + chunk of 10
        client.graphql.side_effect = [
            {
                "productVariantsBulkUpdate": {
                    "productVariants": [],
                    "userErrors": [],
                }
            },
            {
                "productVariantsBulkUpdate": {
                    "productVariants": [],
                    "userErrors": [],
                }
            },
        ]
        with patch.object(sys, "argv", ["bulk_prices.py", "--resume", str(state_path)]):
            assert bp.main() == 0
        assert client.graphql.call_count == 2
        first = client.graphql.call_args_list[0][0][1]
        second = client.graphql.call_args_list[1][0][1]
        assert len(first["variants"]) == 250
        assert len(second["variants"]) == 10


def test_save_state_to_path_is_atomic(tmp_path):
    from shopify.scripts.products.bulk_prices import _save_state_to_path

    target = tmp_path / "state.json"
    _save_state_to_path(target, {"a": 1})
    assert target.exists()
    # No tmp file should remain after a successful save.
    tmps = list(tmp_path.glob("*.tmp*"))
    assert tmps == []


def test_bulk_prices_raises_on_ambiguous_sku(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "prices.csv"
    _write_csv(csv_path, [{"sku": "DUP", "price": "10.00"}])
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            {
                "productVariants": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/ProductVariant/1",
                                "product": {"id": "gid://shopify/Product/100"},
                            }
                        },
                        {
                            "node": {
                                "id": "gid://shopify/ProductVariant/2",
                                "product": {"id": "gid://shopify/Product/200"},
                            }
                        },
                    ]
                }
            },
        ]
        with (
            patch.object(sys, "argv", ["bulk_prices.py", "--from-csv", str(csv_path)]),
            pytest.raises(AmbiguousSkuError) as exc_info,
        ):
            bp.main()
        assert exc_info.value.sku == "DUP"
        assert "gid://shopify/ProductVariant/1" in exc_info.value.variant_ids
        assert "gid://shopify/ProductVariant/2" in exc_info.value.variant_ids


def test_bulk_prices_raises_on_missing_sku(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "prices.csv"
    _write_csv(csv_path, [{"sku": "MISSING", "price": "10.00"}])
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            {"productVariants": {"edges": []}},
        ]
        with (
            patch.object(sys, "argv", ["bulk_prices.py", "--from-csv", str(csv_path)]),
            pytest.raises(SkuNotFoundError) as exc_info,
        ):
            bp.main()
        assert exc_info.value.sku == "MISSING"
