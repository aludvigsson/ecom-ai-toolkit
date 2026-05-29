import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.metrics import aggregate as aggcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.metrics.aggregate.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.metrics.aggregate.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_aggregate_dry_run_builds_body_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "aggregate.py",
                "--metric-id",
                "MET1",
                "--measurement",
                "count",
                "--interval",
                "day",
                "--start",
                "2026-01-01T00:00:00Z",
                "--end",
                "2026-01-31T00:00:00Z",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert aggcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "metric-aggregate"
    attrs = parsed["data"]["attributes"]
    assert attrs["metric_id"] == "MET1"
    assert attrs["measurements"] == ["count"]
    assert attrs["interval"] == "day"
    assert attrs["filter"] == [
        "greater-or-equal(datetime,2026-01-01T00:00:00Z)",
        "less-than(datetime,2026-01-31T00:00:00Z)",
    ]


def test_aggregate_posts_to_endpoint(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"data": {"type": "metric-aggregate", "attributes": {}}}
        with patch.object(
            sys,
            "argv",
            [
                "aggregate.py",
                "--metric-id",
                "MET1",
                "--measurement",
                "count",
                "--start",
                "2026-01-01T00:00:00Z",
                "--end",
                "2026-01-31T00:00:00Z",
            ],
        ):
            assert aggcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "metric-aggregates"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["metric_id"] == "MET1"
        assert body["data"]["attributes"]["measurements"] == ["count"]


def test_aggregate_multiple_measurements(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "aggregate.py",
                "--metric-id",
                "MET1",
                "--measurement",
                "count",
                "--measurement",
                "sum_value",
                "--start",
                "2026-01-01T00:00:00Z",
                "--end",
                "2026-01-31T00:00:00Z",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert aggcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["attributes"]["measurements"] == ["count", "sum_value"]
