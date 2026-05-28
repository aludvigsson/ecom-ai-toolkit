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
        raise HTTPException(status_code=400, detail="invalid JSON body") from None
    handler(payload)
    return {"ok": True, "topic": topic}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
