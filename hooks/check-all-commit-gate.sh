#!/usr/bin/env bash
# PreToolUse(Bash) gate: when a `git commit` is about to run, run check_all.sh --fast
# and BLOCK the commit (exit 2) on failure. Dormant unless the repo opts in with a
# .check-all.json marker — so live repos stay ungated until I stage their wiring.
# ponytail: opt-in marker = no global blast radius; commit-time only = CPU-safe.
set -euo pipefail
[ "${1:-}" = "--selftest" ] && { echo "ok"; exit 0; }

inp="$(cat)"
cmd="$(printf '%s' "$inp" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null || true)"
cwd="$(printf '%s' "$inp" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("cwd","") or ".")' 2>/dev/null || echo .)"

# only care about real commits, and let escape hatches through
case "$cmd" in
  *"git commit"*) : ;;
  *) exit 0 ;;
esac
case "$cmd" in *"--no-verify"*) exit 0 ;; esac

root="$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$root" ] && [ -f "$root/.check-all.json" ] || exit 0   # not opted in → silent pass

if ! ~/.claude/tools/check-all/check_all.sh "$root" --fast >/tmp/checkall_gate.$$.log 2>&1; then
  echo "check-all gate FAILED — commit blocked. See /tmp/checkall_gate.$$.log . Bypass: add --no-verify." >&2
  exit 2
fi
exit 0
