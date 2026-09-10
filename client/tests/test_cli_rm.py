from __future__ import annotations

import argparse
from pathlib import Path

from vaultsafe_client import cli
from vaultsafe_client.commands import rm
from vaultsafe_client.config import Config


class FakeClient:
    def __init__(self) -> None:
        self.deleted: list[int] = []

    def delete_item(self, item_id: int) -> None:
        self.deleted.append(item_id)


def test_run_deletes_with_yes(tmp_path: Path, monkeypatch, capsys):
    client = FakeClient()
    monkeypatch.setattr(cli, "login", lambda _cfg: client)
    monkeypatch.setattr(cli, "resolve_vault", lambda *a, **k: 1)
    monkeypatch.setattr(rm.cli, "find_items", lambda *a, **k: [{"id": 7, "service": "github"}])

    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice", default_vault=1).save(path)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    rm.register(sub)
    args = parser.parse_args(["rm", "github", "-y"])
    args.config = path
    assert rm.run(args) == 0
    assert client.deleted == [7]
    assert "deleted" in capsys.readouterr().out


def test_run_confirms(tmp_path: Path, monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(cli, "login", lambda _cfg: client)
    monkeypatch.setattr(cli, "resolve_vault", lambda *a, **k: 1)
    monkeypatch.setattr(rm.cli, "find_items", lambda *a, **k: [{"id": 7, "service": "github"}])
    monkeypatch.setattr("builtins.input", lambda _p: "y")

    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice", default_vault=1).save(path)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    rm.register(sub)
    args = parser.parse_args(["rm", "github"])
    args.config = path
    assert rm.run(args) == 0
    assert client.deleted == [7]


def test_run_no_match_errors(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "login", lambda _cfg: FakeClient())
    monkeypatch.setattr(cli, "resolve_vault", lambda *a, **k: 1)
    monkeypatch.setattr(rm.cli, "find_items", lambda *a, **k: [])

    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice", default_vault=1).save(path)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    rm.register(sub)
    args = parser.parse_args(["rm", "none"])
    args.config = path
    assert rm.run(args) == 1
    assert "no item matching" in capsys.readouterr().err
