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


def test_bulk_query_polls_until_complete_then_yields_rows(httpx_mock, monkeypatch, cfg):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    # Mutation kickoff
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {
                "bulkOperationRunQuery": {
                    "bulkOperation": {"id": "gid://bulk/1", "status": "CREATED"},
                    "userErrors": [],
                }
            }
        },
    )
    # First poll: still running
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {
                "currentBulkOperation": {
                    "status": "RUNNING",
                    "url": None,
                    "errorCode": None,
                    "objectCount": 0,
                    "id": "gid://bulk/1",
                }
            }
        },
    )
    # Second poll: completed
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {
                "currentBulkOperation": {
                    "status": "COMPLETED",
                    "url": "https://results.example/bulk.jsonl",
                    "errorCode": None,
                    "objectCount": 2,
                    "id": "gid://bulk/1",
                }
            }
        },
    )
    # The download
    httpx_mock.add_response(
        method="GET",
        url="https://results.example/bulk.jsonl",
        content=b'{"id":"gid://Order/1"}\n{"id":"gid://Order/2"}\n',
    )

    client = ShopifyClient(config=cfg)
    rows = list(
        client.bulk_query(
            "query { orders { edges { node { id } } } }",
            poll_interval=0.0,
            max_wait=10.0,
        )
    )
    assert rows == [{"id": "gid://Order/1"}, {"id": "gid://Order/2"}]


def test_bulk_query_raises_on_failed_status(httpx_mock, monkeypatch, cfg):
    from shopify.utils.client import ShopifyBulkOperationError

    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {
                "bulkOperationRunQuery": {
                    "bulkOperation": {"id": "gid://bulk/1", "status": "CREATED"},
                    "userErrors": [],
                }
            }
        },
    )
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {
                "currentBulkOperation": {
                    "status": "FAILED",
                    "url": None,
                    "errorCode": "INTERNAL_SERVER_ERROR",
                    "objectCount": 0,
                    "id": "gid://bulk/1",
                }
            }
        },
    )
    client = ShopifyClient(config=cfg)
    with pytest.raises(ShopifyBulkOperationError):
        list(client.bulk_query("query { x }", poll_interval=0.0, max_wait=10.0))


def test_bulk_query_yields_nothing_when_url_is_empty(httpx_mock, monkeypatch, cfg):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {
                "bulkOperationRunQuery": {
                    "bulkOperation": {"id": "gid://bulk/1", "status": "CREATED"},
                    "userErrors": [],
                }
            }
        },
    )
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {
                "currentBulkOperation": {
                    "status": "COMPLETED",
                    "url": None,
                    "errorCode": None,
                    "objectCount": 0,
                    "id": "gid://bulk/1",
                }
            }
        },
    )
    client = ShopifyClient(config=cfg)
    assert list(client.bulk_query("query { x }", poll_interval=0.0, max_wait=10.0)) == []


def test_bulk_query_does_one_final_poll_after_deadline(httpx_mock, monkeypatch, cfg):
    """If max_wait expires between polls, do one final un-timed poll before raising.

    Avoids spurious failures when the next poll would have returned COMPLETED.
    """
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    # Mutation kickoff
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {
                "bulkOperationRunQuery": {
                    "bulkOperation": {"id": "gid://bulk/1", "status": "CREATED"},
                    "userErrors": [],
                }
            }
        },
    )
    # First poll inside the loop: still RUNNING. With max_wait=0 the loop
    # body never enters; the deadline-expired branch runs and we get one
    # un-timed final poll.
    # The final un-timed poll returns COMPLETED + url.
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {
                "currentBulkOperation": {
                    "status": "COMPLETED",
                    "url": "https://results.example/bulk.jsonl",
                    "errorCode": None,
                    "objectCount": 1,
                    "id": "gid://bulk/1",
                }
            }
        },
    )
    httpx_mock.add_response(
        method="GET",
        url="https://results.example/bulk.jsonl",
        content=b'{"id":"gid://Order/1"}\n',
    )
    client = ShopifyClient(config=cfg)
    rows = list(client.bulk_query("query { x }", poll_interval=0.0, max_wait=0.0))
    assert rows == [{"id": "gid://Order/1"}]


def test_bulk_query_retries_jsonl_download_on_transient_error(httpx_mock, monkeypatch, cfg):
    """A single 5xx during the JSONL download is retried (up to 3 attempts)."""
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {
                "bulkOperationRunQuery": {
                    "bulkOperation": {"id": "gid://bulk/1", "status": "CREATED"},
                    "userErrors": [],
                }
            }
        },
    )
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={
            "data": {
                "currentBulkOperation": {
                    "status": "COMPLETED",
                    "url": "https://results.example/bulk.jsonl",
                    "errorCode": None,
                    "objectCount": 1,
                    "id": "gid://bulk/1",
                }
            }
        },
    )
    # First download attempt: 500. Second attempt: success.
    httpx_mock.add_response(
        method="GET",
        url="https://results.example/bulk.jsonl",
        status_code=500,
        content=b"oh no",
    )
    httpx_mock.add_response(
        method="GET",
        url="https://results.example/bulk.jsonl",
        content=b'{"id":"gid://Order/1"}\n',
    )

    # Patch time.sleep so the retry backoff doesn't slow the test.
    import shopify.utils.client as client_mod

    monkeypatch.setattr(client_mod.time, "sleep", lambda *_a, **_k: None)
    client = ShopifyClient(config=cfg)
    rows = list(client.bulk_query("query { x }", poll_interval=0.0, max_wait=10.0))
    assert rows == [{"id": "gid://Order/1"}]
