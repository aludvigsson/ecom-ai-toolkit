import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.campaigns import pause as pausecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.campaigns.pause.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.campaigns.pause.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_pause_dry_run_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", ["pause.py", "--id", "c1", "--dry-run", "--output", "json"]):
            assert pausecmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "c1"
    assert parsed["data"]["status"] == "PAUSED"


def test_pause_posts_paused_status(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"success": True}
        with patch.object(sys, "argv", ["pause.py", "--id", "c1"]):
            assert pausecmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "c1"
        assert (kwargs.get("data") or args[1])["status"] == "PAUSED"


def test_pause_not_yes_gated(monkeypatch):
    """Pausing is low-risk: it must run without --yes."""
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"success": True}
        with patch.object(sys, "argv", ["pause.py", "--id", "c1"]):
            assert pausecmd.main() == 0
