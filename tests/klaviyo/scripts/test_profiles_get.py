import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from klaviyo.scripts.profiles import get as getcmd
from klaviyo.utils.client import ResourceNotFoundError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.profiles.get.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.profiles.get.KlaviyoClient"))
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
            "data": {"id": "01H", "type": "profile", "attributes": {"email": "a@b.com"}}
        }
        with patch.object(sys, "argv", ["get.py", "--id", "01H", "--output", "json"]):
            assert getcmd.main() == 0
        client.get.assert_called_once_with("profiles/01H")
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "01H"
    assert parsed["email"] == "a@b.com"


def test_get_by_email_resolves(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": [{"id": "01H", "type": "profile", "attributes": {"email": "a@b.com"}}]
        }
        with patch.object(sys, "argv", ["get.py", "--email", "a@b.com", "--output", "json"]):
            assert getcmd.main() == 0
        _, kwargs = client.get.call_args
        assert kwargs["params"]["filter"] == 'equals(email,"a@b.com")'
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "01H"


def test_get_by_email_not_found_raises(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {"data": []}
        with (
            patch.object(sys, "argv", ["get.py", "--email", "missing@b.com"]),
            pytest.raises(ResourceNotFoundError),
        ):
            getcmd.main()


def test_get_requires_id_or_email(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["get.py"]),
            pytest.raises(SystemExit),
        ):
            getcmd.main()
