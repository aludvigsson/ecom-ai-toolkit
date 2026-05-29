import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.lists import delete as deletecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.lists.delete.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.lists.delete.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_delete_dry_run_skips_call_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", ["delete.py", "--id", "LST1", "--dry-run"]):
            assert deletecmd.main() == 0
        assert client.delete.call_count == 0
    assert "LST1" in capsys.readouterr().out


def test_delete_without_yes_errors(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", ["delete.py", "--id", "LST1"]):
            try:
                rc = deletecmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.delete.call_count == 0


def test_delete_with_yes_calls(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.delete.return_value = {}
        with patch.object(sys, "argv", ["delete.py", "--id", "LST1", "--yes"]):
            assert deletecmd.main() == 0
        client.delete.assert_called_once_with("lists/LST1")
    assert "Deleted: LST1" in capsys.readouterr().out
