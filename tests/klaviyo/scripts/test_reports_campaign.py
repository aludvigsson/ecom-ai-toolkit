import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.reports import campaign as cmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.reports.campaign.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.reports.campaign.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_campaign_report_dry_run_builds_body_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "campaign.py",
                "--statistic",
                "opens",
                "--statistic",
                "clicks",
                "--timeframe",
                "last_30_days",
                "--conversion-metric-id",
                "MET1",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert cmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "campaign-values-report"
    attrs = parsed["data"]["attributes"]
    assert attrs["statistics"] == ["opens", "clicks"]
    assert attrs["timeframe"] == {"key": "last_30_days"}
    assert attrs["conversion_metric_id"] == "MET1"


def test_campaign_report_posts_to_endpoint(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"data": {"type": "campaign-values-report", "attributes": {}}}
        with patch.object(
            sys,
            "argv",
            [
                "campaign.py",
                "--statistic",
                "opens",
                "--timeframe",
                "last_30_days",
                "--conversion-metric-id",
                "MET1",
            ],
        ):
            assert cmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "campaign-values-reports"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["statistics"] == ["opens"]
