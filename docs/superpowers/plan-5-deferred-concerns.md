# Plan 5 — Deferred concerns (v0.5.0-alpha)

Findings from the final Plan 5 whole-plan code review (webhook CRUD + FastAPI receiver). None blocked v0.5.0-alpha — all tests pass, ruff clean, CI green. Plan 5 is the last plan in the v1 sequence, so these are post-v1 polish rather than prerequisites for a follow-on plan.

## Important

### I-1. Receiver does not fail fast on a missing `SHOPIFY_WEBHOOK_SECRET`
**Where:** `shopify/scripts/webhooks/receiver/app.py` calls `require_secret("SHOPIFY_WEBHOOK_SECRET")` inside the request handler.

**Why:** With no secret configured the app boots cleanly and `GET /healthz` returns `200` — so a load balancer / orchestrator marks the container healthy — but **every** webhook `POST` returns `500` (the `MissingSecretError` propagates as an unhandled exception). Verified: `POST /webhooks/orders/create` → `500`, `GET /healthz` → `200` when the secret is unset. The misconfiguration is invisible until the first real webhook fails, and the health check actively hides it.

**Fix options:**
- (a) Resolve the secret once at startup (module load or a FastAPI startup event) and store it on `app.state`; a missing secret then crashes the process at boot — loud and immediate.
- (b) Have `/healthz` check that the secret is resolvable and return `503` if not.
Prefer (a); optionally also (b) for defence in depth.

### I-2. Synchronous handlers run on the event loop and risk Shopify's delivery timeout
**Where:** `receiver/handlers/*.py` expose `def handle(payload)` (sync), invoked directly inside the async `receive` endpoint.

**Why:** The stub shape invites users to put real business logic — DB writes, outbound HTTP, queue pushes — directly in `handle`, which executes on the asyncio event loop thread and blocks it. Shopify expects a 2xx within ~5s and retries with backoff otherwise, so a slow handler causes duplicate deliveries and head-of-line blocking for concurrent webhooks.

**Fix:** Dispatch handler work via `fastapi.BackgroundTasks` (respond `200` immediately, process after) or push to an external queue. Document the pattern in the `shopify-webhooks` skill and add a one-line note to each stub's TODO.

### I-3. No idempotency / replay handling
**Where:** receiver dispatch path; handler stubs.

**Why:** Shopify retries on non-2xx (and occasionally double-delivers), and the receiver ignores the `X-Shopify-Webhook-Id` header, so handlers can process the same event more than once. For non-idempotent logic (charging, emailing, decrementing stock) that's a correctness bug in the consumer's code.

**Fix:** Surface `X-Shopify-Webhook-Id` to handlers (or note it in the skill) and recommend a dedupe store. At minimum, add an idempotency caveat to the stub TODOs and the skill's "Add a topic" section.

## Suggestions

### S-1. Resolve the secret once instead of per-request
**Where:** `app.py`. `require_secret` is called on every request. It's cached after the first `.env.local` load (`_env_loaded` global), so the cost is small, but reading it once into `app.state` at startup is cleaner and pairs naturally with the I-1 fix.

### S-2. `list.py` silently truncates at `--limit`
**Where:** `shopify/scripts/webhooks/list.py` fetches `first: --limit` and does not paginate. A store with more subscriptions than the limit silently drops the overflow. Add a pitfall note to the `shopify-webhooks` skill (stores rarely exceed the default, so low urgency) or loop on `pageInfo.hasNextPage`.

### S-3. `X-Shopify-Topic` header is ignored
**Where:** `app.py` derives the topic purely from the URL path (`{ns}/{name}`). This is clean (one callback URL per topic) but means a header/path mismatch goes unnoticed. Optionally cross-check `X-Shopify-Topic` against the path and `400`/log on disagreement.

### S-4. Dockerfile has no `HEALTHCHECK`
**Where:** `receiver/Dockerfile`. `/healthz` exists but isn't wired to a container `HEALTHCHECK` instruction. Adding one improves behaviour under orchestrators that don't define their own probe. (Note: if I-1(b) is taken, `/healthz` becomes a more meaningful probe.)

### S-5. No request-body size guard
**Where:** `app.py` reads the full body via `await request.body()`. Bounded by Shopify payload sizes in practice, so low priority, but a deployed public endpoint could be sent an arbitrarily large body.

## Triage
- I-1: small, high-value — fix in the next polish pass (fail-fast at startup).
- I-2, I-3: primarily documentation in the `shopify-webhooks` skill + stub TODOs; the code change (BackgroundTasks) is optional and consumer-dependent.
- S-1: fold into the I-1 fix.
- S-2, S-3, S-4, S-5: opportunistic.

## v1 status
Plans 1–5 all shipped. Webhook CRUD + receiver complete; `webhooks` extra installable; CI installs it and runs the receiver suite. The only open Plan 5 Definition-of-Done item is the **manual dev-shop smoke test** (subscribe a topic, fire a test event, confirm the receiver logs the dispatch) — requires live shop credentials.
