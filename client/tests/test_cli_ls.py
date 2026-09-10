from __future__ import annotations

import argparse
from pathlib import Path

from vaultsafe_client import cli
from vaultsafe_client.commands import ls
from vaultsafe_client.config import Config


def test_run_lists_items(tmp_path: Path, monkeypatch, capsys):
    class FakeClient:
        def list_items(self, vault_id: int, *, service=None, tag=None) -> list[dict]:
            return [
                {"id": 1, "service": "github", "tags": ["work"]},
                {"id": 2, "service": "bank", "tags": []},
            ]

    monkeypatch.setattr(cli, "login", lambda _cfg: FakeClient())
    monkeypatch.setattr(cli, "resolve_vault", lambda *a, **k: 1)

    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice", default_vault=1).save(path)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    ls.register(sub)
    args = parser.parse_args(["ls", "git"])
    args.config = path
    assert ls.run(args) == 0
    out = capsys.readouterr().out
    assert "github" in out and "work" in out
