import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.metaobjects import upsert as upsertcmd
from shopify.utils.client import ShopifyUserError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.metaobjects.upsert.load_config"))
    mock_client_class = stack.enter_context(
        patch("shopify.scripts.metaobjects.upsert.ShopifyClient")
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


def test_upsert_dry_run_prints_inputs_and_skips_graphql(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "upsert.py",
                "--type",
                "swatch",
                "--handle",
                "blue",
                "--fields",
                '{"color":"blue"}',
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert upsertcmd.main() == 0
        assert client.graphql.call_count == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["handle"] == {"type": "swatch", "handle": "blue"}
    assert parsed["metaobject"] == {"fields": [{"key": "color", "value": "blue"}]}


def test_upsert_accepts_list_form_fields_from_file(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    fields = [
        {"key": "color", "value": "blue"},
        {"key": "size", "value": "L"},
    ]
    fpath = tmp_path / "fields.json"
    fpath.write_text(json.dumps(fields), encoding="utf-8")

    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "metaobjectUpsert": {
                "metaobject": {
                    "id": "gid://shopify/Metaobject/1",
                    "handle": "blue",
                    "type": "swatch",
                    "fields": fields,
                },
                "userErrors": [],
            }
        }
        with patch.object(
            sys,
            "argv",
            [
                "upsert.py",
                "--type",
                "swatch",
                "--handle",
                "blue",
                "--fields",
                str(fpath),
                "--output",
                "json",
            ],
        ):
            assert upsertcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables == {
            "handle": {"type": "swatch", "handle": "blue"},
            "metaobject": {"fields": fields},
        }


def test_upsert_userErrors_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "metaobjectUpsert": {
                "metaobject": None,
                "userErrors": [{"field": ["fields"], "message": "is invalid", "code": "INVALID"}],
            }
        }
        with (
            patch.object(
                sys,
                "argv",
                [
                    "upsert.py",
                    "--type",
                    "swatch",
                    "--handle",
                    "blue",
                    "--fields",
                    '{"color":"not-a-color"}',
                ],
            ),
            pytest.raises(ShopifyUserError),
        ):
            upsertcmd.main()
