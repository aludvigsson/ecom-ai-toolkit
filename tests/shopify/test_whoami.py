import sys
from unittest.mock import patch

from shopify.scripts import whoami


def test_whoami_prints_shop_name(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    fake_data = {
        "shop": {
            "name": "My Test Shop",
            "primaryDomain": {"url": "https://x.com"},
            "plan": {"displayName": "Basic"},
        }
    }
    with (
        patch("shopify.scripts.whoami.load_config") as mock_cfg,
        patch("shopify.scripts.whoami.ShopifyClient") as mock_client,
    ):
        mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
        mock_cfg.return_value.domains = {
            "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
        }
        mock_client.return_value.graphql.return_value = fake_data
        with patch.object(sys, "argv", ["whoami.py"]):
            whoami.main()
    out = capsys.readouterr().out
    assert "My Test Shop" in out
