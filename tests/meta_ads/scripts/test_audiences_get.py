import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.audiences import get as getcmd
from meta_ads.utils.client import MetaAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.audiences.get.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.audiences.get.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_audience_get_by_id(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "id": "aud1",
            "name": "Newsletter buyers",
            "subtype": "CUSTOM",
            "approximate_count_lower_bound": 1000,
        }
        with patch.object(sys, "argv", ["get.py", "--id", "aud1", "--output", "json"]):
            assert getcmd.main() == 0
        args, kwargs = client.get.call_args
        assert args[0] == "aud1"
        assert "subtype" in kwargs["params"]["fields"]
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "aud1"
    assert parsed["name"] == "Newsletter buyers"


def test_audience_get_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {"error": {"message": "bad", "code": 100, "fbtrace_id": "Z"}}
        with (
            patch.object(sys, "argv", ["get.py", "--id", "aud1"]),
            pytest.raises(MetaAPIError),
        ):
            getcmd.main()
