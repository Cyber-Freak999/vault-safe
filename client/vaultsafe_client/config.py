from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    pass


def default_config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "vaultsafe" / "config.toml"


@dataclass(frozen=True)
class Config:
    base_url: str
    username: str
    default_vault: int | None = None

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        vault_line = (
            f"default_vault = {self.default_vault}" if self.default_vault is not None else ""
        )
        path.write_text(
            f'base_url = "{self.base_url}"\nusername = "{self.username}"\n{vault_line}\n',
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> Config:
        if not path.exists():
            raise ConfigError(f"no config file at {path} with valid schema; run 'vs init' first")
        try:
            with path.open("rb") as fh:
                data = tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"invalid config: {exc}") from exc
        base_url = data.get("base_url")
        username = data.get("username")
        if not isinstance(base_url, str):
            raise ConfigError("config missing 'base_url'")
        if not isinstance(username, str):
            raise ConfigError("config missing 'username'")
        default_vault = data.get("default_vault")
        if default_vault is not None and not isinstance(default_vault, int):
            raise ConfigError("'default_vault' must be an integer")
        return cls(base_url=base_url.rstrip("/"), username=username, default_vault=default_vault)
