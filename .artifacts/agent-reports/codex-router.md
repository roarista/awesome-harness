# Codex sessions route through free-model-router (2026-10-02)

VERDICT: done. Codex sessions now carry the router contract and `route-model.sh` works inside the Codex seatbelt sandbox.

## Shas
- free-model-router `feffa83` on main (pushed)
- awesome-harness `66245e6` on codex-procedure-parity (pushed)

## Failures reproduced in `codex sandbox -- …` (CODEX_SANDBOX=seatbelt, network disabled)
1. `fmr route` crashed, exit 1, with PermissionError on `~/.local/state/free-model-router/decisions.jsonl`.
2. `route-model.sh` died at `mktemp` because `$TMPDIR` is unwritable. `set -e` killed it before fmr ran.
3. `codex app-server` failed in 5.4s (state sqlite writes denied) and then fell back to rollout correctly. It did not hang.
Note: `codex sandbox macos` is not a subcommand in this CLI. The form is `codex sandbox -- <cmd>`, and `-C` requires `--permission-profile`.

## Fixes
- `fmr/receipts.py`: `log_decision` catches OSError, warns on stderr (naming the id and FMR_DECISIONS), and returns the id. The decision prints with exit 0.
- `fmr/usage.py`: when `CODEX_SANDBOX` is set, `codex_usage` skips the app-server and reads rollout directly (`fallback_reason` says so). Behavior outside the sandbox is unchanged.
- `tests/test_sandbox.py` (2 tests, real OSError, no mocking of the broken part). Mutation check: with each fix reverted, its test fails by name (FileExistsError / "spawned"). Restored afterwards, 139 tests pass.
- `tools/route-model.sh`: output is captured in a variable and parsed with builtins, with no temp files. fmr's stderr now passes through, so the receipt warning is visible. That is the one behavior change on the Claude side.
- `install.sh --codex`: also copies `tools/route-model.sh` to `~/.codex/tools/route-model.sh`.
- `codex/AGENTS.md` adds a Routing operating rule, and the Subagents line now says to take models from the router. The `codex/skills/awesomeharness/SKILL.md` Code loop has the router paragraph in the same wording as the Claude skill, plus Codex specifics: native Codex subagent for Codex-family models, `claude -p --model` for Claude-family models, and how to handle receipts in the sandbox.

## Drift check before install
All live `~/.codex` files matched repo HEAD (AGENTS.md, 6 skills, both standards, hooks). The only difference was `~/.codex/tools/check-all/check_all.sh`, which lacked repo commit b072fab (`.scratch` prune). It had no local edits, so the install updating it was the intended change. Nothing was clobbered.

## Verification
- free-model-router `unittest discover`: Ran 139, OK.
- awesome-harness `tools/git-hooks/test_pre_commit.sh`: 29 passed, 0 failed.
- `codex sandbox -- …/awesome-harness/tools/route-model.sh "fix the retry bug in uploader.py"`: exit 0 in 3.7s. First 3 lines:
  ```
  NECESSITY: LAUNCH
  BUILDER: claude-opus-5-5 via claude effort=medium
  AUDITOR: gpt-6-astra via codex-audit effort=medium cross_family=True
  ```
  The same output comes from the installed `~/.codex/tools/route-model.sh` (5.6s).
- route-model.sh on the host: LAUNCH, DO-NOT-LAUNCH, fmr-failure→legacy (FMR_CARDS bogus), and FMR_DISABLE paths all checked.
- After the install, `~/.codex/AGENTS.md` and the skill grep positive for route-model/fmr.
- No `codex exec` was run and no reset credits were touched. Two host verification receipts (9c238197, eb5d4beb) were recorded as `abandoned` with a note.

## Open items / decisions for Ro
- **Stale Claude copy:** `~/.claude/tools/route-model.sh` (Aug 4) has zero `fmr route`, so Claude sessions outside awesome-harness that call it get the legacy table. The Claude skill's relative `tools/route-model.sh` only resolves inside this repo. Fix: run `./install.sh` (Claude side, which merges settings.json; not run here because it is out of scope).
- **Sandbox receipts are lost.** For a sandboxed route to be logged, either add `~/.local/state/free-model-router` to `sandbox_workspace_write.writable_roots` in `~/.codex/config.toml` (a config change that needs Ro's yes) or rerun the route with escalated permissions.
- Running Claude-family builders from Codex (`claude -p`) needs network, so from a sandboxed Codex session it needs escalation. This is untested live.
- No cross-family audit was run on these diffs. Next step: a codex-audit pass on feffa83 and 66245e6 (Claude-built, so the auditor must be Codex).
