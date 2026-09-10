from __future__ import annotations

import argparse
from pathlib import Path

from vaultsafe_client import cli
from vaultsafe_client.commands import get
from vaultsafe_client.config import Config


class FakeClient:
    def get_secret(self, item_id: int) -> dict[str, str]:
        return {"password": "s3cret!"}


def _args(tmp_path: Path, argv: list[str]) -> argparse.Namespace:
    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice", default_vault=1).save(path)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    get.register(sub)
    args = parser.parse_args(["get", *argv])
    args.config = path
    return args


def test_run_copies_to_clipboard(tmp_path: Path, monkeypatch, capsys):
    copied: list[str] = []
    monkeypatch.setattr(cli, "login", lambda _cfg: FakeClient())
    monkeypatch.setattr(cli, "resolve_vault", lambda *a, **k: 1)
    monkeypatch.setattr(get.cli, "find_items", lambda *a, **k: [{"id": 7, "service": "github"}])
    monkeypatch.setattr(get.clipboard, "copy_to_clipboard", lambda t: copied.append(t) or "wl-copy")
    assert get.run(_args(tmp_path, ["github"])) == 0
    assert copied == ["s3cret!"]
    assert "copied" in capsys.readouterr().out


def test_run_show_prints(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "login", lambda _cfg: FakeClient())
    monkeypatch.setattr(cli, "resolve_vault", lambda *a, **k: 1)
    monkeypatch.setattr(get.cli, "find_items", lambda *a, **k: [{"id": 7, "service": "github"}])
    assert get.run(_args(tmp_path, ["github", "--show"])) == 0
    assert "s3cret!" in capsys.readouterr().out


def test_run_no_match_errors(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "login", lambda _cfg: FakeClient())
    monkeypatch.setattr(cli, "resolve_vault", lambda *a, **k: 1)
    monkeypatch.setattr(get.cli, "find_items", lambda *a, **k: [])
    assert get.run(_args(tmp_path, ["nope"])) == 1
    assert "no item matching" in capsys.readouterr().err


def test_run_multi_match_errors(tmp_path: Path, monkeypatch, capsys):
    items = [{"id": 1, "service": "github"}, {"id": 2, "service": "gitlab"}]
    monkeypatch.setattr(cli, "login", lambda _cfg: FakeClient())
    monkeypatch.setattr(cli, "resolve_vault", lambda *a, **k: 1)
    monkeypatch.setattr(get.cli, "find_items", lambda *a, **k: items)
    assert get.run(_args(tmp_path, ["git"])) == 1
    assert "multiple matches" in capsys.readouterr().err
