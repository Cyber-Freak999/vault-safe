# VaultSafe

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

Transport must be TLS for any non-localhost deployment (verifier-based login is
documented as a limitation until a PAKE/SRP upgrade).

## Docs

Design spec: `docs/superpowers/specs/2026-09-08-vaultsafe-design.md`.
Change log: `CHANGELOG.md`.
