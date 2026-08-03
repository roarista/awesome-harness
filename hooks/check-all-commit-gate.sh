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

TAIL = 512 * 1024   # ponytail: these JSONLs grow without bound and are read on EVERY
                    # Bash call. Only the newest 512 KB matters for "latest ts";
                    # upgrade path = rotate the jsonl instead of growing the window.

def tail_lines(path):
    with open(path, errors="replace") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - TAIL))
        if size > TAIL:
            f.readline()          # drop the partial first line
        return f.readlines()

def last(name, keep):
    best = ""
    try:
        for line in tail_lines(os.path.join(st, name)):
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

# --- uncommitted-work notice --------------------------------------------------
# "Commit after every unit" only happens if it is VISIBLE. Before any Bash command,
# if the OLDEST still-uncommitted source edit in this repo is older than the
# threshold (GIT_UNCOMMITTED_WARN_MIN, default 45 min), say so and name the command.
# WARN only, never blocks, fail-open on every error path. Warns at most once per
# GIT_UNCOMMITTED_COOLDOWN_MIN (default 60) per repo — a notice on all 200 Bash calls
# of a session is noise, not a nudge.
# SAME BLIND SPOT as stale_notice: phantom-edit.jsonl records only Write/Edit/MultiEdit,
# so Bash-scripted writes (sed -i, python3 - <<EOF, git apply) produce NO rows and this
# notice stays silent for them. Not fixed here; do not read silence as "all committed".
uncommitted_notice() {  # $1 = repo root
  ST="${HOOK_STATE_DIR:-$HOME/.claude/hooks/state}"
  COOL="${GIT_UNCOMMITTED_COOLDOWN_MIN:-60}"
  # Cooldown FIRST and in pure shell: the suppressed path is the common one, so it must
  # not pay for a python start-up on every Bash call.
  stamp="$ST/uncommitted-warn${1//\//_}"
  if [ "$COOL" != "0" ] && [ -n "$(find "$stamp" -mmin "-$COOL" 2>/dev/null)" ]; then return 0; fi
  out="$(ST="$ST" ROOT="$1" MINS="${GIT_UNCOMMITTED_WARN_MIN:-45}" \
  python3 - <<'PYEND' 2>/dev/null
import json, os, datetime, subprocess
st, root = os.environ["ST"], os.environ["ROOT"].rstrip("/")
try:
    mins = float(os.environ.get("MINS") or 45)
except Exception:
    mins = 45.0
SRC = (".py", ".sh", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb",
       ".java", ".c", ".h", ".cpp", ".sql", ".md")
# -z + split on NUL: `awk '{print $NF}'` mangles paths containing spaces, so those
# files never matched and the notice silently under-warned on exactly them.
try:
    out = subprocess.run(["git", "-C", root, "status", "--porcelain", "-z",
                          "--no-renames"], capture_output=True, timeout=10).stdout
except Exception:
    raise SystemExit(0)
dirty = {os.path.join(root, e[3:]) for e in out.decode("utf-8", "replace").split("\0")
         if len(e) > 3}
if not dirty:
    raise SystemExit(0)

TAIL = 512 * 1024   # ponytail: bounded read, same reason as stale_notice. An edit
                    # older than the newest 512 KB of rows is not reported.
oldest = None
try:
    with open(os.path.join(st, "phantom-edit.jsonl"), errors="replace") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - TAIL))
        if size > TAIL:
            f.readline()
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            fp = str(r.get("file", ""))
            if not fp.startswith(root + "/") or not fp.endswith(SRC):
                continue
            if fp not in dirty:      # already committed -> not our problem
                continue
            ts = r.get("ts", "")
            if ts and (oldest is None or ts < oldest):
                oldest = ts
except Exception:
    raise SystemExit(0)
if not oldest:
    raise SystemExit(0)
try:
    age = (datetime.datetime.now() - datetime.datetime.fromisoformat(oldest)).total_seconds() / 60.0
except Exception:
    raise SystemExit(0)
if age < mins:
    raise SystemExit(0)
msg = ("UNCOMMITTED FOR %d MIN: oldest uncommitted source edit here is from %s. "
       "THE PROCEDURE step PERSIST says commit after each completed unit, and another "
       "terminal may be working in this repo. Run:\n"
       "  bash %s/tools/git-sync.sh -m \"<what you finished>\"\n"
       "(fetches + rebases before pushing; never forces, never resets.)\n"
       % (age, oldest, root))
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                         "additionalContext": msg}}))
PYEND
)" || true
  [ -n "$out" ] || return 0
  mkdir -p "$ST" 2>/dev/null; : > "$stamp" 2>/dev/null || true   # arm the cooldown
  printf '%s\n' "$out"
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

  # --- uncommitted_notice cases ---
  export GIT_UNCOMMITTED_COOLDOWN_MIN=0        # cooldown gets its own case below
  r2="$(mktemp -d)"; git -C "$r2" init -q; r2="$(cd "$r2" && pwd -P)"
  printf 'x\n' > "$r2/w.py"
  old="$(python3 -c 'import datetime;print((datetime.datetime.now()-datetime.timedelta(minutes=90)).isoformat())')"
  printf '{"ts": "%s", "file": "%s/w.py"}\n' "$old" "$r2" > "$d/phantom-edit.jsonl"
  out="$(uncommitted_notice "$r2")"
  case "$out" in
    *"UNCOMMITTED FOR"*git-sync*) echo "ok: 90-min-old uncommitted edit -> warns + names git-sync" ;;
    *) echo "FAIL: expected uncommitted warning, got: $out"; exit 1 ;;
  esac
  out="$(GIT_UNCOMMITTED_WARN_MIN=999 uncommitted_notice "$r2")"
  [ -z "$out" ] && echo "ok: threshold env respected -> silent" || { echo "FAIL: $out"; exit 1; }
  git -C "$r2" add -A >/dev/null 2>&1
  git -C "$r2" -c user.email=t@t -c user.name=t commit -qm x >/dev/null 2>&1
  out="$(uncommitted_notice "$r2")"
  [ -z "$out" ] && echo "ok: once committed -> silent" || { echo "FAIL: $out"; exit 1; }
  out="$(HOOK_STATE_DIR=/nonexistent uncommitted_notice "$r2")"
  [ -z "$out" ] && echo "ok: missing state -> fail-open silent" || { echo "FAIL: $out"; exit 1; }
  out="$(uncommitted_notice /definitely/not/a/repo)"
  [ -z "$out" ] && echo "ok: non-repo -> fail-open silent" || { echo "FAIL: $out"; exit 1; }

  # paths with spaces must still match (awk '{print $NF}' used to mangle them)
  printf 'x\n' > "$r2/a b.py"
  printf '{"ts": "%s", "file": "%s/a b.py"}\n' "$old" "$r2" > "$d/phantom-edit.jsonl"
  out="$(uncommitted_notice "$r2")"
  case "$out" in
    *"UNCOMMITTED FOR"*) echo "ok: dirty path with a space -> warns" ;;
    *) echo "FAIL: expected warning for 'a b.py', got: $out"; exit 1 ;;
  esac

  # cooldown: with a real cooldown, only the FIRST of several calls may speak
  rm -f "$d"/uncommitted-warn*
  n=0
  for _ in 1 2 3; do
    [ -n "$(GIT_UNCOMMITTED_COOLDOWN_MIN=60 uncommitted_notice "$r2")" ] && n=$((n+1))
  done
  [ "$n" = 1 ] && echo "ok: cooldown -> exactly 1 of 3 calls warned" \
    || { echo "FAIL: cooldown let $n of 3 calls warn"; exit 1; }
  unset GIT_UNCOMMITTED_COOLDOWN_MIN
  rm -rf "$r2"
  rm -rf "$d"; echo "ok"; exit 0
fi

# One python start, not two: this runs before EVERY Bash call.
parsed="$(python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
print(d.get("cwd","") or ".")
print(d.get("tool_input",{}).get("command","").replace("\n"," "))' 2>/dev/null || printf '.\n')"
cwd="${parsed%%$'\n'*}"
cmd="${parsed#*$'\n'}"
[ "$cmd" = "$cwd" ] && cmd=""

# only care about real commits, and let escape hatches through
case "$cmd" in
  *"git commit"*) : ;;
  *)
    root="$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || true)"
    [ -n "$root" ] && uncommitted_notice "$root"
    exit 0 ;;
esac
case "$cmd" in
  *"--no-verify"*) exit 0 ;;
esac

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
