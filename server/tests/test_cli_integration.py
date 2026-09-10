# server/tests/test_cli_integration.py
import pytest
from vaultsafe_client import VaultClient
from vaultsafe_client.cli_main import main
from vaultsafe_client.config import Config
from vaultsafe_client.kdf import KdfParams

FAST = KdfParams(memory_cost=8, iterations=1, parallelism=1)
MASTER = "master-pw"


@pytest.fixture
def cli_env(live_server, tmp_path, monkeypatch):
    client = VaultClient(live_server.url)
    client.register("alice", MASTER, params=FAST)
    client.login("alice", MASTER)
    vault = client.create_vault("personal")
    config_path = tmp_path / "config.toml"
    Config(base_url=live_server.url, username="alice", default_vault=vault["id"]).save(config_path)
    monkeypatch.setattr("vaultsafe_client.cli.getpass.getpass", lambda _prompt="": MASTER)
    monkeypatch.setattr(
        "vaultsafe_client.commands.add.clipboard.copy_to_clipboard", lambda _t: "wl-copy"
    )
    return config_path


@pytest.mark.django_db
def test_cli_add_get_ls_rm(cli_env, capsys):
    assert main(["--config", str(cli_env), "add", "github", "-t", "work"]) == 0
    assert "stored github" in capsys.readouterr().out

    assert main(["--config", str(cli_env), "get", "github", "--show"]) == 0
    assert capsys.readouterr().out.strip()

    assert main(["--config", str(cli_env), "ls"]) == 0
    assert "github" in capsys.readouterr().out

    assert main(["--config", str(cli_env), "rm", "github", "-y"]) == 0
    assert main(["--config", str(cli_env), "get", "github", "--show"]) == 1


@pytest.mark.django_db
def test_cli_wrong_master_password(cli_env, monkeypatch, capsys):
    monkeypatch.setattr("vaultsafe_client.cli.getpass.getpass", lambda _prompt="": "wrong-pw")
    assert main(["--config", str(cli_env), "unlock"]) == 1
    assert "error" in capsys.readouterr().err


def test_cli_gen(capsys):
    assert main(["gen", "24"]) == 0
    assert len(capsys.readouterr().out.strip()) == 24


@pytest.mark.django_db
def test_cli_export_import_round_trip(cli_env, tmp_path, capsys):
    assert main(["--config", str(cli_env), "add", "github", "-t", "work"]) == 0
    capsys.readouterr()
    export_path = tmp_path / "backup.json"
    assert main(["--config", str(cli_env), "export", str(export_path)]) == 0
    assert export_path.exists()
    assert main(["--config", str(cli_env), "rm", "github", "-y"]) == 0
    capsys.readouterr()
    assert main(["--config", str(cli_env), "import", str(export_path)]) == 0
    capsys.readouterr()
    assert main(["--config", str(cli_env), "get", "github", "--show"]) == 0
    assert capsys.readouterr().out.strip()
