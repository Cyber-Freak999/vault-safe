# Changelog

All notable changes follow Conventional Commits.

## [1.1.0] - CLI

### Added

- `vs` CLI with `init`, `unlock`, `add`, `get`, `ls`, `rm`, `gen` subcommands; config at `~/.config/vaultsafe/config.toml`; `vs` console script in `vaultsafe-client`.
- Live-server end-to-end CLI integration tests.

## [1.2.0] - encrypted backup

### Added

- `vs export` / `vs import`: encrypted, self-describing JSON backups sealed under the account KEK (no separate backup password).

## [Unreleased]

### Added

- uv workspace with `server/` (Django) and `client/` (reference client) packages.
- MIT license, GitHub Actions CI, and self-hosting docs for public release.

## [0.1.0] - client crypto core
- Argon2id KEK/verifier derivation, AES-256-GCM envelope, HTTP client.

## [0.2.0] - accounts
- Zero-knowledge register, preauth, login/logout/me, token auth, brute-force lockout.

## [0.3.0] - vaults
- Vault and item CRUD, service/tag search, server-side envelope validation, audit log.

## [0.4.0] - hardening & docs
- OpenAPI schema + Swagger UI, end-to-end integration tests, throttle coverage, README.

## [1.0.0] - core complete
- Full zero-knowledge core verified: client crypto, accounts, vaults, audit, docs.