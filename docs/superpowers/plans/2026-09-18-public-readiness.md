# Public-Release Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the VaultSafe repository safe and complete to publish publicly (make the GitHub repo public) by adding a license, production deployment documentation, GitHub Actions CI, and removing local-machine path leaks.

**Architecture:** Documentation and repo-hygiene pass over the existing single-branch repo. Adds four artifacts — MIT `LICENSE`, a `## Deploy (self-hosted)` README section (moving the buried TLS/PAKE limitation up to deployers), `.github/workflows/ci.yml` mirroring the README gates, and replacing three absolute local paths in `docs/superpowers/plans/2026-09-10-vaultsafe-cli.md`. No Python source or product behavior changes; no version bumps, no tags.

**Tech Stack:** MIT license text; GitHub Actions (ubuntu-latest + `astral-sh/setup-uv`); existing uv workspace gates (ruff, mypy, pytest) run exactly as in `.pre-commit-config.yaml`.

## Global Constraints

- Commit messages follow Conventional Commits (existing repo convention).
- Every task ends green: `pre-commit run --all-files` must pass before commit.
- No source, dependency, version, or `uv.lock` changes anywhere in this plan.
- Copyright holder line in the license MUST read `Copyright (c) 2026 Cyber-Freak999` (sole repo author).
- CI gate commands must be character-identical to README `## Develop` gates and `.pre-commit-config.yaml` entries.
- Keep trunk-based `main`; create no feature branch or worktree; create no git tags.
- Repo slug for badge/workflow URLs: `Cyber-Freak999/vault-safe`; uv version pinned: `0.11.29`; Python `3.13`.

---

### Task 1: Commit the plan document

**Files:**
- Create: `docs/superpowers/plans/2026-09-18-public-readiness.md` (this file)
- Test: N/A (repo convention: each plan is committed up front)

**Interfaces:**
- Consumes: nothing.
- Produces: the committed plan document at `docs/superpowers/plans/2026-09-18-public-readiness.md`, referenced by the ledger and by Task 6's checklist.

- [ ] **Step 1: Commit the plan**

Run:

```bash
git add docs/superpowers/plans/2026-09-18-public-readiness.md
git commit -m "docs: add public-readiness plan"
```

- [ ] **Step 2: Verify**

Run: `git log --oneline -1`
Expected: `docs: add public-readiness plan`

---

### Task 2: Add MIT license

**Files:**
- Create: `LICENSE`
- Test: `git diff --cached --stat` includes `LICENSE`

**Interfaces:**
- Consumes: nothing.
- Produces: top-level `LICENSE` (MIT text), referenced by README `## Docs` in Task 3 and by the CHANGELOG entry in Task 6.

- [ ] **Step 1: Create the `LICENSE` file**

```
MIT License

Copyright (c) 2026 Cyber-Freak999

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Verify content**

Run: `head -3 LICENSE`
Expected: `MIT License` then `Copyright (c) 2026 Cyber-Freak999` then blank line.

- [ ] **Step 3: Run gates**

Run: `pre-commit run --all-files`
Expected: all hooks pass/are skipped (LICENSE matches no `types` filter).

- [ ] **Step 4: Commit**

```bash
git add LICENSE
git commit -m "docs: add MIT license"
```

- [ ] **Step 5: Verify**

Run: `git log --oneline -1`
Expected: `docs: add MIT license`

---

### Task 3: Document production deployment and surface the security limitation

**Files:**
- Modify: `README.md` (insert Deploy section between the Develop gates block at line 36 and `## CLI` at line 38; remove the old TLS note at lines 77-78)

**Interfaces:**
- Consumes: nothing (self-contained README edit).
- Produces: `## Deploy (self-hosted)` section documenting env vars and the TLS/PAKE limitation; consumed by Task 4 (badge placement reviews README top) and Task 6 (final README check).

- [ ] **Step 1: Insert the Deploy section**

Open `README.md`. After the closing ` ``` ` of the Develop gates block (line 36) and before `## CLI (`vs`)` (line 38), insert:

```markdown
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
```

- [ ] **Step 2: Remove the old, buried TLS note**

In `README.md`, delete lines 77-78 (`Transport must be TLS for any non-localhost deployment (verifier-based login is` / `documented as a limitation until a PAKE/SRP upgrade).`) — the notice now lives in the Deploy section.

- [ ] **Step 3: Verify section order**

Run: `rg -n '^## ' README.md`
Expected order: `# VaultSafe`, `## Layout`, `## Develop`, `## Deploy (self-hosted)`, `## CLI (`vs`)`, `## API`, `## Docs`.

- [ ] **Step 4: Verify no old note remains**

Run: `rg -n 'Transport must be TLS' README.md`
Expected: exactly one match, on the Deploy-section line starting `**Security limitation:**`.

- [ ] **Step 5: Run gates**

Run: `pre-commit run --all-files`
Expected: all hooks pass/are skipped (Markdown matches no `types` filter).

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: add self-hosting and production env documentation"
```

- [ ] **Step 7: Verify**

Run: `git log --oneline -1`
Expected: `docs: add self-hosting and production env documentation`

---

### Task 4: Add GitHub Actions CI and README badge

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `README.md` (insert CI badge under the `# VaultSafe` title at line 1)

**Interfaces:**
- Consumes: Task 3's updated README (badge sits at top; gate commands are the documented ones).
- Produces: `.github/workflows/ci.yml` (runs on push to `main` and on PRs) plus a badge URL consumed by Task 6's final checklist.

- [ ] **Step 1: Create the workflow**

Create `.github/workflows/ci.yml` with exact content:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  gates:
    name: quality gates
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          version: "0.11.29"

      - name: Sync workspace
        run: uv sync

      - name: ruff format (server)
        run: cd server && uv run ruff format --check .

      - name: ruff check (server)
        run: cd server && uv run ruff check .

      - name: ruff format (client)
        run: cd client && uv run ruff format --check .

      - name: ruff check (client)
        run: cd client && uv run ruff check .

      - name: mypy (client)
        run: cd client && uv run mypy vaultsafe_client

      - name: mypy (server)
        run: cd server && uv run mypy accounts vaults common vaultsafe

      - name: pytest (client)
        run: cd client && uv run pytest -q

      - name: pytest (server)
        run: cd server && uv run pytest -q
```

- [ ] **Step 2: Validate the YAML parses**

Run:

```bash
uv run --with pyyaml python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); assert d['jobs']['gates'], 'no gates job'; print('YAML OK')"
```

Expected: `YAML OK`

- [ ] **Step 3: Validate step names map 1:1 to README gates**

Run: `rg -o '^      - name: .*' .github/workflows/ci.yml`
Expected lines (order): Checkout, Install uv, Sync workspace, ruff format (server), ruff check (server), ruff format (client), ruff check (client), mypy (client), mypy (server), pytest (client), pytest (server).

- [ ] **Step 4: Add the CI badge to the README**

In `README.md`, on the line directly below `# VaultSafe` (line 1), insert:

```markdown
[![CI](https://github.com/Cyber-Freak999/vault-safe/actions/workflows/ci.yml/badge.svg)](https://github.com/Cyber-Freak999/vault-safe/actions/workflows/ci.yml)
```

- [ ] **Step 5: Run gates**

Run: `pre-commit run --all-files`
Expected: all hooks pass/are skipped.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml README.md
git commit -m "ci: add GitHub Actions quality-gate workflow"
```

- [ ] **Step 7: Verify**

Run: `git log --oneline -1`
Expected: `ci: add GitHub Actions quality-gate workflow`

---

### Task 5: Remove local-machine path leaks from committed docs

**Files:**
- Modify: `docs/superpowers/plans/2026-09-10-vaultsafe-cli.md:1671`, `:2379`, `:2441`

**Interfaces:**
- Consumes: nothing.
- Produces: cleaned CLI plan with no machine-local absolute path references; verified by Task 6's search.

- [ ] **Step 1: Locate every absolute local path in the CLI plan (expect exactly 3)**

Run: `git grep -n '/home/' -- docs/superpowers/plans/2026-09-10-vaultsafe-cli.md`
Expected: exactly three matches, at lines 1671, 2379, 2441 — each a shell line of the form `cd /home/<user>/projects/vault-safe && pre-commit run --all-files` (the verbatim string is what grep matched; do not type the `<user>` path by hand, copy it from the match).

- [ ] **Step 2: Replace each path-qualified command with the bare command**

In `docs/superpowers/plans/2026-09-10-vaultsafe-cli.md`, for each of the three matched lines (1671, 2379, 2441), delete the `cd /home/.../vault-safe &&` prefix and keep `pre-commit run --all-files` as the whole command (`pre-commit run` is invoked from the repo root, which is the context the plan documents). Line 2441 is inside a checklist item: keep the `- [ ]` prefix and the trailing `— clean`.

- [ ] **Step 3: Verify no local paths remain in tracked files**

Run: `git grep -n '/home/' -- docs/superpowers/plans/2026-09-10-vaultsafe-cli.md`
Expected: no matches (exit status 1, empty output).

Also run `git grep -nE 'cyberfreak[0-9]{3}@'` — the author's personal email must not appear in any tracked file content. Note the pattern is written so this search itself does not match (the digits are inside a character class); expected: no matches.

- [ ] **Step 4: Run gates**

Run: `pre-commit run --all-files`
Expected: all hooks pass/are skipped.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-09-10-vaultsafe-cli.md
git commit -m "docs: remove local paths from CLI plan"
```

- [ ] **Step 6: Verify**

Run: `git log --oneline -1`
Expected: `docs: remove local paths from CLI plan`

---

### Task 6: Changelog entry and final verification

**Files:**
- Modify: `CHANGELOG.md` (append a bullet under `## [Unreleased]` → `### Added`)

**Interfaces:**
- Consumes: Tasks 1-5 artifacts (LICENSE, README Deploy + badge, CI workflow, cleaned docs).
- Produces: final green baseline and the "ready to make public" decision evidence.

- [ ] **Step 1: Append the CHANGELOG entry**

In `CHANGELOG.md`, under `### Added` (line 20) in the `## [Unreleased]` section, add a second bullet directly below the existing one at line 22:

```markdown
- MIT license, GitHub Actions CI, and self-hosting docs for public release.
```

- [ ] **Step 2: Run the full gate suite**

Run: `pre-commit run --all-files`
Expected: all four hooks pass.

- [ ] **Step 3: Run final verification checks**

Run each and confirm:

```bash
test -f LICENSE
rg -q '## Deploy (self-hosted)' README.md
test -f .github/workflows/ci.yml
uv run --with pyyaml python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('workflow YAML valid')"
rg -n '/home/' docs/superpowers/plans/2026-09-10-vaultsafe-cli.md; test $? -eq 1 && echo "OK: no local paths" || echo "FAIL: local path leak"
git status --porcelain
```

Expected: `LICENSE` exists; Deploy section found; workflow file exists and says `workflow YAML valid`; `OK: no local paths`; `git status --porcelain` shows `CHANGELOG.md` as the only modified file.

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: note public release readiness in changelog"
```

- [ ] **Step 5: Verify commit history**

Run: `git log --oneline -7`
Expected (newest to oldest):

```
docs: note public release readiness in changelog
docs: remove local paths from CLI plan
ci: add GitHub Actions quality-gate workflow
docs: add self-hosting and production env documentation
docs: add MIT license
docs: add public-readiness plan
<previous commit>
```

- [ ] **Step 6: Update the progress ledger**

Append a Public-Readiness block to `.superpowers/sdd/progress.md` recording Tasks 1-6 as complete and noting: "All gates green locally; push `main` to `origin` and flip the GitHub repo visibility to public."

---

## Post-Plan Verification Checklist (run at the end)

- [ ] `git log --oneline -6` shows the six public-readiness commits at the tip of `main`
- [ ] `git status` clean; `main` in sync with `origin/main` only AFTER the final push
- [ ] `pre-commit run --all-files` passes
- [ ] `LICENSE` present at repo root with `Copyright (c) 2026 Cyber-Freak999`
- [ ] README has `## Deploy (self-hosted)` documenting `DJANGO_SECRET_KEY`/`DJANGO_DEBUG`/`DJANGO_ALLOWED_HOSTS`/`DJANGO_CSRF_TRUSTED_ORIGINS` and the TLS/PAKE limitation
- [ ] README has the CI badge; `.github/workflows/ci.yml` exists and is valid YAML
- [ ] `git grep -n '/home/' -- docs/superpowers/plans/2026-09-10-vaultsafe-cli.md` returns nothing
- [ ] No `[project]` version, dependency, or `uv.lock` changes in any of the six commits
- [ ] Push `main` to `origin`, then set the GitHub repo to public