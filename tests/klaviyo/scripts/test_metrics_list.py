import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.metrics import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.metrics.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.metrics.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_metrics_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "MET1",
                    "type": "metric",
                    "attributes": {"name": "Placed Order", "integration": {"name": "Shopify"}},
                }
            ]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "MET1"
    assert parsed[0]["name"] == "Placed Order"


def test_metrics_list_passes_limit(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--limit", "7"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["limit"] == 7
