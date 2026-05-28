# Plan 5: Shopify Webhooks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship webhook subscription management (CRUD scripts) plus a runnable FastAPI receiver with HMAC validation and per-topic handler stubs. Receiver is *runnable code*, not a deployed service — the toolkit doesn't own deployment.

**Architecture:** CRUD scripts mirror the Plan 2/3 conventions. The receiver is a small FastAPI app under `shopify/scripts/webhooks/receiver/`. HMAC validation is implemented as a FastAPI dependency that runs on every endpoint and 401s on signature mismatch. Each subscribed topic has a stub handler module in `handlers/` that the user fills in.

**Tech Stack:** Adds `fastapi` and `uvicorn[standard]` (already declared under `webhooks` extras in Plan 1). For tests: `httpx` (already installed) and `fastapi.testclient`.

**Spec reference:** §§ 6.1 (`webhooks/`), 6.3 (receiver boundaries: code shipped, deploy is consumer's), 6.6 (`shopify-webhooks` skill).

**Depends on:** Plan 1. The `webhooks` extra must be installable: `uv sync --extra shopify --extra webhooks`.

---

## File Structure

| Path | Responsibility |
|---|---|
| `shopify/scripts/webhooks/__init__.py` | empty |
| `shopify/scripts/webhooks/list.py` | List webhook subscriptions |
| `shopify/scripts/webhooks/create.py` | Create a webhook subscription |
| `shopify/scripts/webhooks/delete.py` | Delete a webhook subscription |
| `shopify/scripts/webhooks/receiver/__init__.py` | empty |
| `shopify/scripts/webhooks/receiver/app.py` | FastAPI app + route registration |
| `shopify/scripts/webhooks/receiver/hmac.py` | HMAC SHA256 validation per Shopify spec |
| `shopify/scripts/webhooks/receiver/handlers/__init__.py` | Topic→handler dispatch table |
| `shopify/scripts/webhooks/receiver/handlers/orders_create.py` | Stub: log + persist + no-op |
| `shopify/scripts/webhooks/receiver/handlers/orders_updated.py` | Stub |
| `shopify/scripts/webhooks/receiver/handlers/products_update.py` | Stub |
| `shopify/scripts/webhooks/receiver/handlers/app_uninstalled.py` | Stub |
| `shopify/scripts/webhooks/receiver/Dockerfile` | Container image for the receiver |
| `shopify/scripts/webhooks/receiver/README.md` | Run locally + deploy hints |
| `skills/shopify-webhooks/SKILL.md` | Single skill covering CRUD + receiver setup |
| `tests/shopify/scripts/test_webhooks_*.py` | CRUD script tests |
| `tests/shopify/receiver/__init__.py` | empty |
| `tests/shopify/receiver/test_hmac.py` | Unit test for HMAC validation |
| `tests/shopify/receiver/test_app.py` | FastAPI TestClient tests with fixture HMAC signatures |

---

## Task 1: CRUD scripts — `shopify/scripts/webhooks/list.py`

GraphQL:
```graphql
query Subs($first: Int!) {
  webhookSubscriptions(first: $first) {
    edges { node {
      id topic format
      endpoint {
        __typename
        ... on WebhookHttpEndpoint { callbackUrl }
        ... on WebhookEventBridgeEndpoint { arn }
        ... on WebhookPubSubEndpoint { pubSubProject pubSubTopic }
      }
      createdAt updatedAt
    } }
  }
}
```

- [ ] **Step 1: Test (mocked):** verify HTTP-endpoint and EventBridge-endpoint outputs both render in table/json.
- [ ] **Step 2: Implement.** Flags: `--topic` (filter), plus common.
- [ ] **Step 3: Commit**

```bash
mkdir -p shopify/scripts/webhooks tests/shopify/scripts
touch shopify/scripts/webhooks/__init__.py
# write + test + commit
git add shopify/scripts/webhooks/ tests/shopify/scripts/test_webhooks_list.py
git commit -m "feat(shopify): webhooks/list.py"
```

---

## Task 2: `shopify/scripts/webhooks/create.py`

Uses `webhookSubscriptionCreate(topic: WebhookSubscriptionTopic!, webhookSubscription: WebhookSubscriptionInput!)`.

- [ ] **Step 1: Test (mocked):** verify topic and callbackUrl appear in the input shape; `--dry-run` does not call mutation.
- [ ] **Step 2: Implement.** Flags: `--topic` (required, e.g. `ORDERS_CREATE`), `--callback-url` (required), `--format` (`JSON` default, or `XML`), `--api-version` (defaults to `cfg.domains.shopify.api_version`), `--dry-run`.
- [ ] **Step 3: Commit**

```graphql
mutation Create($topic: WebhookSubscriptionTopic!, $input: WebhookSubscriptionInput!) {
  webhookSubscriptionCreate(topic: $topic, webhookSubscription: $input) {
    webhookSubscription { id topic }
    userErrors { field message }
  }
}
```

---

## Task 3: `shopify/scripts/webhooks/delete.py`

`webhookSubscriptionDelete(id: ID!)`. Requires `--yes` to confirm.

- [ ] **Step 1: Test (mocked).**
- [ ] **Step 2: Implement.** Flags: `--id`, `--yes`.
- [ ] **Step 3: Commit**

---

## Task 4: Receiver — HMAC validation

**Files:**
- Create: `shopify/scripts/webhooks/receiver/__init__.py`
- Create: `shopify/scripts/webhooks/receiver/hmac.py`
- Create: `tests/shopify/receiver/__init__.py`
- Create: `tests/shopify/receiver/test_hmac.py`

Shopify HMAC spec: header `X-Shopify-Hmac-Sha256`; signature is base64 of HMAC-SHA256 of raw request body using webhook shared secret.

- [ ] **Step 1: Test (no FastAPI yet, pure-Python):**
```python
import base64
import hashlib
import hmac as _hmac

from shopify.scripts.webhooks.receiver.hmac import verify_signature


def test_verify_signature_accepts_correct_signature():
    secret = "topsecret"
    body = b'{"id":1}'
    sig = base64.b64encode(_hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    assert verify_signature(secret=secret, body=body, header_value=sig) is True


def test_verify_signature_rejects_tampered_body():
    secret = "topsecret"
    body = b'{"id":1}'
    sig = base64.b64encode(_hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    assert verify_signature(secret=secret, body=b'{"id":2}', header_value=sig) is False


def test_verify_signature_rejects_missing_header():
    assert verify_signature(secret="x", body=b"y", header_value=None) is False
```

- [ ] **Step 2: Implement.**

```python
"""Shopify HMAC SHA256 verification per
https://shopify.dev/docs/apps/webhooks/configuration/https#step-5-verify-the-webhook"""
from __future__ import annotations

import base64
import hashlib
import hmac


def verify_signature(*, secret: str, body: bytes, header_value: str | None) -> bool:
    if not header_value:
        return False
    expected = base64.b64encode(hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()).decode("utf-8")
    return hmac.compare_digest(expected, header_value)
```

- [ ] **Step 3: Test pass + commit**

```bash
uv run pytest tests/shopify/receiver/test_hmac.py -v
git add shopify/scripts/webhooks/receiver/__init__.py shopify/scripts/webhooks/receiver/hmac.py tests/shopify/receiver/
git commit -m "feat(shopify): webhook receiver HMAC SHA256 verification"
```

---

## Task 5: Receiver — handler stubs and dispatch

**Files:**
- Create: `shopify/scripts/webhooks/receiver/handlers/__init__.py`
- Create: `shopify/scripts/webhooks/receiver/handlers/orders_create.py`
- Create: `shopify/scripts/webhooks/receiver/handlers/orders_updated.py`
- Create: `shopify/scripts/webhooks/receiver/handlers/products_update.py`
- Create: `shopify/scripts/webhooks/receiver/handlers/app_uninstalled.py`

- [ ] **Step 1: Write the dispatch table**

`handlers/__init__.py`:
```python
"""Topic → handler dispatch. Each handler accepts a parsed JSON payload."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from shopify.scripts.webhooks.receiver.handlers import (
    app_uninstalled,
    orders_create,
    orders_updated,
    products_update,
)

HANDLERS: dict[str, Callable[[dict[str, Any]], None]] = {
    "orders/create":   orders_create.handle,
    "orders/updated":  orders_updated.handle,
    "products/update": products_update.handle,
    "app/uninstalled": app_uninstalled.handle,
}
```

- [ ] **Step 2: Write each stub handler with the same shape**

Example `handlers/orders_create.py`:
```python
"""orders/create — stub. Fill in business logic for your store."""
from __future__ import annotations

from typing import Any

from core.logging import get_logger

_log = get_logger("ecom.webhooks.orders_create")


def handle(payload: dict[str, Any]) -> None:
    _log.info("orders/create received id=%s name=%s", payload.get("id"), payload.get("name"))
    # TODO: wire to your domain logic (e.g. enqueue follow-up, mirror to warehouse, etc.)
```

Repeat for the other three handlers with appropriately scoped log messages.

- [ ] **Step 3: Commit**

```bash
git add shopify/scripts/webhooks/receiver/handlers/
git commit -m "feat(shopify): webhook receiver handler stubs and dispatch table"
```

---

## Task 6: Receiver — FastAPI app

**Files:**
- Create: `shopify/scripts/webhooks/receiver/app.py`
- Create: `tests/shopify/receiver/test_app.py`

- [ ] **Step 1: Write failing test (FastAPI TestClient)**

```python
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
```

- [ ] **Step 2: Run, confirm fail**

```bash
uv sync --extra dev --extra shopify --extra webhooks
uv run pytest tests/shopify/receiver/test_app.py -v
```
Expected: ImportError or AttributeError.

- [ ] **Step 3: Implement `app.py`**

```python
"""Shopify webhook receiver.

Single POST endpoint family at /webhooks/{topic_namespace}/{topic_name} that:
  1. Verifies HMAC SHA256 using SHOPIFY_WEBHOOK_SECRET.
  2. Dispatches the parsed JSON payload to the matching handler.

Deployment is the consumer's concern; see ./README.md.
"""
from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, Request

from core.logging import get_logger
from core.secrets import require_secret
from shopify.scripts.webhooks.receiver.handlers import HANDLERS
from shopify.scripts.webhooks.receiver.hmac import verify_signature

app = FastAPI(title="ecom-ai-toolkit Shopify webhook receiver", version="0.5.0")
_log = get_logger("ecom.webhooks.receiver")


@app.post("/webhooks/{ns}/{name}")
async def receive(ns: str, name: str, request: Request) -> dict:
    topic = f"{ns}/{name}"
    body = await request.body()
    sig = request.headers.get("X-Shopify-Hmac-Sha256")
    secret = require_secret("SHOPIFY_WEBHOOK_SECRET")
    if not verify_signature(secret=secret, body=body, header_value=sig):
        _log.warning("HMAC verification failed topic=%s", topic)
        raise HTTPException(status_code=401, detail="invalid signature")
    handler = HANDLERS.get(topic)
    if handler is None:
        raise HTTPException(status_code=404, detail=f"no handler for topic {topic!r}")
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid JSON body")
    handler(payload)
    return {"ok": True, "topic": topic}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 4: Tests pass + commit**

```bash
uv run pytest tests/shopify/receiver/ -v
git add shopify/scripts/webhooks/receiver/app.py tests/shopify/receiver/test_app.py
git commit -m "feat(shopify): FastAPI webhook receiver with HMAC verification and topic dispatch"
```

---

## Task 7: Receiver — Dockerfile + README

**Files:**
- Create: `shopify/scripts/webhooks/receiver/Dockerfile`
- Create: `shopify/scripts/webhooks/receiver/README.md`

- [ ] **Step 1: Write Dockerfile**

```dockerfile
FROM python:3.12-slim

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra shopify --extra webhooks --no-dev

COPY core ./core
COPY shopify ./shopify

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "shopify.scripts.webhooks.receiver.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Write README**

```markdown
# Shopify webhook receiver

A minimal FastAPI app that verifies Shopify HMAC signatures and dispatches
webhook payloads to per-topic handler modules.

**This toolkit ships runnable code, not a deployed service.** Deployment is
your responsibility.

## Run locally

```bash
# from repo root
uv sync --extra shopify --extra webhooks
SHOPIFY_WEBHOOK_SECRET=<your secret> \
  uv run uvicorn shopify.scripts.webhooks.receiver.app:app --reload
```

Then expose via a tunnel for end-to-end testing:

```bash
cloudflared tunnel --url http://localhost:8000   # or ngrok http 8000
```

Register the tunnel URL as a webhook subscription:

```bash
uv run shopify/scripts/webhooks/create.py \
  --topic ORDERS_CREATE \
  --callback-url https://<your-tunnel>/webhooks/orders/create
```

## Run in a container

```bash
docker build -t ecom-ai-toolkit-webhooks -f shopify/scripts/webhooks/receiver/Dockerfile .
docker run --rm -p 8000:8000 \
  -e SHOPIFY_WEBHOOK_SECRET=<your secret> \
  ecom-ai-toolkit-webhooks
```

## Deploy

Any container platform works: Cloud Run, Fly, Render, Railway, Kubernetes,
your own VPS. Set `SHOPIFY_WEBHOOK_SECRET` as an environment variable.

## Adding a topic

1. Add a stub at `handlers/<ns>_<name>.py` (matching Shopify topic format with
   `/` replaced by `_`).
2. Register it in `handlers/__init__.py`'s `HANDLERS` dict.
3. Register a Shopify webhook subscription pointing at
   `/webhooks/<ns>/<name>` via `webhooks/create.py`.
```

- [ ] **Step 3: Commit**

```bash
git add shopify/scripts/webhooks/receiver/Dockerfile shopify/scripts/webhooks/receiver/README.md
git commit -m "docs: webhook receiver Dockerfile and deploy README"
```

---

## Task 8: `skills/shopify-webhooks/SKILL.md`

Single skill covers CRUD + receiver setup per spec § 6.6. Triggers: "list webhook subscriptions", "subscribe to orders/create", "delete webhook X", "set up the webhook receiver". Reference both the CRUD scripts and the `receiver/README.md` for deployment.

- [ ] Write + commit.

---

## Task 9: Smoke + final sweep

- [ ] Full test suite: `uv run pytest -v` (now includes receiver tests).
- [ ] Ruff clean.
- [ ] (Manual, dev shop) Subscribe to one topic via `webhooks/create.py`, send a fake event via Shopify admin, verify receiver logs the dispatch.
- [ ] Update `CHANGELOG.md` under `0.5.0`.
- [ ] Tag: `git tag -a v0.5.0-alpha -m "Shopify webhooks (CRUD + receiver)"`.

---

## Definition of Done

- [ ] 3 CRUD scripts in `shopify/scripts/webhooks/` implemented and tested.
- [ ] FastAPI receiver app runnable locally (`uv run uvicorn …`) and in a container (`docker build && docker run`).
- [ ] HMAC verification module unit-tested.
- [ ] App handles valid/invalid/unknown-topic cases (TestClient tests pass).
- [ ] Receiver README documents local run, container, and deploy hints.
- [ ] `shopify-webhooks` skill covers CRUD + receiver setup.
- [ ] CI green (note: receiver tests require `webhooks` extra — update CI workflow to `uv sync --extra dev --extra shopify --extra webhooks` if necessary).
- [ ] CHANGELOG bumped.
