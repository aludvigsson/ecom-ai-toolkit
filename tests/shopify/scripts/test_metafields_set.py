import io
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.metafields import set as setcmd
from shopify.utils.client import ShopifyUserError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.metafields.set.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.metafields.set.ShopifyClient"))
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


def test_set_single_metafield_via_flags_dry_run(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "set.py",
                "--owner-id",
                "gid://shopify/Product/1",
                "--namespace",
                "custom",
                "--key",
                "color",
                "--value",
                "blue",
                "--type",
                "single_line_text_field",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert setcmd.main() == 0
        assert client.graphql.call_count == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed == [{"chunk": 0, "count": 1}]


def test_set_batch_from_stdin_json(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    batch = [
        {
            "ownerId": "gid://shopify/Product/1",
            "namespace": "custom",
            "key": "a",
            "value": "1",
            "type": "single_line_text_field",
        },
        {
            "ownerId": "gid://shopify/Product/2",
            "namespace": "custom",
            "key": "b",
            "value": "2",
            "type": "single_line_text_field",
        },
    ]
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(batch)))
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "metafieldsSet": {
                "metafields": [
                    {
                        "id": "gid://shopify/Metafield/9",
                        "namespace": "custom",
                        "key": "a",
                        "value": "1",
                        "type": "single_line_text_field",
                    }
                ],
                "userErrors": [],
            }
        }
        with patch.object(sys, "argv", ["set.py", "--batch", "-", "--output", "json"]):
            assert setcmd.main() == 0
        assert client.graphql.call_count == 1
        variables = _variables_from_call(client.graphql.call_args)
        assert variables == {"input": batch}


def test_set_chunks_at_25(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    batch = [
        {
            "ownerId": f"gid://shopify/Product/{i}",
            "namespace": "custom",
            "key": f"k{i}",
            "value": str(i),
            "type": "single_line_text_field",
        }
        for i in range(30)
    ]
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(batch)))
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {"metafieldsSet": {"metafields": [], "userErrors": []}}
        with patch.object(sys, "argv", ["set.py", "--batch", "-", "--output", "json"]):
            assert setcmd.main() == 0
        assert client.graphql.call_count == 2
        first_vars = _variables_from_call(client.graphql.call_args_list[0])
        second_vars = _variables_from_call(client.graphql.call_args_list[1])
        assert len(first_vars["input"]) == 25
        assert len(second_vars["input"]) == 5


def test_set_userErrors_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "metafieldsSet": {
                "metafields": [],
                "userErrors": [
                    {"field": ["value"], "message": "Value is invalid", "code": "INVALID"}
                ],
            }
        }
        with (
            patch.object(
                sys,
                "argv",
                [
                    "set.py",
                    "--owner-id",
                    "gid://shopify/Product/1",
                    "--namespace",
                    "custom",
                    "--key",
                    "color",
                    "--value",
                    "not-a-color",
                    "--type",
                    "color",
                ],
            ),
            pytest.raises(ShopifyUserError),
        ):
            setcmd.main()
