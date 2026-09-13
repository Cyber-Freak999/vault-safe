# VaultSafe CLI (`vs`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a daily-use `vs` CLI for VaultSafe in two milestones — v1.1.0 (CLI core: init/unlock/add/get/ls/rm/gen) and v1.2.0 (encrypted export/import backup).

**Architecture:** New modules inside the existing `client/vaultsafe_client/` package (`config`, `generator`, `clipboard`, `cli` shared lib, `cli_main` entry point, `commands/` package of one-module-per-command, `export` bundle lib). A `vs` console script is registered in `client/pyproject.toml`. The server is untouched by functionality; CLI integration tests live under `server/tests/` (the only place with `live_server`, the `_fast_throttle` fixture, and the `vaultsafe-client` workspace dependency). The API and crypto are reused as-is — no server changes.

**Tech Stack:** Python 3.13 stdlib additions only on the client (`argparse`, `getpass`, `tomllib`, `subprocess`, `shutil`, `secrets`, `json`), over existing `httpx`/`argon2-cffi`/`cryptography`. Server untouched.

## Global Constraints

- Conventional Commits; commit per task step with a single `feat:`/`test:`/`docs:` message.
- Commands run from each member dir: `uv run --project client ...` / `uv run --project server ...`; root repo gate is `pre-commit run --all-files`.
- Gates must stay green at every commit: alongside `ruff format --check .`, `ruff check .`, `mypy vaultsafe_client` (client) / `mypy accounts vaults common vaultsafe` (server), `pytest -q` both members.
- Client quality gates read `client/pyproject.toml`: ruff line-length 100, mypy strict, tests under `client/tests/`.
- Integration tests requiring a live server and `django_db` live in `server/tests/test_cli_integration.py` and reuse the autouse `_fast_throttle` fixture (login: 1000/min) plus `live_server`.
- CLI exit codes: `0` success, `1` operational error (message to stderr), `130` on Ctrl-C. `main(argv: list[str] | None = None) -> int`; script wrapper is `raise SystemExit(main())`.
- CLI config file: `~/.config/vaultsafe/config.toml` (or `$XDG_CONFIG_HOME/vaultsafe/config.toml`), with `base_url`, `username`, `default_vault` (optional).
- Auth/session: prompt for master password per command via `getpass`; derive KEK in-memory; no tokens or KEK persisted. Password never printed for `get` except with `--show` or when no clipboard tool exists.
- No code comments unless required for clarity; no new client dependencies; `list_items` item dicts have `id`, `vault`, `service`, `tags`, `envelope` keys (server `VaultItemSerializer`).
- Client package version bumps and tags: v1.1.0 at end of Milestone A, v1.2.0 at end of Milestone B. Both `client/pyproject.toml:3` and `server/pyproject.toml:3` bump together (repo-level parity convention), plus `uv lock` to refresh `uv.lock`, and a `CHANGELOG.md` section.

## File Structure

### Milestone A — v1.1.0 CLI core

| File | Responsibility |
|---|---|
| `client/vaultsafe_client/config.py` | Config dataclass, `~/.config/vaultsafe` discovery, TOML load/save |
| `client/vaultsafe_client/generator.py` | `generate_password()` — crypto-random with all char classes |
| `client/vaultsafe_client/clipboard.py` | `copy_to_clipboard()` — wl-copy/xclip/pbcopy via stdin, fallback |
| `client/vaultsafe_client/cli.py` | Shared helpers for commands (load config, login, vault resolve, item search) |
| `client/vaultsafe_client/cli_main.py` | argparse parser + `main()` dispatcher + `vs` entry point |
| `client/vaultsafe_client/commands/__init__.py` | Registry: `register_all(sub)` imports every command module |
| `client/vaultsafe_client/commands/init.py` | `vs init` — write config, ping `/api/health` |
| `client/vaultsafe_client/commands/unlock.py` | `vs unlock` — verify master password |
| `client/vaultsafe_client/commands/add.py` | `vs add <service> [--ask] [-t TAG]` |
| `client/vaultsafe_client/commands/get.py` | `vs get <service> [--show]` |
| `client/vaultsafe_client/commands/ls.py` | `vs ls [query] [--tag T]` |
| `client/vaultsafe_client/commands/rm.py` | `vs rm <service> [-y]` |
| `client/vaultsafe_client/commands/gen.py` | `vs gen [length]` |
| `client/vaultsafe_client/client.py` | Add public `health()` and `current_kek()` to `VaultClient` |
| `client/tests/test_config.py` | Config unit tests |
| `client/tests/test_generator.py` | Generator unit tests |
| `client/tests/test_clipboard.py` | Clipboard unit tests (mocked) |
| `server/tests/test_cli_integration.py` | Live-server end-to-end CLI tests |
| `client/pyproject.toml`, `server/pyproject.toml`, `uv.lock`, `CHANGELOG.md` | Version bumps → 1.1.0, `[project.scripts]`, changelog entry; tag `v1.1.0` |

### Milestone B — v1.2.0 export/import backup

| File | Responsibility |
|---|---|
| `client/vaultsafe_client/export.py` | Bundle builder + wrap/unwrap backup envelope |
| `client/vaultsafe_client/commands/export_cmd.py` | `vs export [path]` |
| `client/vaultsafe_client/commands/import_cmd.py` | `vs import <path>` |
| `client/tests/test_export.py` | Export lib unit tests |
| `server/tests/test_cli_integration.py` | e2e export→import test (extend) |
| `client/pyproject.toml`, `server/pyproject.toml`, `uv.lock`, `CHANGELOG.md`, `README.md` | Version → 1.2.0, changelog, README CLI section; tag `v1.2.0` |

## Task Parallelization Map

- **Wave 1 (3 parallel):** A1 config, A2 generator, A3 clipboard — disjoint modules, each self-contained with unit tests.
- **Wave 2 (1):** A4 shared `cli.py` + `client.py` `health()`/`current_kek()` + `cli_main.py` skeleton + `commands/__init__.py` stub. Depends on A1–A3.
- **Wave 3 (7 parallel):** A5 init, A6 unlock, A7 add, A8 get, A9 ls, A10 rm, A11 gen — each writes exactly one `commands/<name>.py` plus its own unit test. No two touch the same file.
- **Wave 4 (1):** A12 — wire `commands/__init__.py` import list, integration test file, version bump 1.1.0, tag, changelog.
- **Wave 5 (1):** B1 export lib + `current_kek()` split none needed (already in A4). Depends on A-waves.
- **Wave 6 (2 parallel):** B2 export command, B3 import command — disjoint files, both depend on B1 + A4 helpers.
- **Wave 7 (1):** B4 — export/import integration tests, version 1.2.0, changelog, README, tag.

Constraint for parallel waves: operate on a clean git state; commit your own file(s) only; never force-push; run gates that can run without the not-yet-merged sibling commands (skip wiring the registry until Wave 4 / Wave 7).

---

## Milestone A — v1.1.0 CLI core

### Task A1: Config module

**Files:**
- Create: `client/vaultsafe_client/config.py`
- Create: `client/tests/test_config.py`

**Interfaces:**
- Consumes: stdlib only (`tomllib`, `os`, `dataclasses`, `pathlib`).
- Produces:
  - `ConfigError(ValueError)`
  - `default_config_path() -> Path`
  - `Config` frozen dataclass with `base_url: str`, `username: str`, `default_vault: int | None`; methods `save(path: Path) -> None`, classmethod `load(cls, path: Path) -> Config`.

- [ ] **Step 1: Write the failing unit test**

```python
# client/tests/test_config.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: vaultsafe_client.config`

- [ ] **Step 3: Write minimal implementation**

```python
# client/vaultsafe_client/config.py
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    pass


def default_config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "vaultsafe" / "config.toml"


@dataclass(frozen=True)
class Config:
    base_url: str
    username: str
    default_vault: int | None = None

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        vault_line = f"default_vault = {self.default_vault}" if self.default_vault is not None else ""
        path.write_text(
            f'base_url = "{self.base_url}"\nusername = "{self.username}"\n{vault_line}\n',
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> Config:
        if not path.exists():
            raise ConfigError(f"no config file at {path}; run 'vs init' first")
        try:
            with path.open("rb") as fh:
                data = tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"invalid config: {exc}") from exc
        base_url = data.get("base_url")
        username = data.get("username")
        if not isinstance(base_url, str):
            raise ConfigError("config missing 'base_url'")
        if not isinstance(username, str):
            raise ConfigError("config missing 'username'")
        default_vault = data.get("default_vault")
        if default_vault is not None and not isinstance(default_vault, int):
            raise ConfigError("'default_vault' must be an integer")
        return cls(base_url=base_url.rstrip("/"), username=username, default_vault=default_vault)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_config.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Gates + commit**

Run: `uv run --project client ruff format . && uv run --project client ruff check . && uv run --project client mypy vaultsafe_client && uv run --project client pytest -q`
Expected: format clean, checks pass, mypy clean, all tests pass.

```bash
git add client/vaultsafe_client/config.py client/tests/test_config.py
git commit -m "feat: add CLI config module"
```

### Task A2: Password generator

**Files:**
- Create: `client/vaultsafe_client/generator.py`
- Create: `client/tests/test_generator.py`

**Interfaces:**
- Consumes: stdlib `secrets`.
- Produces: `generate_password(length: int = 20) -> str` — crypto-random, at least one lowercase, uppercase, digit, and symbol; raises `ValueError` when `length` outside 8..128.

- [ ] **Step 1: Write the failing unit test**

```python
# client/tests/test_generator.py
from __future__ import annotations

import string

import pytest

from vaultsafe_client.generator import generate_password


def test_default_length_is_20():
    assert len(generate_password()) == 20


def test_custom_length():
    assert len(generate_password(12)) == 12


@pytest.mark.parametrize("length", [7, 129, 0, -1])
def test_out_of_range_rejected(length: int):
    with pytest.raises(ValueError):
        generate_password(length)


def test_contains_each_character_class():
    pw = generate_password(24)
    assert any(c in string.ascii_lowercase for c in pw)
    assert any(c in string.ascii_uppercase for c in pw)
    assert any(c in string.digits for c in pw)
    assert any(c in string.punctuation for c in pw)


def test_generated_values_differ():
    assert len({generate_password() for _ in range(100)}) > 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_generator.py -v`
Expected: FAIL with `ModuleNotFoundError: vaultsafe_client.generator`

- [ ] **Step 3: Write minimal implementation**

```python
# client/vaultsafe_client/generator.py
from __future__ import annotations

import secrets
import string

MIN_LENGTH = 8
MAX_LENGTH = 128
_GROUPS = (string.ascii_lowercase, string.ascii_uppercase, string.digits, string.punctuation)
_ALPHABET = string.ascii_letters + string.digits + string.punctuation


def generate_password(length: int = 20) -> str:
    if not MIN_LENGTH <= length <= MAX_LENGTH:
        raise ValueError(f"length must be between {MIN_LENGTH} and {MAX_LENGTH}")
    chars = [secrets.choice(group) for group in _GROUPS]
    chars += [secrets.choice(_ALPHABET) for _ in range(length - len(chars))]
    return "".join(_shuffle(chars))


def _shuffle(chars: list[str]) -> list[str]:
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return chars
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_generator.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Gates + commit**

Run: `uv run --project client ruff format . && uv run --project client ruff check . && uv run --project client mypy vaultsafe_client && uv run --project client pytest -q`
Expected: all clean/pass.

```bash
git add client/vaultsafe_client/generator.py client/tests/test_generator.py
git commit -m "feat: add crypto-random password generator"
```

### Task A3: Clipboard helper

**Files:**
- Create: `client/vaultsafe_client/clipboard.py`
- Create: `client/tests/test_clipboard.py`

**Interfaces:**
- Consumes: stdlib `shutil`, `subprocess`.
- Produces: `copy_to_clipboard(text: str) -> str | None` — pipes `text` (utf-8) into the first available of `wl-copy`, `xclip`, `pbcopy`; returns the tool name used, or `None` if none is installed.

- [ ] **Step 1: Write the failing unit test**

```python
# client/tests/test_clipboard.py
from __future__ import annotations

import subprocess

import vaultsafe_client.clipboard as clipboard


def test_uses_first_available_tool(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> None:
        calls.append(list(cmd))
        return None

    monkeypatch.setattr(clipboard.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(clipboard.subprocess, "run", fake_run)
    assert clipboard.copy_to_clipboard("s3cret") == "wl-copy"
    assert calls == [["wl-copy"]]


def test_falls_to_second_tool(monkeypatch):
    which_calls: list[str] = []

    def fake_which(name: str):
        which_calls.append(name)
        return None if name == "wl-copy" else f"/usr/bin/{name}"

    monkeypatch.setattr(clipboard.shutil, "which", fake_which)
    monkeypatch.setattr(clipboard.subprocess, "run", lambda cmd, **kwargs: None)
    assert clipboard.copy_to_clipboard("x") == "xclip"
    assert which_calls == ["wl-copy", "xclip"]


def test_returns_none_when_no_tool(monkeypatch):
    monkeypatch.setattr(clipboard.shutil, "which", lambda name: None)
    assert clipboard.copy_to_clipboard("x") is None


def test_feeds_text_via_stdin(monkeypatch):
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> None:
        captured["input"] = kwargs.get("input")
        return None

    monkeypatch.setattr(clipboard.shutil, "which", lambda name: "/usr/bin/pbcopy")
    monkeypatch.setattr(clipboard.subprocess, "run", fake_run)
    clipboard.copy_to_clipboard("s3cret")
    assert captured["input"] == b"s3cret"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_clipboard.py -v`
Expected: FAIL with `ModuleNotFoundError: vaultsafe_client.clipboard`

- [ ] **Step 3: Write minimal implementation**

```python
# client/vaultsafe_client/clipboard.py
from __future__ import annotations

import shutil
import subprocess

_TOOLS = ("wl-copy", "xclip", "pbcopy")


def copy_to_clipboard(text: str) -> str | None:
    for tool in _TOOLS:
        if shutil.which(tool) is None:
            continue
        subprocess.run([tool], input=text.encode("utf-8"), check=True)
        return tool
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_clipboard.py -v`
Expected: PASS

- [ ] **Step 5: Gates + commit**

Run: `uv run --project client ruff format . && uv run --project client ruff check . && uv run --project client mypy vaultsafe_client && uv run --project client pytest -q`
Expected: all clean/pass.

```bash
git add client/vaultsafe_client/clipboard.py client/tests/test_clipboard.py
git commit -m "feat: add clipboard copy helper"
```

### Task A4: Shared CLI core, entry point, and client helpers

**Files:**
- Create: `client/vaultsafe_client/cli.py`
- Create: `client/vaultsafe_client/cli_main.py`
- Create: `client/vaultsafe_client/commands/__init__.py` (registry shell — empty for now; populated in A12)
- Modify: `client/vaultsafe_client/client.py` (add `health()` after the `me()` method and `current_kek()` in the internals section)
- Modify: `client/pyproject.toml` (add `[project.scripts]`)
- Create: `client/tests/test_cli.py`

**Interfaces:**
- Consumes (from A1–A3): `Config`, `ConfigError`, `default_config_path()`; `VaultClient`.
- Produces:
  - `cli.load_config(path: Path | None = None) -> Config`
  - `cli.login(config: Config) -> VaultClient` (getpass prompt, returns unlocked client with `_kek` set)
  - `cli.resolve_vault(config, client, path, *, explicit=None) -> int`
  - `cli.find_items(client, vault_id, query) -> list[Any]` (exact casefold-first, then substring)
  - `VaultClient.health() -> dict[str, Any]` (GET `/api/health`, public)
  - `VaultClient.current_kek() -> bytes` (raises `VaultApiError("not_unlocked", ...)` when not logged in)
  - `cli_main.main(argv: list[str] | None = None) -> int`, `cli_main.HELP` entry; `[project.scripts] vs = "vaultsafe_client.cli_main:main"`
  - Every command module exposes `register(subparsers: Any) -> None` (adds a subparser and sets `handler`) and `run(args: argparse.Namespace) -> int`. Command modules import shared helpers as `from .. import cli` and call `cli.load_config(args.config)` / `cli.login(config)` / `cli.resolve_vault(config, client, args.config, explicit=args.vault)` so tests can monkeypatch `vaultsafe_client.cli.*`.

- [ ] **Step 1: Write the failing unit tests**

```python
# client/tests/test_cli.py
from __future__ import annotations

from pathlib import Path

import pytest

from vaultsafe_client import cli
from vaultsafe_client.config import Config, ConfigError


class FakeClient:
    def __init__(self, vaults: list[dict]) -> None:
        self._vaults = vaults

    def list_vaults(self) -> list[dict]:
        return self._vaults

    def list_items(self, vault_id: int, *, service=None, tag=None) -> list[dict]:
        return [
            {"id": 1, "service": "github", "tags": ["work"]},
            {"id": 2, "service": "GitLab", "tags": []},
            {"id": 3, "service": "bank", "tags": ["personal"]},
        ]


@pytest.fixture
def config(tmp_path: Path) -> tuple[Path, Config]:
    path = tmp_path / "config.toml"
    return path, Config(base_url="http://x", username="alice")


def test_find_items_prefers_exact_casefold(config):
    _, cfg = config
    matches = cli.find_items(FakeClient([]), 1, "gitlab")
    assert [m["service"] for m in matches] == ["GitLab"]


def test_find_items_falls_back_to_substring(config):
    _, cfg = config
    matches = cli.find_items(FakeClient([]), 1, "git")
    assert {m["service"] for m in matches} == {"github", "GitLab"}


def test_resolve_vault_uses_explicit(config):
    path, cfg = config
    client = FakeClient([{"id": 7, "name": "personal"}])
    assert cli.resolve_vault(cfg, client, path, explicit=7) == 7


def test_resolve_vault_uses_default(config):
    path, cfg = config
    cfg = Config(base_url=cfg.base_url, username=cfg.username, default_vault=3)
    client = FakeClient([{"id": 3, "name": "work"}])
    assert cli.resolve_vault(cfg, client, path) == 3


def test_resolve_vault_prompts_and_persists(config, monkeypatch, capsys):
    path, cfg = config
    client = FakeClient([{"id": 5, "name": "personal"}])
    monkeypatch.setattr("builtins.input", lambda _prompt: "5")
    assert cli.resolve_vault(cfg, client, path) == 5
    assert "personal" in capsys.readouterr().out
    assert Config.load(path).default_vault == 5


def test_resolve_vault_rejects_bad_id(config, monkeypatch):
    path, cfg = config
    client = FakeClient([{"id": 5, "name": "personal"}])
    monkeypatch.setattr("builtins.input", lambda _prompt: "nope")
    with pytest.raises(ConfigError):
        cli.resolve_vault(cfg, client, path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: vaultsafe_client.cli`

- [ ] **Step 3: Write shared cli.py**

```python
# client/vaultsafe_client/cli.py
from __future__ import annotations

import getpass
from pathlib import Path
from typing import Any

from .client import VaultClient
from .config import Config, ConfigError, default_config_path

MASTER_PROMPT = "Master password: "


def load_config(path: Path | None = None) -> Config:
    return Config.load(path or default_config_path())


def login(config: Config) -> VaultClient:
    password = getpass.getpass(MASTER_PROMPT)
    client = VaultClient(config.base_url)
    client.login(config.username, password)
    return client


def resolve_vault(
    config: Config,
    client: VaultClient,
    path: Path | None,
    *,
    explicit: int | None = None,
) -> int:
    if explicit is not None:
        return explicit
    if config.default_vault is not None:
        return config.default_vault
    vaults = [dict(v) for v in client.list_vaults()]
    if not vaults:
        raise ConfigError("no vaults; create one via the API first")
    print("vaults:")
    for vault in vaults:
        print(f"  {vault['id']}: {vault['name']}")
    raw = input("vault id: ").strip()
    if not raw.isdigit():
        raise ConfigError("vault id must be an integer")
    chosen = int(raw)
    if not any(v["id"] == chosen for v in vaults):
        raise ConfigError(f"no vault with id {chosen}")
    Config(config.base_url, config.username, chosen).save(path or default_config_path())
    return chosen


def find_items(client: VaultClient, vault_id: int, query: str) -> list[Any]:
    items = [dict(i) for i in client.list_items(vault_id)]
    folded = query.casefold()
    exact = [i for i in items if str(i["service"]).casefold() == folded]
    if exact:
        return exact
    return [i for i in items if folded in str(i["service"]).casefold()]
```

- [ ] **Step 4: Add public helpers to `client.py`**

Insert after the `me()` method (after line 112):

```python
    def health(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._request("GET", "/api/health"))
```

Insert at the end of the internals section (after `_require_unlocked`):

```python
    def current_kek(self) -> bytes:
        return self._require_unlocked()
```

- [ ] **Step 5: Write `cli_main.py`**

```python
# client/vaultsafe_client/cli_main.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import commands
from .client import VaultApiError
from .config import ConfigError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vs",
        description="VaultSafe zero-knowledge password CLI",
    )
    parser.add_argument("--config", type=Path, default=None, help="config file path")
    sub = parser.add_subparsers(dest="command", required=True)
    commands.register_all(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except VaultApiError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("aborted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Write `commands/__init__.py` shell**

```python
# client/vaultsafe_client/commands/__init__.py
from __future__ import annotations

from typing import Any

_COMMAND_REGISTERS: list[Any] = []


def register_all(subparsers: Any) -> None:
    for register in _COMMAND_REGISTERS:
        register(subparsers)


def _add_command(register: Any) -> None:
    _COMMAND_REGISTERS.append(register)
```

Task A12 appends the seven command modules to `_add_command` calls.

- [ ] **Step 7: Register the `vs` script in `client/pyproject.toml`**

Append after the `[project]` `dependencies` block:

```toml
[project.scripts]
vs = "vaultsafe_client.cli_main:main"
```

Run `uv lock` at repo root to refresh `uv.lock`.

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_cli.py -v`
Expected: PASS (6 passed)

- [ ] **Step 9: Gates + commit**

Run: `uv run --project client ruff format . && uv run --project client ruff check . && uv run --project client mypy vaultsafe_client && uv run --project client pytest -q`
Expected: all clean/pass.

```bash
git add client/vaultsafe_client/cli.py client/vaultsafe_client/cli_main.py client/vaultsafe_client/commands/__init__.py client/vaultsafe_client/client.py client/pyproject.toml uv.lock client/tests/test_cli.py
git commit -m "feat: add CLI entry point, shared helpers, and health/current_kek clients"
```

---

### Wave 3 — seven parallel command tasks (A5–A11)

Each task below creates exactly **one** command module plus **one** unit test file. Do NOT touch `cli_main.py`, `commands/__init__.py`, `client.py`, or any other command's file.

### Task A5: `vs init`

**Files:**
- Create: `client/vaultsafe_client/commands/init.py`
- Modify: `client/tests/test_cli.py` (append `test_init_writes_config` — or create `client/tests/test_cli_init.py`; appending to `test_cli.py` keeps mypy test-ignore scope, but a separate file is acceptable)

**Interfaces:**
- Consumes: `VaultClient`, `Config`, `default_config_path()`. Produces `register(subparsers)` + `run(args) -> int` for the `init` subcommand (writes config, calls `client.health()`).

- [ ] **Step 1: Write the failing test**

```python
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
```

(replace `init` import line: `from vaultsafe_client.commands import init`)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_cli_init.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `init.py`**

```python
from __future__ import annotations

import argparse
from typing import Any

from ..client import VaultClient
from ..config import Config, default_config_path


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("init", help="create config and verify server reachability")
    p.add_argument("--url", default="http://127.0.0.1:8000", help="server base URL")
    p.add_argument("--username", required=True, help="your username")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = Config(base_url=args.url.rstrip("/"), username=args.username)
    client = VaultClient(args.url)
    client.health()
    path = getattr(args, "config", None) or default_config_path()
    config.save(path)
    print(f"config written to {path}")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_cli_init.py -v`
Expected: PASS

- [ ] **Step 5: Gates + commit**

Run: `uv run --project client ruff format . && uv run --project client ruff check . && uv run --project client mypy vaultsafe_client`
Expected: clean.

```bash
git add client/vaultsafe_client/commands/init.py client/tests/test_cli_init.py
git commit -m "feat: add 'vs init' command"
```

### Task A6: `vs unlock`

**Files:**
- Create: `client/vaultsafe_client/commands/unlock.py`
- Create: `client/tests/test_cli_unlock.py`

**Interfaces:**
- Consumes: `cli.load_config`, `cli.login`. Produces `register`/`run` for `unlock`.

- [ ] **Step 1: Write the failing test**

```python
# client/tests/test_cli_unlock.py
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
```

- [ ] **Step 2–4: Implement + verify**

Run failing then:

```python
# client/vaultsafe_client/commands/unlock.py
from __future__ import annotations

import argparse
from typing import Any

from .. import cli


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("unlock", help="verify master password")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    cli.login(config)
    print("unlocked")
    return 0
```

Run: `uv run --project client pytest tests/test_cli_unlock.py -v`
Expected: PASS

- [ ] **Step 5: Gates + commit**

```bash
git add client/vaultsafe_client/commands/unlock.py client/tests/test_cli_unlock.py
git commit -m "feat: add 'vs unlock' command"
```

### Task A7: `vs add`

**Files:**
- Create: `client/vaultsafe_client/commands/add.py`
- Create: `client/tests/test_cli_add.py`

**Interfaces:**
- Consumes: `cli.load_config`, `cli.login`, `cli.resolve_vault`, `generator.generate_password`, `clipboard.copy_to_clipboard`, stdlib `getpass`.
- Produces: `register`/`run` for `add`. Flags: positional `service`, `-t/--tag` (append), `--ask` (prompt instead of generating), `--vault` (explicit id). Default behavior: generate a password, copy to clipboard (fallback: print to stderr).

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_cli_add.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `add.py`**

```python
from __future__ import annotations

import argparse
import getpass
import sys
from typing import Any

from .. import cli, clipboard, generator


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("add", help="store a new item")
    p.add_argument("service", help="service name")
    p.add_argument("-t", "--tag", action="append", default=[], help="tag (repeatable)")
    p.add_argument("--ask", action="store_true", help="prompt for password instead of generating")
    p.add_argument("--vault", type=int, default=None, help="vault id override")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    client = cli.login(config)
    vault_id = cli.resolve_vault(config, client, args.config, explicit=args.vault)
    if args.ask:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm: ")
        if password != confirm:
            print("error: passwords do not match", file=sys.stderr)
            return 1
    else:
        password = generator.generate_password()
        tool = clipboard.copy_to_clipboard(password)
        if tool is None:
            print(f"warning: could not copy; password: {password}", file=sys.stderr)
        else:
            print("generated password copied to clipboard")
    client.create_item(vault_id, args.service, {"password": password}, tags=list(args.tag))
    print(f"stored {args.service}")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_cli_add.py -v`
Expected: PASS

- [ ] **Step 5: Gates + commit**

```bash
git add client/vaultsafe_client/commands/add.py client/tests/test_cli_add.py
git commit -m "feat: add 'vs add' command"
```

### Task A8: `vs get`

**Files:**
- Create: `client/vaultsafe_client/commands/get.py`
- Create: `client/tests/test_cli_get.py`

**Interfaces:**
- Consumes: `cli.load_config`, `cli.login`, `cli.resolve_vault`, `cli.find_items`, `clipboard.copy_to_clipboard`.
- Produces: `register`/`run` for `get`. Flags: positional `service`, `--show`, `--vault`. Any/zero/many match → error exit 1.

- [ ] **Step 1: Write the failing test**

```python
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
```

Note the captured object pattern is awkward — simplify the plan test to three functions:

```python
def _args(tmp_path: Path, argv: list[str]) -> argparse.Namespace:
    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice", default_vault=1).save(path)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    get.register(sub)
    args = parser.parse_args(argv)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_cli_get.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `get.py`**

```python
from __future__ import annotations

import argparse
import sys
from typing import Any

from .. import cli, clipboard


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("get", help="retrieve and copy a password")
    p.add_argument("service", help="service name")
    p.add_argument("--show", action="store_true", help="print instead of copying")
    p.add_argument("--vault", type=int, default=None, help="vault id override")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    client = cli.login(config)
    vault_id = cli.resolve_vault(config, client, args.config, explicit=args.vault)
    matches = cli.find_items(client, vault_id, args.service)
    if not matches:
        print(f"error: no item matching {args.service!r}", file=sys.stderr)
        return 1
    if len(matches) > 1:
        names = ", ".join(sorted(str(m["service"]) for m in matches))
        print(f"error: multiple matches: {names}", file=sys.stderr)
        return 1
    item = matches[0]
    secret = client.get_secret(int(item["id"]))
    password = secret["password"]
    if args.show:
        print(password)
        return 0
    tool = clipboard.copy_to_clipboard(password)
    if tool is None:
        print("error: no clipboard tool found", file=sys.stderr)
        return 1
    print("copied to clipboard")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_cli_get.py -v`
Expected: PASS

- [ ] **Step 5: Gates + commit**

```bash
git add client/vaultsafe_client/commands/get.py client/tests/test_cli_get.py
git commit -m "feat: add 'vs get' command"
```

### Task A9: `vs ls`

**Files:**
- Create: `client/vaultsafe_client/commands/ls.py`
- Create: `client/tests/test_cli_ls.py`

**Interfaces:**
- Consumes: `cli.load_config`, `cli.login`, `cli.resolve_vault`. Produces `register`/`run` for `ls` (positional `query`?, `-t/--tag`, `--vault`), printing `id\tservice\ttags`.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_cli_ls.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `ls.py`**

```python
from __future__ import annotations

import argparse
from typing import Any

from .. import cli


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("ls", help="list stored services")
    p.add_argument("query", nargs="?", default=None, help="filter by service substring")
    p.add_argument("-t", "--tag", default=None, help="filter by tag")
    p.add_argument("--vault", type=int, default=None, help="vault id override")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    client = cli.login(config)
    vault_id = cli.resolve_vault(config, client, args.config, explicit=args.vault)
    items = client.list_items(vault_id, service=args.query, tag=args.tag)
    for item in items:
        tags = ",".join(item.get("tags", []))
        print(f"{item['id']}\t{item['service']}\t{tags}")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_cli_ls.py -v`
Expected: PASS

- [ ] **Step 5: Gates + commit**

```bash
git add client/vaultsafe_client/commands/ls.py client/tests/test_cli_ls.py
git commit -m "feat: add 'vs ls' command"
```

### Task A10: `vs rm`

**Files:**
- Create: `client/vaultsafe_client/commands/rm.py`
- Create: `client/tests/test_cli_rm.py`

**Interfaces:**
- Consumes: `cli.load_config`, `cli.login`, `cli.resolve_vault`, `cli.find_items`. Produces `register`/`run` for `rm` (positional `service`, `-y/--yes`, `--vault`). No match / multi match → exit 1. Confirmation prompt unless `--yes` (monkeypatch `builtins.input`).

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_cli_rm.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `rm.py`**

```python
from __future__ import annotations

import argparse
import sys
from typing import Any

from .. import cli


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("rm", help="delete an item")
    p.add_argument("service", help="service name")
    p.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    p.add_argument("--vault", type=int, default=None, help="vault id override")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    client = cli.login(config)
    vault_id = cli.resolve_vault(config, client, args.config, explicit=args.vault)
    matches = cli.find_items(client, vault_id, args.service)
    if not matches:
        print(f"error: no item matching {args.service!r}", file=sys.stderr)
        return 1
    if len(matches) > 1:
        names = ", ".join(sorted(str(m["service"]) for m in matches))
        print(f"error: multiple matches: {names}", file=sys.stderr)
        return 1
    item = matches[0]
    if not args.yes:
        answer = input(f"delete {item['service']}? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("aborted")
            return 0
    client.delete_item(int(item["id"]))
    print("deleted")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_cli_rm.py -v`
Expected: PASS

- [ ] **Step 5: Gates + commit**

```bash
git add client/vaultsafe_client/commands/rm.py client/tests/test_cli_rm.py
git commit -m "feat: add 'vs rm' command"
```

### Task A11: `vs gen`

**Files:**
- Create: `client/vaultsafe_client/commands/gen.py`
- Modify: `client/tests/test_cli.py` — append one test (or create `client/tests/test_cli_gen.py`)

**Interfaces:**
- Consumes: `generator.generate_password`. Produces `register`/`run` for `gen` (optional positional `length`, default 20).

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_cli_gen.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `gen.py`**

```python
from __future__ import annotations

import argparse
from typing import Any

from .. import generator


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("gen", help="generate a password")
    p.add_argument("length", nargs="?", type=int, default=20, help="password length")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    print(generator.generate_password(args.length))
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_cli_gen.py -v`
Expected: PASS

- [ ] **Step 5: Gates + commit**

```bash
git add client/vaultsafe_client/commands/gen.py client/tests/test_cli_gen.py
git commit -m "feat: add 'vs gen' command"
```

### Task A12: Wire the registry, add integration tests, ship v1.1.0

**Files:**
- Modify: `client/vaultsafe_client/commands/__init__.py` (register the seven command modules)
- Create: `server/tests/test_cli_integration.py` (live-server end-to-end)
- Modify: `client/pyproject.toml:3`, `server/pyproject.toml:3` (version → `1.1.0`)
- Modify: `uv.lock` (`uv lock`)
- Modify: `CHANGELOG.md` (release section)

**Interfaces:**
- Consumes: all seven command modules (A5–A11), `cli_main.main` (A4), server `live_server` + autouse `_fast_throttle` fixture (server/tests/conftest.py).
- Produces: fully wired `vs`; integration coverage proving the real subprocess-grade CLI drives a real server with real crypto.

- [ ] **Step 1: Wire `commands/__init__.py`**

Replace the shell from A4 with the complete registry:

```python
# client/vaultsafe_client/commands/__init__.py
from __future__ import annotations

from typing import Any

from . import add, gen, get, init, ls, rm, unlock

_COMMAND_REGISTERS: list[Any] = []


def register_all(subparsers: Any) -> None:
    for register in _COMMAND_REGISTERS:
        register(subparsers)


def _add_command(register: Any) -> None:
    _COMMAND_REGISTERS.append(register)


_add_command(add.register)
_add_command(gen.register)
_add_command(get.register)
_add_command(init.register)
_add_command(ls.register)
_add_command(rm.register)
_add_command(unlock.register)
```

Note: imports must stay in that alphabetical order for ruff (isort): `add, gen, get, init, ls, rm, unlock`. The module-level `_add_command(...)` calls populate the registry at import time, so `cli_main._build_parser()` (which calls `commands.register_all`) sees every subcommand with no other change.

- [ ] **Step 2: Write the integration test file**

```python
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
```

Notes:
- The fixture reuses the already-registered user + vault through the real `VaultClient`, then scripts the CLI through `main()` exactly as `vs` will be invoked on the shell.
- `main` catches `ConfigError`/`VaultApiError`/`KeyboardInterrupt` and returns exit codes, so assertions are on return values plus captured output.
- `_fast_throttle` (autouse) gives login 1000/min; `_isolate_lockout`/`_isolate_throttle_cache` (autouse) keep KDF cost and lockout state isolated per test.

- [ ] **Step 3: Run to verify**

Run: `uv run --project server pytest tests/test_cli_integration.py -v`
Expected: 3 PASS (the two `django_db` tests plus `test_cli_gen`).

- [ ] **Step 4: Full gates then commit wiring**

```bash
uv run --project server pytest -q
uv run --project client pytest -q
uv run --project client ruff format --check . && uv run --project client ruff check .
uv run --project server ruff format --check . && uv run --project server ruff check .
cd /home/cyberfreak/projects/vault-safe && pre-commit run --all-files
```

```bash
git add client/vaultsafe_client/commands/__init__.py server/tests/test_cli_integration.py
git commit -m "feat: wire CLI commands and add live-server integration tests"
```

- [ ] **Step 5: Bump to 1.1.0, lock, changelog**

Edit `client/pyproject.toml:3` and `server/pyproject.toml:3`: `version = "1.1.0"`. Run `uv lock` at repo root. Append to `CHANGELOG.md` above `## [Unreleased]`:

```markdown
## [1.1.0] - CLI

### Added

- `vs` CLI with `init`, `unlock`, `add`, `get`, `ls`, `rm`, `gen` subcommands; config at `~/.config/vaultsafe/config.toml`; `vs` console script in `vaultsafe-client`.
- Live-server end-to-end CLI integration tests.
```

Run root gate, then commit and tag:

```bash
git add client/pyproject.toml server/pyproject.toml uv.lock CHANGELOG.md
git commit -m "chore: bump versions to 1.1.0 and document CLI release"
git tag -a v1.1.0 -m "v1.1.0 - CLI core"
```

Milestone A complete. All 43 server tests (incl. 3 CLI integration) + 62 client tests + gates green.

---

## Milestone B — v1.2.0 export/import backup

Encrypted, JSON, self-describing backup files. Encryption reuses the existing envelope machinery: the backup is an `Envelope` sealed under the account KEK already derived at login time, so **no second password prompt** — "same master password" is satisfied by reusing `VaultClient.current_kek()` (A4). The KEK is derived from the master password via the server's published KDF salt/params (available to anyone via `/api/auth/preauth`, so backups stay decryptable offline by anyone holding just the master password + username). Files carry `format`/`version`/`created`/`vault.name` headers.

- Exit-code contract unchanged (0/1/130). All `ExportError` conditions print to stderr and return 1.
- Command modules keep the `from .. import cli` import pattern so unit tests monkeypatch `vaultsafe_client.cli.*`.
- No new server files in this milestone; only `server/tests/test_cli_integration.py` grows (B4).

### Task B1: Export library

**Files:**
- Create: `client/vaultsafe_client/export.py`
- Create: `client/tests/test_export.py`

**Interfaces:**
- Consumes: `VaultClient` (`list_vaults`, `list_items`, `get_secret`), `build_envelope`/`unseal_envelope`/`Envelope`/`EnvelopeError` from `.envelope`, `cryptography` `InvalidTag`.
- Produces:
  - `ExportError(ValueError)`
  - `@dataclass(frozen=True) BundleItem` (`service: str`, `tags: list[str]`, `secrets: dict[str, str]`) with `to_dict()`/`from_dict()`
  - `@dataclass(frozen=True) Bundle` (`vault_name: str`, `items: list[BundleItem]`)
  - `collect_bundle(client: VaultClient, vault_id: int, vault_name: str | None = None) -> Bundle`
  - `export_bundle(bundle: Bundle, kek: bytes) -> bytes`
  - `import_bundle(data: bytes, kek: bytes) -> Bundle`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import json

import pytest

from vaultsafe_client.envelope import build_envelope
from vaultsafe_client.export import (
    DOC_FORMAT,
    DOC_VERSION,
    Bundle,
    BundleItem,
    ExportError,
    collect_bundle,
    export_bundle,
    import_bundle,
)

CEK = bytes(range(32))


def test_round_trip():
    bundle = Bundle("personal", [BundleItem("github", ["work"], {"password": "s3cret!"})])
    data = export_bundle(bundle, CEK)
    assert import_bundle(data, CEK) == bundle


def test_round_trip_empty():
    bundle = Bundle("v", [])
    assert import_bundle(export_bundle(bundle, CEK), CEK) == bundle


def test_wrong_kek_rejected():
    data = export_bundle(Bundle("v", []), CEK)
    with pytest.raises(ExportError):
        import_bundle(data, bytes(range(32, 64)))


def test_tampered_rejected():
    data = bytearray(export_bundle(Bundle("v", [BundleItem("x", [], {"p": "y"})]), CEK))
    data[40] ^= 0xFF
    with pytest.raises(ExportError):
        import_bundle(bytes(data), CEK)


def test_garbage_json_rejected():
    with pytest.raises(ExportError):
        import_bundle(b"not json at all", CEK)


class FakeClient:
    def __init__(self) -> None:
        self.secret = {"password": "s3cret!"}

    def list_vaults(self) -> list[dict]:
        return [{"id": 1, "name": "personal"}]

    def list_items(self, vault_id: int, *, service=None, tag=None) -> list[dict]:
        return [{"id": 7, "service": "github", "tags": ["work"]}]

    def get_secret(self, item_id) -> dict[str, str]:
        return dict(self.secret)


def test_collect_bundle():
    bundle = collect_bundle(FakeClient(), 1)
    assert bundle.vault_name == "personal"
    assert bundle.items == [BundleItem("github", ["work"], {"password": "s3cret!"})]


def test_non_dict_header_rejected():
    with pytest.raises(ExportError):
        import_bundle(b"[]", CEK)


def test_missing_envelope_rejected():
    data = export_bundle(Bundle("v", []), CEK)
    header = json.loads(data.decode("utf-8"))
    del header["envelope"]
    with pytest.raises(ExportError):
        import_bundle(json.dumps(header, sort_keys=True).encode("utf-8"), CEK)


def test_non_list_items_rejected():
    envelope = build_envelope(
        {
            "format": DOC_FORMAT,
            "version": str(DOC_VERSION),
            "vault_name": "v",
            "items": '{"key": 1}',
        },
        CEK,
    )
    data = json.dumps(
        {"format": DOC_FORMAT, "version": DOC_VERSION, "envelope": envelope.to_dict()},
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(ExportError):
        import_bundle(data, CEK)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_export.py -v`
Expected: FAIL with `ModuleNotFoundError: vaultsafe_client.export`

- [ ] **Step 3: Write `export.py`**

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from cryptography.exceptions import InvalidTag

from .client import VaultClient
from .envelope import Envelope, EnvelopeError, build_envelope, unseal_envelope

DOC_FORMAT = "vaultsafe-backup"
DOC_VERSION = 1


class ExportError(ValueError):
    pass


@dataclass(frozen=True)
class BundleItem:
    service: str
    tags: list[str]
    secrets: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {"service": self.service, "tags": self.tags, "secrets": self.secrets}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> BundleItem:
        service = data.get("service")
        tags = data.get("tags", [])
        secrets = data.get("secrets")
        if not isinstance(service, str):
            raise ExportError("backup item missing 'service'")
        if not isinstance(tags, list):
            raise ExportError("backup item 'tags' must be a list")
        if not isinstance(secrets, dict):
            raise ExportError("backup item missing 'secrets'")
        return cls(
            service=service,
            tags=[str(t) for t in tags],
            secrets={str(k): str(v) for k, v in secrets.items()},
        )


@dataclass(frozen=True)
class Bundle:
    vault_name: str
    items: list[BundleItem]

    def to_dict(self) -> dict[str, object]:
        return {"vault_name": self.vault_name, "items": [i.to_dict() for i in self.items]}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Bundle:
        vault_name = data.get("vault_name")
        items = data.get("items")
        if not isinstance(vault_name, str):
            raise ExportError("backup missing 'vault_name'")
        if not isinstance(items, list):
            raise ExportError("backup missing 'items'")
        parsed = [BundleItem.from_dict(cast(dict[str, object], entry)) for entry in items]
        return cls(vault_name=vault_name, items=parsed)


def collect_bundle(client: VaultClient, vault_id: int, vault_name: str | None = None) -> Bundle:
    if vault_name is None:
        vault_name = "vault"
        for vault in [dict(v) for v in client.list_vaults()]:
            if vault["id"] == vault_id:
                vault_name = str(vault["name"])
                break
    items = [
        BundleItem(
            service=str(item["service"]),
            tags=[str(t) for t in item.get("tags", [])],
            secrets=dict(client.get_secret(int(item["id"]))),
        )
        for item in client.list_items(vault_id)
    ]
    return Bundle(vault_name=vault_name, items=items)


def export_bundle(bundle: Bundle, kek: bytes) -> bytes:
    envelope = build_envelope(
        {
            "format": DOC_FORMAT,
            "version": str(DOC_VERSION),
            "created": datetime.now(UTC).isoformat(),
            "vault_name": bundle.vault_name,
            "items": json.dumps([i.to_dict() for i in bundle.items], sort_keys=True),
        },
        kek,
    )
    header = {"format": DOC_FORMAT, "version": DOC_VERSION, "envelope": envelope.to_dict()}
    return json.dumps(header, sort_keys=True).encode("utf-8")


def import_bundle(data: bytes, kek: bytes) -> Bundle:
    try:
        header = cast(dict[str, Any], json.loads(data.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportError("backup is not valid JSON") from exc
    if not isinstance(header, dict):
        raise ExportError("unsupported backup format or version")
    if header.get("format") != DOC_FORMAT or header.get("version") != DOC_VERSION:
        raise ExportError("unsupported backup format or version")
    try:
        envelope = Envelope.from_dict(cast(dict[str, object], header.get("envelope")))
        fields = unseal_envelope(envelope, kek)
    except (EnvelopeError, InvalidTag) as exc:
        raise ExportError("wrong master password or corrupt backup") from exc
    try:
        payload = json.loads(fields["items"])
        if not isinstance(payload, list) or not all(isinstance(entry, dict) for entry in payload):
            raise ExportError("backup contents are malformed")
        items = [BundleItem.from_dict(cast(dict[str, object], entry)) for entry in payload]
    except (json.JSONDecodeError, ExportError) as exc:
        raise ExportError("backup contents are malformed") from exc
    return Bundle(vault_name=fields["vault_name"], items=items)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_export.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Gates + commit**

Run: `uv run --project client ruff format . && uv run --project client ruff check . && uv run --project client mypy vaultsafe_client && uv run --project client pytest -q`
Expected: format clean, checks pass, mypy clean, all tests pass.

```bash
git add client/vaultsafe_client/export.py client/tests/test_export.py
git commit -m "feat: add encrypted backup export library"
```

### Task B2: `vs export`

**Files:**
- Create: `client/vaultsafe_client/commands/export_cmd.py`
- Create: `client/tests/test_cli_export.py`

**Interfaces:**
- Consumes: `cli.load_config`, `cli.login`, `cli.resolve_vault`, `export.collect_bundle`, `export.export_bundle`, `client.current_kek()`, stdlib `sys`. 
- Produces: `register`/`run` for `export`. Flags: optional positional `path` (default `vaultsafe-backup-<vault-name>-<datetime>.json` in cwd), `--vault`. No password prompt beyond login — the account KEK seals the bundle.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_cli_export.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `export_cmd.py`**

```python
# client/vaultsafe_client/commands/export_cmd.py
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import cli, export


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("export", help="write an encrypted backup")
    p.add_argument("path", nargs="?", default=None, help="output file path")
    p.add_argument("--vault", type=int, default=None, help="vault id override")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    client = cli.login(config)
    vault_id = cli.resolve_vault(config, client, args.config, explicit=args.vault)
    try:
        bundle = export.collect_bundle(client, vault_id)
        data = export.export_bundle(bundle, client.current_kek())
    except export.ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    path = Path(args.path) if args.path else default_path(bundle.vault_name)
    path.write_bytes(data)
    print(f"backup written to {path}")
    return 0


def default_path(vault_name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(f"vaultsafe-backup-{vault_name}-{stamp}.json")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_cli_export.py -v`
Expected: PASS

- [ ] **Step 5: Gates + commit**

Run: `uv run --project client ruff format . && uv run --project client ruff check . && uv run --project client mypy vaultsafe_client`
Expected: clean.

```bash
git add client/vaultsafe_client/commands/export_cmd.py client/tests/test_cli_export.py
git commit -m "feat: add 'vs export' command"
```

### Task B3: `vs import`

**Files:**
- Create: `client/vaultsafe_client/commands/import_cmd.py`
- Create: `client/tests/test_cli_import.py`

**Interfaces:**
- Consumes: `cli.load_config`, `cli.login`, `export.import_bundle`, `client.current_kek()`, private helper `_find_or_create_vault(client, name) -> int`. 
- Produces: `register`/`run` for `import`. Flags: positional `path`, `--overwrite`, `--vault-name` (override the vault stored in the backup). Items are re-encrypted under the live server KEK via `create_item`/`update_item`; exact-name matches are skipped unless `--overwrite`. Prints a created/updated/skipped summary to stdout.

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import argparse
from pathlib import Path

from vaultsafe_client import cli
from vaultsafe_client.commands import import_cmd
from vaultsafe_client.config import Config
from vaultsafe_client.export import Bundle, BundleItem


class FakeClient:
    def __init__(self) -> None:
        self.created: list[tuple[int, str, dict, list]] = []
        self.updated: list[tuple[int, str, dict, list]] = []

    def current_kek(self) -> bytes:
        return bytes(range(32))

    def list_vaults(self) -> list[dict]:
        return []

    def create_vault(self, name: str) -> dict:
        return {"id": 5, "name": name}

    def list_items(self, vault_id: int, *, service=None, tag=None) -> list[dict]:
        return []

    def create_item(self, vault_id, service, secret_fields, tags) -> dict:
        self.created.append((vault_id, service, secret_fields, tags))
        return {"id": 1}

    def update_item(self, item_id, *, service=None, secret_fields=None, tags=None) -> dict:
        self.updated.append((item_id, service, secret_fields, tags))
        return {"id": 9}


def test_run_creates_items(tmp_path: Path, monkeypatch, capsys):
    client = FakeClient()
    monkeypatch.setattr(cli, "login", lambda _cfg: client)
    monkeypatch.setattr(
        import_cmd.export,
        "import_bundle",
        lambda *a: Bundle("personal", [BundleItem("github", ["work"], {"password": "x"})]),
    )

    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice").save(path)
    backup = tmp_path / "backup.json"
    backup.write_bytes(b"{}")
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    import_cmd.register(sub)
    args = parser.parse_args(["import", str(backup)])
    args.config = path
    assert import_cmd.run(args) == 0
    assert client.created == [(5, "github", {"password": "x"}, ["work"])]
    assert "created" in capsys.readouterr().out


def test_run_skips_without_overwrite(tmp_path: Path, monkeypatch, capsys):
    class SkipClient(FakeClient):
        def list_items(self, vault_id: int, *, service=None, tag=None) -> list[dict]:
            return [{"id": 9, "service": "github", "tags": ["work"]}]

    client = SkipClient()
    monkeypatch.setattr(cli, "login", lambda _cfg: client)
    monkeypatch.setattr(
        import_cmd.export,
        "import_bundle",
        lambda *a: Bundle("personal", [BundleItem("github", ["work"], {"password": "y"})]),
    )

    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice").save(path)
    backup = tmp_path / "backup.json"
    backup.write_bytes(b"{}")
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    import_cmd.register(sub)
    args = parser.parse_args(["import", str(backup)])
    args.config = path
    assert import_cmd.run(args) == 0
    assert client.created == [] and client.updated == []
    assert "skipped" in capsys.readouterr().out


def test_run_overwrites(tmp_path: Path, monkeypatch, capsys):
    class OverwriteClient(FakeClient):
        def list_items(self, vault_id: int, *, service=None, tag=None) -> list[dict]:
            return [{"id": 9, "service": "github", "tags": ["work"]}]

    client = OverwriteClient()
    monkeypatch.setattr(cli, "login", lambda _cfg: client)
    monkeypatch.setattr(
        import_cmd.export,
        "import_bundle",
        lambda *a: Bundle("personal", [BundleItem("github", ["work"], {"password": "z"})]),
    )

    path = tmp_path / "config.toml"
    Config(base_url="http://x", username="alice").save(path)
    backup = tmp_path / "backup.json"
    backup.write_bytes(b"{}")
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    import_cmd.register(sub)
    args = parser.parse_args(["import", str(backup), "--overwrite"])
    args.config = path
    assert import_cmd.run(args) == 0
    assert client.updated == [(9, "github", {"password": "z"}, ["work"])]
    assert "updated" in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project client pytest tests/test_cli_import.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `import_cmd.py`**

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from .. import cli, export


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("import", help="restore from an encrypted backup")
    p.add_argument("path", help="backup file path")
    p.add_argument("--overwrite", action="store_true", help="update items that already exist")
    p.add_argument("--vault-name", default=None, help="target vault name override")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    client = cli.login(config)
    try:
        bundle = export.import_bundle(Path(args.path).read_bytes(), client.current_kek())
    except (export.ExportError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    vault_id = _find_or_create_vault(client, args.vault_name or bundle.vault_name)
    existing = {str(item["service"]).casefold(): item for item in client.list_items(vault_id)}
    created = updated = skipped = 0
    for item in bundle.items:
        prior = existing.get(item.service.casefold())
        if prior is None:
            client.create_item(vault_id, item.service, item.secrets, tags=list(item.tags))
            created += 1
        elif args.overwrite:
            client.update_item(
                int(prior["id"]),
                service=item.service,
                secret_fields=dict(item.secrets),
                tags=list(item.tags),
            )
            updated += 1
        else:
            skipped += 1
    print(
        f"imported into vault {vault_id}: {created} created, {updated} updated, {skipped} skipped"
    )
    return 0


def _find_or_create_vault(client: Any, name: str) -> int:
    for vault in client.list_vaults():
        if str(vault["name"]).casefold() == name.casefold():
            return int(vault["id"])
    return int(client.create_vault(name)["id"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project client pytest tests/test_cli_import.py -v`
Expected: PASS

- [ ] **Step 5: Gates + commit**

Run: `uv run --project client ruff format . && uv run --project client ruff check . && uv run --project client mypy vaultsafe_client`
Expected: clean.

```bash
git add client/vaultsafe_client/commands/import_cmd.py client/tests/test_cli_import.py
git commit -m "feat: add 'vs import' command"
```

### Task B4: Wire export/import, e2e backup test, release v1.2.0

**Files:**
- Modify: `client/vaultsafe_client/commands/__init__.py` (register `export_cmd` + `import_cmd`)
- Modify: `server/tests/test_cli_integration.py` (append export→import round trip)
- Modify: `client/pyproject.toml:3`, `server/pyproject.toml:3` (version → `1.2.0`)
- Modify: `uv.lock`, `CHANGELOG.md`, `README.md` (CLI section)

- [ ] **Step 1: Register the two new subcommands**

Update the import + registration lines in `client/vaultsafe_client/commands/__init__.py`:

```python
from . import add, export_cmd, gen, get, import_cmd, init, ls, rm, unlock

_add_command(add.register)
_add_command(export_cmd.register)
_add_command(gen.register)
_add_command(get.register)
_add_command(import_cmd.register)
_add_command(init.register)
_add_command(ls.register)
_add_command(rm.register)
_add_command(unlock.register)
```

Verify: `uv run --project client mypy vaultsafe_client` clean; `python -c "import sys; sys.path.insert(0,'client'); from vaultsafe_client.cli_main import main; print(main(['--help']))"` shows `export` and `import` in the subcommand list (exit code 0).

- [ ] **Step 2: Append the backup e2e test**

Add to `server/tests/test_cli_integration.py`:

```python
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
```

- [ ] **Step 3: Run to verify**

Run: `uv run --project server pytest tests/test_cli_integration.py -v`
Expected: 4 PASS (two CLI-round-trip, wrong-password, gen, plus this one — order may vary; total 4 tests in file).

- [ ] **Step 4: Full gates then commit wiring**

```bash
uv run --project server pytest -q
uv run --project client pytest -q
uv run --project client ruff format --check . && uv run --project client ruff check . && uv run --project client mypy vaultsafe_client
uv run --project server ruff format --check . && uv run --project server ruff check . && uv run --project server mypy accounts vaults common vaultsafe
cd /home/cyberfreak/projects/vault-safe && pre-commit run --all-files
```

```bash
git add client/vaultsafe_client/commands/__init__.py server/tests/test_cli_integration.py
git commit -m "feat: wire export/import commands and add backup e2e test"
```

- [ ] **Step 5: Bump to 1.2.0, changelog, README, tag**

Edit `client/pyproject.toml:3` and `server/pyproject.toml:3`: `version = "1.2.0"`. Run `uv lock` at repo root. Append to `CHANGELOG.md` above `## [Unreleased]`:

```markdown
## [1.2.0] - encrypted backup

### Added

- `vs export` / `vs import`: encrypted, self-describing JSON backups sealed under the account KEK (no separate backup password).
```

Append a `## CLI (vs)` section to `README.md` (place it between the `## Develop` and `## API` sections — it describes the daily-use interface on top of the API):

~~~markdown
## CLI (`vs`)

`vs` is a daily-use CLI for VaultSafe. It talks to a running server, prompts for your master password per command, and never stores secrets on disk.

```console
vs init --username alice --url http://127.0.0.1:8000   # one-time setup
vs add github -t work            # generates & copies a password
vs get github                    # copies the password
vs get github --show             # prints it
vs ls                            # list stored services
vs ls --tag work                 # filter by tag
vs rm github                     # delete (asks for confirmation)
vs gen 32                        # print a random password
vs export backup.json            # encrypted backup
vs import backup.json            # restore / migrate
```

Config lives at `~/.config/vaultsafe/config.toml` (or `$XDG_CONFIG_HOME/vaultsafe/config.toml`) with `base_url`, `username`, and optional `default_vault`. Run `vs init` to create it.

Exit codes: `0` success, `1` error, `130` Ctrl-C.
~~~

Run full gates, then commit and tag:

```bash
git add README.md client/pyproject.toml server/pyproject.toml uv.lock CHANGELOG.md
git commit -m "chore: bump versions to 1.2.0 and document the CLI"
git tag -a v1.2.0 -m "v1.2.0 - encrypted backup"
```

Milestone B complete. All gates green; `vs` ships v1.2.0.

---

## Post-Plan Verification Checklist (run at the end)

- [ ] `uv run --project client pytest -q` — all pass
- [ ] `uv run --project server pytest -q` — 40 core + 4 CLI integration tests pass
- [ ] `uv run --project client mypy vaultsafe_client` and `uv run --project server mypy accounts vaults common vaultsafe` — clean
- [ ] `cd /home/cyberfreak/projects/vault-safe && pre-commit run --all-files` — clean
- [ ] `vs --help` (via `uv run --project client vs` or the installed script) lists `init, unlock, add, get, ls, rm, gen, export, import`
- [ ] `git log --oneline -n 5` shows the CLI milestone commits; tags `v1.1.0`, `v1.2.0` point at the release commits
- [ ] Push `main`, `v1.1.0`, `v1.2.0` to `origin`
- [ ] Update `.superpowers/sdd/progress.md` ledger and `todo` checklist; close the CLI phase
