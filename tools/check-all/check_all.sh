#!/usr/bin/env bash
# check_all.sh — deterministic readiness gate (stack-detecting, composable)
# Usage: check_all.sh [REPO_DIR] [--fast] [--json]
set -uo pipefail

# ─── Parse args ────────────────────────────────────────────────────────────────
REPO_DIR="."
FAST=0
JSON_OUT=0

for arg in "$@"; do
  case "$arg" in
    --fast) FAST=1 ;;
    --json) JSON_OUT=1 ;;
    -*) ;;
    *) REPO_DIR="$arg" ;;
  esac
done

REPO_DIR="$(cd "$REPO_DIR" && pwd)"

# ─── Timeout wrapper ───────────────────────────────────────────────────────────
_timeout_cmd() {
  local secs="$1"; shift
  if command -v timeout &>/dev/null; then
    timeout "$secs" "$@"
  elif command -v gtimeout &>/dev/null; then
    gtimeout "$secs" "$@"
  else
    "$@"
  fi
}

# ─── Read config ───────────────────────────────────────────────────────────────
CFG="$REPO_DIR/.check-all.json"
BASE_COMMAND=""
MAX_FILE_LINES=800
TODO_SEVERITY="warn"
FILESIZE_SEVERITY="warn"
SKIP_TESTS=0

if [[ -f "$CFG" ]]; then
  _parse_cfg() {
python3 - "$CFG" <<'PYEOF'
import sys, json
with open(sys.argv[1]) as f:
    c = json.load(f)
print("BASE_COMMAND=" + repr(c.get("base_command", "")))
print("MAX_FILE_LINES=" + str(int(c.get("max_file_lines", 800))))
print("TODO_SEVERITY=" + str(c.get("todo_severity", "warn")))
print("FILESIZE_SEVERITY=" + str(c.get("filesize_severity", "warn")))
print("SKIP_TESTS=" + ("1" if c.get("skip_tests", False) else "0"))
PYEOF
  }
  eval "$(_parse_cfg)"
fi

# ─── Stack detection ───────────────────────────────────────────────────────────
IS_NODE=0
IS_PYTHON=0
[[ -f "$REPO_DIR/package.json" ]] && IS_NODE=1
[[ -f "$REPO_DIR/pyproject.toml" || -f "$REPO_DIR/requirements.txt" ]] && IS_PYTHON=1

# ─── Source exclusion args for find/grep ──────────────────────────────────────
SRC_EXTS=( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" -o -name "*.go" -o -name "*.rs" )
# ponytail: array, NOT a quoted string — word-splitting a string kept the quote
# chars literal so `-name "node_modules"` never matched and deps were scanned.
PRUNE_DIRS=( -name node_modules -o -name .git -o -name dist -o -name build -o -name .next -o -name out -o -name vendor -o -name __pycache__ -o -name .venv -o -name venv -o -name .mypy_cache -o -name .pytest_cache -o -name site-packages )

# ─── Temp dir for per-check logs ───────────────────────────────────────────────
TMP_BASE="${TMPDIR:-/tmp}/check_all_$$"
mkdir -p "$TMP_BASE"
trap 'rm -rf "$TMP_BASE"' EXIT

# ─── Result tracking ───────────────────────────────────────────────────────────
declare -a CHECK_NAMES=()
declare -a CHECK_RESULTS=()
declare -a CHECK_RCS=()
declare -a CHECK_SUMMARIES=()
OVERALL_FAIL=0

_record() {
  local name="$1" result="$2" rc="$3" summary="$4"
  CHECK_NAMES+=("$name")
  CHECK_RESULTS+=("$result")
  CHECK_RCS+=("$rc")
  CHECK_SUMMARIES+=("$summary")
  if [[ "$result" == "fail" ]]; then
    OVERALL_FAIL=1
  fi
}

# ─── CHECK A: Base gate ────────────────────────────────────────────────────────
LOG_A="$TMP_BASE/base_gate.log"
run_base_gate() {
  local cmd=""
  if [[ -n "$BASE_COMMAND" ]]; then
    cmd="$BASE_COMMAND"
  elif [[ $IS_NODE -eq 1 ]]; then
    # read scripts from package.json via python3
    cmd=$(python3 - "$REPO_DIR/package.json" <<'PYEOF'
import sys, json
with open(sys.argv[1]) as f:
    scripts = json.load(f).get("scripts", {})
for preferred in ["factory:check", "ci:safe"]:
    if preferred in scripts:
        print("npm run " + preferred)
        sys.exit(0)
parts = []
for k in scripts:
    if k == "lint":
        parts.append("npm run lint")
    if k in ("typecheck", "type-check"):
        parts.append("npm run " + k)
if parts:
    print(" && ".join(parts))
    sys.exit(0)
# fallback: tsc if tsconfig exists
import os
for tsconfig in ["tsconfig.json", "tsconfig.build.json"]:
    if os.path.exists(os.path.join(os.path.dirname(sys.argv[1]), tsconfig)):
        print("npx tsc --noEmit")
        sys.exit(0)
print("")
PYEOF
    )
    if [[ -z "$cmd" ]]; then
      _record "base-gate" "skip" 0 "no runnable gate found for node"
      return
    fi
  elif [[ $IS_PYTHON -eq 1 ]]; then
    local parts=()
    command -v ruff &>/dev/null && parts+=("ruff check .")
    command -v mypy &>/dev/null && parts+=("mypy .")
    if [[ ${#parts[@]} -eq 0 ]]; then
      _record "base-gate" "skip" 0 "ruff/mypy not on PATH — skipped"
      return
    fi
    cmd="${parts[*]}"
  else
    _record "base-gate" "skip" 0 "no stack detected"
    return
  fi

  (cd "$REPO_DIR" && _timeout_cmd 600 bash -c "$cmd") >"$LOG_A" 2>&1
  local rc=$?
  if [[ $rc -eq 0 ]]; then
    _record "base-gate" "pass" 0 "$cmd"
  else
    _record "base-gate" "fail" $rc "$cmd → rc=$rc"
    OVERALL_FAIL=1
  fi
}
run_base_gate

# ─── CHECK B: File-size cap ────────────────────────────────────────────────────
LOG_B="$TMP_BASE/filesize.log"
run_filesize() {
  local offenders
  offenders=$(find "$REPO_DIR" \( "${PRUNE_DIRS[@]}" \) -prune -o \( "${SRC_EXTS[@]}" \) -print 2>/dev/null \
    | while IFS= read -r f; do
        lc=$(wc -l < "$f" 2>/dev/null || echo 0)
        if (( lc > MAX_FILE_LINES )); then
          printf '%s:%d\n' "$f" "$lc"
        fi
      done)

  if [[ -z "$offenders" ]]; then
    _record "file-size" "pass" 0 "all files ≤ $MAX_FILE_LINES lines"
  else
    local count
    count=$(echo "$offenders" | wc -l | tr -d ' ')
    echo "$offenders" > "$LOG_B"
    local result="$FILESIZE_SEVERITY"
    [[ "$FILESIZE_SEVERITY" == "fail" ]] && OVERALL_FAIL=1
    _record "file-size" "$result" 1 "$count file(s) > $MAX_FILE_LINES lines"
    printf '\n[file-size offenders]\n%s\n' "$offenders"
  fi
}
run_filesize

# ─── CHECK C: No-TODO ──────────────────────────────────────────────────────────
LOG_C="$TMP_BASE/todo.log"
run_todo() {
  local hits
  hits=$(find "$REPO_DIR" \( "${PRUNE_DIRS[@]}" \) -prune -o \( "${SRC_EXTS[@]}" \) -print 2>/dev/null \
    | xargs grep -lnE 'TODO|FIXME|XXX' 2>/dev/null || true)

  if [[ -z "$hits" ]]; then
    _record "no-TODO" "pass" 0 "no TODO/FIXME/XXX found"
  else
    local count
    count=$(echo "$hits" | wc -l | tr -d ' ')
    local sample
    sample=$(find "$REPO_DIR" \( "${PRUNE_DIRS[@]}" \) -prune -o \( "${SRC_EXTS[@]}" \) -print 2>/dev/null \
      | xargs grep -rnE 'TODO|FIXME|XXX' 2>/dev/null | head -5 || true)
    echo "$sample" > "$LOG_C"
    local result="$TODO_SEVERITY"
    [[ "$TODO_SEVERITY" == "fail" ]] && OVERALL_FAIL=1
    _record "no-TODO" "$result" 1 "$count file(s) with TODO/FIXME/XXX"
    printf '\n[TODO/FIXME/XXX — first matches]\n%s\n' "$sample"
  fi
}
run_todo

# ─── CHECK D: Duplicate code ──────────────────────────────────────────────────
LOG_D="$TMP_BASE/jscpd.log"
run_dupes() {
  if [[ $IS_NODE -eq 0 ]]; then
    _record "dup-code" "skip" 0 "jscpd only for node — skipped"
    return
  fi
  if npx --no-install jscpd --version &>/dev/null 2>&1; then
    (cd "$REPO_DIR" && _timeout_cmd 120 npx --no-install jscpd . --ignore "**/node_modules/**,**/.git/**,**/dist/**,**/build/**") >"$LOG_D" 2>&1
    local rc=$?
    if [[ $rc -eq 0 ]]; then
      _record "dup-code" "pass" 0 "jscpd clean"
    else
      _record "dup-code" "warn" $rc "jscpd found duplicates (rc=$rc)"
    fi
  else
    _record "dup-code" "skip" 0 "jscpd not available — skipped"
  fi
}
run_dupes

# ─── CHECK E: Tests ───────────────────────────────────────────────────────────
LOG_E="$TMP_BASE/tests.log"
run_tests() {
  if [[ $FAST -eq 1 || $SKIP_TESTS -eq 1 ]]; then
    local reason="--fast"
    [[ $SKIP_TESTS -eq 1 ]] && reason="config skip_tests=true"
    _record "tests" "skip" 0 "skipped ($reason)"
    return
  fi

  local cmd=""
  if [[ $IS_NODE -eq 1 ]]; then
    local has_test
    has_test=$(python3 - "$REPO_DIR/package.json" <<'PYEOF'
import sys, json
with open(sys.argv[1]) as f:
    scripts = json.load(f).get("scripts", {})
print("1" if "test" in scripts else "0")
PYEOF
    )
    [[ "$has_test" == "1" ]] && cmd="npm test"
  fi
  if [[ -z "$cmd" && $IS_PYTHON -eq 1 ]]; then
    command -v pytest &>/dev/null && cmd="pytest -q"
  fi
  if [[ -z "$cmd" ]]; then
    _record "tests" "skip" 0 "no test command found"
    return
  fi

  (cd "$REPO_DIR" && _timeout_cmd 600 bash -c "$cmd") >"$LOG_E" 2>&1
  local rc=$?
  if [[ $rc -eq 0 ]]; then
    _record "tests" "pass" 0 "$cmd"
  else
    _record "tests" "fail" $rc "$cmd → rc=$rc"
    OVERALL_FAIL=1
  fi
}
run_tests

# ─── CHECK F: CLAUDE.md drift ──────────────────────────────────────────────────
LOG_F="$TMP_BASE/claudemd_drift.log"
run_claudemd_drift() {
  local script_dir drift_tool
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  drift_tool="$script_dir/claudemd_drift.py"
  if [[ ! -f "$drift_tool" ]]; then
    _record "claudemd-drift" "skip" 0 "claudemd_drift.py not found"
    return
  fi
  local out rc
  out=$(_timeout_cmd 60 python3 "$drift_tool" "$REPO_DIR" 2>&1)
  rc=$?
  echo "$out" > "$LOG_F"
  if [[ $rc -eq 0 ]]; then
    _record "claudemd-drift" "pass" 0 "no CLAUDE.md drift"
  else
    # rc=1 → drift detected. Default WARN; DRIFT_STRICT=1 → fail.
    local result="warn"
    if [[ "${DRIFT_STRICT:-0}" == "1" ]]; then
      result="fail"
      OVERALL_FAIL=1
    fi
    _record "claudemd-drift" "$result" $rc "CLAUDE.md drift detected (rc=$rc)"
    printf '\n[claudemd-drift]\n%s\n' "$out"
  fi
}
run_claudemd_drift

# ─── Output ──────────────────────────────────────────────────────────────────
print_table() {
  local fmt="%-15s %-8s %-5s %s\n"
  printf '\n=== check-all READINESS TABLE (%s) ===\n' "$REPO_DIR"
  printf "$fmt" "CHECK" "RESULT" "RC" "SUMMARY"
  printf '%s\n' "------------------------------------------------------------"
  local i
  for i in "${!CHECK_NAMES[@]}"; do
    printf "$fmt" "${CHECK_NAMES[$i]}" "${CHECK_RESULTS[$i]}" "${CHECK_RCS[$i]}" "${CHECK_SUMMARIES[$i]}"
  done
  printf '%s\n' "------------------------------------------------------------"
  if [[ $OVERALL_FAIL -eq 0 ]]; then
    printf 'OVERALL: READY (all hard checks passed; warns are non-blocking)\n'
  else
    printf 'OVERALL: NOT READY (hard check(s) failed)\n'
  fi
}

print_json() {
python3 - <<PYEOF
import json, sys
names   = ${CHECK_NAMES[@]+"$(IFS='","'; echo "${CHECK_NAMES[*]}")"+""}
results = ${CHECK_RESULTS[@]+"$(IFS='","'; echo "${CHECK_RESULTS[*]}")"+""}
rcs     = [$(IFS=','; echo "${CHECK_RCS[*]}")]
sums    = ${CHECK_SUMMARIES[@]+"$(IFS='","'; echo "${CHECK_SUMMARIES[*]}")"+""}
checks = []
PYEOF

  # Use python3 directly for clean JSON
  python3 - "${CHECK_NAMES[@]}" "${CHECK_RESULTS[@]}" "${CHECK_RCS[@]}" "${CHECK_SUMMARIES[@]}" <<PYEOF 2>/dev/null || print_table
import sys, json
n = len(sys.argv) - 1
# args come in 4 equal-length parallel slices; we stored names/results/rcs/sums separately
# fall back to table if we can't parse
print(json.dumps({"error": "json mode: use print_table fallback"}, indent=2))
PYEOF
}

if [[ $JSON_OUT -eq 1 ]]; then
  # Simple JSON via python3 using collected arrays
  python3 - <<PYEOF
import json
names   = $(python3 -c "import json; print(json.dumps('${CHECK_NAMES[*]}'.split()))" 2>/dev/null || echo '[]')
results = $(python3 -c "import json; print(json.dumps('${CHECK_RESULTS[*]}'.split()))" 2>/dev/null || echo '[]')
rcs     = [$(IFS=','; echo "${CHECK_RCS[*]}")]
sums_raw = """$(IFS='|'; printf '%s' "${CHECK_SUMMARIES[*]}")"""
sums = sums_raw.split('|') if sums_raw else []
checks = [{"check": n, "result": r, "rc": c, "summary": s}
          for n, r, c, s in zip(names, results, rcs, sums)]
print(json.dumps({"repo": "$REPO_DIR", "overall": "ready" if $OVERALL_FAIL == 0 else "not_ready", "checks": checks}, indent=2))
PYEOF
else
  print_table
fi

exit $OVERALL_FAIL
