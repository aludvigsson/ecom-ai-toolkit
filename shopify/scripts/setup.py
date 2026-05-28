"""First-run interactive setup for ecom-ai-toolkit.

Walks the user through:
  1. Creating store-config.yaml from the example template.
  2. Creating .env.local from .env.example.
  3. Acquiring a Shopify Admin API access token via one of two paths:
     - Custom-app token (paste from Shopify admin UI). Token never expires;
       recommended for unattended ops.
     - Shopify CLI auth (browser OAuth). Token expires in ~24h; the script
       extracts it from the CLI's config file. Best for interactive use.
  4. Writing the token into .env.local and verifying via a whoami query.

Usage:
  uv run shopify/scripts/setup.py
  uv run shopify/scripts/setup.py --auth-mode cli --store mystore.myshopify.com --scopes read_products,read_orders
  uv run shopify/scripts/setup.py --auth-mode custom-app
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
import getpass
import json
import logging
import os
import platform
import shutil
import subprocess
import sys

from core.config import load_config
from shopify.utils.client import ShopifyClient

_DEFAULT_SCOPES = "read_products,read_orders,read_customers,read_inventory"

_WHOAMI_QUERY = """
query { shop { name primaryDomain { url } plan { displayName } } }
"""


# ---------------------------------------------------------------------------
# Config / env file helpers
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_env_local(*, project_root: Path) -> None:
    """Copy .env.example -> .env.local if missing."""
    env_local = project_root / ".env.local"
    env_example = project_root / ".env.example"
    if env_local.exists():
        return
    if not env_example.exists():
        raise FileNotFoundError(
            f".env.example not found at {env_example}. Cannot bootstrap .env.local without it."
        )
    env_local.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Created {env_local.name} from {env_example.name}.")


def _ensure_store_config_yaml(args: argparse.Namespace, *, project_root: Path) -> bool:
    """Make sure store-config.yaml exists. Returns True if it now exists, False if user aborted."""
    cfg_path = project_root / "store-config.yaml"
    example_path = project_root / "store-config.example.yaml"
    if cfg_path.exists() and cfg_path.read_text(encoding="utf-8").strip():
        return True
    if not example_path.exists():
        raise FileNotFoundError(
            f"store-config.example.yaml not found at {example_path}. "
            "Cannot bootstrap store-config.yaml without it."
        )

    if args.non_interactive:
        cfg_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(
            f"Copied {example_path.name} -> {cfg_path.name}. "
            "Edit it to fill in your store details before re-running."
        )
        return False

    print("No store-config.yaml found. Let's create one.")
    name = _prompt("Store name (e.g. 'Acme'):").strip()
    if not name:
        print("Aborted: store name is required.", file=sys.stderr)
        return False
    default_shopify = args.store or ""
    shopify_domain = (
        _prompt(
            f"Shopify domain (e.g. acme.myshopify.com){f' [{default_shopify}]' if default_shopify else ''}:"
        ).strip()
        or default_shopify
    )
    if not shopify_domain:
        print("Aborted: shopify_domain is required.", file=sys.stderr)
        return False
    primary_domain = _prompt("Primary customer-facing domain (e.g. acme.com):").strip()
    if not primary_domain:
        print("Aborted: primary_domain is required.", file=sys.stderr)
        return False
    storefront_type = (
        _prompt("Storefront type [hydrogen|online_store_2] (default: online_store_2):").strip()
        or "online_store_2"
    )
    if storefront_type not in ("hydrogen", "online_store_2"):
        print(
            f"Aborted: storefront_type must be 'hydrogen' or 'online_store_2', got {storefront_type!r}.",
            file=sys.stderr,
        )
        return False
    default_locale = _prompt("Default locale (e.g. en-US, sv-SE) [en-US]:").strip() or "en-US"

    header = (
        f"store:\n"
        f'  name: "{name}"\n'
        f"  primary_domain: {primary_domain}\n"
        f"  shopify_domain: {shopify_domain}\n"
        f"  storefront_type: {storefront_type}\n"
        f"  default_locale: {default_locale}\n"
    )
    footer = (
        "\n"
        "# Add per-market entries here once you have them, e.g.:\n"
        "# markets:\n"
        '#   - code: "us"\n'
        "#     name: United States\n"
        "#     locale: en-US\n"
        "#     currency: USD\n"
        '#     url_prefix: ""\n'
        "markets: []\n"
        "\n"
        "domains:\n"
        '  shopify:        { enabled: true,  api_version: "2025-10" }\n'
        "  klaviyo:        { enabled: false }\n"
        "  meta_ads:       { enabled: false }\n"
        "  google_ads:     { enabled: false }\n"
        "  microsoft_ads:  { enabled: false }\n"
        "  merchant_center: { enabled: false }\n"
        "  gtm:            { enabled: false }\n"
    )
    yaml_body = header + footer
    cfg_path.write_text(yaml_body, encoding="utf-8")
    print(f"Created {cfg_path.name}. Add markets later by editing the file directly.")
    return True


# ---------------------------------------------------------------------------
# Shopify CLI config helpers
# ---------------------------------------------------------------------------


def _find_cli_token_file() -> Path | None:
    """Return platform-appropriate Shopify CLI store-auth config path, or None on Windows."""
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        return home / "Library" / "Preferences" / "shopify-cli-store-nodejs" / "config.json"
    if system == "Linux":
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else home / ".config"
        return base / "shopify-cli-store-nodejs" / "config.json"
    return None


def _read_cli_token_for_store(store: str, *, config_path: Path) -> tuple[str, dict] | None:
    """Read access token + metadata for the given store from CLI config.

    Returns (token, metadata_dict) where metadata_dict has expires_at, scopes, user_email.
    Returns None if the store isn't found in CLI config (user hasn't run auth yet).
    """
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    handle = store
    if handle.endswith(".myshopify.com"):
        handle = handle[: -len(".myshopify.com")]

    # Walk top-level keys looking for one matching the pattern `<anything>::<handle>`.
    matched_entry = None
    for key, value in data.items():
        if not isinstance(key, str) or "::" not in key:
            continue
        _, _, suffix = key.partition("::")
        if suffix == handle:
            matched_entry = value
            break
    if matched_entry is None:
        return None

    # Drill into myshopify.com.sessionsByUserId.<currentUserId>
    myshop = (matched_entry or {}).get("myshopify.com") or {}
    current_user_id = myshop.get("currentUserId")
    sessions = myshop.get("sessionsByUserId") or {}
    session = sessions.get(current_user_id) if current_user_id else None
    if not session:
        # Fallback: take the first session in the dict.
        if sessions:
            session = next(iter(sessions.values()))
        else:
            return None

    token = session.get("accessToken")
    if not token:
        return None
    metadata = {
        "expires_at": session.get("expiresAt"),
        "scopes": session.get("scopes") or [],
        "user_email": session.get("userEmail") or session.get("email"),
    }
    return token, metadata


# ---------------------------------------------------------------------------
# .env.local writer
# ---------------------------------------------------------------------------


def _write_token_to_env_local(token: str, *, env_local: Path) -> None:
    """Replace the SHOPIFY_ADMIN_ACCESS_TOKEN= line in .env.local, preserving the rest."""
    if not env_local.exists():
        raise FileNotFoundError(f"{env_local} does not exist; cannot write token.")
    existing = env_local.read_text(encoding="utf-8").splitlines(keepends=False)
    out_lines: list[str] = []
    replaced = False
    for line in existing:
        stripped = line.lstrip()
        if stripped.startswith("SHOPIFY_ADMIN_ACCESS_TOKEN="):
            out_lines.append(f"SHOPIFY_ADMIN_ACCESS_TOKEN={token}")
            replaced = True
        else:
            out_lines.append(line)
    if not replaced:
        out_lines.append(f"SHOPIFY_ADMIN_ACCESS_TOKEN={token}")
    env_local.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Whoami verification
# ---------------------------------------------------------------------------


def _verify_setup(config_path: str = "store-config.yaml") -> int:
    """Run a whoami query against the current store-config.yaml + .env.local.

    Returns 0 on success (and prints shop/domain/plan), non-zero on failure.
    Does NOT raise — caller handles the return code.
    """
    try:
        cfg = load_config(config_path)
        # Force-reload .env.local so a freshly-written token is picked up.
        import core.secrets as _secrets

        _secrets._env_loaded = False
        with ShopifyClient(config=cfg) as client:
            data = client.graphql(_WHOAMI_QUERY)
    except Exception as exc:  # noqa: BLE001 - we want to print and return non-zero
        print(f"Verification failed: {exc}", file=sys.stderr)
        return 1
    shop = data.get("shop") or {}
    print(f"Shop:    {shop.get('name')}")
    print(f"Domain:  {(shop.get('primaryDomain') or {}).get('url')}")
    print(f"Plan:    {(shop.get('plan') or {}).get('displayName')}")
    return 0


# ---------------------------------------------------------------------------
# Auth flows
# ---------------------------------------------------------------------------


def _prompt(message: str) -> str:
    """Wrapper around input() that prints the message and returns the response."""
    print(message)
    return input("> ")


def _interactive_auth_mode_choice() -> str:
    """Prompt user for 'custom-app' vs 'cli'. Returns one of those strings."""
    print()
    print("Choose authentication method:")
    print("  1) Custom-app token (recommended for unattended ops; never expires)")
    print("  2) Shopify CLI browser OAuth (expires in ~24h; best for interactive use)")
    for _ in range(3):
        choice = _prompt("Enter 1 or 2:").strip()
        if choice == "1":
            return "custom-app"
        if choice == "2":
            return "cli"
        print(f"Invalid choice: {choice!r}. Try again.")
    print("Defaulting to custom-app after 3 invalid choices.", file=sys.stderr)
    return "custom-app"


def _custom_app_token_flow(store_domain: str) -> str:
    """Print the admin URL, prompt for token paste (via getpass), validate, return."""
    handle = store_domain
    if handle.endswith(".myshopify.com"):
        handle = handle[: -len(".myshopify.com")]
    url = f"https://admin.shopify.com/store/{handle}/settings/apps/development"
    print()
    print("Open this URL in your browser to create or reuse a custom app:")
    print(f"  {url}")
    print()
    print("In Shopify admin: create app -> configure Admin API scopes -> install -> reveal token.")
    print("Token format: shpat_... (Admin API access token, NOT Storefront token).")
    print()
    for _ in range(3):
        token = getpass.getpass("Paste your Admin API access token (input hidden): ").strip()
        if token.startswith("shpat_") and len(token) >= 32:
            return token
        print(
            "Invalid token: must start with 'shpat_' and be at least 32 chars. Try again.",
            file=sys.stderr,
        )
    raise RuntimeError("Failed to acquire a valid custom-app token after 3 attempts.")


def _cli_token_flow(store_domain: str, scopes: list[str]) -> str:
    """Shell out to `shopify store auth`, then read the token from CLI config."""
    if shutil.which("shopify") is None:
        raise RuntimeError(
            "`shopify` CLI not found on PATH. Install it from "
            "https://shopify.dev/docs/api/shopify-cli or use --auth-mode custom-app instead."
        )
    config_path = _find_cli_token_file()
    if config_path is None:
        raise RuntimeError(
            "Windows CLI-token-extraction not supported yet; use --auth-mode custom-app."
        )

    scopes_str = ",".join(scopes)
    print()
    print(
        f"Running: shopify store auth --store {store_domain} --scopes {scopes_str}\n"
        "Your browser will open. Complete the OAuth flow there."
    )
    subprocess.run(
        ["shopify", "store", "auth", "--store", store_domain, "--scopes", scopes_str],
        check=True,
    )

    result = _read_cli_token_for_store(store_domain, config_path=config_path)
    if result is None:
        raise RuntimeError(
            f"Couldn't find {store_domain!r} in shopify CLI config after auth. "
            f"Looked in {config_path}. Try running this script again."
        )
    token, metadata = result
    expires_at = metadata.get("expires_at")
    if expires_at:
        print(f"Token expires at {expires_at}.")
    print(
        "Note: CLI-issued tokens expire in ~24h. For unattended use, switch to "
        "--auth-mode custom-app for a non-expiring custom-app token."
    )
    return token


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Interactive first-run setup for ecom-ai-toolkit.",
    )
    parser.add_argument(
        "--store",
        help="Shopify domain (e.g. acme.myshopify.com). Used to pre-fill prompts and CLI auth.",
    )
    parser.add_argument(
        "--scopes",
        default=_DEFAULT_SCOPES,
        help=f"Comma-separated scopes for CLI auth (default: {_DEFAULT_SCOPES})",
    )
    parser.add_argument(
        "--auth-mode",
        choices=("custom-app", "cli", "prompt"),
        default="prompt",
        help="Auth path. 'prompt' (default) asks interactively.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip interactive prompts; useful for CI smoke tests of file creation.",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    if args.verbose:
        logging.getLogger("ecom").setLevel(logging.DEBUG)

    project_root = _project_root()

    # 1. store-config.yaml
    has_cfg = _ensure_store_config_yaml(args, project_root=project_root)
    if not has_cfg:
        print(
            "Edit store-config.yaml and re-run this script to continue with auth setup.",
            file=sys.stderr,
        )
        return 0

    # 2. .env.local
    _ensure_env_local(project_root=project_root)

    # 3. Check if already configured.
    cfg_path = project_root / "store-config.yaml"
    try:
        cfg = load_config(cfg_path)
        store_domain = cfg.store.shopify_domain
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to load store-config.yaml: {exc}", file=sys.stderr)
        return 1

    # If token already set, try whoami and short-circuit.
    import core.secrets as _secrets

    _secrets._env_loaded = False
    _secrets.load_env_local(project_root / ".env.local")
    existing_token = os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN")
    if existing_token:
        try:
            with ShopifyClient(config=cfg) as client:
                client.graphql(_WHOAMI_QUERY)
            print("Already configured.")
            return _verify_setup(str(cfg_path))
        except Exception:  # noqa: BLE001
            print(
                "Existing SHOPIFY_ADMIN_ACCESS_TOKEN failed whoami check; re-acquiring.",
                file=sys.stderr,
            )

    if args.non_interactive:
        print(
            "Non-interactive mode: stopping before auth. "
            "Edit .env.local to add SHOPIFY_ADMIN_ACCESS_TOKEN and re-run.",
            file=sys.stderr,
        )
        return 0

    # 4. Pick auth mode.
    mode = args.auth_mode
    if mode == "prompt":
        mode = _interactive_auth_mode_choice()

    scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]
    try:
        if mode == "custom-app":
            token = _custom_app_token_flow(store_domain)
        elif mode == "cli":
            token = _cli_token_flow(store_domain, scopes)
        else:
            print(f"Unknown auth mode: {mode!r}", file=sys.stderr)
            return 2
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Auth failed: {exc}", file=sys.stderr)
        return 1

    # 5. Write to .env.local
    env_local = project_root / ".env.local"
    _write_token_to_env_local(token, env_local=env_local)
    print(f"Wrote SHOPIFY_ADMIN_ACCESS_TOKEN to {env_local.name}.")

    # 6. Verify
    return _verify_setup(str(cfg_path))


if __name__ == "__main__":
    sys.exit(main())
