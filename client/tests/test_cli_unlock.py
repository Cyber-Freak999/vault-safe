from __future__ import annotations

import argparse
from pathlib import Path

from vaultsafe_client import cli
from vaultsafe_client.commands import unlock
from vaultsafe_client.config import Config


def test_run_calls_login(tmp_path: Path, monkeypatch, capsys):
    logins: list[Config] = []

    def fake_login(config: Config):
        logins.append(config)
        return object()

    monkeypatch.setattr(cli, "login", fake_login)
    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice").save(path)

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    unlock.register(sub)
    args = parser.parse_args(["unlock"])
    args.config = path
    assert unlock.run(args) == 0
    assert logins and logins[0].username == "alice"
    assert "unlocked" in capsys.readouterr().out
