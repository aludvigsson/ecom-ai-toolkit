import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.ads import create as createcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.ads.create.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.ads.create.MetaClient"))
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
        "Ad 1",
        "--adset-id",
        "as1",
        "--creative-id",
        "cr1",
        *extra,
    ]


def test_ad_create_dry_run_forces_paused(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", _argv("--dry-run", "--output", "json")):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "act_123/ads"
    assert parsed["data"]["status"] == "PAUSED"
    assert parsed["data"]["adset_id"] == "as1"
    assert parsed["data"]["creative"] == '{"creative_id": "cr1"}'


def test_ad_create_posts_paused_body(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "ad9"}
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "act_123/ads"
        data = kwargs.get("data") or args[1]
        assert data["status"] == "PAUSED"
        assert data["creative"] == '{"creative_id": "cr1"}'


def test_ad_create_has_no_active_path(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "ad9"}
        with (
            patch.object(sys, "argv", _argv("--status", "ACTIVE")),
            pytest.raises(SystemExit),
        ):
            createcmd.main()
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["status"] == "PAUSED"
