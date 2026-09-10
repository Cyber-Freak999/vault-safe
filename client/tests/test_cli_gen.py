from __future__ import annotations

import argparse

from vaultsafe_client.commands import gen


def test_run_prints_generated(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gen.generator, "generate_password", lambda n: "x" * n)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    gen.register(sub)
    args = parser.parse_args(["gen", "12"])
    args.config = tmp_path / "unused.toml"
    assert gen.run(args) == 0
    assert capsys.readouterr().out.strip() == "x" * 12


def test_default_length(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gen.generator, "generate_password", lambda n: f"len={n}")
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    gen.register(sub)
    args = parser.parse_args(["gen"])
    args.config = tmp_path / "unused.toml"
    assert gen.run(args) == 0
    assert "len=20" in capsys.readouterr().out
