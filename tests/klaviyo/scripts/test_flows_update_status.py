import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.flows import update_status as cmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.flows.update_status.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.flows.update_status.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_dry_run_builds_body_and_skips_patch_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "update_status.py",
                "--id",
                "FLOW1",
                "--status",
                "live",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert cmd.main() == 0
        assert client.patch.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "flow"
    assert parsed["data"]["id"] == "FLOW1"
    assert parsed["data"]["attributes"]["status"] == "live"


def test_without_yes_errors_in_live_mode(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", ["update_status.py", "--id", "FLOW1", "--status", "live"]):
            try:
                cmd.main()
            except SystemExit as exc:
                assert exc.code != 0
            else:
                raise AssertionError("expected SystemExit")
        assert client.patch.call_count == 0


def test_with_yes_patches_flow(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.patch.return_value = {
            "data": {"id": "FLOW1", "type": "flow", "attributes": {"status": "live"}}
        }
        with patch.object(
            sys, "argv", ["update_status.py", "--id", "FLOW1", "--status", "live", "--yes"]
        ):
            assert cmd.main() == 0
        args, kwargs = client.patch.call_args
        assert args[0] == "flows/FLOW1"
        body = kwargs.get("json") or args[1]
        assert body["data"]["id"] == "FLOW1"
        assert body["data"]["attributes"]["status"] == "live"


def test_status_choices_enforced(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with patch.object(sys, "argv", ["update_status.py", "--id", "FLOW1", "--status", "bogus"]):
            try:
                cmd.main()
            except SystemExit as exc:
                assert exc.code != 0
            else:
                raise AssertionError("expected SystemExit")
