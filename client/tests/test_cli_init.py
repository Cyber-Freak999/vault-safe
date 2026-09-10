from __future__ import annotations

import argparse
from pathlib import Path

from vaultsafe_client.commands import init
from vaultsafe_client.commands.init import register, run


def test_run_pings_health_and_writes_config(tmp_path: Path, monkeypatch, capsys):
    called: list[str] = []

    class FakeConnection:
        def __init__(self, base_url: str) -> None:
            self.base_url = base_url

        def health(self) -> dict:
            called.append(self.base_url)
            return {"status": "ok"}

    monkeypatch.setattr(init, "VaultClient", FakeConnection)
    monkeypatch.setattr(init, "default_config_path", lambda: tmp_path / "config.toml")

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register(sub)
    args = parser.parse_args(["init", "--url", "http://host:1234/", "--username", "alice"])
    assert run(args) == 0
    assert called == ["http://host:1234/"]
    text = (tmp_path / "config.toml").read_text(encoding="utf-8")
    assert "alice" in text and "http://host:1234" in text
    assert "config written" in capsys.readouterr().out


def test_register_sets_handler():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register(sub)
    ns = parser.parse_args(["init", "--username", "alice"])
    assert ns.handler is run
