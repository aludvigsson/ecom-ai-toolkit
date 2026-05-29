import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.accounts import get as getcmd
from meta_ads.utils.client import MetaAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.accounts.get.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.accounts.get.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_get_normalizes_account_id(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "id": "act_123",
            "name": "Main",
            "currency": "USD",
        }
        with patch.object(sys, "argv", ["get.py", "--account-id", "123", "--output", "json"]):
            assert getcmd.main() == 0
        args, kwargs = client.get.call_args
        assert args[0] == "act_123"
        assert "name" in kwargs["params"]["fields"]
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "act_123"
    assert parsed["currency"] == "USD"


def test_get_accepts_prefixed_account_id(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {"id": "act_123", "name": "Main"}
        with patch.object(sys, "argv", ["get.py", "--account-id", "act_123"]):
            assert getcmd.main() == 0
        args, _ = client.get.call_args
        assert args[0] == "act_123"


def test_get_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {"error": {"message": "bad", "code": 100, "fbtrace_id": "Z"}}
        with (
            patch.object(sys, "argv", ["get.py", "--account-id", "123"]),
            pytest.raises(MetaAPIError),
        ):
            getcmd.main()
