from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from klaviyo.utils.client import (
    KlaviyoAPIError,
    KlaviyoClient,
    ResourceNotFoundError,
    check_errors,
)


def _config(api_version="2024-10-15"):
    domain = SimpleNamespace(enabled=True, api_version=api_version)
    store = SimpleNamespace(shopify_domain="example-store.myshopify.com")
    return SimpleNamespace(store=store, domains={"klaviyo": domain})


def _response(json_body, status_code=200):
    resp = MagicMock()
    resp.json.return_value = json_body
    resp.status_code = status_code
    return resp


def test_client_sets_auth_and_revision_headers(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    captured = {}

    def fake_http(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr("klaviyo.utils.client.HttpClient", fake_http)
    KlaviyoClient(config=_config())
    headers = captured["default_headers"]
    assert headers["Authorization"] == "Klaviyo-API-Key pk_examplefixturekey"
    assert headers["revision"] == "2024-10-15"
    assert headers["accept"] == "application/vnd.api+json"
    assert headers["content-type"] == "application/vnd.api+json"


def test_client_revision_override_wins(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    captured = {}
    monkeypatch.setattr(
        "klaviyo.utils.client.HttpClient",
        lambda **kw: captured.update(kw) or MagicMock(),
    )
    KlaviyoClient(config=_config(api_version=None), revision="2099-01-01")
    assert captured["default_headers"]["revision"] == "2099-01-01"


def test_client_revision_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    captured = {}
    monkeypatch.setattr(
        "klaviyo.utils.client.HttpClient",
        lambda **kw: captured.update(kw) or MagicMock(),
    )
    from klaviyo.utils.client import _DEFAULT_REVISION

    KlaviyoClient(config=_config(api_version=None))
    assert captured["default_headers"]["revision"] == _DEFAULT_REVISION


def test_get_returns_parsed_body(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    client = KlaviyoClient(config=_config())
    client._http = MagicMock()
    client._http.get.return_value = _response({"data": [{"id": "p1"}]})
    body = client.get("profiles", params={"page[size]": 50})
    assert body == {"data": [{"id": "p1"}]}
    client._http.get.assert_called_once()


def test_delete_204_returns_empty(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    client = KlaviyoClient(config=_config())
    resp = MagicMock()
    resp.status_code = 204
    client._http = MagicMock()
    client._http.delete.return_value = resp
    assert client.delete("lists/abc") == {}


def test_paginate_follows_links_next(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    client = KlaviyoClient(config=_config())
    page1 = _response(
        {
            "data": [{"id": "a"}, {"id": "b"}],
            "links": {"next": "https://a.klaviyo.com/api/profiles?page[cursor]=NEXT"},
        }
    )
    page2 = _response({"data": [{"id": "c"}], "links": {"next": None}})
    client._http = MagicMock()
    client._http.get.side_effect = [page1, page2]
    items = list(client.paginate("profiles"))
    assert [i["id"] for i in items] == ["a", "b", "c"]
    assert client._http.get.call_count == 2


def test_paginate_respects_limit(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    client = KlaviyoClient(config=_config())
    page = _response(
        {
            "data": [{"id": str(n)} for n in range(50)],
            "links": {"next": "https://a.klaviyo.com/api/profiles?page[cursor]=NEXT"},
        }
    )
    client._http = MagicMock()
    client._http.get.return_value = page
    items = list(client.paginate("profiles", limit=10))
    assert len(items) == 10


def test_check_errors_raises_on_jsonapi_errors():
    body = {
        "errors": [{"detail": "Invalid email", "source": {"pointer": "/data/attributes/email"}}]
    }
    with pytest.raises(KlaviyoAPIError) as exc:
        check_errors(body)
    assert "Invalid email" in str(exc.value)
    assert "/data/attributes/email" in str(exc.value)
    assert exc.value.errors == body["errors"]


def test_check_errors_noop_on_clean_body():
    check_errors({"data": {"id": "p1"}})  # no raise


def test_resource_not_found_is_lookup_error():
    assert issubclass(ResourceNotFoundError, LookupError)
