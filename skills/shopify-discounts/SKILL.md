---
name: shopify-discounts
description: Create, read, update, and delete Shopify discounts — code and automatic — across all four kinds (percentage, fixed amount, BXGY, free shipping) via the discounts/ CLI scripts. Use when the user says list discount codes, create 20% off code, create automatic discount, BXGY discount, free shipping discount, update discount end date, delete expired discounts, active discounts, or coupon code. Honors --output table|json|markdown on list/create/update; create/update honor --dry-run; delete requires --yes for live execution and supports --dry-run without --yes.
---

# shopify-discounts

## When to use

- User wants to **list discounts**: "show active discount codes", "list automatic discounts", "what coupons are running", "any expired codes I can clean up?".
- User wants to **create a discount**: "create a 20% off code SPRING20", "set up an automatic free-shipping rule over EUR 50", "make a buy-one-get-one promotion".
- User wants to **update an existing discount**: "extend SPRING20 by a week", "raise the usage limit", "change the title", "push the end date to year-end".
- User wants to **delete an old or wrong discount**: "remove the SPRING20 code", "delete that expired automatic rule".

## When NOT to use

- **Manual order-level discounts** — those go through draft orders / order edits, not the discount API. Out of scope here.
- **Discount A/B testing** — separate concern (campaign tooling, not discount CRUD).
- **Reading order-level discount applications** (which orders used which discount, total revenue discounted) — that lives on the order, not the discount. Delegate to `shopify-orders`.
- Anything not exposed by `list.py` / `create.py` / `update.py` / `delete.py` (gift cards, price rules legacy API, discount classes via Functions, etc.) — use `shopify-plugin:shopify-admin` directly.

## Prerequisites

- `shopify-auth` has been run successfully **OR** `store-config.yaml` and `.env.local` exist at repo root with `SHOPIFY_ADMIN_ACCESS_TOKEN` populated.
- Project deps installed: `uv sync --extra shopify`.

If any script in this skill returns an auth-shaped error, stop and delegate to `shopify-auth`.

## Code vs automatic, four kinds

Shopify has two parallel discount catalogs: **code** (customer enters a coupon at checkout) and **automatic** (applied at checkout based on rules). Pass `--code <CODE>` on `create.py` to make it a code discount; omit `--code` for automatic. Each catalog supports four **kinds**, selected via `--kind`:

- `percentage` — N% off (e.g. 20% off)
- `fixed` — fixed money amount off (e.g. EUR 10 off)
- `bxgy` — buy X get Y (the simple "buy one get one free" form is supported here)
- `free-shipping` — waived shipping cost

`update.py` and `delete.py` **auto-detect the kind** from the existing discount node — you don't pass `--kind` on those; the script queries `codeDiscountNode` and `automaticDiscountNode` for the given GID, reads `__typename`, and dispatches to the right mutation.

## Canonical workflows

### 1. List all discounts (code + automatic)

```bash
uv run shopify/scripts/discounts/list.py --type all
```

### 2. List only active code discounts

```bash
uv run shopify/scripts/discounts/list.py --type code --status ACTIVE
```

`--status` is applied client-side (Shopify's discount-node connections don't accept it as a query argument).

### 3. Create a 20% off code (always dry-run first)

```bash
uv run shopify/scripts/discounts/create.py \
  --kind percentage \
  --code SPRING20 \
  --title "Spring 2026" \
  --value 20 \
  --starts-at 2026-03-01T00:00:00Z \
  --ends-at 2026-03-31T23:59:59Z \
  --usage-limit 1000 \
  --dry-run

# Looks right? Drop --dry-run:
uv run shopify/scripts/discounts/create.py \
  --kind percentage \
  --code SPRING20 \
  --title "Spring 2026" \
  --value 20 \
  --starts-at 2026-03-01T00:00:00Z \
  --ends-at 2026-03-31T23:59:59Z \
  --usage-limit 1000
```

### 4. Create automatic free shipping (no code)

```bash
uv run shopify/scripts/discounts/create.py \
  --kind free-shipping \
  --title "Free shipping over 50" \
  --applies-to all
```

### 5. Update an existing discount's end date

```bash
uv run shopify/scripts/discounts/update.py \
  --id gid://shopify/DiscountCodeNode/123 \
  --ends-at 2026-12-31T23:59:59Z
```

The script first runs the detect query to learn that `123` is a `DiscountCodeBasic`, then routes to `discountCodeBasicUpdate`.

### 6. Delete a discount (dry-run first, then `--yes`)

```bash
uv run shopify/scripts/discounts/delete.py \
  --id gid://shopify/DiscountAutomaticNode/456 \
  --dry-run

# Looks right? Confirm with --yes:
uv run shopify/scripts/discounts/delete.py \
  --id gid://shopify/DiscountAutomaticNode/456 \
  --yes
```

## Common pitfalls

- **`--value` for percentages is 0-100** (`20` means 20%), normalised to the API's 0-1 fraction internally (sent as `0.20`). Passing `0.20` will silently create a 0.2% off discount, which is almost never what you want.
- **`--value` for `fixed` is a money amount string-like** (`10.00`); currency is inferred from the shop's primary currency. Multi-currency stores need a follow-up flag (not in v0.3).
- **`--ends-at` is exclusive in Shopify** (a discount with `endsAt = 2026-03-31T23:59:59Z` is no longer valid at midnight Z). Use `23:59:59Z` to mean "valid through that day".
- **`--starts-at` defaults to "now"** (UTC, formatted to second precision). For future scheduling pass an explicit ISO datetime so the operator can see exactly when activation lands.
- **`--code` value is case-insensitive in Shopify** at the matching layer; customers typing `spring20` will still match `SPRING20`. Pass uppercase for clarity in the admin UI.
- **`delete.py` is destructive and irreversible.** Always run `--dry-run` first; the script will print the detected kind so you can confirm you're deleting the right node. Then add `--yes`.
- **`update.py` requires the discount to exist already.** The script auto-detects whether it's code or automatic; if the `--id` is wrong, the detect query returns no match and the script errors clearly without running any mutation.
- **`update.py --value` requires `--applies-to`.** A partial `customerGets` update that sends a new value without an items selector fails Shopify's input validation. The script enforces this at parse time so you never round-trip a broken mutation. If you only want to extend dates or rename a discount, leave `--value` off and you don't need `--applies-to`.
- **BXGY is the most complex.** The `create.py` script supports the simple "buy X get Y free with item-level selection" case (effectively a percentage-1.0 discount on the get-side). Anything more advanced (tiered, percent-of, mix of buy/get item sets, customer-segment gating) needs `shopify-plugin:shopify-admin` directly.
- **`--applies-to`** accepts `all`, `collection:<gid>`, or `product:<gid>`. Anything else raises. To target a list of products or collections, call the API directly via `shopify-plugin:shopify-admin`.
- **One discount per invocation.** Each `create.py` / `update.py` / `delete.py` call hits exactly one Shopify mutation. To delete five expired codes, loop the script five times (or use `list.py --status EXPIRED` to feed a shell loop).

## Reference

For the full `DiscountCodeBasicInput`, `DiscountAutomaticBasicInput`, `DiscountCodeBxgyInput`, `DiscountCodeFreeShippingInput` (and their automatic + update variants) schemas, the complete set of `customerGets` / `customerBuys` selectors (collections, products, all, percentage, discountAmount, discountOnQuantity), and the `combinesWith` / `customerSelection` rules, defer to the `shopify-plugin:shopify-admin` skill from the Shopify-AI-Toolkit plugin dependency.
