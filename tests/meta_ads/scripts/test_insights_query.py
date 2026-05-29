import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.insights import query as querycmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.insights.query.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.insights.query.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_insights_account_node_and_default_params(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [{"impressions": "100", "clicks": "5", "spend": "12.50"}]
        )
        with patch.object(
            sys,
            "argv",
            ["query.py", "--account-id", "123", "--level", "campaign", "--output", "json"],
        ):
            assert querycmd.main() == 0
        args, kwargs = client.paginate.call_args
        assert args[0] == "act_123/insights"
        params = kwargs.get("params") or args[1]
        assert params["level"] == "campaign"
        assert params["date_preset"] == "last_30d"
        assert "impressions" in params["fields"]
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["impressions"] == "100"


def test_insights_object_id_node(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["query.py", "--object-id", "c1", "--level", "ad"]):
            assert querycmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "c1/insights"


def test_insights_time_range_overrides_preset(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(
            sys,
            "argv",
            [
                "query.py",
                "--account-id",
                "123",
                "--since",
                "2026-05-01",
                "--until",
                "2026-05-28",
            ],
        ):
            assert querycmd.main() == 0
        _, kwargs = client.paginate.call_args
        params = kwargs["params"]
        assert params["time_range"] == '{"since": "2026-05-01", "until": "2026-05-28"}'
        assert "date_preset" not in params


def test_insights_breakdowns_passed_through(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(
            sys,
            "argv",
            ["query.py", "--account-id", "123", "--breakdowns", "age,gender"],
        ):
            assert querycmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["breakdowns"] == "age,gender"


def test_insights_requires_a_node(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["query.py"]),
            pytest.raises(SystemExit),
        ):
            querycmd.main()


def test_insights_since_and_until_must_pair(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["query.py", "--account-id", "123", "--since", "2026-05-01"]),
            pytest.raises(SystemExit),
        ):
            querycmd.main()
