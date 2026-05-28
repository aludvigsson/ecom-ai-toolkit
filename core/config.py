"""Load and validate store-config.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class Market(BaseModel):
    code: str
    name: str
    locale: str
    currency: str
    url_prefix: str = ""


class Store(BaseModel):
    name: str
    primary_domain: str
    shopify_domain: str
    storefront_type: Literal["hydrogen", "online_store_2"]
    default_locale: str


class DomainConfig(BaseModel):
    enabled: bool = False
    api_version: str | None = None


class StoreConfig(BaseModel):
    store: Store
    markets: list[Market] = Field(default_factory=list)
    domains: dict[str, DomainConfig] = Field(default_factory=dict)

    def market(self, code: str) -> Market:
        for m in self.markets:
            if m.code == code:
                return m
        raise KeyError(f"No market with code={code!r} in store-config.yaml")


def load_config(path: str | Path = "store-config.yaml") -> StoreConfig:
    """Load and validate a store-config.yaml file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"store-config not found at {p}. "
            f"Copy store-config.example.yaml to store-config.yaml and edit."
        )
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    return StoreConfig.model_validate(raw)
