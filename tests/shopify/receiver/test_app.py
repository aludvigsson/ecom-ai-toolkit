import base64
import hashlib
import hmac
import json

import pytest

from shopify.scripts.webhooks.receiver.app import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SHOPIFY_WEBHOOK_SECRET", "topsecret")
    from fastapi.testclient import TestClient

    return TestClient(app)


def _sign(body: bytes, secret: str = "topsecret") -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def test_post_with_valid_signature_returns_200(client):
    body = json.dumps({"id": 1, "name": "#1001"}).encode()
    r = client.post(
        "/webhooks/orders/create",
        content=body,
        headers={"X-Shopify-Hmac-Sha256": _sign(body), "X-Shopify-Topic": "orders/create"},
    )
    assert r.status_code == 200


def test_post_with_bad_signature_returns_401(client):
    body = b'{"id":1}'
    r = client.post(
        "/webhooks/orders/create",
        content=body,
        headers={"X-Shopify-Hmac-Sha256": "wrong", "X-Shopify-Topic": "orders/create"},
    )
    assert r.status_code == 401


def test_post_unknown_topic_returns_404(client):
    body = b'{"id":1}'
    r = client.post(
        "/webhooks/wat/wat",
        content=body,
        headers={"X-Shopify-Hmac-Sha256": _sign(body), "X-Shopify-Topic": "wat/wat"},
    )
    assert r.status_code == 404


def test_healthz_ok_when_secret_set(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_healthz_degraded_when_secret_missing(monkeypatch):
    # skip .env.local loading so the secret is genuinely absent
    monkeypatch.setattr("core.secrets._env_loaded", True)
    monkeypatch.delenv("SHOPIFY_WEBHOOK_SECRET", raising=False)
    from fastapi.testclient import TestClient

    c = TestClient(app)
    r = c.get("/healthz")
    assert r.status_code == 503
    assert r.json()["status"] == "degraded"


def test_startup_fails_fast_when_secret_missing(monkeypatch):
    monkeypatch.setattr("core.secrets._env_loaded", True)
    monkeypatch.delenv("SHOPIFY_WEBHOOK_SECRET", raising=False)
    from fastapi.testclient import TestClient

    from core.secrets import MissingSecretError

    # entering the TestClient context runs the lifespan startup, which raises
    with pytest.raises(MissingSecretError), TestClient(app):
        pass
