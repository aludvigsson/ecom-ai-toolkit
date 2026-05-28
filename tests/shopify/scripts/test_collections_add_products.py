import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.collections import add_products as cmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.collections.add_products.load_config"))
    mock_client_class = stack.enter_context(
        patch("shopify.scripts.collections.add_products.ShopifyClient")
    )
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _variables_from_call(call_args):
    if len(call_args[0]) > 1:
        return call_args[0][1]
    return call_args[1].get("variables")


def test_add_products_dry_run_prints_chunks_and_skips_mutation(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "add_products.py",
                "--collection-id",
                "gid://shopify/Collection/1",
                "--handles",
                "p1,p2,p3",
                "--dry-run",
            ],
        ):
            assert cmd.main() == 0
        assert client.graphql.call_count == 0
    out = capsys.readouterr().out
    # Dry-run should mention the chunked IDs (here, all three handles)
    assert "p1" in out
    assert "p2" in out
    assert "p3" in out


def test_add_products_resolves_handles_via_lookup(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)

        def fake_graphql(query, variables=None):
            if "productByHandle" in query:
                handle = variables["handle"]
                return {"productByHandle": {"id": f"gid://shopify/Product/{handle}"}}
            return {
                "collectionAddProducts": {
                    "collection": {"id": variables["id"]},
                    "userErrors": [],
                }
            }

        client.graphql.side_effect = fake_graphql
        with patch.object(
            sys,
            "argv",
            [
                "add_products.py",
                "--collection-id",
                "gid://shopify/Collection/1",
                "--handles",
                "alpha,beta",
            ],
        ):
            assert cmd.main() == 0
        # Last call should be the collectionAddProducts mutation with resolved IDs
        mutation_calls = [
            c for c in client.graphql.call_args_list if "collectionAddProducts" in c.args[0]
        ]
        assert len(mutation_calls) == 1
        variables = _variables_from_call(mutation_calls[0])
        assert variables == {
            "id": "gid://shopify/Collection/1",
            "productIds": [
                "gid://shopify/Product/alpha",
                "gid://shopify/Product/beta",
            ],
        }


def test_add_products_chunks_at_250(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    csv_path = tmp_path / "ids.csv"
    lines = ["product_id"]
    for i in range(260):
        lines.append(f"gid://shopify/Product/{i}")
    csv_path.write_text("\n".join(lines) + "\n")

    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "collectionAddProducts": {
                "collection": {"id": "gid://shopify/Collection/1"},
                "userErrors": [],
            }
        }
        with patch.object(
            sys,
            "argv",
            [
                "add_products.py",
                "--collection-id",
                "gid://shopify/Collection/1",
                "--from-csv",
                str(csv_path),
            ],
        ):
            assert cmd.main() == 0
        mutation_calls = [
            c for c in client.graphql.call_args_list if "collectionAddProducts" in c.args[0]
        ]
        assert len(mutation_calls) == 2
        first_vars = _variables_from_call(mutation_calls[0])
        second_vars = _variables_from_call(mutation_calls[1])
        assert len(first_vars["productIds"]) == 250
        assert len(second_vars["productIds"]) == 10
