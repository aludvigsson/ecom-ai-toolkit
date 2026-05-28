import pytest

from core.config import StoreConfig
from core.secrets import MissingSecretError
from shopify.utils.client import ShopifyClient, ShopifyGraphQLError

_CFG_DICT = {
    "store": {
        "name": "Test",
        "primary_domain": "test.example",
        "shopify_domain": "test-store.myshopify.com",
        "storefront_type": "online_store_2",
        "default_locale": "en-US",
    },
    "markets": [],
    "domains": {"shopify": {"enabled": True, "api_version": "2025-10"}},
}


@pytest.fixture
def cfg():
    return StoreConfig.model_validate(_CFG_DICT)


def test_graphql_returns_data(httpx_mock, monkeypatch, cfg):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_test")
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {"shop": {"name": "Test"}},
            "extensions": {"cost": {"actualQueryCost": 1}},
        },
    )
    client = ShopifyClient(config=cfg)
    result = client.graphql("query { shop { name } }")
    assert result["shop"]["name"] == "Test"


def test_graphql_user_errors_raise(httpx_mock, monkeypatch, cfg):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_test")
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={"errors": [{"message": "Field 'foo' doesn't exist"}]},
    )
    client = ShopifyClient(config=cfg)
    with pytest.raises(ShopifyGraphQLError) as exc:
        client.graphql("query { foo }")
    assert "doesn't exist" in str(exc.value)


def test_missing_token_raises(monkeypatch, cfg):
    monkeypatch.delenv("SHOPIFY_ADMIN_ACCESS_TOKEN", raising=False)
    with pytest.raises(MissingSecretError) as exc:
        ShopifyClient(config=cfg)
    assert "SHOPIFY_ADMIN_ACCESS_TOKEN" in str(exc.value)


def test_graphql_partial_success_attaches_data_to_error(httpx_mock, monkeypatch, cfg):
    """Shopify can return both `data` and `errors`; the partial data should be
    recoverable via the exception's `.data` attribute."""
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_test")
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {"products": {"edges": [{"node": {"id": "gid://Product/1"}}]}},
            "errors": [{"message": "Some field failed"}],
        },
    )
    client = ShopifyClient(config=cfg)
    with pytest.raises(ShopifyGraphQLError) as exc:
        client.graphql("query { products { edges { node { id } } } }")
    assert exc.value.data is not None
    assert exc.value.data["products"]["edges"][0]["node"]["id"] == "gid://Product/1"


def test_shopify_client_supports_context_manager(httpx_mock, monkeypatch, cfg):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_test")
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={"data": {"shop": {"name": "Test"}}},
    )
    with ShopifyClient(config=cfg) as client:
        result = client.graphql("query { shop { name } }")
    assert result["shop"]["name"] == "Test"


def test_check_user_errors_passes_when_empty():
    ShopifyClient.check_user_errors(
        {"productUpdate": {"product": {"id": "x"}, "userErrors": []}},
        mutation="productUpdate",
    )


def test_check_user_errors_raises_when_present():
    from shopify.utils.client import ShopifyUserError

    with pytest.raises(ShopifyUserError) as exc:
        ShopifyClient.check_user_errors(
            {"productUpdate": {"userErrors": [{"field": ["title"], "message": "is too short"}]}},
            mutation="productUpdate",
        )
    assert "title" in str(exc.value)
    assert "too short" in str(exc.value)
    assert exc.value.mutation == "productUpdate"
    assert exc.value.errors[0]["message"] == "is too short"
