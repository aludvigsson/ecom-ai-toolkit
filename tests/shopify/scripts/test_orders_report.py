import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.orders import report as reportcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.orders.report.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.orders.report.ShopifyClient"))
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _order(
    *,
    oid: str,
    name: str,
    total: str,
    refunded: str = "0.00",
    currency: str = "SEK",
    cancelled: str | None = None,
) -> dict:
    return {
        "id": oid,
        "name": name,
        "createdAt": "2026-05-15T10:00:00Z",
        "cancelledAt": cancelled,
        "displayFinancialStatus": "PAID",
        "currentTotalPriceSet": {"shopMoney": {"amount": total, "currencyCode": currency}},
        "currentTotalRefundedSet": {"shopMoney": {"amount": refunded, "currencyCode": currency}},
    }


def _line(*, parent: str, sku: str, qty: int, name: str) -> dict:
    return {"__parentId": parent, "sku": sku, "quantity": qty, "name": name}


def test_report_summarises_gmv_and_count(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.bulk_query.return_value = iter(
            [
                _order(oid="gid://Order/1", name="#1001", total="100.00"),
                _order(oid="gid://Order/2", name="#1002", total="250.00", refunded="50.00"),
                _line(parent="gid://Order/1", sku="A", qty=1, name="Alpha"),
                _line(parent="gid://Order/2", sku="A", qty=2, name="Alpha"),
            ]
        )
        with patch.object(
            sys,
            "argv",
            ["report.py", "--from", "2026-05-01", "--to", "2026-05-31"],
        ):
            assert reportcmd.main() == 0
    out = capsys.readouterr().out
    assert "Orders summary 2026-05-01 to 2026-05-31" in out
    assert "| Order count | 2 |" in out
    assert "| GMV | 350.00 SEK |" in out
    assert "| Refunds | 50.00 SEK |" in out
    assert "| Net | 300.00 SEK |" in out


def test_report_excludes_cancelled_orders_from_count(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.bulk_query.return_value = iter(
            [
                _order(oid="gid://Order/1", name="#1001", total="100.00"),
                _order(
                    oid="gid://Order/2",
                    name="#1002",
                    total="250.00",
                    cancelled="2026-05-16T09:00:00Z",
                ),
            ]
        )
        with patch.object(sys, "argv", ["report.py", "--from", "2026-05-01", "--to", "2026-05-31"]):
            assert reportcmd.main() == 0
    out = capsys.readouterr().out
    assert "| Order count | 1 |" in out
    assert "| GMV | 100.00 SEK |" in out


def test_report_top_skus_ranked_by_units(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.bulk_query.return_value = iter(
            [
                _order(oid="gid://Order/1", name="#1001", total="100.00"),
                _order(oid="gid://Order/2", name="#1002", total="100.00"),
                _line(parent="gid://Order/1", sku="LOW", qty=1, name="LowProd"),
                _line(parent="gid://Order/1", sku="HIGH", qty=5, name="HighProd"),
                _line(parent="gid://Order/2", sku="HIGH", qty=3, name="HighProd"),
                _line(parent="gid://Order/2", sku="MID", qty=4, name="MidProd"),
            ]
        )
        with patch.object(
            sys,
            "argv",
            ["report.py", "--from", "2026-05-01", "--to", "2026-05-31", "--top-n", "3"],
        ):
            assert reportcmd.main() == 0
    out = capsys.readouterr().out
    # Top SKU should be HIGH with 8 units; MID with 4; LOW with 1
    lines = out.splitlines()
    sku_rows = [
        line
        for line in lines
        if line.startswith("| ") and any(s in line for s in ("HighProd", "MidProd", "LowProd"))
    ]
    assert sku_rows[0].startswith("| HIGH | 8 |")
    assert sku_rows[1].startswith("| MID | 4 |")
    assert sku_rows[2].startswith("| LOW | 1 |")
