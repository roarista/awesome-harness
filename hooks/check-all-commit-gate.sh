#!/usr/bin/env bash
# PreToolUse(Bash) gate: when a `git commit` is about to run, run check_all.sh --fast
# and BLOCK the commit (exit 2) on failure. Dormant unless the repo opts in with a
# .check-all.json marker — so live repos stay ungated until I stage their wiring.
# ponytail: opt-in marker = no global blast radius; commit-time only = CPU-safe.
set -euo pipefail

# --- staleness notice ---------------------------------------------------------
# Was check-all run since the newest source edit in this repo? Compares the last
# PASSING check-all.jsonl stamp (written by check_all.sh) against phantom-edit.jsonl,
# which already timestamps every Edit/Write. WARN only, never blocks, fail-open.
# BLIND SPOT (known, not fixed): phantom-edit.jsonl only records Write/Edit/MultiEdit;
# Bash-scripted writes (python3 - <<EOF, sed -i, git apply) produce no rows, so this
# notice is silent for exactly the builders who routed around the Edit gate.
# ponytail: warn not block - phantom-edit.jsonl is advisory bookkeeping, and a repo
# that never opted into .check-all.json should not become uncommittable.
stale_notice() {  # $1 = repo root
  ST="${HOOK_STATE_DIR:-$HOME/.claude/hooks/state}" ROOT="$1" python3 - <<'PYEND' 2>/dev/null || true
import json, os
st, root = os.environ["ST"], os.environ["ROOT"].rstrip("/")
SRC = (".py", ".sh", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb",
       ".java", ".c", ".h", ".cpp", ".sql")

def last(name, keep):
    best = ""
    try:
        with open(os.path.join(st, name)) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if keep(r):
                    best = max(best, r.get("ts", ""))
    except Exception:
        return None
    return best

edit = last("phantom-edit.jsonl",
            lambda r: str(r.get("file", "")).startswith(root + "/")
            and str(r.get("file", "")).endswith(SRC))
# ok is required: a check-all that FAILED must not silence the notice. Rows written
# before the `ok` field existed have no ok key and are ignored (treated as unknown).
run = last("check-all.jsonl",
           lambda r: str(r.get("root", "")).rstrip("/") == root
           and r.get("ok") is True)
if not edit or (run and run >= edit):
    raise SystemExit(0)
msg = ("CHECK-ALL NOT RUN: source here was edited at %s and check-all has %s. "
       "THE PROCEDURE step VERIFY is incomplete without it. Run:\n"
       "  ~/.claude/tools/check-all/check_all.sh %s\n"
       % (edit, ("not run since (last run %s)" % run) if run else "never run here",
          root))
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                         "additionalContext": msg}}))
PYEND
}

if [ "${1:-}" = "--selftest" ]; then
  d="$(mktemp -d)"; export HOOK_STATE_DIR="$d"
  printf '{"ts": "2026-01-02T00:00:00", "file": "/r/a.py"}\n' > "$d/phantom-edit.jsonl"
  printf '{"ts": "2026-01-01T00:00:00", "root": "/r", "ok": true}\n' > "$d/check-all.jsonl"
  out="$(stale_notice /r)"
  case "$out" in
    *"CHECK-ALL NOT RUN"*) echo "ok: edit newer than check-all -> warns" ;;
    *) echo "FAIL: expected warning, got: $out"; exit 1 ;;
  esac
  printf '{"ts": "2026-01-03T00:00:00", "root": "/r", "ok": false}\n' >> "$d/check-all.jsonl"
  out="$(stale_notice /r)"
  case "$out" in
    *"CHECK-ALL NOT RUN"*) echo "ok: FAILING check-all does not silence the warning" ;;
    *) echo "FAIL: expected warning for ok:false, got: $out"; exit 1 ;;
  esac
  printf '{"ts": "2026-01-04T00:00:00", "root": "/r", "ok": true}\n' >> "$d/check-all.jsonl"
  out="$(stale_notice /r)"
  [ -z "$out" ] && echo "ok: passing check-all newer than edit -> silent" \
    || { echo "FAIL: expected silence, got: $out"; exit 1; }
  out="$(stale_notice /other)"
  [ -z "$out" ] && echo "ok: unrelated repo -> silent" || { echo "FAIL: $out"; exit 1; }
  out="$(HOOK_STATE_DIR=/nonexistent stale_notice /r)"
  [ -z "$out" ] && echo "ok: missing state -> fail-open silent" || { echo "FAIL: $out"; exit 1; }
  rm -rf "$d"; echo "ok"; exit 0
fi

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
[ -n "$root" ] || exit 0
if [ ! -f "$root/.check-all.json" ]; then       # not opted into blocking → warn only
  stale_notice "$root"
  exit 0
fi

if ! ~/.claude/tools/check-all/check_all.sh "$root" --fast >/tmp/checkall_gate.$$.log 2>&1; then
  echo "check-all gate FAILED — commit blocked. See /tmp/checkall_gate.$$.log . Bypass: add --no-verify." >&2
  exit 2
fi
stale_notice "$root"
exit 0
