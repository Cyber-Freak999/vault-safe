from __future__ import annotations

from pathlib import Path

import pytest

from vaultsafe_client.config import Config, ConfigError, default_config_path


def test_default_config_path_uses_xdg(monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/xdg")
    assert default_config_path() == Path("/tmp/xdg/vaultsafe/config.toml")


def test_default_config_path_falls_back_to_home(monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert default_config_path() == Path.home() / ".config" / "vaultsafe" / "config.toml"


def test_save_and_load_round_trip(tmp_path: Path):
    path = tmp_path / "config.toml"
    config = Config(base_url="http://127.0.0.1:8000", username="alice", default_vault=2)
    config.save(path)
    assert Config.load(path) == config


def test_load_strips_trailing_slash(tmp_path: Path):
    path = tmp_path / "config.toml"
    Config(base_url="http://127.0.0.1:8000/", username="alice").save(path)
    assert Config.load(path).base_url == "http://127.0.0.1:8000"


def test_load_missing_file_raises(tmp_path: Path):
    with pytest.raises(ConfigError, match="schema"):
        Config.load(tmp_path / "nope.toml")


def test_load_malformed_toml_raises(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text("not toml {{{", encoding="utf-8")
    with pytest.raises(ConfigError):
        Config.load(path)


def test_load_missing_username_raises(tmp_path: Path):
    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice").save(path)
    path.write_text('base_url = "http://x"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="username"):
        Config.load(path)
