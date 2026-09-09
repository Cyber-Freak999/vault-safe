# Changelog

All notable changes follow Conventional Commits.

## [Unreleased]

### Added

- uv workspace with `server/` (Django) and `client/` (reference client) packages.

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