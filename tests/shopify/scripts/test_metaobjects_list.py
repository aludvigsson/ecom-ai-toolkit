import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.metaobjects import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.metaobjects.list.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.metaobjects.list.ShopifyClient"))
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


def test_list_metaobjects_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "metaobjects": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Metaobject/1",
                            "handle": "swatch-blue",
                            "type": "my_custom_type",
                            "displayName": "Blue",
                            "updatedAt": "2025-01-01T00:00:00Z",
                            "fields": [
                                {"key": "color", "value": "blue", "type": "color"},
                                {"key": "label", "value": "Blue", "type": "single_line_text_field"},
                            ],
                        }
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        with patch.object(
            sys,
            "argv",
            ["list.py", "--type", "my_custom_type", "--output", "json", "--limit", "5"],
        ):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables == {"type": "my_custom_type", "first": 5}
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed[0]["handle"] == "swatch-blue"
    assert parsed[0]["fields_count"] == 2
    assert parsed[0]["fields"] == [
        {"key": "color", "value": "blue", "type": "color"},
        {"key": "label", "value": "Blue", "type": "single_line_text_field"},
    ]


def test_list_metaobjects_collapses_fields_in_table_output(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "metaobjects": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Metaobject/1",
                            "handle": "swatch-blue",
                            "type": "my_custom_type",
                            "displayName": "Blue",
                            "updatedAt": "2025-01-01T00:00:00Z",
                            "fields": [
                                {"key": "color", "value": "blue", "type": "color"},
                                {"key": "label", "value": "Blue", "type": "single_line_text_field"},
                            ],
                        }
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        with patch.object(sys, "argv", ["list.py", "--type", "my_custom_type"]):
            assert listcmd.main() == 0
    out = capsys.readouterr().out
    assert "fields_count" in out
    # Raw fields list shouldn't be there in table form
    assert "'key':" not in out
    assert "single_line_text_field" not in out
