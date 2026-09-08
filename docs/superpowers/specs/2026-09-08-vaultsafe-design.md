# VaultSafe Design

**Date:** 2026-09-08
**Status:** Approved (target for implementation)

## Purpose

VaultSafe is a **zero-knowledge, self-hosted password manager**. The user's explicit goal is to
host and run it locally as a personal replacement for browser password managers and Bitwarden —
not only as a portfolio exercise.

Two implications follow from that goal:

1. **Zero-knowledge model.** The server (even a locally hosted one) must never see the master
   password, any derived encryption key, or plaintext secrets. A compromised or curious server
   yields only ciphertext and search metadata.
2. **Local-first hosting.** Single user, SQLite, `manage.py runserver` is an acceptable runtime
   for this phase. Settings read from the environment so a move to `gunicorn`/Postgres/containers
   is configuration-only, never a redesign.

## Scope (this build, "core")

- Authentication (register / login / logout) with verifier-based, zero-knowledge password flow.
- Vaults (containers) and encrypted items with plaintext `service` + `tags` metadata for search.
- Ownership isolation, audit logging, rate limiting, and brute-force lockout.
- In-repo reference **Python client library** (pure Python, no Django imports) that performs all
  crypto and talks to the API. Integration tests run real crypto against the real server.
- OpenAPI/Swagger documentation.

**Explicitly deferred** (future milestones, not in this spec):
- Daily-use surface: CLI (`vs add github`, `vs get github`) vs. local web UI — decision deferred.
- TOTP 2FA, encrypted backup export/import, key/password rotation.
- OS keyring integration for caching the KEK at rest.
- Multi-device sync and remote hosting.

## Architecture

UV workspace monorepo with two members:

- `server/` — Django project (`vaultsafe`) + Django REST Framework.
- `client/` — `vaultsafe-client`, pure-Python reference client (Argon2id, AES-256-GCM envelope,
  HTTP layer). No Django imports; usable/reusable independently.

### Server apps

| App      | Responsibility                                                        |
|----------|------------------------------------------------------------------------|
| `accounts` | Registration, login/logout, token auth, verifier storage.             |
| `vaults`   | Vault + VaultItem CRUD, metadata search, envelope validation.         |
| `common`   | Throttling, brute-force lockout, audit logging, health check.         |

Because the server never receives the password, Django's password-validators do not apply —
password strength rules are enforced client-side (documented in the client).

## Crypto envelope

Key hierarchy, two layers:

```
master password (client, in memory only)
   │  Argon2id(salt)
   ▼
KEK ──► wraps ──► DEK (random 256-bit, one per item)
            │ AES-256-GCM        │ AES-256-GCM
            ▼                     ▼
        wrapped_key            ciphertext
```

- **Registration:** client generates `salt`, derives `KEK = Argon2id(password, salt)`, then derives
  `verifier = Argon2id(KEK, verifier_salt)` and sends only `{username, salt, verifier_salt,
  verifier, argon2 params}`. The password never leaves the client.
- **Login:** server verifies against stored `verifier`, issues a Bearer token. The client unwraps
  nothing yet; it holds `KEK` in memory for the session.
- **Store item:** client generates a random `DEK` per item; encrypts secret fields
  (`username`, `password`, `notes`) with AES-256-GCM into `{nonce_c, ciphertext}`; wraps `DEK`
  with `KEK` into `{nonce_k, wrapped_key}`. Server stores the envelope plus plaintext
  `service` and `tags`.
- **Read item:** client fetches envelope → unwraps `DEK` with `KEK` → decrypts payload.

### Envelope schema (versioned)

```json
{
  "version": 1,
  "nonce_c":  "<base64, 12 bytes>",
  "ciphertext": "<base64>",
  "nonce_k": "<base64, 12 bytes>",
  "wrapped_key": "<base64>"
}
```

The client validates the version before decoding; unknown versions are rejected.

### Explicitly non-secret metadata

`service` and `tags` are stored in plaintext to enable server-side search (same trade-off the
major password managers make). `username`, `password`, `notes` are always inside the envelope.

### Documented limitation

Verifier-based login means a captured database allows offline guessing against the derived
verifier; mitigated by Argon2id cost and transport TLS. Production zero-knowledge systems add
challenge-response (SRP/PAKE). This is a documented limitation with an upgrade path, **not**
built in this phase. Transport must run over TLS in any non-localhost deployment.

## Data model

```
User
    username            unique, plaintext handle
    kdf_salt            bytes
    kdf_params          JSON {alg, memory_cost, time_cost, parallelism}
    verifier            bytes (Argon2id(KEK, verifier_salt))
    verifier_salt       bytes

Vault
    owner -> User       FK
    name                plaintext
    created_at, updated_at

VaultItem
    vault -> Vault      FK
    service             plaintext, indexed (searchable)
    tags                plaintext (searchable)
    envelope            JSON (versioned, validated server-side only for shape/version)
    last_accessed_at    datetime
    created_at, updated_at

AuditLog
    user -> User        FK
    action              text (login, create_item, read_item, update_item, delete_item, ...)
    item -> VaultItem   nullable FK
    ip                  text
    at                  datetime
```

Django's `AUTH_USER_MODEL` remains the default; `kdf_salt`, `kdf_params`, `verifier`,
`verifier_salt` live on a one-to-one profile model.

## API surface

All endpoints under an `api/` prefix. Auth via DRF Bearer TokenAuthentication.

```
POST /api/auth/register    {username, verifier, verifier_salt, kdf_salt, kdf_params}
POST /api/auth/login       {username, verifier} -> {token}
POST /api/auth/logout
GET  /api/me                -> {username, created_at}

GET|POST   /api/vaults      list / create vault. DELETE (/api/vaults/{id}) cascades items.
GET|PATCH|DELETE /api/vaults/{id}

GET|POST   /api/vaults/{vault_id}/items     list supports ?service=&tag=
GET|PATCH|DELETE /api/items/{id}

GET  /api/audit            owner-only access log, ?limit=
GET  /api/health
```

Rules:

- Every object enforces ownership — cross-user reads/writes are impossible (querysets scoped to
  `request.user`).
- Item GET/PATCH transport the raw envelope only. **The server never decrypts.**
- PATCH replaces the whole envelope + metadata (client re-encrypts); there is no server-side
  partial field update of secret fields.

## Security & hardening

- **Rate limiting:** DRF throttles on all endpoints; a tighter throttle on `/api/auth/login`.
- **Brute-force lockout:** failed-login counter per account + per IP; temporary lockout window
  after N failures (in-memory is acceptable for single-user local hosting; note migration path to
  DB-backed counter).
- **Settings:** `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` read from environment with safe
  development defaults (localhost). Production checklist followed before any non-local exposure.
- **Injection:** ORM-based queries and DRF serializer validation mitigate SQLi/XSS. Tests
  provably round-trip hostile `service`/`tag` values.
- **CSRF:** token-authenticated API — CSRF is not required for the API surface by DRF convention.
- **Docs:** `drf-spectacular` — `/api/schema` + Swagger UI.

## Error handling

Uniform error envelope:
`{"error": {"code": "<machine-read-code>", "message": "<human>", "fields": {...}}}`.

- HTTP 401/403/404 with consistent codes.
- Validation errors map field → message under `fields`.
- 429 rate-limit responses carry `Retry-After`.
- The client parses this envelope and surfaces code + message.

## Testing

- **Client** (pytest): encrypt→decrypt round trip; wrong key fails; tampered ciphertext fails;
  Argon2id/KDF vectors; envelope version rejection; hostile-metadata round trip.
- **Server** (pytest-django): register/login/logout; verifier mismatch rejected; brute-force
  lockout; vault/item CRUD + ownership isolation; search; audit entries written on each action;
  throttles return 429.
- **Integration:** client crypto running against the live test server (test DB) — full
  zero-knowledge flow end-to-end.

## Build phases

1. **Phase 0 — Workspace:** restructure into uv workspace (`server/`, `client/`); dependencies
   (`djangorestframework`, `drf-spectacular`, `argon2-cffi`, `cryptography`,
   `pytest`, `pytest-django`); baseline settings via env; move `db.sqlite3` under server.
2. **Phase 1 — Client crypto core:** Argon2id derivation, envelope build/unseal, tests.
3. **Phase 2 — Accounts:** register/login/logout/me, token auth, brute-force lockout, tests.
4. **Phase 3 — Vaults:** vault + item CRUD, search, ownership, audit log, tests.
5. **Phase 4 — Hardening & docs:** env-driven production settings, throttles, Swagger,
   client↔server integration tests, README rewrite.
6. **Phase 5 (deferred):** CLI and/or web UI decision and implementation.

## Local hosting defaults

- SQLite single-user database.
- `python manage.py runserver` for normal use; settings are env-driven so production packaging
  (`gunicorn`, Postgres, containers) is config-only.
- The API contract is host-agnostic — the future CLI/UI talks to it identically over localhost or
  a remote box (with TLS).

## Success criteria

- A fresh install runs on `localhost`; registration and end-to-end store/read of a secret work via
  the reference client with the server never possessing any plaintext.
- Searching by `service`/`tag` returns envelopes; only the correct master password decrypts them.
- Brute-force lockout triggers after the configured failed attempts; throttles respond 429.
- Full test suite green: client unit, server unit, and client↔server integration.