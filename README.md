# VaultSafe
[![CI](https://github.com/Cyber-Freak999/vault-safe/actions/workflows/ci.yml/badge.svg)](https://github.com/Cyber-Freak999/vault-safe/actions/workflows/ci.yml)

A self-hosted, zero-knowledge password manager API with a reference Python client.

The server never sees your master password or your secrets. All encryption happens
client-side: a master password is stretched with Argon2id into a KEK, which wraps a
random per-item DEK (AES-256-GCM). The server stores only search metadata (`service`,
`tags`) plus opaque envelopes.

## Layout

- `server/` — Django 5.2 + Django REST Framework API (apps: accounts, vaults, common).
- `client/` — `vaultsafe-client`: pure-Python reference client (Argon2id, envelope, HTTP).

## Develop

Prereqs: uv (Python 3.13).

```bash
uv sync                       # lock + install all workspace members
uv run --project server python server/manage.py migrate
uv run --project server python server/manage.py runserver
```

Quality gates (enforced by pre-commit on every commit):

```bash
cd server && uv run ruff format --check .
cd server && uv run ruff check .
cd client && uv run ruff format --check .
cd client && uv run ruff check .
cd client && uv run mypy vaultsafe_client
cd server && uv run mypy accounts vaults common vaultsafe
cd client && uv run pytest
cd server && uv run pytest
```

## Deploy (self-hosted)

VaultSafe is a normal Django app; run it behind TLS with gunicorn. Set these environment variables:

| Variable | Required in prod | Dev default | Purpose |
|----------|------------------|-------------|---------|
| `DJANGO_SECRET_KEY` | yes | dev-only fallback (`server/vaultsafe/settings.py:12`) | Django secret; generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | no | `1` | must be `0` in production |
| `DJANGO_ALLOWED_HOSTS` | no | `localhost,127.0.0.1,[::1]` | comma-separated hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | no | `http://localhost,http://127.0.0.1` | comma-separated origins |

With `DJANGO_DEBUG=0`, Django enables HSTS, SSL redirect, and secure cookies automatically (`server/vaultsafe/settings.py:111-117`).

```bash
export DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
export DJANGO_DEBUG=0
export DJANGO_ALLOWED_HOSTS="vaults.example.com"
export DJANGO_CSRF_TRUSTED_ORIGINS="https://vaults.example.com"

uv sync --project server --group prod
uv run --project server python server/manage.py migrate
uv run --project server gunicorn vaultsafe.wsgi:application
```

**Security limitation:** Transport must be TLS for any non-localhost deployment. The login protocol uses a password verifier, not a full PAKE/SRP, so an operator who captures the database could still brute-force the verifier offline; this is a documented limitation until a PAKE/SRP upgrade.

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

## API

Register, preauth, login, logout, me, vaults, items, search, audit, health.
Interactive docs at `/api/docs` (OpenAPI schema at `/api/schema`).

Zero-knowledge flow:

```python
from vaultsafe_client import VaultClient

c = VaultClient("http://127.0.0.1:8000")
c.register("alice", "correct horse battery staple")
c.login("alice", "correct horse battery staple")
vault = c.create_vault("personal")
item = c.create_item(vault["id"], "github", {"username": "alice", "password": "s3cret"})
print(c.get_secret(item["id"]))
```

## Docs

Design spec: `docs/superpowers/specs/2026-09-08-vaultsafe-design.md`.
Change log: `CHANGELOG.md`.
