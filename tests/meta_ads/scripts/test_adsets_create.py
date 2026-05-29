import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.adsets import create as createcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.adsets.create.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.adsets.create.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def _argv(*extra):
    return [
        "create.py",
        "--account-id",
        "123",
        "--name",
        "Broad EU",
        "--campaign-id",
        "c1",
        "--daily-budget",
        "3000",
        "--billing-event",
        "IMPRESSIONS",
        "--optimization-goal",
        "LINK_CLICKS",
        "--targeting",
        '{"geo_locations": {"countries": ["SE"]}}',
        *extra,
    ]


def test_adset_create_dry_run_forces_paused(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", _argv("--dry-run", "--output", "json")):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "act_123/adsets"
    assert parsed["data"]["status"] == "PAUSED"
    assert parsed["data"]["campaign_id"] == "c1"
    assert parsed["data"]["targeting"] == '{"geo_locations": {"countries": ["SE"]}}'


def test_adset_create_posts_paused_body(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "as9"}
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "act_123/adsets"
        data = kwargs.get("data") or args[1]
        assert data["status"] == "PAUSED"
        assert data["daily_budget"] == 3000
        assert data["billing_event"] == "IMPRESSIONS"
        assert data["optimization_goal"] == "LINK_CLICKS"


def test_adset_create_has_no_active_path(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "as9"}
        with (
            patch.object(sys, "argv", _argv("--status", "ACTIVE")),
            pytest.raises(SystemExit),
        ):
            createcmd.main()
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["status"] == "PAUSED"


def test_adset_create_rejects_bad_targeting_json(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        argv = [
            "create.py",
            "--account-id",
            "123",
            "--name",
            "X",
            "--campaign-id",
            "c1",
            "--daily-budget",
            "3000",
            "--billing-event",
            "IMPRESSIONS",
            "--optimization-goal",
            "LINK_CLICKS",
            "--targeting",
            "{not json",
        ]
        with (
            patch.object(sys, "argv", argv),
            pytest.raises(SystemExit),
        ):
            createcmd.main()
