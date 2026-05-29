# Klaviyo campaign send / cancel endpoint — verification note

**Task:** Plan K2, Task 4 (BLOCKING verification before Tasks 5 & 6).
**Verified:** 2026-05-29.

## Revision in play

- `klaviyo.utils.client._DEFAULT_REVISION` = **`2024-10-15`**
- `store-config.example.yaml` → `domains.klaviyo.api_version` = **`"2024-10-15"`**

Both the toolkit default and the example config target the **`2024-10-15`** dated
revision. The send/cancel shapes below are stable across recent dated revisions
(`2024-06-15` through the current `2026-04-15`); they are not specific to a single
revision, so the implementation is correct for `2024-10-15` and the current default.

> CAVEAT: verified against Klaviyo's published API reference and OpenAPI spec only
> (no live Klaviyo API key / network-authenticated account was available in this
> execution environment). Confirm against a live `2024-10-15` account before relying
> on the cancel/revert state transitions in production. If a live check finds a
> different shape for the configured revision, update this note AND the Tasks 5/6
> scripts + tests to match.

## Confirmed shape: `campaign-send-jobs` resource

The established shape the plan assumes is **correct**. Scheduling vs. immediate is
expressed on the **campaign** resource (`send_strategy`), and triggering the send is
a separate **`campaign-send-jobs`** call. Cancellation is a `PATCH` on the send job.

### 1. Trigger send (send now) — `schedule.py` immediate path

- **Method/path:** `POST /api/campaign-send-jobs`
- **JSON:API type:** `campaign-send-job`
- **`data.id`:** the **campaign ID** (the send job is created with the campaign's id;
  "The ID of the campaign to send")
- **Attributes:** none required.

```json
{
  "data": {
    "type": "campaign-send-job",
    "id": "<campaign-id>"
  }
}
```

This triggers the campaign to send **asynchronously**. Scope: `campaigns:write`.
Rate limits: burst 10/s, steady 150/m.

### 2. Schedule a send — `schedule.py` scheduled path

Scheduling is **NOT** an attribute on `campaign-send-jobs`. The send time lives on
the **campaign** via the `send_strategy` attribute (set at campaign create, or via
`PATCH /api/campaigns/{id}`). `send_strategy.method` is one of:

- `immediate` — send right away.
- `static` — send at a specific `datetime` (ISO 8601). Optional
  `options.is_local` enables local-recipient-timezone send (requires UTC time).
- `throttled` — `datetime` + `throttle_percentage` (allowed: 10,11,13,14,17,20,25,33,50).
- `smart_send_time` — optimized send on a specified `date`.

Example `send_strategy` for a static scheduled send:

```json
{
  "method": "static",
  "datetime": "2026-06-01T09:00:00+00:00",
  "options": { "is_local": false }
}
```

> IMPLEMENTATION NOTE for Task 5: a future-dated/scheduled campaign is configured by
> setting `send_strategy` on the campaign. The `POST /campaign-send-jobs` call is what
> actually queues/triggers the send. `schedule.py` should: for an immediate send, POST
> the send job with just `{type, id}`; for a scheduled send, set the campaign's
> `send_strategy` (static `datetime`) first, then POST the send job. The plan's body
> text refers to a `scheduled_at`/`send_strategy` — the verified field is
> `send_strategy.datetime` on the **campaign**, not a `scheduled_at` attribute on the
> send job. Adjust the Task 5 body/assertions accordingly.

### 3. Cancel / revert a send — `cancel.py`

- **Method/path:** `PATCH /api/campaign-send-jobs/{id}`
- **JSON:API type:** `campaign-send-job`
- **`data.id`:** "The ID of the currently sending campaign to cancel or revert"
  (same id used to create the job).
- **Required attribute:** `action`, enum **`cancel`** | **`revert`**.
  - `cancel` → status `CANCELED` (permanent).
  - `revert` → status back to `DRAFT`.

```json
{
  "data": {
    "type": "campaign-send-job",
    "id": "<campaign-id>",
    "attributes": {
      "action": "cancel"
    }
  }
}
```

Scope: `campaigns:write`. This matches the plan's assumed cancel shape
(`PATCH /campaign-send-jobs/{id}` with `{"attributes": {"action": "cancel"}}`).
Note `revert` is also available and may be worth exposing as a `--action` choice in
`cancel.py`.

## Net effect on Tasks 5 & 6

- Cancel (Task 6): plan's assumed shape is **confirmed** — implement as written.
- Send-now (Task 5 immediate): `POST /campaign-send-jobs` with `{type, id}` (no
  attributes) — confirmed.
- Scheduled send (Task 5 scheduled): the schedule lives on the **campaign**
  (`send_strategy.datetime`), not on the send job. If Task 5's code/tests assume a
  `scheduled_at` attribute on the `campaign-send-jobs` body, adjust them to set
  `send_strategy` on the campaign per this note before implementing.

## Sources (accessed 2026-05-29)

- Campaigns API overview — https://developers.klaviyo.com/en/reference/campaigns_api_overview
- Create Campaign Send Job — https://developers.klaviyo.com/en/reference/create_campaign_send_job
- Update/Cancel Campaign Send Job — https://developers.klaviyo.com/en/reference/update_campaign_send_job
- OpenAPI spec (send) — https://raw.githubusercontent.com/klaviyo/openapi/main/openapi/stable/apis/send_campaign.json
- OpenAPI spec (cancel) — https://raw.githubusercontent.com/klaviyo/openapi/main/openapi/stable/apis/cancel_campaign_send.json
- OpenAPI spec (campaign create — send_strategy) — https://raw.githubusercontent.com/klaviyo/openapi/main/openapi/stable/apis/create_campaign.json
