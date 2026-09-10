from __future__ import annotations

import argparse
from pathlib import Path

from vaultsafe_client import cli
from vaultsafe_client.commands import import_cmd
from vaultsafe_client.config import Config
from vaultsafe_client.export import Bundle, BundleItem


class FakeClient:
    def __init__(self) -> None:
        self.created: list[tuple[int, str, dict, list]] = []
        self.updated: list[tuple[int, str, dict, list]] = []

    def current_kek(self) -> bytes:
        return bytes(range(32))

    def list_vaults(self) -> list[dict]:
        return []

    def create_vault(self, name: str) -> dict:
        return {"id": 5, "name": name}

    def list_items(self, vault_id: int, *, service=None, tag=None) -> list[dict]:
        return []

    def create_item(self, vault_id, service, secret_fields, tags) -> dict:
        self.created.append((vault_id, service, secret_fields, tags))
        return {"id": 1}

    def update_item(self, item_id, *, service=None, secret_fields=None, tags=None) -> dict:
        self.updated.append((item_id, service, secret_fields, tags))
        return {"id": 9}


def test_run_creates_items(tmp_path: Path, monkeypatch, capsys):
    client = FakeClient()
    monkeypatch.setattr(cli, "login", lambda _cfg: client)
    monkeypatch.setattr(
        import_cmd.export,
        "import_bundle",
        lambda *a: Bundle("personal", [BundleItem("github", ["work"], {"password": "x"})]),
    )

    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice").save(path)
    backup = tmp_path / "backup.json"
    backup.write_bytes(b"{}")
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    import_cmd.register(sub)
    args = parser.parse_args(["import", str(backup)])
    args.config = path
    assert import_cmd.run(args) == 0
    assert client.created == [(5, "github", {"password": "x"}, ["work"])]
    assert "created" in capsys.readouterr().out


def test_run_skips_without_overwrite(tmp_path: Path, monkeypatch, capsys):
    class SkipClient(FakeClient):
        def list_items(self, vault_id: int, *, service=None, tag=None) -> list[dict]:
            return [{"id": 9, "service": "github", "tags": ["work"]}]

    client = SkipClient()
    monkeypatch.setattr(cli, "login", lambda _cfg: client)
    monkeypatch.setattr(
        import_cmd.export,
        "import_bundle",
        lambda *a: Bundle("personal", [BundleItem("github", ["work"], {"password": "y"})]),
    )

    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice").save(path)
    backup = tmp_path / "backup.json"
    backup.write_bytes(b"{}")
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    import_cmd.register(sub)
    args = parser.parse_args(["import", str(backup)])
    args.config = path
    assert import_cmd.run(args) == 0
    assert client.created == [] and client.updated == []
    assert "skipped" in capsys.readouterr().out


def test_run_overwrites(tmp_path: Path, monkeypatch, capsys):
    class OverwriteClient(FakeClient):
        def list_items(self, vault_id: int, *, service=None, tag=None) -> list[dict]:
            return [{"id": 9, "service": "github", "tags": ["work"]}]

    client = OverwriteClient()
    monkeypatch.setattr(cli, "login", lambda _cfg: client)
    monkeypatch.setattr(
        import_cmd.export,
        "import_bundle",
        lambda *a: Bundle("personal", [BundleItem("github", ["work"], {"password": "z"})]),
    )

    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice").save(path)
    backup = tmp_path / "backup.json"
    backup.write_bytes(b"{}")
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    import_cmd.register(sub)
    args = parser.parse_args(["import", str(backup), "--overwrite"])
    args.config = path
    assert import_cmd.run(args) == 0
    assert client.updated == [(9, "github", {"password": "z"}, ["work"])]
    assert "updated" in capsys.readouterr().out
