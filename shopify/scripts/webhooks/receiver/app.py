"""Shopify webhook receiver.

Single POST endpoint family at /webhooks/{topic_namespace}/{topic_name} that:
  1. Verifies HMAC SHA256 using SHOPIFY_WEBHOOK_SECRET.
  2. Dispatches the parsed JSON payload to the matching handler.

Deployment is the consumer's concern; see ./README.md.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger
from core.secrets import get_secret, require_secret
from shopify.scripts.webhooks.receiver.handlers import HANDLERS
from shopify.scripts.webhooks.receiver.hmac import verify_signature

_SECRET = "SHOPIFY_WEBHOOK_SECRET"
_log = get_logger("ecom.webhooks.receiver")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast: without the signing secret every webhook would 500 at request
    # time while /healthz still reported 200. Crash at boot instead.
    require_secret(_SECRET)
    yield


app = FastAPI(
    title="ecom-ai-toolkit Shopify webhook receiver",
    version="0.5.1",
    lifespan=lifespan,
)


@app.post("/webhooks/{ns}/{name}")
async def receive(ns: str, name: str, request: Request) -> dict:
    topic = f"{ns}/{name}"
    body = await request.body()
    sig = request.headers.get("X-Shopify-Hmac-Sha256")
    secret = require_secret(_SECRET)
    if not verify_signature(secret=secret, body=body, header_value=sig):
        _log.warning("HMAC verification failed topic=%s", topic)
        raise HTTPException(status_code=401, detail="invalid signature")
    handler = HANDLERS.get(topic)
    if handler is None:
        raise HTTPException(status_code=404, detail=f"no handler for topic {topic!r}")
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid JSON body") from None
    # Shopify may retry/duplicate deliveries; the webhook id lets handlers dedupe.
    webhook_id = request.headers.get("X-Shopify-Webhook-Id")
    _log.info("dispatching topic=%s webhook_id=%s", topic, webhook_id)
    handler(payload)
    return {"ok": True, "topic": topic}


@app.get("/healthz")
def healthz() -> JSONResponse:
    # Reflect readiness: a receiver with no signing secret cannot process any
    # webhook, so it must not report healthy to a load balancer / orchestrator.
    if not get_secret(_SECRET):
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "detail": f"{_SECRET} not set"},
        )
    return JSONResponse(status_code=200, content={"status": "ok"})
