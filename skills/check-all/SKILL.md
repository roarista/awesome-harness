# check-all — Deterministic Readiness Gate

## Purpose
Run a deterministic battery of checks against any repo before shipping, handing off to another agent, or opening a PR. Composes existing repo-level gate commands and adds universal checks that Ro's repos typically lack (file-size caps, no-TODO scan, duplicate-code detection).

## Trigger phrases
- "check-all"
- "/check-all"
- "is this ready to ship?"
- "run the gate"
- before any PR / handoff / deploy

## Invocation
```bash
bash /Users/rodrigoarista/.claude/tools/check-all/check_all.sh [REPO_DIR] [--fast] [--json]
```

- `REPO_DIR` — path to repo root (default: current working directory)
- `--fast` — skip tests (CI-light mode; still runs lint/typecheck/file-size/TODO)
- `--json` — emit JSON instead of the human-readable table

### Examples
```bash
# Full run from inside a repo
bash /Users/rodrigoarista/.claude/tools/check-all/check_all.sh . 

# Fast gate before handing off (no tests)
bash /Users/rodrigoarista/.claude/tools/check-all/check_all.sh /path/to/repo --fast

# JSON output for programmatic consumption
bash /Users/rodrigoarista/.claude/tools/check-all/check_all.sh /path/to/repo --json
```

## Checks performed

| Check | Type | Default severity | Notes |
|-------|------|-----------------|-------|
| **base-gate** | HARD | fail | Composes existing repo scripts (factory:check → ci:safe → lint/typecheck); falls back to tsc/ruff/mypy |
| **file-size** | soft | warn | Flags source files > 800 lines |
| **no-TODO** | soft | warn | Grep for TODO/FIXME/XXX in source files |
| **dup-code** | soft | warn | jscpd if available; skip-with-note if not |
| **semgrep** | soft | warn | Deterministic OSS SAST (bugs/injections/secrets). GUARDED: silent skip if `semgrep` not on PATH; `SEMGREP_STRICT=1` → fail |
| **tests** | HARD | fail | Skipped under `--fast`; runs npm test / pytest -q |

**Hard checks:** rc != 0 → OVERALL FAIL → exit 1  
**Soft checks (warn):** listed in table, exit 0 unless configured to "fail"

## Reading the output

```
=== check-all READINESS TABLE (/path/to/repo) ===
CHECK           RESULT   RC    SUMMARY
------------------------------------------------------------
base-gate       pass     0     npm run factory:check
file-size       warn     1     3 file(s) > 800 lines
no-TODO         warn     1     2 file(s) with TODO/FIXME/XXX
dup-code        skip     0     jscpd not available — skipped
tests           pass     0     npm test
------------------------------------------------------------
OVERALL: READY (all hard checks passed; warns are non-blocking)
```

- `pass` — check succeeded
- `fail` — check failed (hard checks → OVERALL NOT READY)
- `warn` — check found issues but not blocking (unless configured to "fail")
- `skip` — check was not applicable or was bypassed

File-size and TODO offenders are printed above the table so they're actionable.

## Optional deterministic SAST: semgrep

An optional **semgrep** step complements the LLM review council with a zero-token,
deterministic static scan (bugs / injection / secrets). It runs:

```bash
semgrep --config auto --error --quiet
```

**Guarded** — it runs only if `semgrep` is on `PATH`; when absent it is a silent
no-op (`skip`), so a repo that hasn't installed semgrep is never wedged. Findings
are **warn** (non-blocking) by default; set `SEMGREP_STRICT=1` to make findings a
hard fail. Install (optional): `pipx install semgrep` (or `brew install semgrep`).

## Optional config: `.check-all.json`

Place in the repo root to override defaults:

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

All keys are optional. Absent file → all defaults apply.

| Key | Type | Default | Notes |
|-----|------|---------|-------|
| `base_command` | string | auto-detect | Override the gate command |
| `max_file_lines` | int | 800 | Lines-per-file threshold |
| `todo_severity` | "warn"\|"fail" | "warn" | Whether TODOs block shipping |
| `filesize_severity` | "warn"\|"fail" | "warn" | Whether oversized files block |
| `skip_tests` | bool | false | Permanently skip tests (like --fast) |
| `src_globs` | array | auto | Source patterns to scan |

## Stack detection
- `package.json` present → node checks enabled
- `pyproject.toml` or `requirements.txt` → python checks enabled
- Both can be active simultaneously

## When to use --fast
- Pre-commit hook (fast feedback)
- Quick sanity before handing off to another agent
- CI environments where tests run separately

## Exit codes
- `0` — all hard checks passed (warns/skips are fine)
- `1` — at least one hard check failed OR a "fail"-severity soft check tripped

## Integration tips
- Add to CLAUDE.md: "Before handing off, run check-all --fast"  
- Wire into pre-PR step: `bash ~/.claude/tools/check-all/check_all.sh . && gh pr create ...`
- Use `--json` to pipe results into downstream agents or scripts
