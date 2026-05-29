import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.ads import update as updatecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.ads.update.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.ads.update.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_ad_update_name(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"success": True}
        with patch.object(sys, "argv", ["update.py", "--id", "ad1", "--name", "Renamed"]):
            assert updatecmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "ad1"
        assert (kwargs.get("data") or args[1]) == {"name": "Renamed"}


def test_ad_update_creative_serializes(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"success": True}
        with patch.object(sys, "argv", ["update.py", "--id", "ad1", "--creative-id", "cr2"]):
            assert updatecmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["creative"] == '{"creative_id": "cr2"}'


def test_ad_update_dry_run_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["update.py", "--id", "ad1", "--name", "N", "--dry-run", "--output", "json"],
        ):
            assert updatecmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["name"] == "N"


def test_ad_update_requires_a_field(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["update.py", "--id", "ad1"]),
            pytest.raises(SystemExit),
        ):
            updatecmd.main()
