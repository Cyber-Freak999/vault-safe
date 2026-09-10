# client/tests/test_cli_export.py
from __future__ import annotations

import argparse
from pathlib import Path

from vaultsafe_client import cli
from vaultsafe_client.commands import export_cmd
from vaultsafe_client.config import Config
from vaultsafe_client.export import Bundle


def test_run_writes_backup(tmp_path: Path, monkeypatch, capsys):
    class FakeClient:
        def current_kek(self) -> bytes:
            return bytes(range(32))

    monkeypatch.setattr(cli, "login", lambda _cfg: FakeClient())
    monkeypatch.setattr(cli, "resolve_vault", lambda *a, **k: 1)
    monkeypatch.setattr(export_cmd.export, "collect_bundle", lambda *a: Bundle("personal", []))
    monkeypatch.setattr(export_cmd.export, "export_bundle", lambda b, k: b"DATA")

    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice", default_vault=1).save(path)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    export_cmd.register(sub)
    args = parser.parse_args(["export", str(tmp_path / "backup.json")])
    args.config = path
    assert export_cmd.run(args) == 0
    assert (tmp_path / "backup.json").read_bytes() == b"DATA"
    assert "backup written" in capsys.readouterr().out


def test_run_default_path(tmp_path: Path, monkeypatch, capsys):
    class FakeClient:
        def current_kek(self) -> bytes:
            return bytes(range(32))

    monkeypatch.setattr(cli, "login", lambda _cfg: FakeClient())
    monkeypatch.setattr(cli, "resolve_vault", lambda *a, **k: 1)
    monkeypatch.setattr(export_cmd.export, "collect_bundle", lambda *a: Bundle("personal", []))
    monkeypatch.setattr(export_cmd.export, "export_bundle", lambda b, k: b"DATA")

    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice", default_vault=1).save(path)
    monkeypatch.chdir(tmp_path)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    export_cmd.register(sub)
    args = parser.parse_args(["export"])
    args.config = path
    assert export_cmd.run(args) == 0
    written = [p for p in tmp_path.iterdir() if p.name.startswith("vaultsafe-backup-personal-")]
    assert written and written[0].read_bytes() == b"DATA"
