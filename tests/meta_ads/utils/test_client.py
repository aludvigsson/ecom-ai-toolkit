from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from meta_ads.utils.client import (
    MetaAPIError,
    MetaClient,
    account_path,
    check_error,
)


def _config(api_version="v21.0"):
    domain = SimpleNamespace(enabled=True, api_version=api_version)
    store = SimpleNamespace(shopify_domain="example-store.myshopify.com")
    return SimpleNamespace(store=store, domains={"meta_ads": domain})


def _response(json_body, status_code=200):
    resp = MagicMock()
    resp.json.return_value = json_body
    resp.status_code = status_code
    resp.content = b"{}"
    return resp


def test_account_path_normalizes_with_and_without_prefix():
    assert account_path("123") == "act_123"
    assert account_path("act_123") == "act_123"
    assert account_path(123) == "act_123"


def test_client_sets_bearer_auth_and_versioned_base_url(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    captured = {}

    def fake_http(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr("meta_ads.utils.client.HttpClient", fake_http)
    MetaClient(config=_config())
    assert captured["base_url"] == "https://graph.facebook.com/v21.0/"
    headers = captured["default_headers"]
    assert headers["Authorization"] == "Bearer EAAexampletoken"


def test_client_api_version_override_wins(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    captured = {}
    monkeypatch.setattr(
        "meta_ads.utils.client.HttpClient",
        lambda **kw: captured.update(kw) or MagicMock(),
    )
    MetaClient(config=_config(api_version=None), api_version="v19.0")
    assert captured["base_url"] == "https://graph.facebook.com/v19.0/"


def test_client_api_version_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    captured = {}
    monkeypatch.setattr(
        "meta_ads.utils.client.HttpClient",
        lambda **kw: captured.update(kw) or MagicMock(),
    )
    from meta_ads.utils.client import _DEFAULT_VERSION

    MetaClient(config=_config(api_version=None))
    assert captured["base_url"] == f"https://graph.facebook.com/{_DEFAULT_VERSION}/"


def test_get_returns_parsed_body(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    client = MetaClient(config=_config())
    client._http = MagicMock()
    client._http.get.return_value = _response({"data": [{"id": "c1"}]})
    body = client.get("act_123/campaigns", params={"fields": "id,name"})
    assert body == {"data": [{"id": "c1"}]}
    client._http.get.assert_called_once()


def test_post_returns_parsed_body(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    client = MetaClient(config=_config())
    client._http = MagicMock()
    client._http.post.return_value = _response({"id": "c9"})
    assert client.post("act_123/campaigns", data={"name": "X"}) == {"id": "c9"}
    _, kwargs = client._http.post.call_args
    assert kwargs["data"] == {"name": "X"}


def test_delete_empty_body_returns_empty(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    client = MetaClient(config=_config())
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b""
    client._http = MagicMock()
    client._http.delete.return_value = resp
    assert client.delete("c9") == {}


def test_paginate_follows_paging_next(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    client = MetaClient(config=_config())
    page1 = _response(
        {
            "data": [{"id": "a"}, {"id": "b"}],
            "paging": {"next": "https://graph.facebook.com/v21.0/act_123/campaigns?after=NEXT"},
        }
    )
    page2 = _response({"data": [{"id": "c"}], "paging": {}})
    client._http = MagicMock()
    client._http.get.side_effect = [page1, page2]
    items = list(client.paginate("act_123/campaigns"))
    assert [i["id"] for i in items] == ["a", "b", "c"]
    assert client._http.get.call_count == 2


def test_paginate_respects_limit(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    client = MetaClient(config=_config())
    page = _response(
        {
            "data": [{"id": str(n)} for n in range(50)],
            "paging": {"next": "https://graph.facebook.com/v21.0/act_123/campaigns?after=NEXT"},
        }
    )
    client._http = MagicMock()
    client._http.get.return_value = page
    items = list(client.paginate("act_123/campaigns", limit=10))
    assert len(items) == 10


def test_check_error_raises_with_all_fields():
    body = {
        "error": {
            "message": "Invalid parameter",
            "code": 100,
            "error_subcode": 1487056,
            "fbtrace_id": "AbC123xyz",
        }
    }
    with pytest.raises(MetaAPIError) as exc:
        check_error(body)
    msg = str(exc.value)
    assert "Invalid parameter" in msg
    assert "100" in msg
    assert "1487056" in msg
    assert "AbC123xyz" in msg
    assert exc.value.code == 100
    assert exc.value.subcode == 1487056
    assert exc.value.fbtrace_id == "AbC123xyz"


def test_check_error_token_code_names_env_var():
    body = {"error": {"message": "expired", "code": 190, "fbtrace_id": "Z"}}
    with pytest.raises(MetaAPIError) as exc:
        check_error(body)
    assert "META_ACCESS_TOKEN" in str(exc.value)


def test_check_error_noop_on_clean_body():
    check_error({"data": [{"id": "c1"}]})  # no raise
