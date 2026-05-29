import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.metrics import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.metrics.get.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.metrics.get.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_get_by_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {"id": "MET1", "type": "metric", "attributes": {"name": "Placed Order"}}
        }
        with patch.object(sys, "argv", ["get.py", "--id", "MET1", "--output", "json"]):
            assert getcmd.main() == 0
        client.get.assert_called_once_with("metrics/MET1")
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "MET1"
    assert parsed["name"] == "Placed Order"


def test_get_requires_id(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with patch.object(sys, "argv", ["get.py"]):
            try:
                getcmd.main()
            except SystemExit as exc:
                assert exc.code != 0
            else:
                raise AssertionError("expected SystemExit")
