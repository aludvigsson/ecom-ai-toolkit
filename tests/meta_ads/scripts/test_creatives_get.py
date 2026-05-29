import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.creatives import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.creatives.get.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.creatives.get.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_creative_get_by_id(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "id": "cr1",
            "name": "Hero",
            "object_type": "SHARE",
            "thumbnail_url": "https://x/thumb.png",
        }
        with patch.object(sys, "argv", ["get.py", "--id", "cr1", "--output", "json"]):
            assert getcmd.main() == 0
        args, kwargs = client.get.call_args
        assert args[0] == "cr1"
        assert "thumbnail_url" in kwargs["params"]["fields"]
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "cr1"
    assert parsed["thumbnail_url"] == "https://x/thumb.png"
