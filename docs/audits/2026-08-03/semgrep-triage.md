# semgrep triage — tools/semgrep/ rulesets, first ship-gate run

Command: `semgrep --config tools/semgrep/ --json --quiet hooks/ tools/ scripts/`
Measured (re-run by auditor, 2026-08-03): **0 errors, 73 files scanned, 90 findings**
(context said 94 — actual live count is 90; classified against 90).

## Counts per verdict
- REAL: 3
- BY-DESIGN: ~64 (fail-open hooks + cosmetic post-effects + correct deny-site exits)
- WONTFIX: ~23 (test fixtures, .bak dir, ruleset false positives)

## RANKED REAL (most dangerous first)

1. **tools/codemap.py:74 — py-except-swallows — `py_symbols_ast`**
   `except OSError:` at :67 is narrow and fine, but the broader `try:` around
   `ast.parse(src)` at :77 has no dedicated `except SyntaxError` — any parse
   failure falls through with no handler shown in range and the function's
   only declared catch is `OSError` at line 67, meaning a genuine
   `SyntaxError` from `ast.parse` is UNCAUGHT (crashes) while a read failure
   is silently swallowed to `return 0`/`[]`. Either way the caller (codemap
   generation, the exact artifact just shipped and described in memory as
   catching 2 fabricated signals) can render a file as "0 symbols" instead of
   "could not parse" — the identical failure class Task 1 just fixed for
   semgrep's own parsing. Caller wrongly believes the file has no symbols.
   ```
   65:        with open(path, "r", errors="replace") as fh:
   66:            return sum(1 for _ in fh)
   67:    except OSError:
   68:        return 0
   ```

2. **tools/harness-coach.py:260 — py-except-swallows — settings.json wiring block**
   ```
   259:    if SETTINGS.exists():
   260:        try:
   261:            hk = json.loads(SETTINGS.read_text()).get("hooks", {})
   262:            wired = {ev: [h.get("command", "").split("/")[-1].strip('"')
   ...
   268:        except Exception:
   269:            pass
   ```
   A malformed `settings.json` (the live hook-wiring file) silently drops the
   entire "settings.json hook wiring" section from the weekly digest. The
   reader (Ro or the LLM stage) sees a report that looks complete but is
   missing the one section that would show a hook silently unwired —
   directly the failure mode memory `harness-auditor-yield-verdict` already
   flags ("harness-coach's LLM stage ... can't verify coverage").

3. **tools/harness-coach.py:201-219 — py-except-swallows — harness-usage telemetry**
   ```
   201:    try:
   202:        usage = Path.home() / ".claude" / "hooks" / "state" / "harness-usage.jsonl"
   ...
   218:    except Exception:
   219:        pass
   ```
   Same pattern: any read/parse error on the telemetry file drops the
   "are harness features being used?" section with no note that it failed
   vs. legitimately had no data — a reader can't distinguish "0 usage" from
   "couldn't read the file."

## BY-DESIGN (fail-open hooks, correct on purpose)
All `py-except-swallows` / `py-deny-site` / `env-var-no-default` findings inside
`hooks/*.py` (excluding `.bak-contextdiet/`) whose swallow guards the hook's
own PreToolUse/PostToolUse entrypoint — e.g. `builder-fence.py:75`,
`codemap-inject.py:50,129`, `coding-routing-guard.py:78`, `compact-prep-gate.py:119,141`,
`filesize-cap.py:90`, `graphify-blindspot.py:58,80,97,112`, `graphify-gate.py:108,123,136,211`,
`harness-enforce.py:81`, `main-edit-guard.py:53,72`, `manifest-guard.py:50,64,73,125`,
`northstar-inject.py:99,128,163`, `northstar-protect.py:40`, `now-gate.py:66,87`,
`phantom-edit-guard.py:53,71`, `post-agent-guard.py:54`, `precompact-handoff.py:57,261`,
`reread-guard.py:51,60,86,128`, `route-only-gate.py:96`, `session-checkpoint.py:57,110`,
`skill-reinject-guard.py:43,56`, `token-discipline.py:75`, `understand-gate.py:109,132,142`.
Correct: a raised exception here blocks the user's real tool call; fail-open is the spec.
All `py-deny-site` hits inside hooks (`check-all-commit-gate.sh:259` sh-deny-site,
`builder-fence.py:186`) are the enforcement exit itself firing correctly, flagged
only because the rule pattern-matches raw `exit`/`sys.exit` instead of a wrapped
helper — behavior is correct.
`hooks/harness-coach.py:374-378` (notification + `open-findings.sh` launch) and
`tools/claudemd-trim.py:505-514` (same pattern) swallow AFTER the report is
already atomically written to disk — failure here only loses a desktop
notification, never the artifact. Correct to ignore.
`hooks/pre_compact_global.sh` (`ml sync 2>&1 | tail -6 | sed ...`, no pipefail)
is consistent with the rest of the script's `cmd || { echo …; exit 0; }`
fail-open pattern for a precompact hook — intentional, matches the file's own style.

## WONTFIX
- `hooks/.bak-contextdiet/harness-enforce.py:81`, `.../post-agent-guard.py:18` —
  dead backup directory, not on any execution path.
- `hardcoded-home-path` × 2, `hooks/abs-path-nudge.py:109,124` — both are
  fake test-fixture paths (`/Users/x/foo.py`, `/Users/x/bar.py`) inside the
  file's own `__main__` self-test, not real machine-specific paths. Ruleset
  false positive (matches `/Users/` prefix regardless of context).
- `env-var-no-default` × 7 (`harness-usage-telemetry.py:102`,
  `main-edit-guard.py:132,137`, `understand-gate.py:207,209,211,214`) — every
  one is `os.environ["X"] = value` (a WRITE, inside a self-test block that
  saves/restores `HOME` or a kill-switch var), not an unguarded read. Ruleset
  false positive: the rule matches `os.environ[...]` regardless of read vs.
  write. None of these run under `set -u` (they're Python, not shell) so the
  "unset var" framing doesn't even apply.
- `sh-pipeline-no-pipefail` × 10 at line 1 (shebang) — 5 of the 10 files
  already have `set -euo pipefail` further down (`tools/retrieve.sh:16`,
  `tools/chains/c2-prior-art.sh:11`, `c3-enumerate.sh:13`,
  `hooks/kill-stuck-sessions.sh:4`, `tools/gemini-opencode.sh:5`) — ruleset
  false positive, flags file at line 1 before scanning the rest. The
  remaining 5 (`hooks/caveman-discipline.sh` — `#!/bin/sh`, no bash pipefail
  support at all; `hooks/pre_compact_global.sh`, `tools/open-findings.sh`,
  `tools/run-harness-scout.sh` — `set -u` only, by design per their own
  `|| exit 0` fallback style; `tools/graphify-blast.sh` — `set -eu`,
  best-effort per-target loop that already handles failure per iteration)
  are all low-stakes utility/notification scripts, not gates.
- `py-subprocess-unchecked` × 7 — every instance checked resolves the
  returncode through an explicit path: `tools/memgraph/mem.py:193` propagates
  via `raise SystemExit(result.returncode)` at :202; `tools/goal/goal_judge.py:157`
  returns `proc.returncode` to a caller (`goal_judge.py:116,122,136,145,149`)
  that all `return`/assign it; `tools/claudemd-trim.py:506,511` and
  `tools/harness-coach.py:375,378` are post-write notification/launcher calls
  (see BY-DESIGN); `hooks/spawn-necessity.py:184` is a `git init` inside a
  disposable tempdir in the file's own self-test. Ruleset false positive
  or genuinely cosmetic in every case found.
- `py-deny-site` remainder not already covered above (`hooks/compact-prep-gate.py:154`,
  `hooks/graphify-gate.py:108`, `hooks/irreversible-pause.py:162`,
  `hooks/main-edit-guard.py:112`, `hooks/northstar-protect.py:40`,
  `hooks/now-gate.py:87`, `hooks/reread-guard.py:128`, `hooks/route-only-gate.py:96`,
  `hooks/skill-reinject-guard.py:43`, `hooks/understand-gate.py:142`) — all are
  the gate's own enforcement `exit`, correct by construction.
- `tools/check-all/claudemd_drift.py:244` — narrow `except (json.JSONDecodeError, OSError)`
  around an *optional* `package.json` scripts check, falls back to empty set;
  low-stakes, correctly scoped exception type already (not bare `Exception`).

## Specifically checked and clean
- **`tools/finding.sh`, `tools/git-sync.sh`** — 0 semgrep findings in this run.
  `finding.sh:8` has `set -euo pipefail`; its two `except Exception` are shell
  heredoc'd Python one-liners at :93/:115 that semgrep's Python rules do not
  parse as a `.py` file, so they were never scanned — worth a follow-up but
  out of scope for this triage (ruleset only globs `*.py`/`*.sh` top-level).
  `git-sync.sh:24` uses `set -uo pipefail` deliberately per its own
  `# ponytail:` comment at :22 — matches spec exactly, no finding raised.
- **`tools/chains/*` / `tools/retrieve.sh`** — only 2 chain files matched
  (`c2-prior-art.sh`, `c3-enumerate.sh`), both false-positive pipefail hits
  (already have `set -euo pipefail`); `retrieve.sh` matched once, same false
  positive. No REAL findings in the retrieval layer.
