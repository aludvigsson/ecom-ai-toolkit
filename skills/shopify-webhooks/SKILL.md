---
name: shopify-webhooks
description: Manage Shopify webhook subscriptions (list, create, delete) via the webhooks/ CLI scripts, and run the bundled FastAPI receiver that verifies HMAC SHA256 signatures and dispatches payloads to per-topic handlers. Use when the user says list webhook subscriptions, subscribe to orders/create, create a webhook, delete webhook X, set up the webhook receiver, verify webhook HMAC, or handle Shopify webhooks. list honors --output table|json|markdown and --topic filter; create requires --topic and --callback-url (HTTPS) and honors --dry-run; delete requires --yes for live execution and supports --dry-run without --yes.
---

# shopify-webhooks

## When to use

- User wants to **list webhook subscriptions**: "show my webhook subscriptions", "what topics am I subscribed to", "any webhooks pointing at the old URL?".
- User wants to **create a subscription**: "subscribe to orders/create", "send products/update to this endpoint", "register a webhook for app/uninstalled".
- User wants to **delete a subscription**: "remove that webhook", "delete the orders/create subscription".
- User wants to **run / understand the receiver**: "set up the webhook receiver", "how do I verify the HMAC signature", "where do I add handler logic".

## When NOT to use

- **Deploying the receiver** — this toolkit ships runnable code, not a deployed service. Deployment (Cloud Run, Fly, a VPS, etc.) is the consumer's concern; see `shopify/scripts/webhooks/receiver/README.md`.
- **EventBridge or PubSub subscriptions** — `create.py` only creates HTTP subscriptions. `list.py` *displays* EventBridge/PubSub endpoints (flattened into `endpoint_kind` / `endpoint_target`), but creating them needs `shopify-plugin:shopify-admin` directly.
- Anything not exposed by `list.py` / `create.py` / `delete.py` (updating a subscription, bulk operations, GDPR mandatory webhooks config) — use `shopify-plugin:shopify-admin` directly.

## Prerequisites

- `shopify-auth` has been run successfully **OR** `store-config.yaml` and `.env.local` exist at repo root with `SHOPIFY_ADMIN_ACCESS_TOKEN` populated.
- CLI scripts: `uv sync --extra shopify`.
- Receiver (FastAPI + uvicorn): `uv sync --extra shopify --extra webhooks`.

If any script returns an auth-shaped error, stop and delegate to `shopify-auth`.

## CRUD scripts

### List subscriptions

```bash
uv run shopify/scripts/webhooks/list.py
uv run shopify/scripts/webhooks/list.py --topic ORDERS_CREATE   # filter by topic
```

The polymorphic `endpoint` field is flattened into `endpoint_kind` (the
`__typename`: `WebhookHttpEndpoint` / `WebhookEventBridgeEndpoint` /
`WebhookPubSubEndpoint`) and `endpoint_target` (callback URL, ARN, or
`project:topic`) so table output stays readable.

### Create a subscription (dry-run first)

```bash
uv run shopify/scripts/webhooks/create.py \
  --topic ORDERS_CREATE \
  --callback-url https://example.com/webhooks/orders/create \
  --dry-run

# Looks right? Drop --dry-run:
uv run shopify/scripts/webhooks/create.py \
  --topic ORDERS_CREATE \
  --callback-url https://example.com/webhooks/orders/create
```

Flags: `--topic` (required, `WebhookSubscriptionTopic` enum value such as
`ORDERS_CREATE`), `--callback-url` (required, **must be HTTPS** — enforced at
parse time), `--format` (`JSON` default or `XML`).

### Delete a subscription (dry-run, then `--yes`)

```bash
uv run shopify/scripts/webhooks/delete.py --id gid://shopify/WebhookSubscription/123 --dry-run

# Confirm with --yes:
uv run shopify/scripts/webhooks/delete.py --id gid://shopify/WebhookSubscription/123 --yes
```

Destructive. `--dry-run` prints the intended deletion and exits 0 without
`--yes`; live execution requires `--yes`.

## The receiver

A minimal FastAPI app at `shopify/scripts/webhooks/receiver/` that:

1. Verifies the `X-Shopify-Hmac-Sha256` header against the raw request body
   using `SHOPIFY_WEBHOOK_SECRET` (base64 HMAC-SHA256). Mismatch → `401`.
2. Dispatches the parsed JSON payload to the matching per-topic handler.
   Unknown topic → `404`; malformed JSON → `400`.

Endpoint family: `POST /webhooks/{ns}/{name}` (e.g. `/webhooks/orders/create`).
Health check: `GET /healthz`.

### Run locally

```bash
uv sync --extra shopify --extra webhooks
SHOPIFY_WEBHOOK_SECRET=<your secret> \
  uv run uvicorn shopify.scripts.webhooks.receiver.app:app --reload
```

Expose via a tunnel (`cloudflared tunnel --url http://localhost:8000` or
`ngrok http 8000`), then register the tunnel URL with `create.py`.

### Add a topic

1. Add a stub at `receiver/handlers/<ns>_<name>.py` (Shopify topic with `/`
   replaced by `_`) exposing a `handle(payload: dict) -> None` function.
2. Register it in `receiver/handlers/__init__.py`'s `HANDLERS` dict keyed by
   the `ns/name` topic string.
3. Register a Shopify subscription pointing at `/webhooks/<ns>/<name>`.

Shipped stubs: `orders/create`, `orders/updated`, `products/update`,
`app/uninstalled`. They log and no-op — fill in your domain logic.

See `receiver/README.md` for the container build and deploy hints.

## Common pitfalls

- **`--callback-url` must be HTTPS.** The parser rejects non-HTTPS at parse
  time; Shopify won't accept an HTTP endpoint anyway.
- **`--topic` is the enum, not the path.** Use `ORDERS_CREATE` (the
  `WebhookSubscriptionTopic` value) for the CRUD scripts, but the receiver
  route is the slash form `/webhooks/orders/create`.
- **The receiver verifies HMAC over the *raw* body.** Any middleware that
  re-serialises the body before verification will break the signature. The app
  reads `await request.body()` directly for this reason.
- **`SHOPIFY_WEBHOOK_SECRET` is the webhook signing secret**, distinct from the
  Admin API access token. It must be set in the receiver's environment.
- **Unregistered topics 404.** Subscribing to a topic in Shopify is separate
  from adding a handler — do both, or the receiver returns `404` for that topic.
- **Deployment is out of scope.** The toolkit gives you runnable code and a
  Dockerfile; where it runs is yours to decide.

## Reference

For subscription updates, EventBridge/PubSub endpoint creation, GDPR mandatory
webhooks, and the full `WebhookSubscriptionInput` schema, defer to the
`shopify-plugin:shopify-admin` skill.
