import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.campaigns import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.campaigns.get.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.campaigns.get.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_campaign_get_by_id(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "id": "c1",
            "name": "Spring Sale",
            "objective": "OUTCOME_SALES",
            "status": "PAUSED",
        }
        with patch.object(sys, "argv", ["get.py", "--id", "c1", "--output", "json"]):
            assert getcmd.main() == 0
        args, kwargs = client.get.call_args
        assert args[0] == "c1"
        assert "objective" in kwargs["params"]["fields"]
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "c1"
    assert parsed["status"] == "PAUSED"
