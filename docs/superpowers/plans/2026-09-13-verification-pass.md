# VaultSafe Verification Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-run the full VaultSafe quality-gate suite end-to-end on current `main` (after docs commit `38b4456`) and confirm everything is green, then mark the backlog item shipped.

**Architecture:** Verification-only pass — no source code changes. Runs the repo's root `pre-commit` hook set first (it drives ruff/mypy/pytest for both members), then repeats each gate explicitly per member exactly as the backlog and README specify, so a green result is confirmed two independent ways. On any red gate the pass halts and reports; nothing is marked shipped.

**Tech Stack:** pre-commit 4.6.2, uv 0.11.29, Python 3.13 workspace (`vaultsafe-client` + `vaultsafe-server`), ruff, mypy (strict), pytest / pytest-django.

## Global Constraints

- Working tree must be clean and on `main` **before** any gate runs; commit `38b4456` must be in `HEAD`'s ancestry (already verified: it is).
- Gates run from the member dirs (client/server); root gate is `pre-commit run --all-files`. Commands run verbatim as listed below.
- **Failure rule:** if any step returns non-zero or unexpected output, STOP. Capture the failing output, report it to the user, and do NOT proceed to later steps (no BACKLOG.md edit, no commit).
- Success means: every step exit 0, ruff "All checks passed!", mypy "Success", pytest all pass.
- Only file modified is `BACKLOG.md` (verification pass checkbox). No version bump, no CHANGELOG edit, no code changes.
- Conventional Commits for the closing docs commit.
- Out of scope: the "SDD wrap-up" and "New milestone candidates" backlog items.

## File Structure

| File | Responsibility |
|---|---|
| `docs/superpowers/plans/2026-09-13-verification-pass.md` | This plan (created at start of execution) |
| `BACKLOG.md:7` | Verification pass checkbox — flipped `- [ ]` → `- [x]` only after every gate is green |

---

### Task 1: Verify baseline state

**Files:** none (read-only checks)

- [ ] **Step 1: Confirm repo baseline**

```bash
git status
git branch --show-current
git merge-base --is-ancestor 38b4456 HEAD && echo "38b4456 in ancestry"
```
Expected: working tree clean, branch `main`, output `38b4456 in ancestry`. If the tree is dirty, STOP and report.

- [ ] **Step 2: Confirm toolchain availability**

```bash
pre-commit --version
uv --version
uv sync --check
```
Expected: versions print (≥ pre-commit 4.6.2, ≥ uv 0.11); `uv sync --check` exits 0 and reports lockfile up to date (a note about "Would uninstall 1 package" is an acceptable pre-pass info line — see next step).

- [ ] **Step 3: Align workspace environments**

```bash
uv sync
```
Expected: exit 0, environment brought to lockfile state ("Audited/Built/Installed" summary). This removes the stale-package delta from Step 2 so gates verify the true lockfile state.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-09-13-verification-pass.md
git commit -m "docs: add verification pass plan"
```
Only commit the plan doc if it was created as a tracked file. If a plan-file location is already established in the repo, follow it.

---

### Task 2: Root gate — pre-commit full hook set

**Files:** none

- [ ] **Step 1: Run the full pre-commit hook set**

Run from repo root:

```bash
pre-commit run --all-files
```
Expected: all 4 hooks (ruff-format, ruff-lint, mypy, pytest) report PASS and final line `All files passed!`, exit 0. Any hook failing or modifying files → STOP and report.

---

### Task 3: Client gates (explicit)

**Files:** none

- [ ] **Step 1: ruff format check**

```bash
uv run --project client ruff format --check .
```
Expected: exit 0, no "would reformat" lines.

- [ ] **Step 2: ruff lint**

```bash
uv run --project client ruff check .
```
Expected: final line `All checks passed!`, exit 0.

- [ ] **Step 3: mypy strict**

```bash
uv run --project client mypy vaultsafe_client
```
Expected: `Success: no issues found in N source files`, exit 0.

- [ ] **Step 4: pytest**

```bash
uv run --project client pytest -q
```
Expected: exit 0, `N passed`.

---

### Task 4: Server gates (explicit)

**Files:** none

- [ ] **Step 1: ruff format check**

```bash
uv run --project server ruff format --check .
```
Expected: exit 0, no "would reformat" lines.

- [ ] **Step 2: ruff lint**

```bash
uv run --project server ruff check .
```
Expected: final line `All checks passed!`, exit 0.

- [ ] **Step 3: mypy strict**

```bash
uv run --project server mypy accounts vaults common vaultsafe
```
Expected: `Success: no issues found in N source files`, exit 0.

- [ ] **Step 4: pytest**

```bash
uv run --project server pytest -q
```
Expected: exit 0, `N passed` (includes the live-server CLI integration tests).

---

### Task 5: Confirm green end-to-end and ship

**Files:**
- Modify: `BACKLOG.md:7`

- [ ] **Step 1: Tick the backlog item**

Edit `BACKLOG.md` — change line 7 from `- [ ] Re-run the full gate suite...` to `- [x] Re-run the full gate suite...` (the "## Verification pass" section only; leave SDD wrap-up and milestone items unchecked).

- [ ] **Step 2: Verify final diff is scope-limited**

```bash
git status
git diff
```
Expected: only `BACKLOG.md` modified, only the one checkbox flipped.

- [ ] **Step 3: Commit**

```bash
git add BACKLOG.md
git commit -m "docs: mark verification pass complete"
```

- [ ] **Step 4: Report**

Report to the user: every gate green (pre-commit at root + client + server), exit 0 across the board, and the backlog item ticked. Note that the "SDD wrap-up" and "Housekeeping" backlog items remain.

---

## Self-Review

- **Spec coverage:** Backlog item requires (a) `pre-commit run --all-files` at root → Task 2; (b) client ruff format/check, mypy, pytest → Task 3; (c) server ruff format/check, mypy, pytest → Task 4; (d) "confirm everything is green end-to-end" → Tasks 1 + 5 and the failure-stop rule. All covered.
- **Placeholder scan:** No TBD/TODO; every step has exact commands and expected output.
- **Type/name consistency:** All commands match README's gate list and `.pre-commit-config.yaml` verbatim.