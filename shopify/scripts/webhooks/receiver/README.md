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
