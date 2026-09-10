from __future__ import annotations

import argparse
from pathlib import Path

from vaultsafe_client import cli
from vaultsafe_client.commands import add
from vaultsafe_client.config import Config


def _basic_args(tmp_path: Path, service: str = "github", **kwargs: object) -> argparse.Namespace:
    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice", default_vault=1).save(path)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add.register(sub)
    argv = ["add", service]
    if kwargs.get("ask"):
        argv.append("--ask")
    if kwargs.get("tags"):
        argv += ["-t", "work", "-t", "dev"]
    args = parser.parse_args(argv)
    args.config = path
    return args


def test_run_generates_and_creates(tmp_path: Path, monkeypatch, capsys):
    created: dict[str, object] = {}

    class FakeClient:
        def create_item(self, vault_id, service, secret_fields, tags) -> dict:
            created.update(vault=vault_id, service=service, secret=secret_fields, tags=tags)
            return {"id": 1}

    monkeypatch.setattr(cli, "login", lambda _cfg: FakeClient())
    monkeypatch.setattr(cli, "resolve_vault", lambda *a, **k: 1)
    monkeypatch.setattr(add.generator, "generate_password", lambda: "GenP@ss1")
    monkeypatch.setattr(add.clipboard, "copy_to_clipboard", lambda _t: "wl-copy")

    assert add.run(_basic_args(tmp_path)) == 0
    assert created == {
        "vault": 1,
        "service": "github",
        "secret": {"password": "GenP@ss1"},
        "tags": [],
    }
    assert "stored github" in capsys.readouterr().out


def test_run_ask_prompts_and_creates(tmp_path: Path, monkeypatch, capsys):
    created: dict[str, object] = {}

    class FakeClient:
        def create_item(self, vault_id, service, secret_fields, tags) -> dict:
            created.update(secret=secret_fields)
            return {"id": 2}

    monkeypatch.setattr(cli, "login", lambda _cfg: FakeClient())
    monkeypatch.setattr(cli, "resolve_vault", lambda *a, **k: 1)
    monkeypatch.setattr(add.getpass, "getpass", lambda _p: "s3cret!")
    args = _basic_args(tmp_path, ask=True)
    assert add.run(args) == 0
    assert created["secret"] == {"password": "s3cret!"}
