---
name: check-all
description: Run a deterministic battery of pre-ship checks against any repo — composes the repo's own gate commands and adds universal ones (file-size caps, no-TODO scan, duplicate-code detection, optional semgrep). Use before shipping, before handing work back to Ro, before opening a PR, or whenever Ro says "check-all" / "run the gate" / "is this ready to ship?".
---

# check-all — deterministic readiness gate

> **Step 6 of THE PROCEDURE** (`~/.codex/AGENTS.md`), the deterministic half. It costs no tokens and cannot be fooled by intent — run it rather than asserting the code works.

## Invocation

```bash
bash ~/.codex/tools/check-all/check_all.sh [REPO_DIR] [--fast] [--json]
```

- `REPO_DIR` — repo root (default: current directory)
- `--fast` — skip tests (still runs lint/typecheck/file-size/TODO)
- `--json` — machine-readable output instead of the table

## Checks

| Check | Type | Default | Notes |
|-------|------|---------|-------|
| **base-gate** | HARD | fail | Composes the repo's own scripts (factory:check → ci:safe → lint/typecheck); falls back to tsc/ruff/mypy |
| **file-size** | soft | warn | Flags source files > 800 lines |
| **no-TODO** | soft | warn | TODO/FIXME/XXX in source files |
| **dup-code** | soft | warn | jscpd if available, else skipped |
| **semgrep** | soft | warn | ADVISORY only — prints findings, never fails the gate. `SEMGREP_STRICT=1` makes it blocking. Silent skip if semgrep is not on PATH |
| **tests** | HARD | fail | Skipped under `--fast`; runs npm test / pytest -q |

Hard check fails → OVERALL FAIL → exit 1. Soft checks warn and exit 0 unless configured to fail.

Exit codes: `0` all hard checks passed; `1` a hard check failed or a "fail"-severity soft check tripped.

## Optional per-repo config: `.check-all.json`

```json
{
  "base_command": "npm run factory:check",
  "max_file_lines": 500,
  "todo_severity": "fail",
  "filesize_severity": "warn",
  "skip_tests": false,
  "src_globs": ["src/**/*.ts", "lib/**/*.py"]
}
```

All keys optional; absent file means all defaults apply.

## Rules

- Report the gate's **real output**. Never summarize a run you did not perform, and never call a change ready on a failing hard check.
- Use `--fast` for a mid-work sanity pass; run the full gate before the close (`compact-prep`).
- If the script is missing, the harness was not installed for Codex: run `./install.sh --codex` from the awesome-harness repo.
