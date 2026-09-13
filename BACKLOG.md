# Backlog

Work that has been identified but not yet scheduled. Pick an item, break it into a plan, and update this file when shipped.

## Verification pass

- [ ] Re-run the full gate suite after the final docs commit `38b4456` (docs sync) and confirm everything is green end-to-end:
  - pre-commit run --all-files at repo root
  - client: ruff format/check, mypy, pytest
  - server: ruff format/check, mypy, pytest

## SDD wrap-up

- [ ] Mark `docs/superpowers/plans/2026-09-10-vaultsafe-cli.md` as shipped (status line/heading noting v1.2.0 + shipped).
- [ ] Confirm `.superpowers/sdd/progress.md` ledger is final (A1–B4 + FINAL rows already recorded).

## New milestone candidates

Ideas for a future release (scope and pick before planning):

- [ ] Vault key rotation / `vs rotate` command.
- [ ] Backup encryption hardening.
- [ ] Server TLS for remote vault access.
- [ ] Other v1.3.0 ideas — refine scope before pickup.

## Housekeeping

- [ ] README / CHANGELOG polish and any remaining repo hygiene.