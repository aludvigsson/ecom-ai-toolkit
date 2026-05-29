import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.flows import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.flows.get.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.flows.get.KlaviyoClient"))
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
            "data": {
                "id": "FLOW1",
                "type": "flow",
                "attributes": {"name": "Welcome", "status": "live"},
            }
        }
        with patch.object(sys, "argv", ["get.py", "--id", "FLOW1", "--output", "json"]):
            assert getcmd.main() == 0
        client.get.assert_called_once_with("flows/FLOW1")
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "FLOW1"
    assert parsed["name"] == "Welcome"


def test_get_with_actions_fetches_subresource(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {"id": "FLOW1", "type": "flow", "attributes": {"name": "Welcome"}}
        }
        client.paginate.return_value = iter(
            [
                {
                    "id": "ACT1",
                    "type": "flow-action",
                    "attributes": {"action_type": "SEND_EMAIL", "status": "live"},
                }
            ]
        )
        with patch.object(
            sys, "argv", ["get.py", "--id", "FLOW1", "--with-actions", "--output", "json"]
        ):
            assert getcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert client.paginate.call_args[0][0] == "flows/FLOW1/flow-actions"
        assert kwargs["limit"] == 50
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["flow"]["id"] == "FLOW1"
    assert parsed["actions"][0]["id"] == "ACT1"
    assert parsed["actions"][0]["action_type"] == "SEND_EMAIL"


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
