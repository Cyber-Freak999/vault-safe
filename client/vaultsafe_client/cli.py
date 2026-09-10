from __future__ import annotations

import getpass
from pathlib import Path
from typing import Any

from .client import VaultClient
from .config import Config, ConfigError, default_config_path

MASTER_PROMPT = "Master password: "


def load_config(path: Path | None = None) -> Config:
    return Config.load(path or default_config_path())


def login(config: Config) -> VaultClient:
    password = getpass.getpass(MASTER_PROMPT)
    client = VaultClient(config.base_url)
    client.login(config.username, password)
    return client


def resolve_vault(
    config: Config,
    client: VaultClient,
    path: Path | None,
    *,
    explicit: int | None = None,
) -> int:
    if explicit is not None:
        return explicit
    if config.default_vault is not None:
        return config.default_vault
    vaults = [dict(v) for v in client.list_vaults()]
    if not vaults:
        raise ConfigError("no vaults; create one via the API first")
    print("vaults:")
    for vault in vaults:
        print(f"  {vault['id']}: {vault['name']}")
    raw = input("vault id: ").strip()
    if not raw.isdigit():
        raise ConfigError("vault id must be an integer")
    chosen = int(raw)
    if not any(v["id"] == chosen for v in vaults):
        raise ConfigError(f"no vault with id {chosen}")
    Config(config.base_url, config.username, chosen).save(path or default_config_path())
    return chosen


def find_items(client: VaultClient, vault_id: int, query: str) -> list[Any]:
    items = [dict(i) for i in client.list_items(vault_id)]
    folded = query.casefold()
    exact = [i for i in items if str(i["service"]).casefold() == folded]
    if exact:
        return exact
    return [i for i in items if folded in str(i["service"]).casefold()]
