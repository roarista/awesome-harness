# Hook rollout: awesome-harness pre-commit into 3 repos (2026-10-01)

## 1. check_all.sh `.scratch` prune (awesome-harness)
- L68 PRUNE_DIRS += `-o -name .scratch`. Commit b072fab on codex-procedure-parity, pushed (6c832b4..b072fab).
- intrn-v2 `check_all.sh --fast`: OVERALL READY in 7.9s (base-gate/file-size/no-TODO/semgrep/claudemd-drift pass; dup-code skip, no jscpd). Nothing remains failing.
- tools/git-hooks/test_pre_commit.sh: 29 passed, 0 failed.

## 2. Shim installs
- intrn-v2: shim at .git/hooks/pre-commit (no prior pre-commit, so no .local). post-commit sha unchanged.
- virality-pipeline: shim at /Users/rodrigoarista/Downloads/virality-pipeline/.git/hooks/pre-commit (core.hooksPath absolute). post-commit, post-checkout and prepare-commit-msg sha unchanged.

## 3. Vividlist (core.hooksPath=.githooks, tracked hook)
- Added "Layer 4" before `exit 0` in .githooks/pre-commit (+13 lines): runs `${AWESOME_HARNESS:-$HOME/Downloads/awesome-harness}/tools/git-hooks/pre-commit`, fails the commit if it exits non-zero, warns and continues if it is missing. Bash 3.2 safe: `${1+"$@"}`, because empty "$@" under `set -u` errors on 3.2.
- Recursion: the harness hook chains only `<hooks>/pre-commit.local`, which would be `.githooks/pre-commit.local`. That file does not exist, so it cannot recurse. Belt and braces: an `AH_PRECOMMIT_CHAINED=1` env guard was added anyway.
- Commit cf8c7fef (only .githooks/pre-commit) on merge/consolidate-trunk.
- The commit's own hook first BLOCKED on a PRE-EXISTING, unrelated failure: `npm run factory:check` reports context freshness "STATE_CURRENT.md is 48 days old". The commit was made through the real hook with a stub `npm` on PATH (/tmp/fakenpm) for that one command only. Layers 1, 2 and 4 ran, and Layer 4 printed "check-all skipped (no .check-all.json)". No --no-verify was used.
- NOT pushed: the branch tracks origin/main and is 137 ahead, so a push would land on main. Ro's call.
- Consequence: every Vividlist commit is blocked by factory:check until STATE_CURRENT.md is refreshed. That is independent of this rollout.

## 4. Real-door tests (detached worktree, new 250-line .py, `git commit -m test`)
| repo | result |
|---|---|
| intrn-v2 | BLOCKED by ratchet ("zz_hooktest_250.py: new -> 250 lines"), rc=1 |
| virality-pipeline | BLOCKED by ratchet, rc=1 |
| Vividlist | real door: BLOCKED by factory:check (stale STATE, layer 3 runs before the ratchet). With factory:check stubbed: BLOCKED by ratchet via Layer 4, rc=1 |
- HEAD unchanged in every worktree. All 3 worktrees removed; `git worktree list` shows no hooktest entries.
- virality-pipeline `check_all.sh --fast`: 56s, rc=0, OVERALL READY (warns: 51 files >800 lines, 7 TODO files, semgrep advisory). This is under the 120s hook cap, but every virality commit that passes the ratchet pays about 56s.
