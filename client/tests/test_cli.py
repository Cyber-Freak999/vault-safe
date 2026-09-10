from __future__ import annotations

from pathlib import Path

import pytest

from vaultsafe_client import cli
from vaultsafe_client.config import Config, ConfigError


class FakeClient:
    def __init__(self, vaults: list[dict]) -> None:
        self._vaults = vaults

    def list_vaults(self) -> list[dict]:
        return self._vaults

    def list_items(self, vault_id: int, *, service=None, tag=None) -> list[dict]:
        return [
            {"id": 1, "service": "github", "tags": ["work"]},
            {"id": 2, "service": "GitLab", "tags": []},
            {"id": 3, "service": "bank", "tags": ["personal"]},
        ]


@pytest.fixture
def config(tmp_path: Path) -> tuple[Path, Config]:
    path = tmp_path / "config.toml"
    return path, Config(base_url="http://x", username="alice")


def test_find_items_prefers_exact_casefold(config):
    _, cfg = config
    matches = cli.find_items(FakeClient([]), 1, "gitlab")
    assert [m["service"] for m in matches] == ["GitLab"]


def test_find_items_falls_back_to_substring(config):
    _, cfg = config
    matches = cli.find_items(FakeClient([]), 1, "git")
    assert {m["service"] for m in matches} == {"github", "GitLab"}


def test_resolve_vault_uses_explicit(config):
    path, cfg = config
    client = FakeClient([{"id": 7, "name": "personal"}])
    assert cli.resolve_vault(cfg, client, path, explicit=7) == 7


def test_resolve_vault_uses_default(config):
    path, cfg = config
    cfg = Config(base_url=cfg.base_url, username=cfg.username, default_vault=3)
    client = FakeClient([{"id": 3, "name": "work"}])
    assert cli.resolve_vault(cfg, client, path) == 3


def test_resolve_vault_prompts_and_persists(config, monkeypatch, capsys):
    path, cfg = config
    client = FakeClient([{"id": 5, "name": "personal"}])
    monkeypatch.setattr("builtins.input", lambda _prompt: "5")
    assert cli.resolve_vault(cfg, client, path) == 5
    assert "personal" in capsys.readouterr().out
    assert Config.load(path).default_vault == 5


def test_resolve_vault_rejects_bad_id(config, monkeypatch):
    path, cfg = config
    client = FakeClient([{"id": 5, "name": "personal"}])
    monkeypatch.setattr("builtins.input", lambda _prompt: "nope")
    with pytest.raises(ConfigError):
        cli.resolve_vault(cfg, client, path)
