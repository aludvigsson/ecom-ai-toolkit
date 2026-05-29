import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.campaigns import cancel as cancelcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.campaigns.cancel.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.campaigns.cancel.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_cancel_dry_run_prints_body_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["cancel.py", "--id", "CMP1", "--dry-run", "--output", "json"]
        ):
            assert cancelcmd.main() == 0
        assert client.patch.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "campaign-send-job"
    assert parsed["data"]["id"] == "CMP1"
    assert parsed["data"]["attributes"]["action"] == "cancel"


def test_cancel_without_yes_errors_in_live_mode(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", ["cancel.py", "--id", "CMP1"]):
            try:
                rc = cancelcmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.patch.call_count == 0


def test_cancel_with_yes_patches_send_job(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.patch.return_value = {"data": {"id": "CMP1", "type": "campaign-send-job"}}
        with patch.object(sys, "argv", ["cancel.py", "--id", "CMP1", "--yes"]):
            assert cancelcmd.main() == 0
        args, kwargs = client.patch.call_args
        assert args[0] == "campaign-send-jobs/CMP1"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["action"] == "cancel"
